#!/usr/bin/env python3
"""
MindKernel v0.2 Cognition Engine
Experience → Cognition 转换层

将 experience_records 中的经验晋升为认知规则（Cognition），
写入 cognition_rules 表，供 C→D 闭环使用。

_epistemic_state 推导规则：
  - outcome=positive AND confidence >= 0.6  → supported
  - outcome=negative OR confidence < 0.4    → refuted
  - otherwise                               → uncertain

_unknown_type 推导规则（仅 uncertain 时）：
  - episode_summary 含 "边界"/"超范围" → out_of_scope
  - episode_summary 含 "不确定"/"两可" → multipath
  - otherwise                               → ontic_unknowable

_risk_tier 推导：
  - 已知的 blocked/abstained 决策 → high
  - experience.confidence < 0.5    → medium
  - otherwise                      → low

_impact_tier 推导：
  - outcome=positive → medium
  - outcome=negative → high
  - otherwise        → low

Decision mode if uncertain → explore（低风险默认探索）
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from schema_runtime import SchemaValidationError, validate_payload

DEFAULT_DB = ROOT / "data" / "mindkernel_v0_1.sqlite"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def in_days_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def conn(db_path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    return c


def _derive_epistemic_state(outcome: str, confidence: float) -> str:
    if outcome == "positive" and confidence >= 0.6:
        return "supported"
    if outcome == "negative" or confidence < 0.4:
        return "refuted"
    return "uncertain"


def _derive_unknown_type(episode_summary: str) -> str:
    s = episode_summary.lower()
    if any(kw in s for kw in ("边界", "超范围", "out_of_scope", "scope")):
        return "out_of_scope"
    if any(kw in s for kw in ("不确定", "两可", "multiple", "ambiguous", "歧义")):
        return "multipath"
    return "ontic_unknowable"


def _derive_risk_tier(outcome: str, confidence: float, episode_summary: str = "") -> str:
    s = episode_summary.lower()
    # 有明确阻断关键词 → high
    if any(kw in s for kw in ("blocked", "abstained", "拒绝", "阻断", "违规")):
        return "high"
    if outcome == "negative" and confidence < 0.5:
        return "medium"
    return "low"


def _derive_impact_tier(outcome: str) -> str:
    if outcome == "positive":
        return "medium"
    if outcome == "negative":
        return "high"
    return "low"


def _derive_rule(experience_payload: dict, epistemic_state: str) -> str:
    """从 experience 生成自然语言认知规则摘要。"""
    summary = experience_payload.get("episode_summary", "")
    outcome = experience_payload.get("outcome", "")
    action = experience_payload.get("action_taken", "")

    state_map = {
        "supported": "已知有效",
        "uncertain": "尚待验证",
        "refuted": "已证伪",
    }
    state_label = state_map.get(epistemic_state, epistemic_state)

    rule_parts = [f"[{state_label}]"]
    if action and action != "derive_from_memory":
        rule_parts.append(f"动作: {action}")
    if summary:
        # 截取前120字符
        snippet = summary[:120].strip()
        rule_parts.append(f"经验: {snippet}")
    rule_parts.append(f"结论状态: {state_label}")

    return " | ".join(rule_parts)


def _derive_scope(experience_payload: dict) -> dict:
    """从 experience payload 推导 scope。domains/channels 留空（未知）。"""
    outcome = experience_payload.get("outcome", "")
    risk_tier = _derive_risk_tier(
        outcome,
        experience_payload.get("confidence", 0.5),
        experience_payload.get("episode_summary", ""),
    )
    return {
        "domains": [],
        "channels": [],
        "risk_tier_max": risk_tier,
    }


def experience_to_cognition(
    c: sqlite3.Connection,
    experience_id: str,
    actor_id: str = "mk-cognition-engine",
) -> dict:
    """
    将一条 experience 晋升为 cognition 写入 cognition_rules 表。

    Returns:
        {"cognition_id": str, "status": str, "epistemic_state": str, "confidence": float}
    """
    row = c.execute(
        "SELECT payload_json FROM experience_records WHERE id=?",
        (experience_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"experience not found: {experience_id}")

    exp_payload = json.loads(row["payload_json"])

    outcome = exp_payload.get("outcome", "neutral")
    confidence = float(exp_payload.get("confidence", 0.5))
    epistemic_state = _derive_epistemic_state(outcome, confidence)

    unknown_type = "multipath"
    decision_mode_if_uncertain = "explore"
    auto_verify_budget = 3
    if epistemic_state != "uncertain":
        unknown_type = None
        decision_mode_if_uncertain = None
        auto_verify_budget = None

    cognition_id = f"cog_{uuid.uuid4().hex[:12]}"
    risk_tier = _derive_risk_tier(outcome, confidence, exp_payload.get("episode_summary", ""))
    impact_tier = _derive_impact_tier(outcome)
    scope = _derive_scope(exp_payload)
    rule_text = _derive_rule(exp_payload, epistemic_state)

    evidence_refs = exp_payload.get("memory_refs", [])
    if not evidence_refs:
        evidence_refs = [experience_id]

    review_due_at_val = in_days_iso(14)
    next_action_at_val = in_days_iso(7)

    cognition_payload: dict = {
        "id": cognition_id,
        "rule": rule_text,
        "scope": scope,
        "epistemic_state": epistemic_state,
        "confidence": round(confidence, 3),
        "falsify_if": f"outcome=='{outcome}'_confidence_dropped",
        "review_interval": "P14D",
        "risk_tier": risk_tier,
        "impact_tier": impact_tier,
        "status": "candidate",
        "evidence_refs": evidence_refs,
        "created_at": now_iso(),
        "review_due_at": review_due_at_val,
        "next_action_at": next_action_at_val,
        "updated_at": now_iso(),
    }

    # uncertain 时才加入这几个字段（schema allOf if-then 要求）
    if epistemic_state == "uncertain":
        cognition_payload["unknown_type"] = _derive_unknown_type(exp_payload.get("episode_summary", ""))
        cognition_payload["decision_mode_if_uncertain"] = "explore"
        cognition_payload["uncertainty_ttl"] = "P14D"
        cognition_payload["auto_verify_budget"] = 3

    try:
        validate_payload("cognition.schema.json", cognition_payload)
    except SchemaValidationError as e:
        raise ValueError(f"cognition schema validation failed: {e}") from e

    # 检查是否已存在
    exists = c.execute(
        "SELECT 1 FROM cognition_rules WHERE id=?",
        (cognition_id,),
    ).fetchone()
    if exists:
        raise ValueError(f"cognition already exists: {cognition_id}")

    # 去重：同一 experience 已有 cognition 则跳过（查 payload_json 中的 evidence_refs）
    existing = c.execute(
        """
        SELECT id FROM cognition_rules
        WHERE payload_json LIKE ?
        LIMIT 1
        """,
        (f"%{experience_id}%",),
    ).fetchone()
    if existing:
        return {
            "cognition_id": existing["id"],
            "status": "duplicate",
            "skipped": True,
            "experience_id": experience_id,
        }

    t = now_iso()
    c.execute(
        "INSERT INTO cognition_rules(id, status, payload_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (
            cognition_id,
            cognition_payload["status"],
            json.dumps(cognition_payload, ensure_ascii=False),
            t,
            t,
        ),
    )

    # 写入 audit
    _write_audit(
        c,
        event_type="state_transition",
        actor_type="system",
        actor_id=actor_id,
        object_type="cognition",
        object_id=cognition_id,
        before={"status": None},
        after={"status": "candidate", "epistemic_state": epistemic_state},
        reason="Experience promoted to cognition via cognition_engine.",
        evidence_refs=evidence_refs,
        metadata={"experience_id": experience_id},
    )

    c.commit()

    return {
        "cognition_id": cognition_id,
        "status": cognition_payload["status"],
        "epistemic_state": epistemic_state,
        "confidence": cognition_payload["confidence"],
        "risk_tier": risk_tier,
        "impact_tier": impact_tier,
        "experience_id": experience_id,
    }


def batch_experience_to_cognition(
    c: sqlite3.Connection,
    experience_ids: list[str] | None = None,
    since_days: int = 30,
    actor_id: str = "mk-cognition-engine",
) -> dict:
    """
    批量将 experience 晋升为 cognition。

    Args:
        experience_ids: 指定 ID 列表；为 None 则查询最近 since_days 的 candidate/experience 记录
    """
    if experience_ids:
        placeholders = ",".join("?" * len(experience_ids))
        rows = c.execute(
            f"SELECT id, payload_json FROM experience_records WHERE id IN ({placeholders})",
            experience_ids,
        ).fetchall()
    else:
        cutoff = in_days_iso(-since_days)
        rows = c.execute(
            """
            SELECT id, payload_json FROM experience_records
            WHERE created_at >= ? AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (cutoff,),
        ).fetchall()

    results = []
    skipped = 0
    for row in rows:
        try:
            result = experience_to_cognition(c, row["id"], actor_id)
            if result.get("skipped"):
                skipped += 1
            results.append(result)
        except Exception as e:
            results.append({"experience_id": row["id"], "error": str(e)})

    applied = [r for r in results if not r.get("error") and not r.get("skipped")]
    return {
        "total": len(rows),
        "applied": len(applied),
        "skipped": skipped,
        "failed": sum(1 for r in results if r.get("error")),
        "results": results,
    }


