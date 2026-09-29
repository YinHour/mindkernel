"""Read an explicitly selected Codex transcript without changing the source.

This adapter targets the desktop response_item/message shape observed in
September 2026. Unknown or incomplete records make ok=False. A known absence
of assistant creation time is a warning when its write time is valid; these
times remain separate. A parsed report is not evidence of learning quality.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path


class CodexSessionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


_NON_DIALOGUE_RECORDS = {"event_msg", "world_state", "turn_context", "token_usage_record", "compacted"}
_NON_DIALOGUE_ITEMS = {"reasoning", "function_call", "function_call_output", "custom_tool_call", "custom_tool_call_output"}
_CONTEXT_KINDS = {"plugins.recommendations", "agents_md.instructions", "environments.environment_context"}
_REPLY_OPEN = "<send_user_message_question_reply>"
_REPLY_CLOSE = "</send_user_message_question_reply>"


def _utc_time(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        if not math.isfinite(value):
            return None
        return datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _valid_recorded_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _structured_reply(text: str) -> str:
    if not text.startswith(_REPLY_OPEN) or not text.endswith(_REPLY_CLOSE):
        raise ValueError("Incomplete structured reply carrier")
    replies = json.loads(text[len(_REPLY_OPEN):-len(_REPLY_CLOSE)].strip())
    if not isinstance(replies, list) or not replies:
        raise ValueError("Expected a nonempty reply list")
    parts = []
    for reply in replies:
        if not isinstance(reply, dict) or not all(isinstance(reply.get(k), str) for k in ("question", "answer")):
            raise ValueError("Expected question and answer text")
        parts.append(f"问题：{reply['question']}\n回答：{reply['answer']}")
    return "\n\n".join(parts)


def read_codex_session(session_file: str | Path, *, expected_thread_id: str,
                       max_bytes: int | None = None, expected_sha256: str | None = None) -> dict:
    """Return a deterministic report of one bounded snapshot; never write files.

    The caller must supply both a file and its expected task ID. Source order
    is retained. Original message time and transcript write time are separate.
    max_bytes and expected_sha256 allow replay of a growing file's old prefix.
    """
    source = Path(session_file).resolve()
    with source.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        if max_bytes is not None and (isinstance(max_bytes, bool) or not isinstance(max_bytes, int)
                                      or max_bytes <= 0 or max_bytes > size):
            raise CodexSessionError("invalid_snapshot_size", "Snapshot size must be positive and no larger than the source.")
        limit = size if max_bytes is None else max_bytes
        snapshot = stream.read(limit)
    if len(snapshot) != limit:
        raise CodexSessionError("source_changed", "Source became shorter while reading; select a new snapshot.")
    digest = hashlib.sha256(snapshot).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise CodexSessionError("snapshot_mismatch", "Snapshot SHA-256 does not match the expected value.")
    lines = snapshot.splitlines(keepends=True)
    try:
        header = json.loads(lines[0])
    except (IndexError, ValueError, UnicodeError):
        raise CodexSessionError("unsupported_header", "Expected a complete Codex session_meta header.") from None
    if not isinstance(header, dict) or header.get("type") != "session_meta" or not isinstance(header.get("payload"), dict):
        raise CodexSessionError("unsupported_header", "Expected a Codex session_meta header.")
    meta = header["payload"]
    if not expected_thread_id or meta.get("id") != expected_thread_id:
        raise CodexSessionError("thread_mismatch", "The source task does not match the explicit task allowlist.")

    messages, revisions, issues = [], [], []
    excluded, record_types, response_types = Counter(), Counter(), Counter()
    seen: dict[str, set[str]] = {}
    first_lines: dict[str, int] = {}
    duplicates = 0

    def issue(code: str, line: int, message: str, severity: str = "error"):
        issues.append({"code": code, "severity": severity, "source_line": line, "message": message})

    for line_number, raw in enumerate(lines, 1):
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError):
            is_tail = line_number == len(lines) and not raw.endswith(b"\n")
            issue("incomplete_tail" if is_tail else "invalid_json", line_number,
                  "Record is incomplete or invalid; no content was imported.")
            excluded["unreadable_record"] += 1
            continue
        if not isinstance(record, dict) or not isinstance(record.get("type"), str):
            issue("invalid_record", line_number, "Expected an object with a record type.")
            excluded["invalid_record"] += 1
            continue
        kind = record["type"]
        record_types[kind] += 1
        if line_number == 1:
            excluded["session_header"] += 1
            continue
        if kind in _NON_DIALOGUE_RECORDS:
            excluded[f"record:{kind}"] += 1
            continue
        if kind != "response_item":
            issue("unknown_record_type", line_number, "Unsupported top-level record type.")
            excluded["unknown_record_type"] += 1
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
            issue("invalid_response_item", line_number, "Expected a typed response item.")
            excluded["invalid_response_item"] += 1
            continue
        item_type = payload["type"]
        response_types[item_type] += 1
        if item_type in _NON_DIALOGUE_ITEMS:
            excluded[f"item:{item_type}"] += 1
            continue
        if item_type != "message":
            issue("unknown_response_type", line_number, "Unsupported response item type.")
            excluded["unknown_response_type"] += 1
            continue
        role = payload.get("role")
        if role in ("system", "developer", "tool"):
            excluded["other_role"] += 1
            continue
        if role not in ("user", "assistant"):
            issue("unknown_role", line_number, "Unsupported message role.")
            excluded["unknown_role"] += 1
            continue
        metadata = payload.get("internal_chat_message_metadata_passthrough")
        if not isinstance(metadata, dict):
            metadata = {}
        kinds = metadata.get("content_item_kinds")
        if role == "user":
            if not isinstance(kinds, list) or not kinds or not all(isinstance(k, str) for k in kinds):
                issue("unknown_user_origin", line_number, "User message origin is not identifiable.")
                excluded["unknown_user_origin"] += 1
                continue
            user_kinds = [k.startswith("user.") for k in kinds]
            if not any(user_kinds):
                if all(k in _CONTEXT_KINDS for k in kinds):
                    excluded["user_role_context_envelope"] += 1
                else:
                    issue("unknown_user_origin", line_number, "Unrecognized user-role origin label.")
                    excluded["unknown_user_origin"] += 1
                continue
            if not all(user_kinds):
                issue("mixed_user_origin", line_number, "User and injected context share a message; do not infer human authorship.")
                excluded["mixed_user_origin"] += 1
                continue
            if any(k != "user.text" for k in kinds):
                issue("unsupported_content", line_number, "Only plain user text is supported in this version.")
                excluded["unsupported_content"] += 1
                continue
        phase = payload.get("phase") if role == "assistant" else None
        if role == "assistant" and phase not in ("commentary", "final_answer"):
            issue("unknown_assistant_phase", line_number, "Assistant phase is not known to be visible dialogue.")
            excluded["unknown_assistant_phase"] += 1
            continue
        message_id = payload.get("id")
        if not isinstance(message_id, str) or not message_id:
            issue("missing_message_id", line_number, "A stable message ID is required.")
            excluded["missing_message_id"] += 1
            continue
        content = payload.get("content")
        text_kind = "input_text" if role == "user" else "output_text"
        if not isinstance(content, list) or not content or not all(
            isinstance(c, dict) and c.get("type") == text_kind and isinstance(c.get("text"), str) for c in content
        ):
            issue("unsupported_content", line_number, "Message contains unsupported or malformed content; no partial text was imported.")
            excluded["unsupported_content"] += 1
            continue
        raw_text = "\n".join(c["text"] for c in content)
        if not raw_text.strip():
            issue("empty_message", line_number, "Visible message has no text.")
            excluded["empty_message"] += 1
            continue
        text, interaction_type = raw_text, "text"
        if role == "user" and raw_text.strip().startswith(_REPLY_OPEN):
            try:
                text = _structured_reply(raw_text.strip())
                interaction_type = "structured_reply"
            except ValueError:
                issue("invalid_structured_reply", line_number, "Structured question reply could not be decoded.")
                excluded["invalid_structured_reply"] += 1
                continue
        epoch = metadata.get("create_time")
        created_at = _utc_time(epoch)
        recorded_at = record.get("timestamp")
        if created_at is None:
            # Desktop assistant records observed in the real snapshot omit this
            # field. Preserve that absence; write time is not a substitute.
            severity = "warning" if role == "assistant" and "create_time" not in metadata and _valid_recorded_time(recorded_at) else "error"
            issue("missing_created_at", line_number, "Original creation time is missing or invalid; retained as null.", severity)
        if not _valid_recorded_time(recorded_at):
            issue("missing_recorded_at", line_number, "Transcript write time is missing or invalid; retained as null.")
            recorded_at = None
        turn_id = metadata.get("turn_id")
        if not isinstance(turn_id, str) or not turn_id:
            issue("missing_turn_id", line_number, "Turn ID is missing or invalid; retained as null.")
            turn_id = None
        message = {
            "id": message_id, "thread_id": expected_thread_id, "turn_id": turn_id,
            "role": role, "phase": phase, "interaction_type": interaction_type,
            "text": text, "raw_text": raw_text if interaction_type == "structured_reply" else None,
            "created_at": created_at, "created_at_epoch": epoch if created_at else None,
            "recorded_at": recorded_at, "source_line": line_number,
            "source_ref": f"{source}#L{line_number}",
            "content_item_kinds": kinds if isinstance(kinds, list) else [],
        }
        # A later envelope can repeat a message; write time/line are not new evidence.
        semantic = {k: v for k, v in message.items() if k not in {"recorded_at", "source_line", "source_ref"}}
        fingerprint = json.dumps(semantic, ensure_ascii=False, sort_keys=True)
        if message_id in seen:
            if fingerprint in seen[message_id]:
                duplicates += 1
                excluded["duplicate_message"] += 1
                continue
            issue("message_revision", line_number, "Same ID has changed content or provenance; earlier message retained.")
            revisions.append({"original_source_line": first_lines[message_id], "message": message})
            excluded["message_revision"] += 1
        else:
            seen[message_id] = set()
            first_lines[message_id] = line_number
            messages.append(message)
        seen[message_id].add(fingerprint)
    if not messages:
        issue("no_visible_messages", 1, "No supported visible messages; this is not a successful data import.")
    error_count = sum(i["severity"] == "error" for i in issues)
    warning_count = sum(i["severity"] == "warning" for i in issues)
    return {
        "schema_version": "codex-visible-session/v0.1", "ok": error_count == 0,
        "source": {"path": str(source), "thread_id": expected_thread_id, "cwd": meta.get("cwd"),
                   "cli_version": meta.get("cli_version"), "history_mode": meta.get("history_mode"),
                   "snapshot_bytes": len(snapshot), "snapshot_sha256": digest, "snapshot_lines": len(lines)},
        "summary": {"message_count": len(messages), "by_role": dict(Counter(m["role"] for m in messages)),
                    "assistant_phases": dict(Counter(m["phase"] for m in messages if m["role"] == "assistant")),
                    "structured_reply_count": sum(m["interaction_type"] == "structured_reply" for m in messages),
                    "duplicate_messages": duplicates, "revision_count": len(revisions), "issue_count": len(issues),
                    "error_count": error_count, "warning_count": warning_count,
                    "excluded": dict(excluded), "record_types": dict(record_types), "response_types": dict(response_types)},
        "messages": messages, "revisions": revisions, "issues": issues,
    }
