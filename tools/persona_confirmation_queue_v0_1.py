#!/usr/bin/env python3
"""CLI wrapper: persona confirmation queue (v0.1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.persona_confirmation_queue_v0_1 import (  # noqa: E402
    DEFAULT_DB,
    build_apply_plan,
    build_ask_payload,
    conn,
    enqueue_from_routed,
    execute_apply_plan,
    get_event,
    init_db,
    list_compensations,
    list_events,
    mark_status,
    resolve_compensation,
    resolve_event,
    timeout_scan,
)


def _load_json(path: str) -> dict:
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def _write_jsonl(path: str, rows: list[dict]):
    p = Path(path).expanduser().resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return str(p)


def main():
    p = argparse.ArgumentParser(description="MindKernel persona confirmation queue v0.1")
    p.add_argument("--db", default=str(DEFAULT_DB), help="SQLite file path")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db")

    ef = sub.add_parser("enqueue-from-routed")
    ef.add_argument("--routed-file", required=True, help="route-proposals output json path")
    ef.add_argument("--deadline-minutes", type=int, default=60)
    ef.add_argument("--fallback-policy", default="defer")
    ef.add_argument("--all-high-risk", action="store_true", help="enqueue all pending_review items, not just persona conflicts")

    ls = sub.add_parser("list")
    ls.add_argument("--status", choices=["open", "notified", "awaiting_human", "closed"])
    ls.add_argument("--limit", type=int, default=20)

    ask = sub.add_parser("ask")
    ask.add_argument("--event-id", required=True)

    mn = sub.add_parser("mark-notified")
    mn.add_argument("--event-id", required=True)

    ma = sub.add_parser("mark-awaiting")
    ma.add_argument("--event-id", required=True)

    rs = sub.add_parser("resolve")
    rs.add_argument("--event-id", required=True)
    rs.add_argument("--decision", required=True, choices=["approve", "reject", "ask_more"])
    rs.add_argument("--reason", default="")

    ts = sub.add_parser("timeout-scan")
    ts.add_argument("--now", help="ISO datetime, default now")
    ts.add_argument("--limit", type=int, default=200)

    ap = sub.add_parser("apply-plan")
    ap.add_argument("--routed-file", required=True, help="route-proposals output json path")
    ap.add_argument("--output", help="optional full apply-plan output path")
    ap.add_argument("--apply-out", help="optional apply_candidates jsonl path")
    ap.add_argument("--blocked-out", help="optional blocked jsonl path")

    ae = sub.add_parser("apply-exec")
    ae.add_argument("--plan-file", required=True, help="apply-plan output json path")
    ae.add_argument("--workspace", default=".", help="workspace root for file writeback")
    ae.add_argument("--dry-run", action="store_true")
    ae.add_argument("--output", help="optional apply execution output path")

    cps = sub.add_parser("compensations")
    cps.add_argument("--status", choices=["pending", "resolved", "skipped"])
    cps.add_argument("--limit", type=int, default=20)

    rcp = sub.add_parser("resolve-compensation")
    rcp.add_argument("--compensation-id", required=True)
    rcp.add_argument("--note", default="")

    getp = sub.add_parser("get")
    getp.add_argument("--event-id", required=True)

    args = p.parse_args()

    db = Path(args.db).expanduser().resolve()
    db.parent.mkdir(parents=True, exist_ok=True)
    c = conn(db)
    init_db(c)

    if args.cmd == "init-db":
        print(json.dumps({"ok": True, "db": str(db)}))
        return

    if args.cmd == "enqueue-from-routed":
        routed = _load_json(args.routed_file)
        out = enqueue_from_routed(
            c,
            routed,
            only_persona_conflict=not args.all_high_risk,
            deadline_minutes=max(1, int(args.deadline_minutes)),
            fallback_policy=args.fallback_policy,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.cmd == "list":
        print(json.dumps(list_events(c, status=args.status, limit=max(1, int(args.limit))), ensure_ascii=False, indent=2))
        return

    if args.cmd == "ask":
        print(json.dumps(build_ask_payload(c, args.event_id), ensure_ascii=False, indent=2))
        return

    if args.cmd == "mark-notified":
        print(json.dumps(mark_status(c, args.event_id, "notified"), ensure_ascii=False, indent=2))
        return

    if args.cmd == "mark-awaiting":
        print(json.dumps(mark_status(c, args.event_id, "awaiting_human"), ensure_ascii=False, indent=2))
        return

    if args.cmd == "resolve":
        print(json.dumps(resolve_event(c, args.event_id, args.decision, reason=args.reason), ensure_ascii=False, indent=2))
        return

    if args.cmd == "timeout-scan":
        print(json.dumps(timeout_scan(c, now=args.now, limit=max(1, int(args.limit))), ensure_ascii=False, indent=2))
        return

    if args.cmd == "apply-plan":
        routed = _load_json(args.routed_file)
        out = build_apply_plan(c, routed)

        if args.output:
            out_path = Path(args.output).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            out["output"] = str(out_path)

        if args.apply_out:
            out["apply_out"] = _write_jsonl(args.apply_out, out.get("apply_candidates", []))

        if args.blocked_out:
            out["blocked_out"] = _write_jsonl(args.blocked_out, out.get("blocked", []))

        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.cmd == "apply-exec":
        plan = _load_json(args.plan_file)
        out = execute_apply_plan(
            c,
            workspace=Path(args.workspace),
            apply_plan=plan,
            dry_run=args.dry_run,
        )
        if args.output:
            out_path = Path(args.output).expanduser().resolve()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            out["output"] = str(out_path)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.cmd == "compensations":
        print(json.dumps(list_compensations(c, status=args.status, limit=max(1, int(args.limit))), ensure_ascii=False, indent=2))
        return

    if args.cmd == "resolve-compensation":
        print(json.dumps(resolve_compensation(c, args.compensation_id, note=args.note), ensure_ascii=False, indent=2))
        return

    if args.cmd == "get":
        print(json.dumps(get_event(c, args.event_id), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    main()
