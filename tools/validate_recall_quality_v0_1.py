#!/usr/bin/env python3
"""Validate recall quality baseline (accuracy/recall/noise + M->E input quality)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import memory_index_v0_1 as mi  # noqa: E402

DEFAULT_FIXTURE = ROOT / "data" / "fixtures" / "recall-quality-v0_1" / "cases.json"
DEFAULT_BASELINE = ROOT / "data" / "fixtures" / "recall-quality-v0_1" / "baseline.json"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _is_me_input_valid(fact: dict) -> bool:
    try:
        if not isinstance(fact.get("id"), str) or not fact["id"]:
            return False
        if fact.get("kind") not in {"W", "B", "O", "S"}:
            return False
        if not isinstance(fact.get("content"), str) or not fact["content"].strip():
            return False
        if not isinstance(fact.get("entities"), list):
            return False
        conf = float(fact.get("confidence"))
        if conf < 0.0 or conf > 1.0:
            return False
        if not isinstance(fact.get("source_ref"), str) or "#L" not in fact["source_ref"]:
            return False
    except Exception:
        return False
    return True


def evaluate_case(c, case: dict) -> dict:
    query = case.get("query")
    kind = case.get("kind")
    entity = case.get("entity")
    since_days = case.get("since_days")
    limit = int(case.get("limit", 20))

    out = mi.cmd_recall(c, query=query, kind=kind, entity=entity, since_days=since_days, limit=limit)
    facts = out.get("facts", [])

    returned = len(facts)
    refs = [f.get("source_ref") for f in facts if isinstance(f.get("source_ref"), str)]

    expected_refs = case.get("expected_source_refs", [])
    expect_count = case.get("expect_count")

    if expected_refs:
        hit = sum(1 for r in expected_refs if r in refs)
        recall_score = hit / len(expected_refs)
    else:
        hit = 0
        if expect_count is None:
            expect_count = 0
        recall_score = 1.0 if returned == int(expect_count) else 0.0

    precision = (hit / returned) if returned > 0 else (1.0 if (expect_count == 0 or not expected_refs) else 0.0)
    noise_rate = 1.0 - precision if returned > 0 else 0.0

    valid_count = sum(1 for f in facts if _is_me_input_valid(f))
    me_input_valid_rate = (valid_count / returned) if returned > 0 else 1.0

    min_hits = int(case.get("min_hits", len(expected_refs) if expected_refs else int(expect_count or 0)))
    max_noise = float(case.get("max_noise", 1.0))
    min_me_input_valid_rate = float(case.get("min_me_input_valid_rate", 1.0))

    passed = (
        (hit >= min_hits)
        and (noise_rate <= max_noise)
        and (me_input_valid_rate >= min_me_input_valid_rate)
    )

    return {
        "id": case.get("id", "case"),
        "query": query,
        "kind": kind,
        "entity": entity,
        "since_days": since_days,
        "limit": limit,
        "returned": returned,
        "hit": hit,
        "expected_count": len(expected_refs) if expected_refs else int(expect_count or 0),
        "recall": round(recall_score, 4),
        "precision": round(precision, 4),
        "noise_rate": round(noise_rate, 4),
        "me_input_valid_rate": round(me_input_valid_rate, 4),
        "passed": passed,
        "top_source_refs": refs[:5],
    }


def run_validation(fixture_file: Path, baseline_file: Path, strict: bool = True) -> dict:
    spec = json.loads(fixture_file.read_text(encoding="utf-8"))
    baseline = json.loads(baseline_file.read_text(encoding="utf-8"))

    ws_rel = spec.get("workspace_fixture")
    if not ws_rel:
        raise ValueError("fixture spec missing workspace_fixture")

    workspace_src = (ROOT / ws_rel).resolve()
    if not workspace_src.exists():
        raise ValueError(f"workspace fixture not found: {workspace_src}")

    cases = spec.get("cases") or []
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture spec cases[] must be non-empty")

    tmp = Path(tempfile.mkdtemp(prefix="mk-recall-q-v01-"))
    ws = tmp / "workspace"
    shutil.copytree(workspace_src, ws)
    db = tmp / "index.sqlite"

    c = mi.connect(db)
    mi.init_db(c)
    reindex = mi.cmd_reindex(c, workspace=ws, incremental=True, retry_failures=True, max_retries=3)

    case_reports = [evaluate_case(c, case) for case in cases]

    accuracy = _mean([1.0 if x["passed"] else 0.0 for x in case_reports])
    macro_recall = _mean([float(x["recall"]) for x in case_reports])
    macro_noise = _mean([float(x["noise_rate"]) for x in case_reports])
    me_input_valid_rate = _mean([float(x["me_input_valid_rate"]) for x in case_reports])

    thresholds = baseline.get("thresholds", {})
    checks = {
        "accuracy": accuracy >= float(thresholds.get("min_accuracy", 0.0)),
        "macro_recall": macro_recall >= float(thresholds.get("min_macro_recall", 0.0)),
        "macro_noise": macro_noise <= float(thresholds.get("max_macro_noise", 1.0)),
        "me_input_valid_rate": me_input_valid_rate >= float(thresholds.get("min_me_input_valid_rate", 0.0)),
    }

    ok = all(checks.values())

    report = {
        "ok": ok,
        "strict": strict,
        "fixture": str(fixture_file),
        "baseline": str(baseline_file),
        "workspace": str(ws),
        "db": str(db),
        "reindex": {
            "docs": reindex.get("docs", 0),
            "facts": reindex.get("facts", 0),
            "failed": reindex.get("failed", 0),
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "macro_recall": round(macro_recall, 4),
            "macro_noise": round(macro_noise, 4),
            "me_input_valid_rate": round(me_input_valid_rate, 4),
        },
        "thresholds": thresholds,
        "checks": checks,
        "cases": case_reports,
    }

    if strict and not ok:
        raise AssertionError(json.dumps(report, ensure_ascii=False, indent=2))

    return report


def main():
    p = argparse.ArgumentParser(description="Validate recall quality baseline v0.1")
    p.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="cases json path")
    p.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="baseline json path")
    p.add_argument("--out", help="optional report output path")
    p.add_argument("--no-strict", action="store_true", help="do not fail on threshold regression")
    args = p.parse_args()

    fixture = Path(args.fixture).expanduser().resolve()
    baseline = Path(args.baseline).expanduser().resolve()

    report = run_validation(fixture, baseline, strict=not args.no_strict)

    if args.out:
        out = Path(args.out).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["out"] = str(out)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
