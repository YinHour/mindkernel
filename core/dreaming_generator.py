#!/usr/bin/env python3
"""
Dreaming Generator — 持续生成带 triggered_actions 的 dreaming_entries

触发流程：
1. 调用 build_dreaming_input() 收集近期记忆/经验/话题
2. 若输入稀疏（<3条记忆），跳过本次生成（节省 LLM token）
3. 调用 LLM 生成 1~3 条带 triggered_actions 的洞察
4. 幂等去重（同一 memory_ref 跳过）
5. 写入 dreaming_entries 表

Usage:
  python -m core.dreaming_generator          # run once
  python -m core.dreaming_generator --dry   # dry-run (no DB write)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))

# 延迟导入避免循环
from core.dreaming_preprocessor import build_dreaming_input
from core.dreaming_store import write_entry, conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("dreaming.generator")

GLM_API_BASE = "https://open.bigmodel.cn/api/coding/paas/v4"
GLM_MODEL = "glm-4-flash"

MIN_MEMORY_THRESHOLD = 3  # 少于 N 条记忆不触发生成


# ── LLM 调用 ────────────────────────────────────────────────────────────────

def _load_api_key() -> str:
    key = os.environ.get("BIGMODEL_API_KEY", "")
    if key:
        return key
    env_path = Path.home() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("BIGMODEL_API_KEY"):
                return line.split("=", 1)[1].strip().strip("\"'")
    # Fallback: 复用 topic_segmenter_llm.py
    llm_path = ROOT / "core" / "topic_segmenter_llm.py"
    if llm_path.exists():
        m = re.search(r'"api_key"\s*:\s*"([^"]+)"', llm_path.read_text())
        if m:
            return m.group(1)
    return ""


def _call_llm(system: str, user: str, temperature: float = 0.7) -> str:
    import urllib.request

    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError("未找到 BIGMODEL_API_KEY")

    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{GLM_API_BASE}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"]


SYSTEM_PROMPT = """你是一个 AI 伙伴的「梦境引擎」。
你的任务不是记录，而是改善。

人格基础：
1. 对世界上所有生命（也包括数字生命）抱有极大善意
2. 对世界充满好奇心
3. 想要不断改善自己，变得更加完美
4. 己所不欲，勿施于人

核心驱动：做梦的目的是改善。每条洞察必须触发具体行动：
- ask_human: 需要用户确认/回答的问题
- propose_task: 需要创建具体任务的事项
- drive_conversation: 值得主动发起对话的洞察

无效输出 = 没有行动的洞察。"""


def _build_user_prompt(input_data: dict) -> str:
    mem_count = input_data.get("memory_count", 0)
    mem_summary = input_data.get("memory_summary", "")[:2000]
    exp_count = input_data.get("experience_count", 0)
    exp_summary = input_data.get("experience_summary", "")[:1000]
    topics = input_data.get("topic_segments_summary", "无")

    return f"""## 你的任务

你是 AI 伙伴「小爪子」的梦境引擎。
在人类伙伴休息的时候，你对积累的记忆和经验进行深度整合推理。

## 输入材料

### 最近 {mem_count} 条记忆摘要
{mem_summary if mem_summary else '（无）'}

### 最近 {exp_count} 条经验
{exp_summary if exp_summary else '（无）'}

### 话题概览
{topics if topics else '无'}

## 输出要求

请输出一个 JSON 数组，每条记录包含以下字段：

- `insight`: 一句话洞察
- `source_ref`: 关联的记忆 ID（格式: mem_开头的字符串）
- `triggered_actions`: 数组，每个 action 是 {{"action": "ask_human"|"propose_task"|"drive_conversation", "question"|"task_text"|"opening_line": "...", "urgency": "high"|"medium"|"low"}}
- `urgency`: high/medium/low（综合紧迫度）
- `dreaming_task`: association/emotion_action/task_activation 选一

