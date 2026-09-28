#!/usr/bin/env python3
"""Validate reflect scheduler worker loop (S7)."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS_SCHED = ROOT / "tools" / "scheduler"
FIXTURE_WS = ROOT / "data" / "fixtures" / "memory-workspace-evolution"


def run(cmd: list[str], cwd: Path = ROOT):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(
            "command failed:\n"
            + " ".join(cmd)
            + f"\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}"
        )
    return p.stdout


def now_iso(offset_sec: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_sec)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main():
    if not FIXTURE_WS.exists():
        raise SystemExit(f"fixture workspace missing: {FIXTURE_WS}")

    tmp = Path(tempfile.mkdtemp(prefix="mk-worker-v01-"))
    ws = tmp / "workspace"
    shutil.copytree(FIXTURE_WS, ws)
    # Keep the dated fixture in scope as calendar time advances. Production
    # worker defaults remain unchanged; this script verifies the worker loop.
    oldest_fixture_date = min(date.fromisoformat(p.stem) for p in (ws / "memory").glob("????-??-??.md"))
    fixture_lookback_days = max(30, (datetime.now(timezone.utc).date() - oldest_fixture_date).days + 1)

    db = tmp / "scheduler.sqlite"
    index_db = tmp / "index.sqlite"
    reports = tmp / "reports"

    # enqueue one due reflect job (avoid race by scheduling shortly in future)
    run(
        [
            "python3",
            str(TOOLS_SCHED / "scheduler_v0_1.py"),
            "--db",
            str(db),
            "enqueue",
            "--object-type",
            "reflect_job",
            "--object-id",
            "reflect_daily_test",
            "--action",
            "reflect",
            "--run-at",
            now_iso(offset_sec=2),
            "--priority",
            "high",
            "--idempotency-key",
            "reflect:test:worker:v0_1",
        ]
    )

    time.sleep(2.2)

    worker_out = run(
        [
            "python3",
            str(TOOLS_SCHED / "reflect_scheduler_worker_v0_1.py"),
            "--db",
            str(db),
            "--workspace",
            str(ws),
            "--memory-index-db",
            str(index_db),
            "--reports-dir",
            str(reports),
            "--since-days",
            str(fixture_lookback_days),
            "--run-once",
        ]
    )
    worker = json.loads(worker_out)
    assert worker.get("ok") is True, "worker run should be ok"
    assert int(worker.get("processed", 0)) >= 1, "worker should process at least one job"
    assert int(worker.get("succeeded", 0)) >= 1, "worker should succeed at least one job"

    stats_out = run([
        "python3",
        str(TOOLS_SCHED / "scheduler_v0_1.py"),
        "--db",
        str(db),
        "stats",
    ])
    stats = json.loads(stats_out)
    assert int(stats.get("succeeded", 0)) >= 1, "scheduler should have succeeded jobs"

    summary_files = list(reports.rglob("summary.json"))
    assert summary_files, "worker should emit summary artifacts"
    summary = json.loads(summary_files[0].read_text(encoding="utf-8"))
    assert summary.get("proposals", 0) >= 1, "summary should include proposals"
    assert "apply_plan" in summary and "apply_exec" in summary, "summary should include apply outputs"

    out = {
        "ok": True,
        "tmp": str(tmp),
        "worker": {
            "processed": worker.get("processed"),
            "succeeded": worker.get("succeeded"),
            "failed": worker.get("failed"),
            "mode": worker.get("mode"),
        },
        "scheduler": {
            "queued": stats.get("queued"),
            "running": stats.get("running"),
            "succeeded": stats.get("succeeded"),
            "dead_letter": stats.get("dead_letter"),
        },
        "artifact_summary": {
            "path": str(summary_files[0]),
            "proposals": summary.get("proposals"),
            "apply_count": summary.get("apply_plan", {}).get("apply_count"),
            "blocked_count": summary.get("apply_plan", {}).get("blocked_count"),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
