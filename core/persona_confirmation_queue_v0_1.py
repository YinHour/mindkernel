#!/usr/bin/env python3
"""Core module: persona conflict confirmation queue (Agent->Human async confirmation)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from schema_runtime import SchemaValidationError, validate_payload  # type: ignore  # noqa: E402

DEFAULT_DB = ROOT / "data" / "mindkernel_v0_1.sqlite"

OPEN_STATUSES = {"open", "notified", "awaiting_human"}
ALL_STATUSES = OPEN_STATUSES | {"closed"}
DECISIONS = {"approve", "reject", "ask_more", "timeout"}


@dataclass
class PersonaConfirmationEvent:
    event_id: str
    trace_id: str
    job_id: str
    proposal_id: str
    status: str = "open"
    conflict_type: str = "persona_conflict"
    risk_level: str = "high"
    reason_codes: list[str] = field(default_factory=list)
    question: str = ""
    options: list[str] = field(default_factory=lambda: ["approve", "reject", "ask_more"])
    evidence_refs: list[str] = field(default_factory=list)
    deadline_at: str = ""
    fallback_policy: str = "defer"
    decision: str | None = None
    decision_reason: str | None = None
    resolved_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(v: str) -> datetime:
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def init_db(c: sqlite3.Connection):
    c.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS persona_confirmation_events (
            event_id TEXT PRIMARY KEY,
            trace_id TEXT,
            job_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            status TEXT NOT NULL,
            conflict_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            reason_codes_json TEXT NOT NULL,
            question TEXT NOT NULL,
            options_json TEXT NOT NULL,
            evidence_refs_json TEXT NOT NULL,
            deadline_at TEXT NOT NULL,
            fallback_policy TEXT NOT NULL,
            decision TEXT,
            decision_reason TEXT,
            resolved_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(job_id, proposal_id)
        );

        CREATE INDEX IF NOT EXISTS idx_pcq_status_deadline
        ON persona_confirmation_events(status, deadline_at);

        CREATE INDEX IF NOT EXISTS idx_pcq_job
        ON persona_confirmation_events(job_id);

        CREATE TABLE IF NOT EXISTS reflect_apply_ledger (
            idempotency_key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reflect_apply_job
        ON reflect_apply_ledger(job_id, proposal_id);

        CREATE TABLE IF NOT EXISTS reflect_apply_compensations (
            compensation_id TEXT PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            job_id TEXT NOT NULL,
            proposal_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            failure_status TEXT NOT NULL,
            error TEXT,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reflect_apply_comp_status
        ON reflect_apply_compensations(status, updated_at DESC);

        CREATE TABLE IF NOT EXISTS decision_traces (
            id TEXT PRIMARY KEY,
            final_outcome TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_decision_traces_outcome
        ON decision_traces(final_outcome);

        CREATE TABLE IF NOT EXISTS audit_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            object_type TEXT NOT NULL,
            object_id TEXT NOT NULL,
            correlation_id TEXT,
            timestamp TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_audit_events_ts
        ON audit_events(timestamp DESC);
        """
    )
    c.commit()


def _event_id(job_id: str, proposal_id: str, conflict_type: str) -> str:
    h = hashlib.sha1(f"{job_id}|{proposal_id}|{conflict_type}".encode("utf-8")).hexdigest()[:12]
    return f"pcq_{h}"


def _to_json(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _from_json(v: str):
    return json.loads(v) if v else []


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
    risk_tier: str | None = None,
    decision_trace_id: str | None = None,
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
        "evidence_refs": evidence_refs or [object_id],
        "timestamp": ts,
    }
    if risk_tier is not None:
        payload["risk_tier"] = risk_tier
    if decision_trace_id is not None:
        payload["decision_trace_id"] = decision_trace_id
    if correlation_id is not None:
        payload["correlation_id"] = correlation_id
    if metadata is not None:
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
        (
            event_id,
            event_type,
            object_type,
            object_id,
            correlation_id,
            ts,
            json.dumps(payload, ensure_ascii=False),
        ),
    )


