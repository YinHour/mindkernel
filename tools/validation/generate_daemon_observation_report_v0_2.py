#!/usr/bin/env python3
"""Generate daemon observation report (v0.2)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_dt(v: str) -> datetime:
    s = v
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _query(conn: sqlite3.Connection, sql: str, params=()):
    cur = conn.execute(sql, params)
    return cur.fetchall()


def render_md(report: dict) -> str:
    m = report["metrics"]
    a = report["alerts"]
    lines = [
        "# Daemon Observation Report (v0.2)",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- daemon_db: {report['daemon_db']}",
        f"- window_hours: {report['window_hours']}",
        f"- batches: {m['batches']}",
        "",
        "## Metrics",
        "",
        f"- processed: {m['processed']}",
        f"- normalized: {m['normalized']}",
        f"- deduped_events: {m['deduped_events']} (rate={m['dedupe_rate']:.4f})",
        f"- candidates: {m['candidates']}",
        f"- enqueued: {m['enqueued']} (rate={m['enqueue_rate']:.4f})",
        f"- throttled: {m['throttled']}",
        f"- skipped_hwm: {m['skipped_hwm']}",
        f"- errors: {m['errors']} (rate={m['error_rate']:.4f})",
        f"- system_repeat_alerts: {m['system_repeat_alerts']}",
        f"- ack_compressed: {m['ack_compressed']}",
        f"- ack_rollup_candidates: {m['ack_rollup_candidates']}",
        "",
        "## Alerts",
        "",
        f"- error_spike: {a['error_spike']}",
        f"- dedupe_high: {a['dedupe_high']}",
        f"- hwm_pressure: {a['hwm_pressure']}",
        f"- system_repeat_spike: {a['system_repeat_spike']}",
        "",
    ]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Generate daemon observation report v0.2")
    p.add_argument("--daemon-db", default=str(ROOT / "data" / "daemon" / "memory_observer_v0_2.sqlite"))
    p.add_argument("--window-hours", type=int, default=24)
    p.add_argument("--dedupe-high-threshold", type=float, default=0.5)
    p.add_argument("--error-spike-threshold", type=float, default=0.05)
    p.add_argument("--hwm-pressure-threshold", type=int, default=10)
    p.add_argument("--system-repeat-threshold", type=int, default=1)
    p.add_argument("--out-json")
    p.add_argument("--out-md")
    args = p.parse_args()

    db = Path(args.daemon_db).expanduser().resolve()
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=max(1, int(args.window_hours)))

    metrics = {
        "batches": 0,
        "processed": 0,
        "normalized": 0,
        "deduped_events": 0,
        "candidates": 0,
        "enqueued": 0,
        "throttled": 0,
        "skipped_hwm": 0,
        "errors": 0,
        "system_repeat_alerts": 0,
        "ack_compressed": 0,
        "ack_rollup_candidates": 0,
        "dedupe_rate": 0.0,
        "enqueue_rate": 0.0,
        "error_rate": 0.0,
    }

    if db.exists():
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        tables = {r[0] for r in _query(c, "SELECT name FROM sqlite_master WHERE type='table'")}
        if "daemon_batches" in tables:
            cols = {r[1] for r in _query(c, "PRAGMA table_info(daemon_batches)")}
            extra_system = "system_repeat_alerts" in cols
            extra_ack = "ack_compressed" in cols
            extra_rollup = "ack_rollup_candidates" in cols

            select_parts = [
                "processed",
                "normalized",
                "deduped_events",
                "candidates",
                "enqueued",
                "throttled",
                "skipped_hwm",
                "errors",
                "ended_at",
                "system_repeat_alerts" if extra_system else "0 AS system_repeat_alerts",
                "ack_compressed" if extra_ack else "0 AS ack_compressed",
                "ack_rollup_candidates" if extra_rollup else "0 AS ack_rollup_candidates",
            ]
            sql = (
                "SELECT "
                + ", ".join(select_parts)
                + " FROM daemon_batches WHERE ended_at >= ?"
            )
            rows = _query(
                c,
                sql,
                (since.replace(microsecond=0).isoformat().replace("+00:00", "Z"),),
            )
            metrics["batches"] = len(rows)
            for r in rows:
                metrics["processed"] += int(r["processed"])
                metrics["normalized"] += int(r["normalized"])
                metrics["deduped_events"] += int(r["deduped_events"])
                metrics["candidates"] += int(r["candidates"])
                metrics["enqueued"] += int(r["enqueued"])
                metrics["throttled"] += int(r["throttled"])
                metrics["skipped_hwm"] += int(r["skipped_hwm"])
                metrics["errors"] += int(r["errors"])
                metrics["system_repeat_alerts"] += int(r["system_repeat_alerts"])
                metrics["ack_compressed"] += int(r["ack_compressed"])
                metrics["ack_rollup_candidates"] += int(r["ack_rollup_candidates"])
        c.close()

    if metrics["normalized"] > 0:
        metrics["dedupe_rate"] = metrics["deduped_events"] / metrics["normalized"]
        metrics["error_rate"] = metrics["errors"] / metrics["normalized"]
    if metrics["candidates"] > 0:
        metrics["enqueue_rate"] = metrics["enqueued"] / metrics["candidates"]

    alerts = {
        "error_spike": metrics["error_rate"] > float(args.error_spike_threshold),
        "dedupe_high": metrics["dedupe_rate"] > float(args.dedupe_high_threshold),
        "hwm_pressure": metrics["skipped_hwm"] >= int(args.hwm_pressure_threshold),
        "system_repeat_spike": metrics["system_repeat_alerts"] >= int(args.system_repeat_threshold),
    }

    report = {
        "ok": True,
        "generated_at": now_iso(),
        "daemon_db": str(db),
        "window_hours": int(args.window_hours),
        "metrics": metrics,
        "alerts": alerts,
    }

    if args.out_json:
        outj = Path(args.out_json).expanduser().resolve()
    else:
        outj = ROOT / "reports" / "daemon" / f"observation_{now.strftime('%Y%m%d_%H%M%S')}.json"
    outj.parent.mkdir(parents=True, exist_ok=True)
    outj.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.out_md:
        outm = Path(args.out_md).expanduser().resolve()
    else:
        outm = outj.with_suffix(".md")
    outm.parent.mkdir(parents=True, exist_ok=True)
    outm.write_text(render_md(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(outj),
                "out_md": str(outm),
                "metrics": report["metrics"],
                "alerts": report["alerts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
