"""Bind manual context annotations to explicit evidence, then assemble offline.

This module never opens a source reference, reads a transcript, or calls a model.
Observation payloads attest to saved evidence; they do not prove its meaning or
original publication time. Historical annotations remain retrospective.
"""
from copy import deepcopy
import hashlib

from tools.experiments.probe_context_v0_1 import _time, _validate, assemble


def _index(items, key):
    if not isinstance(items, (list, tuple)):
        raise ValueError("source collection must be a list or tuple")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError("source or annotation ID is missing")
        if item[key] in result:
            raise ValueError("duplicate source or annotation ID: " + item[key])
        result[item[key]] = item
    return result


def _user_source(source, message, expected_thread_id):
    if message is None:
        return "source_missing", None
    if message.get("thread_id") != expected_thread_id:
        return "source_thread_mismatch", None
    if message.get("role") != "user":
        return "speaker_mismatch", None
    try:
        created = _time(message.get("created_at"))
        written = _time(message.get("recorded_at"))
    except (ValueError, TypeError):
        return "source_time_unknown", None
    # Source writes may have millisecond precision; creation can be finer.
    if _time(source["created_at"]) != created or _time(source["available_at"]) != max(created, written):
        return "source_time_mismatch", None
    if source["ref"] != message.get("source_ref"):
        return "source_ref_mismatch", None
    carrier = message.get("raw_text")
    if carrier is None:
        carrier = message.get("text")
    quote = source.get("quote")
    if not isinstance(carrier, str) or not isinstance(quote, str) or not quote.strip() or quote.strip() != carrier.strip():
        return "quote_mismatch", None
    return None, {"source_written_at": message["recorded_at"],
                  "content_sha256": hashlib.sha256(carrier.encode("utf-8")).hexdigest()}


def _observation_source(source, observation):
    if observation is None:
        return "observation_missing", None
    if any(source[k] != observation.get(k) for k in ("event_id", "ref", "authority")):
        return "observation_metadata_mismatch", None
    try:
        if any(_time(source[k]) != _time(observation.get(k)) for k in ("created_at", "available_at")):
            return "observation_metadata_mismatch", None
    except (ValueError, TypeError):
        return "observation_metadata_mismatch", None
    content = observation.get("content")
    if not isinstance(content, str):
        return "observation_payload_missing", None
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if digest != observation.get("sha256") or digest != source.get("sha256", source.get("container_sha256")):
        return "observation_hash_mismatch", None
    return None, {"source_written_at": None, "content_sha256": digest}


def assemble_from_sources(report, annotations, *, expected_thread_id, as_of, project,
                          task=None, horizon=None, observations=()):
    """Return context groups, successful evidence bindings and explicit exclusions.

    report is a codex-visible-session/v0.1 export from the explicit task.
    annotations use collaboration-context-v0.1. User sources require the full
    original message in source.quote (outer whitespace is ignored). Non-user
    sources require explicit UTF-8 content, SHA-256 and matching metadata in
    observations; no paths are followed. A failed report, mismatched task or
    ambiguous IDs raises ValueError. Unverifiable annotations are excluded.
    """
    if not isinstance(report, dict) or report.get("schema_version") != "codex-visible-session/v0.1" or report.get("ok") is not True:
        raise ValueError("a successful codex-visible-session/v0.1 report is required")
    source = report.get("source")
    if not isinstance(source, dict) or not expected_thread_id or source.get("thread_id") != expected_thread_id:
        raise ValueError("report does not match the explicit task allowlist")
    messages = _index(report.get("messages"), "id")
    observed = _index(observations, "event_id")
    records = _index(annotations, "id")
    accepted, bindings, excluded = [], [], []
    for identifier, record in sorted(records.items()):
        if not _validate(record):
            excluded.append({"id": identifier, "reason": "invalid_record"})
            continue
        evidence = record["source"]
        if evidence["authority"] == "user_explicit":
            reason, details = _user_source(evidence, messages.get(evidence["event_id"]), expected_thread_id)
        else:
            reason, details = _observation_source(evidence, observed.get(evidence["event_id"]))
        if reason:
            excluded.append({"id": identifier, "reason": reason})
            continue
        accepted.append(record)
        bindings.append({"id": identifier, "event_id": evidence["event_id"],
                         "authority": evidence["authority"], "ref": evidence["ref"],
                         "created_at": evidence["created_at"], "available_at": evidence["available_at"],
                         "annotated_at": record["recorded_at"], **details})
    context = assemble(accepted, as_of=as_of, project=project, task=task, horizon=horizon)
    context["excluded"] = sorted(context["excluded"] + excluded, key=lambda r: r["id"])
    return {"schema_version": "source-bound-context/v0.1", "snapshot": deepcopy(source),
            "context": context, "bindings": bindings, "source_excluded": excluded}