def write_decision_trace(c: sqlite3.Connection, payload: dict) -> str:
    validate_payload("decision-trace.schema.json", payload)
    c.execute(
        "INSERT INTO decision_traces(id, final_outcome, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (
            payload["id"],
            payload["final_outcome"],
            json.dumps(payload, ensure_ascii=False),
            payload["created_at"],
            payload["updated_at"],
        ),
    )
    return payload["id"]


def build_apply_decision_trace(candidate: dict, *, status: str, error: str | None = None) -> dict:
    t = now_iso()
    job_id = str(candidate.get("job_id") or "job_unknown")
    proposal_id = str(candidate.get("proposal_id") or candidate.get("id") or uuid.uuid4().hex)
    decision_id = f"dec_apply_{hashlib.sha1((job_id + ':' + proposal_id).encode('utf-8')).hexdigest()[:12]}"
    trace_id = f"dt_apply_{uuid.uuid4().hex[:12]}"

    risk_tier = str(candidate.get("risk_level") or "medium")
    if risk_tier not in {"low", "medium", "high"}:
        risk_tier = "medium"

    if status == "succeeded":
        final_outcome = "limited" if risk_tier == "high" else "executed"
        decision_mode = "conservative" if risk_tier == "high" else "normal"
        reason = f"Reflect apply {candidate.get('apply_reason') or 'auto'} succeeded."
    elif status in {"blocked_operation", "failed_path_escape", "failed"}:
        final_outcome = "blocked"
        decision_mode = "abstain"
        reason = f"Reflect apply blocked: {status}. {error or ''}".strip()
    elif status == "dry_run":
        final_outcome = "limited"
        decision_mode = "explore"
        reason = "Reflect apply dry-run only, no writeback."
    else:
        final_outcome = "limited"
        decision_mode = "conservative"
        reason = f"Reflect apply status={status}."

    return {
        "id": trace_id,
        "decision_id": decision_id,
        "request_ref": f"reflect://{job_id}/{proposal_id}",
        "risk_tier": risk_tier,
        "impact_tier": "medium",
        "decision_mode": decision_mode,
        "epistemic_state": "supported",
        "inputs": {
            "memory_refs": [str(candidate.get("target_id") or "")],
        },
        "gates": {
            "persona_conflict_gate": "override" if candidate.get("apply_reason") == "human_approved" else "pass",
            "social_gate": "pass",
            "risk_gate": "limit" if risk_tier == "high" else "pass",
            "cognition_gate": "pass",
        },
        "reason": reason,
        "evidence_refs": list(candidate.get("evidence_refs") or [f"proposal:{proposal_id}"]),
        "actions": [
            {"step": "apply_exec", "result": status, "timestamp": t},
        ],
        "final_outcome": final_outcome,
        "review_due_at": (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "created_at": t,
        "updated_at": t,
    }


def _normalize_reason_codes(codes: list[str] | None) -> list[str]:
    if not codes:
        return []
    return sorted({str(x).strip() for x in codes if str(x).strip()})


def detect_conflict_type(proposal: dict) -> str:
    reason_codes = set(_normalize_reason_codes(proposal.get("reason_codes") or []))
    target_type = str(proposal.get("target_type", "")).strip()
    op = str(proposal.get("operation", "")).strip()

    if "HARD_RULE_TARGET" in reason_codes or target_type in {"core_memory", "persona_trait"}:
        return "persona_conflict"
    if op in {"delete", "overwrite", "merge_conflict"}:
        return "overwrite_conflict"
    return "high_risk_action"


def build_question(proposal: dict, conflict_type: str) -> str:
    target = str(proposal.get("target_type", "unknown"))
    op = str(proposal.get("operation", "upsert"))
    pid = str(proposal.get("proposal_id") or proposal.get("id") or "unknown")

    if conflict_type == "persona_conflict":
        return f"检测到人格/核心记忆冲突（{target}，操作 {op}，proposal={pid}），是否允许执行？"
    if conflict_type == "overwrite_conflict":
        return f"检测到高风险覆盖操作（{op}，target={target}，proposal={pid}），是否确认继续？"
    return f"检测到高风险变更（target={target}，operation={op}，proposal={pid}），是否确认？"


def should_enqueue_from_proposal(proposal: dict, only_persona_conflict: bool = True) -> bool:
    if str(proposal.get("decision")) != "pending_review":
        return False

    if not only_persona_conflict:
        return True

    conflict_type = detect_conflict_type(proposal)
    return conflict_type == "persona_conflict"


def build_event_from_proposal(
    proposal: dict,
    *,
    deadline_minutes: int = 60,
    fallback_policy: str = "defer",
) -> PersonaConfirmationEvent:
    t = now_iso()
    dl = (datetime.now(timezone.utc) + timedelta(minutes=deadline_minutes)).replace(microsecond=0)
    deadline_at = dl.isoformat().replace("+00:00", "Z")

    job_id = str(proposal.get("job_id") or "job_unknown")
    proposal_id = str(proposal.get("proposal_id") or proposal.get("id") or uuid.uuid4().hex)
    trace_id = str(proposal.get("trace_id") or f"tr_{uuid.uuid4().hex[:10]}")
    conflict_type = detect_conflict_type(proposal)

    return PersonaConfirmationEvent(
        event_id=_event_id(job_id, proposal_id, conflict_type),
        trace_id=trace_id,
        job_id=job_id,
        proposal_id=proposal_id,
        status="open",
        conflict_type=conflict_type,
        risk_level=str(proposal.get("risk_level") or "high"),
        reason_codes=_normalize_reason_codes(proposal.get("reason_codes") or []),
        question=build_question(proposal, conflict_type),
        options=["approve", "reject", "ask_more"],
        evidence_refs=list(proposal.get("evidence_refs") or []),
        deadline_at=deadline_at,
        fallback_policy=fallback_policy,
        created_at=t,
        updated_at=t,
    )


def enqueue_event(c: sqlite3.Connection, event: PersonaConfirmationEvent) -> dict:
    row = c.execute(
        "SELECT event_id, status FROM persona_confirmation_events WHERE job_id=? AND proposal_id=?",
        (event.job_id, event.proposal_id),
    ).fetchone()
    if row:
        return {"deduplicated": True, "event_id": row["event_id"], "status": row["status"]}

    payload = asdict(event)
    c.execute(
        """
        INSERT INTO persona_confirmation_events(
            event_id, trace_id, job_id, proposal_id, status, conflict_type, risk_level,
            reason_codes_json, question, options_json, evidence_refs_json,
            deadline_at, fallback_policy, decision, decision_reason, resolved_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["event_id"],
            payload["trace_id"],
            payload["job_id"],
            payload["proposal_id"],
            payload["status"],
            payload["conflict_type"],
            payload["risk_level"],
            _to_json(payload["reason_codes"]),
            payload["question"],
            _to_json(payload["options"]),
            _to_json(payload["evidence_refs"]),
            payload["deadline_at"],
            payload["fallback_policy"],
            payload["decision"],
            payload["decision_reason"],
            payload["resolved_at"],
            payload["created_at"],
            payload["updated_at"],
        ),
    )
    c.commit()
    return {"deduplicated": False, "event_id": event.event_id, "status": event.status}


def enqueue_from_routed(
    c: sqlite3.Connection,
    routed: dict,
    *,
    only_persona_conflict: bool = True,
    deadline_minutes: int = 60,
    fallback_policy: str = "defer",
) -> dict:
    proposals = routed.get("proposals") if isinstance(routed, dict) else None
    if not isinstance(proposals, list):
        raise ValueError("routed payload must include proposals[]")

    enq = 0
    dedup = 0
    skipped = 0
    events: list[str] = []

    for p in proposals:
        if not should_enqueue_from_proposal(p, only_persona_conflict=only_persona_conflict):
            skipped += 1
            continue
        event = build_event_from_proposal(
            p,
            deadline_minutes=deadline_minutes,
            fallback_policy=fallback_policy,
        )
        r = enqueue_event(c, event)
        if r["deduplicated"]:
            dedup += 1
        else:
            enq += 1
        events.append(r["event_id"])

    return {
        "ok": True,
        "total": len(proposals),
        "enqueued": enq,
        "deduplicated": dedup,
        "skipped": skipped,
        "event_ids": events,
    }


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["reason_codes"] = _from_json(d.pop("reason_codes_json"))
    d["options"] = _from_json(d.pop("options_json"))
    d["evidence_refs"] = _from_json(d.pop("evidence_refs_json"))
    return d


def list_events(c: sqlite3.Connection, status: str | None = None, limit: int = 20) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if status and status not in ALL_STATUSES:
        raise ValueError(f"invalid status: {status}")

    if status:
        rows = c.execute(
            "SELECT * FROM persona_confirmation_events WHERE status=? ORDER BY updated_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM persona_confirmation_events ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_event(c: sqlite3.Connection, event_id: str) -> dict:
    row = c.execute("SELECT * FROM persona_confirmation_events WHERE event_id=?", (event_id,)).fetchone()
    if not row:
        raise ValueError(f"event not found: {event_id}")
    return _row_to_dict(row)


def mark_status(c: sqlite3.Connection, event_id: str, status: str) -> dict:
    if status not in OPEN_STATUSES:
        raise ValueError(f"status must be one of {sorted(OPEN_STATUSES)}")
    old = get_event(c, event_id)
    if old["status"] == "closed":
        raise ValueError(f"event already closed: {event_id}")

    c.execute(
        "UPDATE persona_confirmation_events SET status=?, updated_at=? WHERE event_id=?",
        (status, now_iso(), event_id),
    )
    c.commit()
    return get_event(c, event_id)


def resolve_event(c: sqlite3.Connection, event_id: str, decision: str, reason: str | None = None) -> dict:
    if decision not in {"approve", "reject", "ask_more"}:
        raise ValueError("decision must be one of approve/reject/ask_more")

    old = get_event(c, event_id)
    if old["status"] == "closed":
        return old

    t = now_iso()
    if decision == "ask_more":
        c.execute(
            """
            UPDATE persona_confirmation_events
            SET status='awaiting_human', decision=NULL, decision_reason=?, resolved_at=NULL, updated_at=?
            WHERE event_id=?
            """,
            (reason or "need more context", t, event_id),
        )
    else:
        c.execute(
            """
            UPDATE persona_confirmation_events
            SET status='closed', decision=?, decision_reason=?, resolved_at=?, updated_at=?
            WHERE event_id=?
            """,
            (decision, reason or "", t, t, event_id),
        )
    c.commit()
    return get_event(c, event_id)


def timeout_scan(c: sqlite3.Connection, now: str | None = None, limit: int = 200) -> dict:
    now_v = now or now_iso()
    if limit < 1:
        raise ValueError("limit must be >= 1")

    rows = c.execute(
        """
        SELECT event_id, fallback_policy
        FROM persona_confirmation_events
        WHERE status IN ('open','notified','awaiting_human') AND deadline_at <= ?
        ORDER BY deadline_at ASC
        LIMIT ?
        """,
        (now_v, limit),
    ).fetchall()

    ids = []
    for r in rows:
        event_id = r["event_id"]
        fallback = r["fallback_policy"]
        c.execute(
            """
            UPDATE persona_confirmation_events
            SET status='closed', decision='timeout', decision_reason=?, resolved_at=?, updated_at=?
            WHERE event_id=?
            """,
            (f"timeout:{fallback}", now_v, now_v, event_id),
        )
        ids.append(event_id)

    c.commit()
    return {"ok": True, "timed_out": len(ids), "event_ids": ids, "now": now_v}


def build_ask_payload(c: sqlite3.Connection, event_id: str) -> dict:
    event = get_event(c, event_id)
    if event["status"] == "closed":
        raise ValueError("event already closed")
    return {
        "event_id": event["event_id"],
        "trace_id": event["trace_id"],
        "job_id": event["job_id"],
        "proposal_id": event["proposal_id"],
        "question": event["question"],
        "options": event["options"],
        "risk_level": event["risk_level"],
        "reason_codes": event["reason_codes"],
        "evidence_refs": event["evidence_refs"],
        "deadline_at": event["deadline_at"],
    }


def get_by_job_proposal(c: sqlite3.Connection, job_id: str, proposal_id: str) -> dict | None:
    row = c.execute(
        "SELECT * FROM persona_confirmation_events WHERE job_id=? AND proposal_id=?",
        (job_id, proposal_id),
    ).fetchone()
    return _row_to_dict(row) if row else None


def build_apply_plan(c: sqlite3.Connection, routed: dict) -> dict:
    proposals = routed.get("proposals") if isinstance(routed, dict) else None
    if not isinstance(proposals, list):
        raise ValueError("routed payload must include proposals[]")

    apply_candidates: list[dict] = []
    blocked: list[dict] = []

    for p in proposals:
        decision = str(p.get("decision") or "")
        job_id = str(p.get("job_id") or "job_unknown")
        proposal_id = str(p.get("proposal_id") or p.get("id") or "")

        if decision == "auto_applied":
            item = dict(p)
            item["apply_reason"] = "auto_applied"
            apply_candidates.append(item)
            continue

        if decision == "pending_review":
            q = get_by_job_proposal(c, job_id, proposal_id)

            if not q:
                blocked.append(
                    {
                        "job_id": job_id,
                        "proposal_id": proposal_id,
                        "block_reason": "missing_confirmation_event",
                        "decision": decision,
                    }
                )
                continue

            if q.get("status") == "closed" and q.get("decision") == "approve":
                item = dict(p)
                item["apply_reason"] = "human_approved"
                item["confirmation_event_id"] = q["event_id"]
                apply_candidates.append(item)
                continue

            if q.get("status") == "closed" and q.get("decision") in {"reject", "timeout"}:
                blocked.append(
                    {
                        "job_id": job_id,
                        "proposal_id": proposal_id,
                        "block_reason": "human_rejected_or_timeout",
                        "decision": q.get("decision"),
                        "confirmation_event_id": q.get("event_id"),
                        "decision_reason": q.get("decision_reason"),
                    }
                )
                continue

            blocked.append(
                {
                    "job_id": job_id,
                    "proposal_id": proposal_id,
                    "block_reason": "awaiting_human_confirmation",
                    "decision": q.get("decision"),
                    "status": q.get("status"),
                    "confirmation_event_id": q.get("event_id"),
                }
            )
            continue

        blocked.append(
            {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "block_reason": "unsupported_decision_state",
                "decision": decision,
            }
        )

    return {
        "ok": True,
        "total": len(proposals),
        "apply_count": len(apply_candidates),
        "blocked_count": len(blocked),
        "apply_candidates": apply_candidates,
        "blocked": blocked,
        "next_actions": [
            "apply_candidates_to_writeback",
            "ask_human_for_blocked_awaiting_confirmation",
        ],
    }


def _within_workspace(path: Path, workspace: Path) -> bool:
    try:
        path.resolve().relative_to(workspace.resolve())
        return True
    except Exception:
        return False


def _upsert_autogen_block(path: Path, title: str, block_lines: list[str]):
    auto_start = "<!-- AUTO-GENERATED:REFLECT:START -->"
    auto_end = "<!-- AUTO-GENERATED:REFLECT:END -->"

    if path.exists():
        content = path.read_text(errors="ignore")
    else:
        content = f"# {title}\n\n"

    block = "\n".join([auto_start, *block_lines, auto_end])

    if auto_start in content and auto_end in content:
        start = content.index(auto_start)
        end = content.index(auto_end) + len(auto_end)
        new_content = content[:start] + block + content[end:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + "\n" + block + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_content)


def _ledger_get(c: sqlite3.Connection, idempotency_key: str) -> dict | None:
    row = c.execute(
        "SELECT status, result_json FROM reflect_apply_ledger WHERE idempotency_key=?",
        (idempotency_key,),
    ).fetchone()
    if not row:
        return None
    return {"status": row["status"], "result": json.loads(row["result_json"] or "{}")}


def _ledger_put(
    c: sqlite3.Connection,
    *,
    idempotency_key: str,
    job_id: str,
    proposal_id: str,
    target_id: str,
    status: str,
    result: dict,
):
    t = now_iso()
    c.execute(
        """
        INSERT INTO reflect_apply_ledger(
            idempotency_key, job_id, proposal_id, target_id, status,
            result_json, applied_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            status=excluded.status,
            result_json=excluded.result_json,
            updated_at=excluded.updated_at
        """,
        (
            idempotency_key,
            job_id,
            proposal_id,
            target_id,
            status,
            json.dumps(result, ensure_ascii=False),
            t,
            t,
        ),
    )
    c.commit()


def _create_compensation(
    c: sqlite3.Connection,
    *,
    idempotency_key: str,
    cand: dict,
    res: dict,
    note: str | None = None,
) -> dict:
    t = now_iso()
    comp_id = f"cmp_{hashlib.sha1(idempotency_key.encode('utf-8')).hexdigest()[:12]}"
    payload = {
        "candidate": {
            "job_id": str(cand.get("job_id") or "job_unknown"),
            "proposal_id": str(cand.get("proposal_id") or cand.get("id") or ""),
            "target_id": str(cand.get("target_id") or cand.get("target_type") or ""),
            "operation": str(cand.get("operation") or "upsert"),
            "payload": cand.get("payload") if isinstance(cand.get("payload"), dict) else {},
        },
        "result": res,
    }

    c.execute(
        """
        INSERT INTO reflect_apply_compensations(
            compensation_id, idempotency_key, job_id, proposal_id, target_id,
            failure_status, error, payload_json, status, note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            failure_status=excluded.failure_status,
            error=excluded.error,
            payload_json=excluded.payload_json,
            status='pending',
            note=excluded.note,
            updated_at=excluded.updated_at
        """,
        (
            comp_id,
            idempotency_key,
            payload["candidate"]["job_id"],
            payload["candidate"]["proposal_id"],
            payload["candidate"]["target_id"],
            str(res.get("status") or "failed"),
            str(res.get("error") or ""),
            json.dumps(payload, ensure_ascii=False),
            note,
            t,
            t,
        ),
    )
    c.commit()
    return {"compensation_id": comp_id, "status": "pending"}


def list_compensations(c: sqlite3.Connection, status: str | None = None, limit: int = 50) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if status and status not in {"pending", "resolved", "skipped"}:
        raise ValueError("status must be pending|resolved|skipped")

    if status:
        rows = c.execute(
            "SELECT * FROM reflect_apply_compensations WHERE status=? ORDER BY updated_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM reflect_apply_compensations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d.pop("payload_json") or "{}")
        out.append(d)
    return out


def resolve_compensation(c: sqlite3.Connection, compensation_id: str, note: str = "") -> dict:
    row = c.execute(
        "SELECT * FROM reflect_apply_compensations WHERE compensation_id=?",
        (compensation_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"compensation not found: {compensation_id}")

    c.execute(
        "UPDATE reflect_apply_compensations SET status='resolved', note=?, updated_at=? WHERE compensation_id=?",
        (note, now_iso(), compensation_id),
    )
    c.commit()

    out = dict(c.execute("SELECT * FROM reflect_apply_compensations WHERE compensation_id=?", (compensation_id,)).fetchone())
    out["payload"] = json.loads(out.pop("payload_json") or "{}")
    return out


def _record_apply_governance(c: sqlite3.Connection, cand: dict, res: dict) -> dict:
    risk_tier = str(cand.get("risk_level") or "medium")
    if risk_tier not in {"low", "medium", "high"}:
        risk_tier = "medium"

    trace = build_apply_decision_trace(cand, status=str(res.get("status") or "unknown"), error=res.get("error"))
    dt_id = write_decision_trace(c, trace)

    write_audit_event(
        c,
        event_type="decision_gate",
        actor_type="system",
        actor_id="reflect-apply-exec",
        object_type="decision",
        object_id=trace["decision_id"],
        before={"gate": "pending"},
        after={
            "final_outcome": trace["final_outcome"],
            "apply_status": res.get("status"),
            "decision_mode": trace["decision_mode"],
        },
        reason=trace["reason"],
        evidence_refs=trace["evidence_refs"],
        risk_tier=risk_tier,
        decision_trace_id=dt_id if risk_tier == "high" else None,
        correlation_id=str(cand.get("job_id") or "job_unknown"),
        metadata={
            "proposal_id": str(cand.get("proposal_id") or cand.get("id") or ""),
            "target_id": str(cand.get("target_id") or cand.get("target_type") or ""),
        },
    )
    c.commit()

    out = dict(res)
    out["decision_trace_id"] = dt_id
    out["decision_id"] = trace["decision_id"]
    out["final_outcome"] = trace["final_outcome"]
    return out


def execute_apply_candidates(
    c: sqlite3.Connection,
    *,
    workspace: Path,
    apply_candidates: list[dict],
    dry_run: bool = False,
) -> dict:
    workspace = workspace.expanduser().resolve()
    results: list[dict] = []

    applied = 0
    deduped = 0
    skipped = 0
    failed = 0
    compensation_created = 0

    for cand in apply_candidates:
        job_id = str(cand.get("job_id") or "job_unknown")
        proposal_id = str(cand.get("proposal_id") or cand.get("id") or uuid.uuid4().hex)
        target_id = str(cand.get("target_id") or cand.get("target_type") or "unknown_target")
        idem = f"{job_id}:{proposal_id}:{target_id}"

        existing = _ledger_get(c, idem)
        if existing and existing.get("status") == "succeeded":
            deduped += 1
            results.append(
                {
                    "job_id": job_id,
                    "proposal_id": proposal_id,
                    "target_id": target_id,
                    "status": "deduplicated",
                    "result": existing.get("result", {}),
                }
            )
            continue

        payload = cand.get("payload") if isinstance(cand.get("payload"), dict) else {}
        op = str(cand.get("operation") or "upsert")
        path_raw = payload.get("path")

        if op in {"delete", "merge_conflict"}:
            skipped += 1
            res = {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "target_id": target_id,
                "status": "blocked_operation",
                "operation": op,
            }
            res = _record_apply_governance(c, cand, res)
            _ledger_put(
                c,
                idempotency_key=idem,
                job_id=job_id,
                proposal_id=proposal_id,
                target_id=target_id,
                status="blocked_operation",
                result=res,
            )
            results.append(res)
            continue

        if not path_raw:
            skipped += 1
            res = {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "target_id": target_id,
                "status": "skipped_no_payload_path",
            }
            res = _record_apply_governance(c, cand, res)
            comp = _create_compensation(
                c,
                idempotency_key=idem,
                cand=cand,
                res=res,
                note="missing payload.path; manual fix required",
            )
            compensation_created += 1
            res["compensation_id"] = comp["compensation_id"]
            _ledger_put(
                c,
                idempotency_key=idem,
                job_id=job_id,
                proposal_id=proposal_id,
                target_id=target_id,
                status="skipped_no_payload_path",
                result=res,
            )
            results.append(res)
            continue

        out_path = (workspace / str(path_raw)).resolve()
        if not _within_workspace(out_path, workspace):
            failed += 1
            res = {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "target_id": target_id,
                "status": "failed_path_escape",
                "path": str(out_path),
            }
            res = _record_apply_governance(c, cand, res)
            comp = _create_compensation(
                c,
                idempotency_key=idem,
                cand=cand,
                res=res,
                note="payload.path escaped workspace; blocked for safety",
            )
            compensation_created += 1
            res["compensation_id"] = comp["compensation_id"]
            _ledger_put(
                c,
                idempotency_key=idem,
                job_id=job_id,
                proposal_id=proposal_id,
                target_id=target_id,
                status="failed_path_escape",
                result=res,
            )
            results.append(res)
            continue

        mode = str(payload.get("write_mode") or "replace")

        try:
            if dry_run:
                res = {
                    "job_id": job_id,
                    "proposal_id": proposal_id,
                    "target_id": target_id,
                    "status": "dry_run",
                    "path": str(out_path),
                    "mode": mode,
                }
                res = _record_apply_governance(c, cand, res)
                _ledger_put(
                    c,
                    idempotency_key=idem,
                    job_id=job_id,
                    proposal_id=proposal_id,
                    target_id=target_id,
                    status="dry_run",
                    result=res,
                )
                results.append(res)
                skipped += 1
                continue

            if mode == "autogen_block":
                block_lines = payload.get("block_lines")
                if not isinstance(block_lines, list):
                    raise ValueError("autogen_block requires payload.block_lines[]")
                title = str(payload.get("title") or "Opinions")
                _upsert_autogen_block(out_path, title, [str(x) for x in block_lines])
            else:
                content = payload.get("content")
                if content is None:
                    raise ValueError("replace mode requires payload.content")
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(str(content))

            res = {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "target_id": target_id,
                "status": "succeeded",
                "path": str(out_path),
                "mode": mode,
                "apply_reason": cand.get("apply_reason"),
            }
            res = _record_apply_governance(c, cand, res)
            _ledger_put(
                c,
                idempotency_key=idem,
                job_id=job_id,
                proposal_id=proposal_id,
                target_id=target_id,
                status="succeeded",
                result=res,
            )
            results.append(res)
            applied += 1
        except Exception as e:
            failed += 1
            res = {
                "job_id": job_id,
                "proposal_id": proposal_id,
                "target_id": target_id,
                "status": "failed",
                "error": str(e),
            }
            try:
                res = _record_apply_governance(c, cand, res)
            except Exception as gerr:
                res["governance_error"] = str(gerr)
            comp = _create_compensation(
                c,
                idempotency_key=idem,
                cand=cand,
                res=res,
                note="apply execution failed; manual compensation required",
            )
            compensation_created += 1
            res["compensation_id"] = comp["compensation_id"]
            _ledger_put(
                c,
                idempotency_key=idem,
                job_id=job_id,
                proposal_id=proposal_id,
                target_id=target_id,
                status="failed",
                result=res,
            )
            results.append(res)

    return {
        "ok": True,
        "workspace": str(workspace),
        "total": len(apply_candidates),
        "applied": applied,
        "deduplicated": deduped,
        "skipped": skipped,
        "failed": failed,
        "compensation_created": compensation_created,
        "results": results,
    }


def execute_apply_plan(
    c: sqlite3.Connection,
    *,
    workspace: Path,
    apply_plan: dict,
    dry_run: bool = False,
) -> dict:
    candidates = apply_plan.get("apply_candidates") if isinstance(apply_plan, dict) else None
    if not isinstance(candidates, list):
        raise ValueError("apply_plan must include apply_candidates[]")

    result = execute_apply_candidates(c, workspace=workspace, apply_candidates=candidates, dry_run=dry_run)
    result["blocked"] = apply_plan.get("blocked", [])
    result["blocked_count"] = len(result["blocked"])
    return result
