#!/usr/bin/env python3
"""Validate opinion conflict clustering and polarity detection in memory_index_v0_1."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import memory_index_v0_1 as mi

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "memory-workspace-evolution"


def main():
    if not FIXTURE.exists():
        raise SystemExit(f"fixture not found: {FIXTURE}")

    tmp = Path(tempfile.mkdtemp(prefix="mk-op-conf-v01-"))
    ws = tmp / "workspace"
    shutil.copytree(FIXTURE, ws)
    db = tmp / "index.sqlite"

    c = mi.connect(db)
    mi.init_db(c)
    mi.cmd_reindex(c, workspace=ws, incremental=True, retry_failures=True, max_retries=3)

    out = mi.cmd_reflect(c, since_days=30, workspace=ws, writeback=False, max_per_entity=8, max_opinions=50)
    groups = out.get("opinion_conflict_groups", [])
    conflicts = [g for g in groups if g.get("has_conflict")]

    if not conflicts:
        raise AssertionError("expected at least one opinion conflict group")

    g = conflicts[0]
    pc = g.get("polarity_counts", {})

    assert int(pc.get("positive", 0)) >= 1, "conflict group must include positive opinions"
    assert int(pc.get("negative", 0)) >= 1, "conflict group must include negative opinions"
    assert g.get("recommended_action") == "mandatory_review", "conflict group should recommend mandatory_review"

    print(
        json.dumps(
            {
                "ok": True,
                "workspace": str(ws),
                "db": str(db),
                "conflict_groups": len(conflicts),
                "top_group": {
                    "group_id": g.get("group_id"),
                    "topic_signature": g.get("topic_signature"),
                    "polarity_counts": pc,
                    "recommended_action": g.get("recommended_action"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
