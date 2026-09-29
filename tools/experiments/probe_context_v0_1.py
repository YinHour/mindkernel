"""Offline research probe only; no repository or network writes."""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime


def _time(value):
    if not isinstance(value, str):
        raise ValueError("time must be an ISO string with timezone")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone is required")
    return parsed


def _group(r):
    return r["kind"], r["key"], r["scope"]["project"], r["scope"]["task"]


def _validate(r):
    try:
        for name in ("id", "key", "value"):
            if not isinstance(r[name], str) or not r[name].strip():
                return False
        if r["kind"] not in {"intent", "constraint", "availability", "task_state", "artifact"}:
            return False
        if not isinstance(r["scope"]["project"], str) or not r["scope"]["project"]:
            return False
        if r["scope"]["task"] is not None and not isinstance(r["scope"]["task"], str):
            return False
        source = r["source"]
        if any(not isinstance(source[k], str) or not source[k] for k in ("ref", "event_id")):
            return False
        if source["authority"] not in {"user_explicit", "artifact_observation", "history_summary", "assistant_inference"}:
            return False
        created, available = _time(source["created_at"]), _time(source["available_at"])
        if created > available or available > _time(r["recorded_at"]):
            return False
        start = _time(r["valid_from"])
        if r["valid_until"] is not None and _time(r["valid_until"]) <= start:
            return False
        if r["recheck_after"] is not None:
            _time(r["recheck_after"])
        if r["kind"] == "availability" and r["valid_until"] is None:
            return False
        if r["kind"] in {"intent", "task_state", "artifact"} and r["recheck_after"] is None and r["valid_until"] is None:
            return False
        if r["kind"] in {"task_state", "artifact"} and r["recheck_after"] is None:
            return False
        if not isinstance(r["supersedes"], list) or any(not isinstance(x, str) for x in r["supersedes"]):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def assemble(records, *, as_of, project, task=None, horizon=None):
    cutoff = _time(as_of)
    end = _time(horizon) if horizon is not None else cutoff
    if end < cutoff:
        raise ValueError("horizon must not precede as_of")
    result = dict(current=[], upcoming=[], needs_recheck=[], conflicts=[], excluded=[])
    known, seen = [], set()

    def exclude(r, reason):
        result["excluded"].append({"id": r.get("id", "<missing>"), "reason": reason})

    for r in records:
        if not isinstance(r, dict):
            raise ValueError("each record must be an object")
        record_id = r.get("id")
        if isinstance(record_id, str):
            if record_id in seen:
                raise ValueError("duplicate record id: " + record_id)
            seen.add(record_id)
        if not _validate(r):
            exclude(r, "invalid_record")
            continue
        if _time(r["source"]["available_at"]) > cutoff or _time(r["source"]["created_at"]) > cutoff:
            exclude(r, "future_source")
        elif r["scope"]["project"] != project or r["scope"]["task"] not in (None, task):
            exclude(r, "outside_scope")
        else:
            known.append(r)

    index = {r["id"]: r for r in known}
    retired = set()
    for r in known:
        if r["source"]["authority"] != "user_explicit" or _time(r["valid_from"]) > cutoff:
            continue
        for old_id in r["supersedes"]:
            old = index.get(old_id)
            if old and _group(old) == _group(r) and _time(old["source"]["created_at"]) < _time(r["source"]["created_at"]):
                retired.add(old_id)

    candidates = defaultdict(list)
    for r in known:
        if r["id"] in retired:
            exclude(r, "superseded")
        elif r["valid_until"] is not None and _time(r["valid_until"]) <= cutoff:
            exclude(r, "expired")
        elif _time(r["valid_from"]) > end:
            exclude(r, "beyond_horizon")
        else:
            authority = r["source"]["authority"]
            unconfirmed_human_claim = r["kind"] in {"intent", "constraint", "availability"} and authority != "user_explicit"
            if unconfirmed_human_claim or authority in {"history_summary", "assistant_inference"}:
                result["needs_recheck"].append(deepcopy(r))
            else:
                bucket = "upcoming" if _time(r["valid_from"]) > cutoff else "current"
                candidates[(bucket, _group(r))].append(r)

    for (bucket, _), group in candidates.items():
        def rank(r):
            return (r["source"]["authority"] == "user_explicit", _time(r["source"]["created_at"]))
        best = max(rank(r) for r in group)
        latest = [r for r in group if rank(r) == best]
        for r in group:
            if rank(r) != best:
                exclude(r, "older_or_lower_authority")
        if len({r["value"] for r in latest}) > 1:
            result["conflicts"].extend(deepcopy(latest))
        else:
            winner = min(latest, key=lambda r: r["id"])
            # Rechecking a newer expression must not revive an older constraint.
            due = winner["recheck_after"] is not None and _time(winner["recheck_after"]) <= cutoff
            result["needs_recheck" if due else bucket].append(deepcopy(winner))
            for r in latest:
                if r["id"] != winner["id"]:
                    exclude(r, "equivalent_record")
    for values in result.values():
        values.sort(key=lambda r: r["id"])
    return result