def _write_audit(
    c: sqlite3.Connection,
    *,
    event_type: str,
    actor_type: str,
    actor_id: str,
    object_type: str,
    object_id: str,
    before: dict,
    after: dict,
    reason: str,
    evidence_refs: list[str],
    correlation_id: str | None = None,
    metadata: dict | None = None,
):
    ts = now_iso()
    event_id = f"aud_{uuid.uuid4().hex[:12]}"
    payload = {
        "id": event_id,
        "event_type": event_type,
        "actor": {"type": actor_type, "id": actor_id},
        "object_type": object_type,
        "object_id": object_id,
        "before": before,
        "after": after,
        "reason": reason,
        "evidence_refs": evidence_refs,
        "timestamp": ts,
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id
    if metadata:
        payload["metadata"] = metadata

    c.execute(
        """
        INSERT INTO audit_events(id, event_type, object_type, object_id, correlation_id, timestamp, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_id, event_type, object_type, object_id, correlation_id, ts, json.dumps(payload, ensure_ascii=False)),
    )


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="MindKernel Cognition Engine")
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--experience-id", help="Process single experience")
    p.add_argument("--batch", action="store_true")
    p.add_argument("--since-days", type=int, default=30)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    db = Path(args.db)
    c = conn(db)

    if args.experience_id:
        result = experience_to_cognition(c, args.experience_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.batch:
        result = batch_experience_to_cognition(c, since_days=args.since_days)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Specify --experience-id or --batch")
