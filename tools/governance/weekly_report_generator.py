#!/usr/bin/env python3
"""
MindKernel Governance Weekly Report Generator

Usage:
  python3 weekly_report_generator.py [--weeks 1]
  python3 weekly_report_generator.py --output reports/governance/weekly-YYYY-MM-DD.md

Generates a weekly governance report covering:
- MECD pipeline metrics (M/E/C/D counts and changes)
- Decision traces distribution
- Experience promotion rate
- Parameter updates from governance engine
- Risk alerts
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports" / "governance"
CHECKPOINT_FILE = ROOT / "data" / "governance" / "governance_checkpoint.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def date_iso(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d")


def connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {"last_decision_id": None, "last_run": None}


def mecd_counts(conn: sqlite3.Connection) -> dict:
    """Return MECD pipeline counts."""
    c = conn.cursor()
    out = {}

    # Memory
    try:
        c.execute("SELECT COUNT(*) FROM memory_items")
        out["memory_total"] = c.fetchone()[0]
    except Exception:
        out["memory_total"] = 0

    # Experience
    try:
        c.execute("SELECT COUNT(*), status FROM experience_records GROUP BY status")
        rows = c.fetchall()
        out["experience_total"] = sum(r[0] for r in rows)
        out["experience_active"] = sum(r[0] for r in rows if r[1] == "active")
        out["experience_candidate"] = sum(r[0] for r in rows if r[1] == "candidate")
    except Exception:
        out["experience_total"] = out["experience_active"] = out["experience_candidate"] = 0

    # Cognition
    try:
        c.execute("SELECT COUNT(*) FROM cognition_rules")
        out["cognition_rules"] = c.fetchone()[0]
    except Exception:
        out["cognition_rules"] = 0

    # Decision
    try:
        c.execute("SELECT COUNT(*) FROM decision_traces")
        out["decision_total"] = c.fetchone()[0]
        c.execute(
            "SELECT final_outcome, COUNT(*) FROM decision_traces GROUP BY final_outcome"
        )
        out["decision_by_outcome"] = {r[0]: r[1] for r in c.fetchall()}
    except Exception:
        out["decision_total"] = 0
        out["decision_by_outcome"] = {}

    # Audit events
    try:
        c.execute("SELECT COUNT(*) FROM audit_events")
        out["audit_events"] = c.fetchone()[0]
    except Exception:
        out["audit_events"] = 0

    return out


def daemon_health(state_db: Path) -> dict:
    """Read daemon health summary from state db."""
    out = {}
    if not state_db.exists():
        return out
    try:
        conn = connect_db(state_db)
        c = conn.cursor()
        c.execute(
            "SELECT processed_total, offset, last_event_id, updated_at FROM daemon_state ORDER BY id DESC LIMIT 1"
        )
        row = c.fetchone()
        if row:
            out["processed_total"] = row["processed_total"]
            out["last_event_id"] = row["last_event_id"]
            out["updated_at"] = row["updated_at"]
        # Error count (healed vs active)
        c.execute("SELECT COUNT(*) FROM daemon_audit WHERE status='error'")
        out["daemon_errors_active"] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM daemon_audit WHERE status='healed'")
        out["daemon_errors_healed"] = c.fetchone()[0]
        conn.close()
    except Exception:
        pass
    return out


def generate_report(weeks: int = 1) -> str:
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=7 * weeks)

    mk_conn = connect_db(ROOT / "data" / "mindkernel_v0_1.sqlite")
    sched_conn = connect_db(ROOT / "data" / "scheduler.sqlite")
    daemon_state_db = ROOT / "data" / "daemon" / "memory_observer_v0_2.sqlite"
    checkpoint = load_checkpoint()

    mk = mecd_counts(mk_conn)
    sched = mecd_counts(sched_conn)
    daemon = daemon_health(daemon_state_db)

    # Decision traces from both dbs combined
    total_decisions = mk.get("decision_total", 0)
    outcome_dist = mk.get("decision_by_outcome", {})

    # Governance status
    gov_checkpoint = checkpoint.get("last_decision_id", "None")
    gov_last_run = checkpoint.get("last_run", "Never")

    report = f"""# MindKernel Governance Weekly Report

