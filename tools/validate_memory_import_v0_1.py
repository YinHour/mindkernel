#!/usr/bin/env python3
"""Validate memory JSONL importer (idempotent replay + error isolation)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory_importer_v0_1 import conn, import_memory_jsonl, init_db
from core.session_memory_parser_v0_1 import event_to_memory_object, parse_session, write_jsonl

FIXTURE_SESSION = ROOT / "data" / "fixtures" / "session-logs" / "sample-session.jsonl"


def _count_memory(c) -> int:
    return int(c.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0])


def main():
    if not FIXTURE_SESSION.exists():
        raise SystemExit(f"fixture session missing: {FIXTURE_SESSION}")

    tmp = Path(tempfile.mkdtemp(prefix="mk-import-v01-"))
    db = tmp / "mindkernel_v0_1.sqlite"
    jsonl = tmp / "memory_rows.jsonl"
    broken_jsonl = tmp / "memory_rows_with_error.jsonl"

    parsed = parse_session(FIXTURE_SESSION, include_tool_calls=True, max_events=0)
    rows = [
        event_to_memory_object(
            e,
            review_due_days=7,
            next_action_days=7,
            status="candidate",
        )
        for e in parsed.get("memory_events", [])
    ]
    write_jsonl(jsonl, rows)

    # Broken stream: valid rows + one malformed row (schema invalid)
    with broken_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.write(json.dumps({"id": "mem_broken_only_id"}, ensure_ascii=False) + "\n")

    c = conn(db)
    init_db(c)

    run1 = import_memory_jsonl(c, input_file=jsonl, mode="upsert", actor_id="validate-memory-import")
    assert run1["failed"] == 0, "first import should not fail"
    assert run1["inserted"] == len(rows), "first import should insert all rows"

    run2 = import_memory_jsonl(c, input_file=jsonl, mode="upsert", actor_id="validate-memory-import")
    assert run2["failed"] == 0, "second replay should not fail"
    assert run2["inserted"] == 0 and run2["updated"] == 0, "second replay should not write new rows"
    assert run2["skipped_noop"] == len(rows), "second replay should be full no-op"

    run3 = import_memory_jsonl(c, input_file=broken_jsonl, mode="upsert", actor_id="validate-memory-import")
    assert run3["failed"] >= 1, "broken import should record row-level errors"

    final_count = _count_memory(c)
    assert final_count == len(rows), "broken row must not contaminate memory table count"

    out = {
        "ok": True,
        "tmp": str(tmp),
        "rows": len(rows),
        "run1": {k: run1[k] for k in ["inserted", "updated", "skipped_noop", "failed"]},
        "run2": {k: run2[k] for k in ["inserted", "updated", "skipped_noop", "failed"]},
        "run3": {k: run3[k] for k in ["inserted", "updated", "skipped_noop", "failed"]},
        "final_count": final_count,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
