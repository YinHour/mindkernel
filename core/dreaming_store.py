#!/usr/bin/env python3
"""
Dreaming Store — 做梦条目存储层

管理：
1. dreaming_entries 表（独立 C 层做梦条目）
2. dreaming_human_queue.jsonl（人类介入队列）
3. dreaming_sessions/ 日志目录

不写入 cognition_rules（保持隔离），只在 action 分发时关联。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "mindkernel_v0_1.sqlite"
QUEUE_PATH = ROOT / "data" / "dreaming_human_queue.jsonl"
SESSIONS_DIR = ROOT / "data" / "dreaming_sessions"
LEDGER_PATH = ROOT / "data" / "dreaming_actions_ledger.jsonl"

logger = logging.getLogger("dreaming.store")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def in_days_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ── 表初始化 ────────────────────────────────────────────────────────────────

INIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS dreaming_entries (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    task            TEXT NOT NULL,
    cognition_text  TEXT NOT NULL,
    confidence      REAL NOT NULL,
    confidence_derivation TEXT NOT NULL DEFAULT '',
    epistemic_state TEXT NOT NULL DEFAULT 'uncertain',
    unknown_type    TEXT NOT NULL DEFAULT 'multipath',
    falsify_if      TEXT NOT NULL DEFAULT '',
    review_interval TEXT NOT NULL DEFAULT 'P7D',
    risk_tier       TEXT NOT NULL DEFAULT 'medium',
    impact_tier     TEXT NOT NULL DEFAULT 'medium',
    decision_mode   TEXT NOT NULL DEFAULT 'explore',
    auto_verify_budget INTEGER NOT NULL DEFAULT 2,
    status          TEXT NOT NULL DEFAULT 'candidate',

    -- 做梦专用字段
    dreaming_task        TEXT NOT NULL,
    source_memories     TEXT NOT NULL DEFAULT '[]',
    source_experiences  TEXT NOT NULL DEFAULT '[]',
    triggered_actions   TEXT NOT NULL DEFAULT '[]',
    needs_human_input   INTEGER NOT NULL DEFAULT 0,
    human_input_queue_id TEXT,

    is_feedback_session  INTEGER NOT NULL DEFAULT 0,
    feedback_source_qid  TEXT,

    created_at_dream  TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dreaming_session
    ON dreaming_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_dreaming_status
    ON dreaming_entries(status);
CREATE INDEX IF NOT EXISTS idx_dreaming_human_qid
    ON dreaming_entries(human_input_queue_id);
"""


def ensure_table() -> None:
    with conn() as c:
        c.executescript(INIT_SCHEMA)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ── 写入做梦条目 ───────────────────────────────────────────────────────────