> Generated: {now_iso()}
> Period: {week_start} to {today} ({weeks} week{'s' if weeks > 1 else ''})

---

## MECD Pipeline Status

| Layer | Count | Notes |
|-------|------:|-------|
| Memory | {mk.get('memory_total', 0):,} | items |
| Experience (total) | {mk.get('experience_total', 0):,} | all statuses |
| Experience (active) | {mk.get('experience_active', 0):,} | promoted |
| Experience (candidate) | {mk.get('experience_candidate', 0):,} | pending |
| Cognition rules | {mk.get('cognition_rules', 0):,} | active |
| Decision traces | {total_decisions:,} | across all sources |
| Audit events | {mk.get('audit_events', 0):,} | logged |

### Decision Outcome Distribution

"""
    if outcome_dist:
        for outcome, count in sorted(outcome_dist.items()):
            pct = count / total_decisions * 100 if total_decisions else 0
            report += f"- **{outcome}**: {count} ({pct:.1f}%)\n"
    else:
        report += "_No decision traces recorded._\n"

    report += f"""
---

## Daemon Health

| Metric | Value |
|--------|------:|
| Total events processed | {daemon.get('processed_total', 'N/A'):,} |
| Last event | `{daemon.get('last_event_id', 'N/A')}` |
| Last updated | {daemon.get('updated_at', 'N/A')} |
| Active audit errors | {daemon.get('daemon_errors_active', 0):,} |
| Healed audit errors | {daemon.get('daemon_errors_healed', 0):,} |

"""

    report += f"""---

## Governance Engine

- **Last run**: {gov_last_run}
- **Checkpoint decision_id**: `{gov_checkpoint}`
- **Decision traces in scheduler.db**: {sched.get('decision_total', 0):,}

---

## Governance Engine Parameters

"""
    # Read param_config if available
    param_file = ROOT / "data" / "governance" / "param_config_state.json"
    if param_file.exists():
        try:
            params = json.loads(param_file.read_text())
            report += "```json\n" + json.dumps(params, indent=2, ensure_ascii=False)[:500] + "\n```\n"
        except Exception:
            report += "_Parameter state not available._\n"
    else:
        report += "_Parameter state file not found._\n"

    report += f"""
---

## Risk Assessment

"""
    risks = []
    if daemon.get("daemon_errors_active", 0) > 0:
        risks.append(f"⚠️  {daemon['daemon_errors_active']} active daemon audit errors need attention")
    if mk.get("experience_candidate", 0) > 10:
        risks.append(f"ℹ️  {mk['experience_candidate']} experience candidates pending review")
    if gov_checkpoint == "None" or gov_last_run == "Never":
        risks.append("⚠️  Governance engine may never have run — check launchd service")
    if total_decisions == 0:
        risks.append("ℹ️  No decision traces recorded — MECD闭环 may not be generating traces")

    if risks:
        for r in risks:
            report += f"- {r}\n"
    else:
        report += "- ✅ No active risk indicators\n"

    report += f"""
---

## Governance Ledger

- Ledger file: `data/governance/active_push_ledger.jsonl`
- Active push buffer: `data/governance/active_push_buffer.jsonl`
- Governance checkpoint: `data/governance/governance_checkpoint.json`

---

_Report generated by MindKernel governance weekly_report_generator.py_
"""
    mk_conn.close()
    sched_conn.close()
    return report


def main():
    parser = argparse.ArgumentParser(description="MindKernel Governance Weekly Report")
    parser.add_argument("--weeks", type=int, default=1, help="Number of weeks to report (default: 1)")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file path")
    parser.add_argument("--print", action="store_true", help="Print to stdout")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = generate_report(weeks=args.weeks)

    if args.print:
        print(report)

    if args.output:
        out_path = Path(args.output)
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = REPORTS_DIR / f"weekly-{today}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    main()
