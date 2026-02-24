#!/usr/bin/env python3
"""CLI: import memory JSONL into memory objects storage (v0.1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory_importer_v0_1 import (  # noqa: E402
    DEFAULT_DB,
    conn,
    import_memory_jsonl,
    init_db,
)


def main():
    p = argparse.ArgumentParser(description="Import memory JSONL into objects store")
    p.add_argument("--db", default=str(DEFAULT_DB), help="SQLite db path")
    p.add_argument("--input", required=True, help="memory JSONL file path")
    p.add_argument("--mode", choices=["upsert", "insert-only"], default="upsert")
    p.add_argument("--actor-id", default="memory-importer-v0.1")
    p.add_argument("--strict", action="store_true", help="fail fast on first row error")
    p.add_argument("--out", help="optional report output json path")
    args = p.parse_args()

    db = Path(args.db).expanduser().resolve()
    db.parent.mkdir(parents=True, exist_ok=True)

    input_file = Path(args.input).expanduser().resolve()
    if not input_file.exists():
        raise SystemExit(f"input file not found: {input_file}")

    c = conn(db)
    init_db(c)

    report = import_memory_jsonl(
        c,
        input_file=input_file,
        mode=args.mode,
        actor_id=args.actor_id,
        strict=args.strict,
    )

    if args.out:
        out = Path(args.out).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["out"] = str(out)

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.strict and report.get("failed", 0) > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
