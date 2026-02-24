#!/usr/bin/env python3
"""Core module: import memory JSONL into memory objects storage (v0.1)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from schema_runtime import SchemaValidationError, validate_payload  # type: ignore  # noqa: E402

DEFAULT_DB = ROOT / "data" / "mindkernel_v0_1.sqlite"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS memory_items (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            payload_sha1 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            correlation_id TEXT,
            timestamp TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS memory_import_runs (
            run_id TEXT PRIMARY KEY,
            input_path TEXT NOT NULL,
            mode TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            summary_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_memory_items_status ON memory_items(status);
        CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_memory_import_runs_started ON memory_import_runs(started_at DESC);
        """
    )
    c.commit()


def _sha1_json(payload: dict) -> str:
    canon = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()


def write_audit_event(
    c: sqlite3.Connection,
    *,
    actor_id: str,
    object_id: str,
    before: dict,
    after: dict,
    reason: str,
    evidence_refs: list[str],
    correlation_id: str,
):
    ts = now_iso()
    event_id = f"aud_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": event_id,
        "event_type": "state_transition",
        "actor": {"type": "worker", "id": actor_id},
        "object_type": "memory",
        "object_id": object_id,
        "before": before,
        "after": after,
        "reason": reason,
        "evidence_refs": evidence_refs or [object_id],
        "timestamp": ts,
        "correlation_id": correlation_id,
    }

    try:
        validate_payload("audit-event.schema.json", payload)
    except SchemaValidationError as e:
        raise ValueError(f"audit event schema validation failed: {e}") from e

    c.execute(
        """
        INSERT INTO audit_events(id, event_type, object_type, object_id, correlation_id, timestamp, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            payload["event_type"],
            payload["object_type"],
            object_id,
            correlation_id,
            ts,
            json.dumps(payload, ensure_ascii=False),
        ),
    )


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            raise ValueError(f"invalid JSONL at line {idx}: {e}") from e
        if not isinstance(obj, dict):
            raise ValueError(f"JSONL line {idx} must be object")
        rows.append(obj)
    return rows


def import_memory_rows(
    c: sqlite3.Connection,
    *,
    rows: list[dict],
    input_path: str,
    mode: str = "upsert",
    actor_id: str = "memory-importer-v0.1",
    strict: bool = False,
) -> dict:
    if mode not in {"upsert", "insert-only"}:
        raise ValueError("mode must be upsert|insert-only")

    run_id = f"imr_{uuid.uuid4().hex[:12]}"
    started = now_iso()
    c.execute(
        "INSERT INTO memory_import_runs(run_id, input_path, mode, actor_id, started_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, input_path, mode, actor_id, started),
    )
    c.commit()

    inserted = 0
    updated = 0
    skipped_noop = 0
    failed = 0
    errors: list[dict] = []

    for idx, payload in enumerate(rows, start=1):
        mid = str(payload.get("id") or "")
        try:
            validate_payload("memory.schema.json", payload)
            mid = payload["id"]
            sha = _sha1_json(payload)
            status = str(payload["status"])
            t = now_iso()

            row = c.execute("SELECT status, payload_json, payload_sha1 FROM memory_items WHERE id=?", (mid,)).fetchone()
            if not row:
                c.execute(
                    """
                    INSERT INTO memory_items(id, status, payload_json, payload_sha1, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (mid, status, json.dumps(payload, ensure_ascii=False), sha, t, t),
                )
                write_audit_event(
                    c,
                    actor_id=actor_id,
                    object_id=mid,
                    before={"status": None},
                    after={"status": status},
                    reason="memory imported (insert)",
                    evidence_refs=payload.get("evidence_refs", []),
                    correlation_id=run_id,
                )
                inserted += 1
                continue

            old_sha = str(row["payload_sha1"])
            old_status = str(row["status"])

            if old_sha == sha:
                skipped_noop += 1
                continue

            if mode == "insert-only":
                raise ValueError(f"memory id already exists with different payload: {mid}")

            c.execute(
                "UPDATE memory_items SET status=?, payload_json=?, payload_sha1=?, updated_at=? WHERE id=?",
                (status, json.dumps(payload, ensure_ascii=False), sha, t, mid),
            )
            write_audit_event(
                c,
                actor_id=actor_id,
                object_id=mid,
                before={"status": old_status},
                after={"status": status},
                reason="memory imported (upsert update)",
                evidence_refs=payload.get("evidence_refs", []),
                correlation_id=run_id,
            )
            updated += 1

        except Exception as e:
            failed += 1
            errors.append({"line": idx, "id": mid, "error": str(e)})
            if strict:
                c.rollback()
                raise
            continue

    summary = {
        "ok": failed == 0,
        "run_id": run_id,
        "input_path": input_path,
        "mode": mode,
        "total": len(rows),
        "inserted": inserted,
        "updated": updated,
        "skipped_noop": skipped_noop,
        "failed": failed,
        "errors": errors,
        "started_at": started,
        "finished_at": now_iso(),
    }

    c.execute(
        "UPDATE memory_import_runs SET finished_at=?, summary_json=? WHERE run_id=?",
        (summary["finished_at"], json.dumps(summary, ensure_ascii=False), run_id),
    )
    c.commit()
    return summary


def import_memory_jsonl(
    c: sqlite3.Connection,
    *,
    input_file: Path,
    mode: str = "upsert",
    actor_id: str = "memory-importer-v0.1",
    strict: bool = False,
) -> dict:
    rows = load_jsonl(input_file)
    return import_memory_rows(
        c,
        rows=rows,
        input_path=str(input_file),
        mode=mode,
        actor_id=actor_id,
        strict=strict,
    )
