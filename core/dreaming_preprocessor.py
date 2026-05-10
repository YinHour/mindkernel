#!/usr/bin/env python3
"""
Dreaming Preprocessor — 做梦输入预处理

集成 TopicSegmenter + DialogueContextResolver，
为做梦 LLM 提供结构化的语义输入：
- 最近 7 天记忆摘要
- 最近 30 天经验摘要
- 话题分割单元
- 任务闭环状态
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "mindkernel_v0_1.sqlite"

logger = logging.getLogger("dreaming.preprocessor")

MEMORY_DAYS = 7
EXPERIENCE_DAYS = 30
MAX_MEMORY_SUMMARY_LEN = 3000
MAX_EXPERIENCE_SUMMARY_LEN = 2000
MAX_SEGMENT_SUMMARY_LEN = 1000


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def days_ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ── 记忆摘要 ────────────────────────────────────────────────────────────────

def get_memory_summaries() -> tuple[list[dict], str]:
    """
    返回 (raw_items, summary_text)
    raw_items: [{id, content, created_at, importance}]
    summary_text: 合并的摘要字符串（供 LLM 使用）
    """
    since = days_ago_iso(MEMORY_DAYS)
    items = []

    with conn() as c:
        rows = c.execute(
            """SELECT id, payload_json, created_at FROM memory_items
               WHERE status IN ('active', 'candidate')
                 AND created_at >= ?
               ORDER BY created_at DESC
               LIMIT 200""",
            (since,),
        ).fetchall()

        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
                content = payload.get("content", payload.get("text", ""))
                importance = payload.get("importance", 0.5)
            except Exception:
                content = str(r["payload_json"])
                importance = 0.5

            items.append({
                "id": r["id"],
                "content": content[:500],  # 截断
                "created_at": r["created_at"],
                "importance": importance,
            })

    # 生成摘要文本
    if not items:
        summary = "（近 7 天无记忆数据）"
    else:
        lines = []
        for item in items[:50]:  # 最多 50 条
            ts = item["created_at"][:10]
            lines.append(f"[{ts}] {item['content'][:200]}")
        summary = "\n".join(lines)
        if len(summary) > MAX_MEMORY_SUMMARY_LEN:
            summary = summary[:MAX_MEMORY_SUMMARY_LEN] + "\n...（以上为前50条，共" + str(len(items)) + "条记忆）"

    return items, summary


# ── 经验摘要 ────────────────────────────────────────────────────────────────

def get_experience_summaries() -> tuple[list[dict], str]:
    """返回 (raw_items, summary_text)"""
    since = days_ago_iso(EXPERIENCE_DAYS)
    items = []

    with conn() as c:
        rows = c.execute(
            """SELECT id, payload_json, created_at FROM experience_records
               WHERE status IN ('active')
                 AND created_at >= ?
               ORDER BY created_at DESC
               LIMIT 100""",
            (since,),
        ).fetchall()

        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
                content = payload.get("episode_summary", payload.get("content", ""))
                outcome = payload.get("outcome", "")
                confidence = payload.get("confidence", 0.5)
            except Exception:
                content = str(r["payload_json"])
                outcome = ""
                confidence = 0.5

            items.append({
                "id": r["id"],
                "content": content[:500],
                "outcome": outcome,
                "confidence": confidence,
                "created_at": r["created_at"],
            })

    if not items:
        summary = "（近 30 天无经验数据）"
    else:
        lines = []
        for item in items:
            outcome_tag = f"[{item['outcome']}]" if item['outcome'] else ""
            lines.append(f"- {outcome_tag} {item['content'][:200]}")
        summary = "\n".join(lines)
        if len(summary) > MAX_EXPERIENCE_SUMMARY_LEN:
            summary = summary[:MAX_EXPERIENCE_SUMMARY_LEN] + f"\n...（以上共{len(items)}条经验）"

    return items, summary


# ── 话题分割 ────────────────────────────────────────────────────────────────

def get_topic_segments() -> str:
    """
    加载 TopicSegmenter，对近期记忆进行话题分割，
    返回分割后的摘要文本。
    """
    # 延迟导入，避免循环
    try:
        from core.topic_segmenter import TopicSegmenter
        segmenter = TopicSegmenter()

        # 取近期记忆用于分割
        since = days_ago_iso(MEMORY_DAYS)
        messages = []
        with conn() as c:
            rows = c.execute(
                """SELECT payload_json, created_at FROM memory_items
                   WHERE status IN ('active', 'candidate')
                     AND created_at >= ?
                   ORDER BY created_at ASC""",
                (since,),
            ).fetchall()
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                    text = payload.get("content", payload.get("text", ""))
                    role = payload.get("role", "user")
                except Exception:
                    text = str(r["payload_json"])
                    role = "user"
                if text.strip():
                    messages.append({
                        "role": role,
                        "content": text,
                        "timestamp": r["created_at"],
                    })

        if not messages:
            return "（无话题数据）"

        segments = segmenter.segment(messages)
        lines = []
        for seg in segments[:20]:  # 最多 20 个话题
            # TopicSegment 是 dataclass，用属性访问
            seg_type = getattr(seg, "type", "unknown")
            summary = getattr(seg, "summary", getattr(seg, "description", ""))[:150]
            lines.append(f"[{seg_type}] {summary}")
        return "\n".join(lines) if lines else "（无话题数据）"

    except Exception as e:
        logger.warning(f"[DreamingPreprocessor] 话题分割失败: {e}")
        return f"（话题分割暂不可用: {e}）"


# ── 任务闭环状态 ────────────────────────────────────────────────────────────

def get_task_closure_summary() -> str:
    """
    通过 DialogueContextResolver.active_tasks 获取活跃任务摘要。
    """
    try:
        from core.dialogue_context_resolver import DialogueContextResolver
        resolver = DialogueContextResolver()

        active = resolver.active_tasks or []

        if not active:
            return "（无活跃任务数据）"

        lines = [f"⏳ 活跃任务（{len(active)}个）:"]
        for task in active[:15]:
            desc = task.get("description", str(task))[:100]
            lines.append(f"  - {desc}")
        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"[DreamingPreprocessor] 任务闭环检测失败: {e}")
        return f"（任务闭环检测暂不可用: {e}）"


# ── 打包全部输入 ─────────────────────────────────────────────────────────────

def build_dreaming_input() -> dict:
    """
    构建完整的做梦 LLM 输入数据。
    """
    memory_items, memory_summary = get_memory_summaries()
    exp_items, exp_summary = get_experience_summaries()
    topic_segments = get_topic_segments()
    task_summary = get_task_closure_summary()

    return {
        "memory_count": len(memory_items),
        "memory_items": memory_items,
        "memory_summary": memory_summary,
        "experience_count": len(exp_items),
        "experience_items": exp_items,
        "experience_summary": exp_summary,
        "topic_segments": topic_segments,
        "task_closure_summary": task_summary,
        "generated_at": now_iso(),
    }


if __name__ == "__main__":
    import pprint
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    data = build_dreaming_input()
    print(f"记忆: {data['memory_count']} 条")
    print(f"经验: {data['experience_count']} 条")
    print("=== 记忆摘要（前300字）===")
    print(data["memory_summary"][:300])
    print("=== 话题分割 ===")
    print(data["topic_segments"][:500])
    print("=== 任务闭环 ===")
    print(data["task_closure_summary"][:500])
