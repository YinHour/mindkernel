#!/usr/bin/env python3
"""Release pre-check aggregator for v0.1.0-usable (S10)."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckItem:
    name: str
    command: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_check(item: CheckItem, timeout_sec: int = 240) -> dict:
    p = subprocess.run(
        item.command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    return {
        "name": item.name,
        "ok": p.returncode == 0,
        "returncode": p.returncode,
        "command": " ".join(item.command),
        "stdout": p.stdout[-4000:],
        "stderr": p.stderr[-4000:],
    }


def render_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# Release Check Report: {report['release_target']}")
    lines.append("")
    lines.append(f"- generated_at: {report['generated_at']}")
    lines.append(f"- ok: {report['ok']}")
    lines.append(f"- checks: {report['passed']}/{report['total']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for c in report["checks"]:
        mark = "✅" if c["ok"] else "❌"
        lines.append(f"- {mark} **{c['name']}** (`{c['command']}`)")
    lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Run release check for v0.1.0-usable")
    p.add_argument("--release-target", default="v0.1.0-usable")
    p.add_argument("--out-json", default=str(ROOT / "reports" / "release_check_v0_1.json"))
    p.add_argument("--out-md", default=str(ROOT / "reports" / "release_check_v0_1.md"))
    p.add_argument("--timeout-sec", type=int, default=240)
    p.add_argument("--quick", action="store_true", help="run reduced checks (no unit-tests/system-smoke)")
    p.add_argument("--no-strict", action="store_true", help="return success even if checks fail")
    args = p.parse_args()

    checks = [
        CheckItem("unit-tests", ["python3", "-m", "unittest", "discover", "-s", "test", "-p", "test_*_v0_1.py", "-v"]),
        CheckItem("validate-scenarios", ["python3", "tools/validate_scenarios_v0_1.py"]),
        CheckItem("validate-memory-index", ["python3", "tools/validate_memory_index_v0_1.py"]),
        CheckItem("validate-opinion-conflicts", ["python3", "tools/validate_opinion_conflicts_v0_1.py"]),
        CheckItem("validate-recall-quality", ["python3", "tools/validate_recall_quality_v0_1.py"]),
        CheckItem("validate-memory-import", ["python3", "tools/validate_memory_import_v0_1.py"]),
        CheckItem("validate-scheduler-worker", ["python3", "tools/validate_scheduler_worker_v0_1.py"]),
        CheckItem("validate-apply-compensation", ["python3", "tools/validate_apply_compensation_v0_1.py"]),
        CheckItem("validate-ingest-tools", ["python3", "tools/validate_ingest_tools_v0_1.py"]),
        CheckItem("validate-llm-memory-processor", ["python3", "tools/validate_llm_memory_processor_v0_1.py"]),
        CheckItem("system-smoke", ["python3", "tools/system_smoke_report_v0_1.py"]),
    ]

    if args.quick:
        checks = [c for c in checks if c.name not in {"unit-tests", "system-smoke"}]

    results = [run_check(c, timeout_sec=max(30, int(args.timeout_sec))) for c in checks]
    passed = sum(1 for r in results if r["ok"])

    report = {
        "ok": passed == len(results),
        "release_target": args.release_target,
        "generated_at": now_iso(),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "checks": results,
    }

    out_json = Path(args.out_json).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = Path(args.out_md).expanduser().resolve()
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": report["ok"],
                "release_target": report["release_target"],
                "passed": report["passed"],
                "total": report["total"],
                "out_json": str(out_json),
                "out_md": str(out_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    if not args.no_strict and not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
