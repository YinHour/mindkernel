"""Offline selection of manually annotated evidence; no I/O or semantic extraction.

Callers must bind event text/times to authenticated sources before calling.
Only model_input is suitable for a downstream prompt. Audit diagnostics may
refer to excluded sources and must not be copied into that prompt.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
import json


def _time(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid timestamp') from exc
    if result.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return result


def _scope(value):
    if (not isinstance(value, dict) or set(value) != {'project', 'task'}
            or not isinstance(value['project'], str) or not value['project'].strip()
            or (value['task'] is not None and
                (not isinstance(value['task'], str) or not value['task'].strip()))):
        raise ValueError('scope requires project and optional task')
    return value['project'], value['task']


def _matches(scope, project, task):
    return scope[0] == project and scope[1] in (None, task)


def _encoded(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise ValueError('values must be finite JSON data') from exc


def _events(events, cutoff, project, task):
    index, known, active, excluded = {}, {}, set(), []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('event must be an object')
        mid = event.get('id')
        if not isinstance(mid, str) or not mid.strip() or mid in index:
            raise ValueError('event IDs must be nonempty and unique')
        try:
            scope = _scope(event['scope'])
            created, available = _time(event['created_at']), _time(event['available_at'])
            start = _time(event.get('valid_from', event['created_at']))
            end = _time(event['valid_until']) if event.get('valid_until') is not None else None
            if created > available or (end is not None and end <= start):
                raise ValueError('invalid event time range')
            if (not isinstance(event['authority'], str) or
                    event['authority'] not in {'user_explicit','assistant_inference','history_summary','artifact_observation'}):
                raise ValueError('unsupported authority')
            if not isinstance(event['text'], str) or not event['text'].strip():
                raise ValueError('event text is required')
            if not isinstance(event['claims'], dict) or any(not isinstance(k, str) or not k.strip() for k in event['claims']):
                raise ValueError('claims must map nonempty field names to values')
            _encoded(event['claims'])
        except KeyError as exc:
            raise ValueError('missing event field: ' + str(exc)) from exc
        index[mid] = event
        reason = None
        if max(created, available) > cutoff:
            reason = 'future_source'
        elif not _matches(scope, project, task):
            reason = 'outside_scope'
        elif start > cutoff:
            reason = 'not_yet_effective'
        if reason:
            excluded.append({'id':mid, 'reason':reason})
        else:
            # Expired evidence remains usable to explain a persistent revision,
            # but cannot become an active fact or an unrelated retrieval seed.
            known[mid] = event
            if end is None or cutoff < end:
                active.add(mid)
    return index, known, active, excluded


def _relations(relations, index, known, project, task):
    applicable, errors, seen = [], [], set()
    for rel in relations:
        if not isinstance(rel, dict):
            raise ValueError('relation must be an object')
        rid = rel.get('id')
        if not isinstance(rid, str) or not rid.strip() or rid in seen:
            raise ValueError('relation IDs must be nonempty and unique')
        seen.add(rid)
        try:
            scope = _scope(rel['scope'])
        except (KeyError, ValueError, TypeError):
            errors.append({'id':rid, 'reason':'invalid_relation_scope'})
            continue
        if not _matches(scope, project, task):
            continue
        newer = rel.get('newer')
        if not isinstance(newer, str) or newer not in index:
            errors.append({'id':rid, 'reason':'newer_source_missing'})
            continue
        if newer not in known:
            continue
        new = known[newer]
        if new['authority'] != 'user_explicit':
            continue
        try:
            old = known.get(rel.get('older'))
            field = rel.get('field')
            kind = rel.get('type')
            valid = (old is not None and old['authority'] == 'user_explicit'
                     and old['scope'] == new['scope'] == rel['scope']
                     and _time(old['created_at']) < _time(new['created_at'])
                     and isinstance(field, str) and bool(field.strip()))
            if valid:
                if kind == 'reopen_for_review':
                    valid = field in old['claims']
                elif kind == 'replace_field':
                    valid = field in old['claims'] and field in new['claims']
                elif kind == 'supplement':
                    valid = field in new['claims']
                else:
                    valid = False
            if not valid:
                errors.append({'id':rid, 'reason':'relation_source_scope_or_field_mismatch'})
            else:
                applicable.append(rel)
        except (KeyError, ValueError, TypeError):
            errors.append({'id':rid, 'reason':'invalid_relation'})
    return applicable, errors


def _field_states(known, active, relations):
    states, groups = {}, defaultdict(list)
    for mid, event in known.items():
        states[mid] = {}
        for field, value in event['claims'].items():
            states[mid][field] = {'value':deepcopy(value),
                                  'status':'historical' if mid not in active else 'needs_recheck',
                                  'evidence_ids':[mid], 'reason':'expired' if mid not in active else 'not_user_confirmed'}
            if event['authority'] == 'user_explicit':
                groups[(_scope(event['scope']), field)].append(mid)
    retired = {(r['older'], r['field']) for r in relations if r['type'] == 'replace_field'}
    for (scope, field), mids in groups.items():
        candidates = [mid for mid in mids if mid in active and (mid, field) not in retired]
        for mid in mids:
            states[mid][field].update(status='historical', reason='earlier_or_expired_expression')
        if not candidates:
            continue
        newest = max(_time(known[mid]['created_at']) for mid in candidates)
        winners = sorted(mid for mid in candidates if _time(known[mid]['created_at']) == newest)
        values = {_encoded(known[mid]['claims'][field]) for mid in winners}
        status = 'conflict' if len(values) > 1 else 'current'
        reopens = [r for r in relations if r['type'] == 'reopen_for_review'
                   and r['field'] == field and _scope(r['scope']) == scope
                   and _time(known[r['newer']]['created_at']) >= newest]
        evidence = sorted(set(winners + [r['newer'] for r in reopens]))
        for mid in winners:
            resolved_status = status if status == 'conflict' else ('needs_recheck' if reopens else status)
            states[mid][field].update(status=resolved_status,
                                      reason='reopened_field' if reopens else 'latest_explicit_expression',
                                      evidence_ids=evidence)
    return states, groups


def _closure(seeds, adjacency):
    result, todo = set(seeds), list(seeds)
    while todo:
        mid = todo.pop()
        for related in adjacency[mid] - result:
            result.add(related)
            todo.append(related)
    return result


def select_revision_context(events, relations, *, as_of, project, task=None,
                            seed_ids, required_ids=(), max_history_records=4,
                            max_history_bytes=10000):
    """Return a ready annotated input or an explicit failure with model_input=None.

    Events and relations are caller-supplied manual annotations. Field status
    describes expressions, never proof that an action or configuration succeeded.
    Capacity uses canonical compact UTF-8 JSON of the entire model_input object.
    """
    cutoff = _time(as_of)
    _scope({'project':project, 'task':task})
    for cap in (max_history_records, max_history_bytes):
        if type(cap) is not int or cap < 1:
            raise ValueError('capacity must be a positive integer')
    if not isinstance(events, (list, tuple)) or not isinstance(relations, (list, tuple)):
        raise ValueError('events and relations must be sequences')
    for ids in (seed_ids, required_ids):
        if not isinstance(ids, (list, tuple)) or any(not isinstance(i, str) or not i.strip() for i in ids):
            raise ValueError('seed/required IDs must be sequences of nonempty strings')
    index, known, active, excluded = _events(events, cutoff, project, task)
    rels, errors = _relations(relations, index, known, project, task)
    result = dict(status='ready', model_input=None, selected_ids=[],
                  excluded=sorted(excluded, key=lambda e:e['id']), omissions=[], errors=errors)
    if errors:
        result['status'] = 'invalid_relation'
        return result
    unavailable = set(required_ids) - active
    if unavailable:
        result.update(status='required_unavailable', errors=[{'id':i,'reason':'required_not_available'} for i in sorted(unavailable)])
        return result
    states, groups = _field_states(known, active, rels)
    adjacency = {mid:set() for mid in known}
    for rel in rels:
        adjacency[rel['older']].add(rel['newer'])
        adjacency[rel['newer']].add(rel['older'])
    # Competing manually keyed claims must travel together, even if no explicit
    # edge was supplied. This also preserves simultaneous contradictory claims.
    for mids in groups.values():
        for mid in mids:
            adjacency[mid].update(set(mids) - {mid})

    def ordered(ids):
        return sorted(ids, key=lambda mid:(_time(known[mid]['created_at']),
                                          _time(known[mid]['available_at']), mid))

    def payload(ids):
        history = []
        for mid in ordered(ids):
            e = known[mid]
            history.append({'id':mid, 'text':e['text'], 'scope':deepcopy(e['scope']),
                            'authority':e['authority'], 'created_at':e['created_at'],
                            'available_at':e['available_at'], 'fields':deepcopy(states[mid])})
        return {'as_of':as_of, 'claim_basis':'expressions_not_execution_confirmation',
                'history':history}

    def fits(ids):
        return len(ids) <= max_history_records and len(_encoded(payload(ids))) <= max_history_bytes

    chosen = _closure(required_ids, adjacency)
    if not fits(chosen):
        result.update(status='budget_incomplete', omissions=[{'ids':ordered(chosen), 'reason':'required_group_exceeds_capacity'}])
        return result
    seeds = list(dict.fromkeys(seed_ids))
    for mid in seeds:
        if mid not in active:
            result['omissions'].append({'ids':[mid], 'reason':'seed_not_available'})
    # Evidence groups outrank isolated fill; within each tier caller ranking wins.
    seeds = sorted((mid for mid in seeds if mid in active), key=lambda mid:not bool(adjacency[mid]))
    for mid in seeds:
        if mid in chosen:
            continue
        group = _closure([mid], adjacency)
        proposal = chosen | group
        if fits(proposal):
            chosen = proposal
        elif len(group) > 1:
            result.update(status='budget_incomplete')
            result['omissions'].append({'ids':ordered(group), 'reason':'related_group_exceeds_capacity'})
            return result
        else:
            result['omissions'].append({'ids':[mid], 'reason':'optional_fill_exceeds_capacity'})
    result['selected_ids'] = ordered(chosen)
    conflicts = [{'id':mid, 'field':field, 'reason':'conflicting_latest_values'}
                 for mid in result['selected_ids'] for field, value in states[mid].items()
                 if value['status'] == 'conflict']
    if conflicts:
        result.update(status='conflict', errors=conflicts)
    else:
        result['model_input'] = payload(chosen)
    return result
