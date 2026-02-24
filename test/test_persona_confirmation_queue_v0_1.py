from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.persona_confirmation_queue_v0_1 import (
    build_apply_plan,
    build_ask_payload,
    conn,
    enqueue_from_routed,
    execute_apply_plan,
    get_event,
    init_db,
    list_compensations,
    list_events,
    resolve_compensation,
    resolve_event,
    timeout_scan,
)


class PersonaConfirmationQueueV01Test(unittest.TestCase):
    def test_enqueue_and_resolve(self):
        routed = {
            "proposals": [
                {
                    "proposal_id": "p1",
                    "job_id": "j1",
                    "decision": "pending_review",
                    "risk_level": "high",
                    "target_type": "core_memory",
                    "operation": "upsert",
                    "reason_codes": ["HARD_RULE_TARGET"],
                    "evidence_refs": ["ev://1"],
                },
                {
                    "proposal_id": "p2",
                    "job_id": "j1",
                    "decision": "auto_applied",
                    "risk_level": "low",
                    "target_type": "opinion",
                    "operation": "upsert",
                },
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "q.sqlite"
            c = conn(db)
            init_db(c)

            out = enqueue_from_routed(c, routed, only_persona_conflict=True, deadline_minutes=60)
            self.assertEqual(out["enqueued"], 1)
            self.assertEqual(out["skipped"], 1)

            out2 = enqueue_from_routed(c, routed, only_persona_conflict=True, deadline_minutes=60)
            self.assertEqual(out2["deduplicated"], 1)

            events = list_events(c, status="open", limit=10)
            self.assertEqual(len(events), 1)

            event_id = events[0]["event_id"]
            ask = build_ask_payload(c, event_id)
            self.assertEqual(ask["event_id"], event_id)
            self.assertIn("approve", ask["options"])

            closed = resolve_event(c, event_id, "approve", reason="human approved")
            self.assertEqual(closed["status"], "closed")
            self.assertEqual(closed["decision"], "approve")

    def test_apply_plan_uses_human_approval(self):
        routed = {
            "proposals": [
                {
                    "proposal_id": "p_auto",
                    "job_id": "j_apply",
                    "decision": "auto_applied",
                    "risk_level": "low",
                    "target_type": "opinion",
                    "operation": "upsert",
                },
                {
                    "proposal_id": "p_wait",
                    "job_id": "j_apply",
                    "decision": "pending_review",
                    "risk_level": "high",
                    "target_type": "core_memory",
                    "operation": "overwrite",
                    "reason_codes": ["HARD_RULE_TARGET"],
                    "evidence_refs": ["ev://w"],
                },
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "q.sqlite"
            c = conn(db)
            init_db(c)

            enqueue_from_routed(c, routed, deadline_minutes=60)
            plan1 = build_apply_plan(c, routed)
            self.assertEqual(plan1["apply_count"], 1)
            self.assertEqual(plan1["blocked_count"], 1)

            events = list_events(c, status="open", limit=10)
            resolve_event(c, events[0]["event_id"], "approve", reason="approved")

            plan2 = build_apply_plan(c, routed)
            self.assertEqual(plan2["apply_count"], 2)
            self.assertEqual(plan2["blocked_count"], 0)

    def test_apply_exec_writes_files_and_is_idempotent(self):
        routed = {
            "proposals": [
                {
                    "proposal_id": "p_auto",
                    "job_id": "j_exec",
                    "decision": "auto_applied",
                    "risk_level": "low",
                    "target_type": "opinion",
                    "target_id": "demo_opinion",
                    "operation": "upsert",
                    "payload": {
                        "path": "bank/demo/exec_opinion.md",
                        "content": "# Applied\n\n- ok\n",
                        "write_mode": "replace",
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            db = base / "q.sqlite"
            c = conn(db)
            init_db(c)

            plan = build_apply_plan(c, routed)
            out1 = execute_apply_plan(c, workspace=base, apply_plan=plan, dry_run=False)
            self.assertEqual(out1["applied"], 1)
            self.assertEqual(out1["failed"], 0)
            self.assertIn("decision_trace_id", out1["results"][0])
            self.assertIn("decision_id", out1["results"][0])

            dt_cnt = c.execute("SELECT COUNT(*) FROM decision_traces").fetchone()[0]
            aud_cnt = c.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            self.assertGreaterEqual(dt_cnt, 1)
            self.assertGreaterEqual(aud_cnt, 1)

            p = base / "bank" / "demo" / "exec_opinion.md"
            self.assertTrue(p.exists())
            self.assertIn("Applied", p.read_text(encoding="utf-8"))

            out2 = execute_apply_plan(c, workspace=base, apply_plan=plan, dry_run=False)
            self.assertEqual(out2["deduplicated"], 1)

    def test_apply_exec_creates_compensation_on_failure(self):
        routed = {
            "proposals": [
                {
                    "proposal_id": "p_fail",
                    "job_id": "j_comp",
                    "decision": "auto_applied",
                    "risk_level": "medium",
                    "target_type": "opinion",
                    "target_id": "demo_missing_path",
                    "operation": "upsert",
                    "payload": {
                        "content": "missing path should trigger compensation"
                    },
                }
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            db = base / "q.sqlite"
            c = conn(db)
            init_db(c)

            plan = build_apply_plan(c, routed)
            out = execute_apply_plan(c, workspace=base, apply_plan=plan, dry_run=False)
            self.assertEqual(out["failed"], 0)
            self.assertEqual(out["compensation_created"], 1)

            comps = list_compensations(c, status="pending", limit=10)
            self.assertEqual(len(comps), 1)
            cid = comps[0]["compensation_id"]

            resolved = resolve_compensation(c, cid, note="manual handled")
            self.assertEqual(resolved["status"], "resolved")

    def test_timeout_scan(self):
        routed = {
            "proposals": [
                {
                    "proposal_id": "p_timeout",
                    "job_id": "j_timeout",
                    "decision": "pending_review",
                    "risk_level": "high",
                    "target_type": "core_memory",
                    "operation": "overwrite",
                    "reason_codes": ["HARD_RULE_TARGET"],
                    "evidence_refs": ["ev://t"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "q.sqlite"
            c = conn(db)
            init_db(c)

            out = enqueue_from_routed(c, routed, deadline_minutes=1)
            event_id = out["event_ids"][0]
            event = get_event(c, event_id)
            past = "1999-01-01T00:00:00Z"
            c.execute(
                "UPDATE persona_confirmation_events SET deadline_at=?, updated_at=? WHERE event_id=?",
                (past, past, event_id),
            )
            c.commit()

            ts = timeout_scan(c, now="2000-01-01T00:00:00Z", limit=10)
            self.assertEqual(ts["timed_out"], 1)

            closed = get_event(c, event_id)
            self.assertEqual(closed["status"], "closed")
            self.assertEqual(closed["decision"], "timeout")


if __name__ == "__main__":
    unittest.main()