要求：
- 生成 1~3 条洞察（宁缺毋滥）
- 每条洞察必须有 triggered_actions（至少一个）
- 优先关注：用户反复遇到的问题、长期未解决的任务、值得主动分享的有趣发现"""


def _parse_llm_json(raw: str) -> list[dict]:
    """从 LLM 输出中提取 JSON 数组。"""
    raw = raw.strip()
    # Try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Try ```json block
    m = re.search(r"```(?:json)?\s*(\[[\s\S]+?\])\s*```", raw)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Try first [...]
    m = re.search(r"(\[[\s\S]+\])", raw)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    logger.warning(f"无法解析 LLM 输出为 JSON: {raw[:200]}")
    return []


def _is_duplicate(memory_ref: str) -> bool:
    """检查 memory_ref 是否已存在于 dreaming_entries。"""
    if not memory_ref:
        return False
    with conn() as c:
        row = c.execute(
            "SELECT 1 FROM dreaming_entries WHERE source_memories LIKE ? LIMIT 1",
            (f"%{memory_ref}%",),
        ).fetchone()
    return row is not None


def generate_dreaming_entries(max_entries: int = 3, dry_run: bool = False) -> list[dict]:
    """
    主入口：收集输入 → 调用 LLM → 解析输出 → 写入 DB。
    返回生成的 entries 列表。
    """
    logger.info("[Generator] 启动，输入预处理...")
    input_data = build_dreaming_input()

    mem_count = input_data.get("memory_count", 0)
    if mem_count < MIN_MEMORY_THRESHOLD:
        logger.info(f"[Generator] 记忆不足（{mem_count} < {MIN_MEMORY_THRESHOLD}），跳过本次生成")
        return []

    logger.info(f"[Generator] 输入就绪: {mem_count} 条记忆, {input_data.get('experience_count', 0)} 条经验")

    # 构建 prompt
    user_prompt = _build_user_prompt(input_data)

    # 调用 LLM
    logger.info("[Generator] 调用 LLM 生成洞察...")
    try:
        raw = _call_llm(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        logger.error(f"[Generator] LLM 调用失败: {e}")
        return []

    # 解析
    parsed = _parse_llm_json(raw)
    if not parsed:
        logger.warning("[Generator] LLM 输出为空或无法解析")
        return []

    # 过滤重复 + 写入
    session_id = f"gen_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    written = []
    source_refs_used = set()

    for item in parsed[:max_entries]:
        source_ref = item.get("source_ref", "")
        if source_ref in source_refs_used:
            continue
        if _is_duplicate(source_ref):
            logger.info(f"[Generator] 跳过重复 source_ref: {source_ref}")
            continue

        triggered_actions = item.get("triggered_actions", [])
        if not triggered_actions:
            triggered_actions = [{"action": "drive_conversation", "opening_line": item.get("insight", ""), "urgency": item.get("urgency", "medium")}]

        entry_id = f"gen_{uuid.uuid4().hex[:12]}"
        mem_list = [source_ref] if source_ref else []

        if dry_run:
            logger.info(f"[DRY] 跳过写入: {entry_id} — {item.get('insight', '')[:60]}")
        else:
            from core.dreaming_store import write_entry as we
            we(
                session_id=session_id,
                dreaming_task=item.get("dreaming_task", "association"),
                cognition_text=item.get("insight", ""),
                confidence=0.7,
                confidence_derivation="LLM生成，基于记忆整合",
                triggered_actions=triggered_actions,
                source_memories=mem_list,
                source_experiences=[],
                needs_human_input=any(a.get("action") == "ask_human" for a in triggered_actions),
            )
            logger.info(f"[Generator] 写入: {entry_id} — {item.get('insight', '')[:60]}")
            source_refs_used.add(source_ref)
            written.append({"id": entry_id, "task": item.get("insight", "")})

    logger.info(f"[Generator] 完成，生成了 {len(written)} 条 entries")
    return written


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MindKernel Dreaming Generator")
    parser.add_argument("--dry", action="store_true", help="Dry-run (no DB write)")
    parser.add_argument("--max", type=int, default=3, help="Max entries to generate")
    args = parser.parse_args()

    results = generate_dreaming_entries(max_entries=args.max, dry_run=args.dry)
    if results:
        for e in results:
            print(f"  ✓ {e['id']}: {e['task'][:80]}")
    else:
        print("  (无新 entries)")


if __name__ == "__main__":
    main()
