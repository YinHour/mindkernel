#!/usr/bin/env python3
"""Validate apply compensation flow (C4) for reflect apply execution."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.persona_confirmation_queue_v0_1 import (
    build_apply_plan,
    conn,
    execute_apply_plan,
    init_db,
    list_compensations,
    resolve_compensation,
)


def main():
    routed = {
        "proposals": [
            {
                "proposal_id": "p_comp_001",
                "job_id": "j_comp_001",
                "decision": "auto_applied",
                "risk_level": "medium",
                "target_type": "opinion",
                "target_id": "demo_comp_target",
                "operation": "upsert",
                "payload": {
                    "content": "intentionally missing payload.path to trigger compensation"
                },
            }
        ]
    }

    with tempfile.TemporaryDirectory(prefix="mk-comp-v01-") as td:
        base = Path(td)
        db = base / "comp.sqlite"
        c = conn(db)
        init_db(c)

        plan = build_apply_plan(c, routed)
        out = execute_apply_plan(c, workspace=base, apply_plan=plan, dry_run=False)

        assert out.get("compensation_created", 0) >= 1, "compensation should be created"

        pending = list_compensations(c, status="pending", limit=20)
        assert pending, "pending compensation must exist"

        cid = pending[0]["compensation_id"]
        resolved = resolve_compensation(c, cid, note="validated in script")
        assert resolved.get("status") == "resolved", "compensation should be resolvable"

        report = {
            "ok": True,
            "tmp": str(base),
            "apply": {
                "failed": out.get("failed"),
                "skipped": out.get("skipped"),
                "compensation_created": out.get("compensation_created"),
            },
            "compensation": {
                "compensation_id": cid,
                "status": resolved.get("status"),
            },
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
