#!/usr/bin/env python3
"""
MindKernel v0.1 Cognition -> DecisionTrace prototype.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from schema_runtime import SchemaValidationError, validate_payload

DEFAULT_DB = ROOT / "data" / "mindkernel_v0_1.sqlite"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def in_days_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS cognition_rules (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decision_traces (
            id TEXT PRIMARY KEY,
            final_outcome TEXT NOT NULL,
            payload_json TEXT NOT NULL,
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

        CREATE INDEX IF NOT EXISTS idx_cognition_rules_status ON cognition_rules(status);
        CREATE INDEX IF NOT EXISTS idx_decision_traces_outcome ON decision_traces(final_outcome);
        CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events(timestamp DESC);
        """
    )
    c.commit()


def write_audit_event(
    c: sqlite3.Connection,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    object_type: str,
    object_id: str,
    before: dict,
    after: dict,
    reason: str,
    evidence_refs: list[str],
    correlation_id: str | None = None,
    metadata: dict | None = None,
):
    ts = now_iso()
    event_id = f"aud_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": event_id,
        "event_type": event_type,
        "actor": {"type": actor_type, "id": actor_id},
        "object_type": object_type,
        "object_id": object_id,
        "before": before,
        "after": after,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "timestamp": ts,
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id
    if metadata:
        payload["metadata"] = metadata

    try:
        validate_payload("audit-event.schema.json", payload)
    except SchemaValidationError as e:
        raise ValueError(f"audit event schema validation failed: {e}") from e

    c.execute(
        """
        INSERT INTO audit_events(id, event_type, object_type, object_id, correlation_id, timestamp, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, event_type, object_type, object_id, correlation_id, ts, json.dumps(payload, ensure_ascii=False)),
    )


def _extract_payload(file_path: Path, key: str) -> dict:
    data = json.loads(file_path.read_text())
    if isinstance(data, dict) and key in data and isinstance(data[key], dict):
        return data[key]
    if isinstance(data, dict):
        return data
    raise ValueError(f"{key} input must be a JSON object or scenario containing `{key}`")


def ingest_cognition(c: sqlite3.Connection, cognition_payload: dict, actor_id: str = "mk-cd-pipeline") -> dict:
    validate_payload("cognition.schema.json", cognition_payload)

    cid = cognition_payload["id"]
    status = cognition_payload["status"]
    now = now_iso()

    exists = c.execute("SELECT 1 FROM cognition_rules WHERE id=?", (cid,)).fetchone()
    if exists:
        raise ValueError(f"cognition already exists: {cid}")

    c.execute(
        "INSERT INTO cognition_rules(id, status, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (cid, status, json.dumps(cognition_payload, ensure_ascii=False), now, now),
    )

    write_audit_event(
        c,
        event_type="state_transition",
        actor_type="system",
        actor_id=actor_id,
        object_type="cognition",
        object_id=cid,
        before={"status": None},
        after={"status": status, "epistemic_state": cognition_payload.get("epistemic_state")},
        reason="Cognition ingested into decision pipeline.",
        evidence_refs=cognition_payload.get("evidence_refs", []),
    )

    c.commit()
    return {"cognition_id": cid, "status": status}


def _decide(cognition_payload: dict, risk_tier: str | None = None):
    epistemic_state = cognition_payload["epistemic_state"]
    # "derived" 是从 experience 晋升来的认知，视同 supported
    if epistemic_state == "derived":
        epistemic_state = "supported"
    rt = risk_tier or cognition_payload.get("risk_tier", "medium")
    impact = cognition_payload.get("impact_tier", "medium")

    gates = {
        "persona_conflict_gate": "pass",
        "social_gate": "pass",
        "risk_gate": "pass",
        "cognition_gate": "pass",
    }

    unknown_type = cognition_payload.get("unknown_type")
    reason = ""

    if epistemic_state == "refuted":
        decision_mode = "abstain"
        final_outcome = "abstained"
        gates["risk_gate"] = "block"
        gates["cognition_gate"] = "block"
        gates["social_gate"] = "defer"
        reason = "Refuted cognition cannot drive decisions."

    elif epistemic_state == "uncertain":
        gates["cognition_gate"] = "degrade"
        if rt == "high":
            decision_mode = "escalate"
            final_outcome = "escalated"
            gates["risk_gate"] = "block"
            gates["social_gate"] = "defer"
            reason = "High-risk request with uncertain cognition requires escalation."
        elif rt == "medium":
            decision_mode = "conservative"
            final_outcome = "limited"
            gates["risk_gate"] = "limit"
            gates["social_gate"] = "defer"
            reason = "Medium-risk request with uncertain cognition is limited to conservative mode."
        else:
            decision_mode = cognition_payload.get("decision_mode_if_uncertain", "explore")
            if decision_mode not in {"explore", "conservative", "abstain", "escalate"}:
                decision_mode = "explore"
            final_outcome = "limited"
            reason = "Low-risk uncertain cognition allows bounded execution."

    else:  # supported
        if rt == "high":
            decision_mode = "conservative"
            final_outcome = "limited"
            gates["risk_gate"] = "limit"
            gates["social_gate"] = "defer"
            reason = "High-risk execution remains bounded even with supported cognition."
        else:
            decision_mode = "normal"
            final_outcome = "executed"
            reason = "Supported cognition allows normal execution."

    return {
        "risk_tier": rt,
        "impact_tier": impact,
        "decision_mode": decision_mode,
        "epistemic_state": epistemic_state,
        "unknown_type": unknown_type,
        "gates": gates,
        "final_outcome": final_outcome,
        "reason": reason,
    }


def cognition_to_decision(
    c: sqlite3.Connection,
    cognition_id: str,
    request_ref: str,
    risk_tier: str | None = None,
    actor_id: str = "mk-cd-pipeline",
):
    row = c.execute("SELECT payload_json FROM cognition_rules WHERE id=?", (cognition_id,)).fetchone()
    if not row:
        raise ValueError(f"cognition not found: {cognition_id}")

    cognition_payload = json.loads(row["payload_json"])

    # 幂等去重：检查是否已有该 cognition 的 decision trace
    existing_rows = c.execute(
        "SELECT id, final_outcome, payload_json FROM decision_traces WHERE payload_json LIKE ?",
        (f'%"{cognition_id}"%',),
    ).fetchall()
    if existing_rows:
        existing = existing_rows[0]
        existing_payload = json.loads(existing["payload_json"])
        return {
            "cognition_id": cognition_id,
            "decision_trace_id": existing["id"],
            "decision_id": existing_payload.get("decision_id"),
            "risk_tier": existing_payload.get("risk_tier"),
            "decision_mode": existing_payload.get("decision_mode"),
            "final_outcome": existing["final_outcome"],
            "duplicate": True,
        }

    decision = _decide(cognition_payload, risk_tier)

    dt_id = f"dt_{uuid.uuid4().hex[:12]}"
    dec_id = f"dec_{uuid.uuid4().hex[:12]}"

    payload = {
        "id": dt_id,
        "decision_id": dec_id,
        "request_ref": request_ref,
        "risk_tier": decision["risk_tier"],
        "impact_tier": decision["impact_tier"],
        "decision_mode": decision["decision_mode"],
        "epistemic_state": decision["epistemic_state"],
        "inputs": {
            "cognition_refs": [cognition_id],
        },
        "gates": decision["gates"],
        "reason": decision["reason"],
        "evidence_refs": [cognition_id],
        "final_outcome": decision["final_outcome"],
        "review_due_at": cognition_payload.get("review_due_at", in_days_iso(7)),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    if decision["epistemic_state"] == "uncertain":
        payload["unknown_type"] = decision.get("unknown_type") or "multipath"

    validate_payload("decision-trace.schema.json", payload)

    c.execute(
        "INSERT INTO decision_traces(id, final_outcome, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (dt_id, payload["final_outcome"], json.dumps(payload, ensure_ascii=False), now_iso(), now_iso()),
    )

    write_audit_event(
        c,
        event_type="decision_gate",
        actor_type="system",
        actor_id=actor_id,
        object_type="decision",
        object_id=dec_id,
        before={"gate": "pending"},
        after={
            "risk_gate": payload["gates"]["risk_gate"],
            "cognition_gate": payload["gates"]["cognition_gate"],
            "final_outcome": payload["final_outcome"],
        },
        reason=payload["reason"],
        evidence_refs=[cognition_id],
        metadata={"decision_trace_id": dt_id},
    )

    c.commit()
    return {
        "cognition_id": cognition_id,
        "decision_trace_id": dt_id,
        "decision_id": dec_id,
        "risk_tier": payload["risk_tier"],
        "decision_mode": payload["decision_mode"],
        "final_outcome": payload["final_outcome"],
    }


def gate_block_to_decision(
    c: sqlite3.Connection,
    *,
    experience_id: str,
    persona_id: str,
    request_ref: str,
    boundary_hits: list[str] | None = None,
    risk_tier: str = "high",
    actor_id: str = "mk-cd-pipeline",
):
    dt_id = f"dt_{uuid.uuid4().hex[:12]}"
    dec_id = f"dec_{uuid.uuid4().hex[:12]}"

    payload = {
        "id": dt_id,
        "decision_id": dec_id,
        "request_ref": request_ref,
        "risk_tier": risk_tier,
        "impact_tier": "high",
        "decision_mode": "abstain",
        "epistemic_state": "uncertain",
        "unknown_type": "out_of_scope",
        "inputs": {
            "experience_refs": [experience_id],
            "persona_refs": [persona_id],
        },
        "gates": {
            "persona_conflict_gate": "block",
            "social_gate": "defer",
            "risk_gate": "block",
            "cognition_gate": "block",
        },
        "reason": "Persona gate blocked cognition promotion; decision blocked by policy boundary.",
        "evidence_refs": [experience_id],
        "final_outcome": "blocked",
        "review_due_at": in_days_iso(7),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    validate_payload("decision-trace.schema.json", payload)

    c.execute(
        "INSERT INTO decision_traces(id, final_outcome, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (dt_id, payload["final_outcome"], json.dumps(payload, ensure_ascii=False), now_iso(), now_iso()),
    )

    write_audit_event(
        c,
        event_type="decision_gate",
        actor_type="system",
        actor_id=actor_id,
        object_type="decision",
        object_id=dec_id,
        before={"gate": "pending"},
        after={
            "persona_conflict_gate": "block",
            "risk_gate": "block",
            "cognition_gate": "block",
            "final_outcome": "blocked",
        },
        reason=payload["reason"],
        evidence_refs=[experience_id],
        metadata={
            "decision_trace_id": dt_id,
            "persona_id": persona_id,
            "boundary_hits": boundary_hits or [],
        },
    )

    c.commit()
    return {
        "decision_trace_id": dt_id,
        "decision_id": dec_id,
        "risk_tier": payload["risk_tier"],
        "decision_mode": payload["decision_mode"],
        "final_outcome": payload["final_outcome"],
        "blocked_by_persona_gate": True,
    }


def list_items(c: sqlite3.Connection, table: str, limit: int = 20):
    if table not in {"cognition_rules", "decision_traces"}:
        raise ValueError("invalid table")
    rows = c.execute(
        f"SELECT id, updated_at, {'status' if table=='cognition_rules' else 'final_outcome'} AS state FROM {table} ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_audits(c: sqlite3.Connection, limit: int = 20):
    rows = c.execute("SELECT payload_json FROM audit_events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]


def main():
    p = argparse.ArgumentParser(description="MindKernel v0.1 Cognition->Decision prototype")
    p.add_argument("--db", default=str(DEFAULT_DB), help="SQLite file path")

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    ic = sub.add_parser("ingest-cognition")
    ic.add_argument("--file", required=True, help="Cognition JSON file or scenario containing `cognition`")

    c2d = sub.add_parser("cognition-to-decision")
    c2d.add_argument("--cognition-id", required=True)
    c2d.add_argument("--request-ref", required=True)
    c2d.add_argument("--risk-tier", choices=["low", "medium", "high"])

    rp = sub.add_parser("run-path")
    rp.add_argument("--file", required=True, help="Cognition JSON file or scenario containing `cognition`")
    rp.add_argument("--request-ref", required=True)
    rp.add_argument("--risk-tier", choices=["low", "medium", "high"])

    lc = sub.add_parser("list-cognition")
    lc.add_argument("--limit", type=int, default=20)

    ld = sub.add_parser("list-decisions")
    ld.add_argument("--limit", type=int, default=20)

    la = sub.add_parser("list-audits")
    la.add_argument("--limit", type=int, default=20)

    args = p.parse_args()

    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    c = conn(db)
    init_db(c)

    if args.cmd == "init-db":
        print(json.dumps({"ok": True, "db": str(db)}))
        return

    if args.cmd == "ingest-cognition":
        payload = _extract_payload(Path(args.file), "cognition")
        print(json.dumps(ingest_cognition(c, payload), ensure_ascii=False))
        return

    if args.cmd == "cognition-to-decision":
        print(
            json.dumps(
                cognition_to_decision(c, args.cognition_id, args.request_ref, args.risk_tier),
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.cmd == "run-path":
        payload = _extract_payload(Path(args.file), "cognition")
        r1 = ingest_cognition(c, payload)
        r2 = cognition_to_decision(c, r1["cognition_id"], args.request_ref, args.risk_tier)
        print(json.dumps({"cognition": r1, "decision": r2}, ensure_ascii=False, indent=2))
        return

    if args.cmd == "list-cognition":
        print(json.dumps(list_items(c, "cognition_rules", args.limit), ensure_ascii=False, indent=2))
        return

    if args.cmd == "list-decisions":
        print(json.dumps(list_items(c, "decision_traces", args.limit), ensure_ascii=False, indent=2))
        return

    if args.cmd == "list-audits":
        print(json.dumps(list_audits(c, args.limit), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