def write_entry(
    session_id: str,
    dreaming_task: str,
    cognition_text: str,
    confidence: float,
    confidence_derivation: str,
    triggered_actions: list,
    source_memories: list,
    source_experiences: list,
    needs_human_input: bool,
    is_feedback_session: bool = False,
    feedback_source_qid: Optional[str] = None,
) -> str:
    """
    写入一条做梦条目，返回 entry id。
    """
    ensure_table()

    entry_id = f"cog_dream_{uuid.uuid4().hex[:12]}"
    now = now_iso()

    # epistemic_state 推导（复用 cognition_engine 逻辑）
    epistemic_state = _derive_epistemic_state(confidence)
    unknown_type = "multipath"

    actions_json = json.dumps(triggered_actions, ensure_ascii=False)
    mems_json = json.dumps(source_memories, ensure_ascii=False)
    exps_json = json.dumps(source_experiences, ensure_ascii=False)

    queue_id = None
    if needs_human_input and triggered_actions:
        # 创建人类介入队列
        for a in triggered_actions:
            if a.get("action") == "ask_human":
                queue_id = write_human_queue(
                    question=a.get("question", ""),
                    related_memories=source_memories,
                    related_insight_id=entry_id,
                )
                break

    sql = """
    INSERT INTO dreaming_entries (
        id, session_id, task, cognition_text, confidence,
        confidence_derivation, epistemic_state, unknown_type,
        falsify_if, review_interval, risk_tier, impact_tier,
        decision_mode, auto_verify_budget, status,
        dreaming_task, source_memories, source_experiences,
        triggered_actions, needs_human_input, human_input_queue_id,
        is_feedback_session, feedback_source_qid,
        created_at_dream, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    with conn() as c:
        c.execute(sql, (
            entry_id, session_id, dreaming_task, cognition_text, confidence,
            confidence_derivation, epistemic_state, unknown_type,
            "", "P7D", "medium", "medium",
            "explore", 2, "candidate",
            dreaming_task, mems_json, exps_json,
            actions_json, 1 if needs_human_input else 0, queue_id,
            1 if is_feedback_session else 0, feedback_source_qid,
            now, now, now,
        ))

    logger.info(f"[DreamingStore] 写入条目: {entry_id}, task={dreaming_task}, confidence={confidence}")
    return entry_id


def _derive_epistemic_state(confidence: float) -> str:
    if confidence >= 0.7:
        return "supported"
    elif confidence < 0.4:
        return "refuted"
    return "uncertain"


# ── 人类介入队列 ────────────────────────────────────────────────────────────

def write_human_queue(
    question: str,
    related_memories: list,
    related_insight_id: str,
) -> str:
    """写入人类介入队列，返回 queue_id"""
    queue_id = f"q_{uuid.uuid4().hex[:8]}"
    entry = {
        "queue_id": queue_id,
        "question": question,
        "related_memories": related_memories,
        "related_insight_id": related_insight_id,
        "status": "pending",
        "created_at": now_iso(),
        "answered_at": None,
        "answer_text": None,
        "expires_at": in_days_iso(7),
    }

    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"[DreamingStore] 写入队列: {queue_id}, question={question[:50]}")
    return queue_id


def load_pending_questions() -> list[dict]:
    """加载所有 pending 的人类介入请求"""
    if not QUEUE_PATH.exists():
        return []
    results = []
    with open(QUEUE_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("status") == "pending":
                    results.append(entry)
            except Exception:
                pass
    return results


def update_queue_answered(queue_id: str, answer_text: str) -> bool:
    """标记队列项为已回答"""
    if not QUEUE_PATH.exists():
        return False

    now = now_iso()
    updated_lines = []
    found = False

    with open(QUEUE_PATH, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get("queue_id") == queue_id:
                entry["status"] = "answered"
                entry["answered_at"] = now
                entry["answer_text"] = answer_text
                found = True
            updated_lines.append(json.dumps(entry, ensure_ascii=False))

    if found:
        with open(QUEUE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(updated_lines) + "\n")
        logger.info(f"[DreamingStore] 更新队列已回答: {queue_id}")

    return found


def expire_old_questions() -> int:
    """过期 7 天未回答的队列项"""
    if not QUEUE_PATH.exists():
        return 0

    now = datetime.now(timezone.utc)
    updated_lines = []
    expired_count = 0

    with open(QUEUE_PATH, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get("status") == "pending":
                try:
                    expires = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
                    if now > expires:
                        entry["status"] = "expired"
                        expired_count += 1
                except Exception:
                    pass
            updated_lines.append(json.dumps(entry, ensure_ascii=False))

    if expired_count > 0:
        with open(QUEUE_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(updated_lines) + "\n")
        logger.info(f"[DreamingStore] 过期 {expired_count} 条队列项")

    return expired_count


# ── Session 日志 ─────────────────────────────────────────────────────────────

def write_session_log(session_id: str, data: dict) -> None:
    """写入 session 日志到 data/dreaming_sessions/YYYY-MM-DD.jsonl"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    log_path = SESSIONS_DIR / f"{today}.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"session_id": session_id, **data}, ensure_ascii=False) + "\n")


# ── Action Ledger（幂等） ──────────────────────────────────────────────────

def is_action_dispatched(action_id: str) -> bool:
    """检查 action 是否已分发（幂等）"""
    if not LEDGER_PATH.exists():
        return False
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get("action_id") == action_id:
                return True
    return False


def mark_action_dispatched(action_id: str, result: dict) -> None:
    """标记 action 已分发"""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"action_id": action_id, "result": result, "dispatched_at": now_iso()}
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 查询 ────────────────────────────────────────────────────────────────────

def get_entries_by_session(session_id: str) -> list[dict]:
    """获取某 session 的所有条目"""
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM dreaming_entries WHERE session_id=? ORDER BY created_at",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_human_queue_entry(queue_id: str) -> Optional[dict]:
    """通过 queue_id 查队列项"""
    if not QUEUE_PATH.exists():
        return None
    with open(QUEUE_PATH, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line.strip())
            if entry.get("queue_id") == queue_id:
                return entry
    return None


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ensure_table()
    print("表初始化完成")
    print(f"pending 问题: {len(load_pending_questions())} 条")
