#!/usr/bin/env python3
"""
Dreaming Worker — 做梦主逻辑

触发流程：
1. 加载预处理数据（记忆/经验/话题/任务）
2. 构建 LLM Prompt
3. 调用 LLM（GLM-4.7 mini）
4. 解析输出，写入 dreaming_entries
5. 分发 triggered_actions
6. 记录 session log
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

# 延迟导入避免循环
from core.dreaming_preprocessor import build_dreaming_input
from core.dreaming_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from core.dreaming_store import (
    write_entry,
    write_session_log,
    get_human_queue_entry,
)
from core.dreaming_state import TRIGGER_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "logs" / "dreaming_worker.log"),
    ],
)
logger = logging.getLogger("dreaming.worker")

DB_PATH = ROOT / "data" / "mindkernel_v0_1.sqlite"

# ── LLM 调用 ────────────────────────────────────────────────────────────────

GLM_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-4-flash"  # 速度快，成本低


def _call_glm(system: str, user: str, temperature: float = 0.7) -> str:
    """调用 GLM-4 API"""
    import urllib.request

    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
    }

    api_key = _load_api_key()
    if not api_key:
        raise RuntimeError("未找到 GLM API Key，请在 environment 或 ~/.env 中设置 BIGMODEL_API_KEY")

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


def _load_api_key() -> str:
    """尝试从多处加载 API Key"""
    import os
    key = os.environ.get("BIGMODEL_API_KEY", "")
    if key:
        return key

    # ~/.env 文件
    env_path = Path.home() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("BIGMODEL_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"\'')

    # 复用 topic_segmenter_llm.py 中的 key（临时方案）
    llm_path = ROOT / "core" / "topic_segmenter_llm.py"
    if llm_path.exists():
        txt = llm_path.read_text()
        import re
        m = re.search(r'"api_key"\s*:\s*"([^"]+)"', txt)
        if m:
            return m.group(1)

    return ""


# ── LLM 输出解析 ───────────────────────────────────────────────────────────

def _parse_llm_output(raw: str) -> dict:
    """
    尝试从 LLM 输出中提取 JSON。
    支持：
    1. 直接 JSON
    2. ```json ... ``` 包裹
    3. 从 { ... } 中提取
    """
    raw = raw.strip()

    # 方案1：直接解析
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 方案2：```json 包裹
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 方案3：找到第一个 { ... }
    m = re.search(r"(\{.*\})", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    raise ValueError(f"无法解析 LLM 输出为 JSON: {raw[:200]}")


# ── 核心处理 ────────────────────────────────────────────────────────────────

def run_dreaming_session(
    session_id: str,
    is_feedback: bool = False,
    feedback_queue_id: str = None,
) -> dict:
    """
    执行一次做梦 session。
    返回 session 结果摘要。
    """
    start_time = time.time()
    now = datetime.now(timezone(timedelta(hours=8)))

    logger.info(f"[DreamingWorker] 开始做梦 session: {session_id}, is_feedback={is_feedback}")

    errors = []
    entry_ids = []

    try:
        if is_feedback and feedback_queue_id:
            # 反馈做梦模式
            result = _run_feedback_dreaming(session_id, feedback_queue_id)
        else:
            # 标准做梦模式
            result = _run_standard_dreaming(session_id)

        entry_ids = result.get("entry_ids", [])
        errors = result.get("errors", [])

    except Exception as e:
        logger.exception(f"[DreamingWorker] 做梦执行异常: {e}")
        errors.append(str(e))

    elapsed = time.time() - start_time
    summary = {
        "session_id": session_id,
        "is_feedback": is_feedback,
        "feedback_queue_id": feedback_queue_id,
        "entry_count": len(entry_ids),
        "errors": errors,
        "elapsed_seconds": round(elapsed, 1),
        "started_at": start_time.isoformat() if isinstance(start_time, datetime) else None,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # 写 session log
    try:
        write_session_log(session_id, summary)
    except Exception as e:
        logger.warning(f"[DreamingWorker] 写 session log 失败: {e}")

    logger.info(
        f"[DreamingWorker] 完成: session={session_id}, "
        f"entries={len(entry_ids)}, errors={len(errors)}, elapsed={elapsed:.1f}s"
    )

    return summary


def _run_standard_dreaming(session_id: str) -> dict:
    """标准做梦流程"""
    # Step 1: 加载预处理数据
    logger.info("[DreamingWorker] Step 1: 加载预处理数据")
    input_data = build_dreaming_input()

    # Step 2: 构建 prompt
    logger.info("[DreamingWorker] Step 2: 构建 LLM Prompt")
    user_prompt = USER_PROMPT_TEMPLATE(
        memory_count=input_data["memory_count"],
        memory_summary=input_data["memory_summary"],
        experience_count=input_data["experience_count"],
        experience_summary=input_data["experience_summary"],
        topic_segments=input_data["topic_segments"],
        task_closure_summary=input_data["task_closure_summary"],
    )

    # Step 3: 调用 LLM
    logger.info("[DreamingWorker] Step 3: 调用 LLM")
    raw_output = _call_glm(SYSTEM_PROMPT, user_prompt, temperature=0.7)
    logger.info(f"[DreamingWorker] LLM 输出长度: {len(raw_output)} 字符")

    # Step 4: 解析输出
    logger.info("[DreamingWorker] Step 4: 解析 LLM 输出")
    try:
        parsed = _parse_llm_output(raw_output)
    except Exception as e:
        logger.error(f"[DreamingWorker] 解析失败: {e}, raw[:200]={raw_output[:200]}")
        return {"entry_ids": [], "errors": [f"JSON解析失败: {e}"]}

    # Step 5: 写入 dreaming_entries
    entry_ids = []
    errors = []

    session_summary = parsed.get("dreaming_session_summary", {})
    memory_items = input_data.get("memory_items", [])
    exp_items = input_data.get("experience_items", [])

    # 5a. association_insights
    for item in parsed.get("association_insights", []):
        try:
            eid = _write_insight_entry(
                session_id=session_id,
                dreaming_task="association",
                cognition_text=item["insight"],
                confidence=float(item.get("confidence", 0.5)),
                confidence_derivation=item.get("confidence_derivation", ""),
                triggered_actions=[{
                    "action": "ask_human",
                    "question": item.get("question_to_human", ""),
                    "urgency": item.get("urgency", "medium"),
                    "channel": "telegram",
                }] if item.get("needs_human_input") else [],
                source_memories=item.get("related_memories", []),
                source_experiences=[],
            )
            entry_ids.append(eid)
        except Exception as e:
            errors.append(f"association写入失败: {e}")
            logger.warning(f"[DreamingWorker] association 写入失败: {e}")

    # 5b. emotion_action_insights
    for item in parsed.get("emotion_action_insights", []):
        try:
            action = item.get("triggered_action", {})
            triggered = []
            if action.get("action") == "propose_task":
                triggered.append({
                    "action": "propose_task",
                    "task_text": action.get("task_text", ""),
                    "urgency": action.get("urgency", "medium"),
                })
            elif action.get("action") == "drive_conversation":
                triggered.append({
                    "action": "drive_conversation",
                    "opening_line": action.get("opening_line", ""),
                    "topic": action.get("topic", ""),
                    "urgency": action.get("urgency", "medium"),
                })

            eid = _write_insight_entry(
                session_id=session_id,
                dreaming_task="emotion_action",
                cognition_text=item["insight"],
                confidence=float(item.get("confidence", 0.5)),
                confidence_derivation=item.get("confidence_derivation", ""),
                triggered_actions=triggered,
                source_memories=item.get("related_memories", []),
                source_experiences=item.get("related_experiences", []),
            )
            entry_ids.append(eid)
        except Exception as e:
            errors.append(f"emotion_action写入失败: {e}")
            logger.warning(f"[DreamingWorker] emotion_action 写入失败: {e}")

    # 5c. task_activation_insights
    for item in parsed.get("task_activation_insights", []):
        try:
            action = item.get("triggered_action", {})
            triggered = []
            if action.get("action") in ("drive_conversation", "propose_task"):
                triggered.append({
                    "action": action["action"],
                    "opening_line": action.get("opening_line", ""),
                    "urgency": action.get("urgency", "medium"),
                })

            eid = _write_insight_entry(
                session_id=session_id,
                dreaming_task="task_activation",
                cognition_text=item.get("task_summary", item.get("insight", "")),
                confidence=float(item.get("confidence", 0.5)),
                confidence_derivation=item.get("confidence_derivation", ""),
                triggered_actions=triggered,
                source_memories=item.get("related_memories", []),
                source_experiences=[],
            )
            entry_ids.append(eid)
        except Exception as e:
            errors.append(f"task_activation写入失败: {e}")
            logger.warning(f"[DreamingWorker] task_activation 写入失败: {e}")

    logger.info(f"[DreamingWorker] 共写入 {len(entry_ids)} 条条目")
    return {"entry_ids": entry_ids, "errors": errors, "raw_output": raw_output}


def _run_feedback_dreaming(session_id: str, queue_id: str) -> dict:
    """反馈做梦流程"""
    from core.dreaming_prompt import FEEDBACK_PROMPT_TEMPLATE

    queue_entry = get_human_queue_entry(queue_id)
    if not queue_entry:
        return {"entry_ids": [], "errors": [f"queue_id={queue_id} 未找到"]}

    human_answer = queue_entry.get("answer_text", "")
    original_insight_id = queue_entry.get("related_insight_id", "")
    original_question = queue_entry.get("question", "")

    # 加载原始洞察（从 dreaming_entries）
    # 这里简化处理，直接构建反馈 prompt
    prompt = FEEDBACK_PROMPT_TEMPLATE(
        human_answer=human_answer,
        original_insight=original_insight_id,
        original_question=original_question,
    )

    raw_output = _call_glm(SYSTEM_PROMPT, prompt, temperature=0.3)
    parsed = _parse_llm_output(raw_output)

    # 写入更新后的洞察
    try:
        eid = _write_insight_entry(
            session_id=session_id,
            dreaming_task="feedback",
            cognition_text=parsed.get("updated_insight", ""),
            confidence=float(parsed.get("confidence", 0.5)),
            confidence_derivation="",
            triggered_actions=[{
                "action": "ask_human" if parsed.get("new_questions") else "none",
                "question": parsed.get("new_questions", [{}])[0] if parsed.get("new_questions") else "",
                "urgency": "medium",
                "channel": "telegram",
            }],
            source_memories=[],
            source_experiences=[],
            is_feedback_session=True,
            feedback_source_qid=queue_id,
        )
        return {"entry_ids": [eid], "errors": []}
    except Exception as e:
        return {"entry_ids": [], "errors": [f"feedback写入失败: {e}"]}


def _write_insight_entry(
    session_id: str,
    dreaming_task: str,
    cognition_text: str,
    confidence: float,
    confidence_derivation: str,
    triggered_actions: list,
    source_memories: list,
    source_experiences: list,
    is_feedback_session: bool = False,
    feedback_source_qid: str = None,
) -> str:
    """写入单条洞察条目"""
    needs_human = any(a.get("action") == "ask_human" for a in triggered_actions)

    return write_entry(
        session_id=session_id,
        dreaming_task=dreaming_task,
        cognition_text=cognition_text,
        confidence=confidence,
        confidence_derivation=confidence_derivation,
        triggered_actions=triggered_actions,
        source_memories=source_memories,
        source_experiences=source_experiences,
        needs_human_input=needs_human,
        is_feedback_session=is_feedback_session,
        feedback_source_qid=feedback_source_qid,
    )


# ── CLI 入口 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dreaming Worker")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--feedback", action="store_true")
    parser.add_argument("--queue-id", default=None)
    args = parser.parse_args()

    session_id = args.session_id or f"dream_{datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')}"

    result = run_dreaming_session(
        session_id=session_id,
        is_feedback=args.feedback,
        feedback_queue_id=args.queue_id,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
