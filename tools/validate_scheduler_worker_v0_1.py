#!/usr/bin/env python3
"""Validate reflect scheduler worker loop (S7)."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main():
    if not FIXTURE_WS.exists():
        raise SystemExit(f"fixture workspace missing: {FIXTURE_WS}")

    tmp = Path(tempfile.mkdtemp(prefix="mk-worker-v01-"))
    ws = tmp / "workspace"
    shutil.copytree(FIXTURE_WS, ws)

    db = tmp / "scheduler.sqlite"
    index_db = tmp / "index.sqlite"
    reports = tmp / "reports"

    # enqueue one due reflect job
    run(
        [
            "python3",
            str(TOOLS / "scheduler_v0_1.py"),
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
            now_iso(),
            "--priority",
            "high",
            "--idempotency-key",
            "reflect:test:worker:v0_1",
        ]
    )

    worker_out = run(
        [
            "python3",
            str(TOOLS / "reflect_scheduler_worker_v0_1.py"),
            "--db",
            str(db),
            "--workspace",
            str(ws),
            "--memory-index-db",
            str(index_db),
            "--reports-dir",
            str(reports),
            "--run-once",
        ]
    )
    worker = json.loads(worker_out)
    assert worker.get("ok") is True, "worker run should be ok"
    assert int(worker.get("processed", 0)) >= 1, "worker should process at least one job"
    assert int(worker.get("succeeded", 0)) >= 1, "worker should succeed at least one job"

    stats_out = run([
        "python3",
        str(TOOLS / "scheduler_v0_1.py"),
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
