"""Acceptance and failure-boundary tests; all sources are synthetic."""
import copy
import importlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'data/fixtures/context-revisions-v0_1/cases.json'


class RevisionSelectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text())
        self.events = {e['id']: e for e in self.fixture['events']}
        self.relations = {r['id']: r for r in self.fixture['relations']}

    def select(self, ids, rels=(), **kwargs):
        try:
            module = importlib.import_module('tools.experiments.select_revision_context_v0_1')
        except ModuleNotFoundError:
            self.fail('revision selection entrypoint is not implemented')
        events = [copy.deepcopy(self.events[i]) for i in ids]
        relations = [copy.deepcopy(self.relations[i]) for i in rels]
        for mid, changes in kwargs.pop('overrides', {}).items():
            next(e for e in events if e['id'] == mid).update(changes)
        options = dict(as_of='2030-01-07T09:00:00Z', project='SyntheticNotebook',
                       seed_ids=ids, required_ids=['E0'] if 'E0' in ids else [])
        options.update(kwargs)
        before = copy.deepcopy((events, relations))
        result = module.select_revision_context(events, relations, **options)
        self.assertEqual((events, relations), before, 'selector mutated caller-owned input')
        return result

    def case(self, cid):
        c = next(c for c in self.fixture['cases'] if c['id'] == cid)
        return self.select(c['event_ids'], c['relation_ids'], as_of=c['as_of'],
                           max_history_records=c.get('max_history_records', 4),
                           overrides=c.get('event_overrides', {}))

    def field(self, result, event_id, key):
        packet = next(p for p in result['model_input']['history'] if p['id'] == event_id)
        return packet['fields'][key]

    def test_s01_future_changes_do_not_revoke_earlier_request(self):
        r = self.case('S01')
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(r['selected_ids'], ['E0', 'E1'])
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['status'], 'current')

    def test_s02_reopen_one_field_without_cancelling_workflow(self):
        r = self.case('S02')
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['status'], 'needs_recheck')
        self.assertEqual(self.field(r, 'E1', 'workflow.activities')['value'], ['planning', 'review'])
        self.assertEqual(self.field(r, 'E1', 'workflow.activities')['status'], 'current')
        self.assertNotIn('needs_user_reply_now', r['model_input'])

    def test_s03_daily_report_and_budget_survive_without_claiming_execution(self):
        r = self.case('S03')
        self.assertEqual(r['selected_ids'], ['E0', 'E1', 'E2', 'E3'])
        self.assertEqual(self.field(r, 'E0', 'weekly_budget')['value'], '2h/week')
        self.assertEqual(self.field(r, 'E3', 'progress_report.frequency')['value'], 'daily')
        self.assertEqual(self.field(r, 'E3', 'progress_report.length')['status'], 'current')
        self.assertEqual(r['model_input']['claim_basis'], 'expressions_not_execution_confirmation')

    def test_s04_capacity_failure_never_emits_old_schedule_as_ready(self):
        r = self.case('S04')
        self.assertEqual(r['status'], 'budget_incomplete')
        self.assertIsNone(r['model_input'])
        self.assertTrue(r['omissions'])

    def test_s05_late_available_revision_is_not_used(self):
        r = self.case('S05')
        self.assertEqual(r['selected_ids'], ['E0', 'E1'])
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['status'], 'current')

    def test_s06_assistant_suggestion_cannot_cancel_user_workflow(self):
        r = self.case('S06')
        self.assertEqual(self.field(r, 'E1', 'workflow.activities')['status'], 'current')
        self.assertEqual(self.field(r, 'A1', 'workflow.activities')['status'], 'needs_recheck')

    def test_s07_other_scope_is_excluded(self):
        r = self.case('S07')
        self.assertEqual(r['selected_ids'], ['E0', 'E1'])
        self.assertEqual({e['id'] for e in r['excluded']}, {'O1', 'T1'})

    def test_s08_explicit_replacement_only_changes_same_field(self):
        r = self.case('S08')
        self.assertEqual(self.field(r, 'E4', 'progress_report.exact_time')['status'], 'historical')
        self.assertEqual(self.field(r, 'E5', 'progress_report.exact_time')['value'], '16:00')
        self.assertEqual(self.field(r, 'E5', 'progress_report.exact_time')['status'], 'current')
        self.assertEqual(self.field(r, 'E3', 'progress_report.frequency')['value'], 'daily')
        self.assertEqual(self.field(r, 'E1', 'workflow.activities')['value'], ['planning', 'review'])

    def test_s09_same_time_conflict_is_not_broken_by_id(self):
        r = self.case('S09')
        self.assertEqual(r['status'], 'conflict')
        self.assertIsNone(r['model_input'])
        self.assertEqual({x['id'] for x in r['errors']}, {'E5', 'E6'})

    def test_s10_applicable_missing_relation_source_is_not_ready(self):
        r = self.case('S10')
        self.assertEqual(r['status'], 'invalid_relation')
        self.assertIsNone(r['model_input'])

    def test_s11_input_order_is_not_semantic_precedence(self):
        a, b = self.case('S03'), self.case('S11')
        self.assertEqual(a['model_input'], b['model_input'])
        self.assertEqual(b['selected_ids'], ['E0', 'E1', 'E2', 'E3'])

    def test_future_missing_older_target_does_not_break_earlier_replay(self):
        r = self.select(['E0', 'E2'], ['R1'], as_of='2030-01-07T08:15:00Z')
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(r['selected_ids'], ['E0'])

    def test_out_of_scope_missing_target_is_ignored(self):
        self.relations['R1']['scope'] = {'project':'OtherSyntheticProject','task':None}
        self.events['E2']['scope'] = self.relations['R1']['scope']
        r = self.select(['E0', 'E2'], ['R1'])
        self.assertEqual(r['status'], 'ready')

    def test_cross_scope_relation_cannot_change_field(self):
        self.events['E2']['scope'] = {'project':'SyntheticNotebook','task':'child'}
        r = self.select(['E0', 'E1', 'E2'], ['R1'], task='child')
        self.assertEqual(r['status'], 'invalid_relation')

    def test_visible_newer_source_must_match_the_relation_scope(self):
        self.events['E2']['scope'] = {'project':'OtherSyntheticProject','task':None}
        r = self.select(['E1','E2'], ['R1'], seed_ids=['E1'])
        self.assertEqual(r['status'], 'invalid_relation')
        self.assertIsNone(r['model_input'])

    def test_non_user_relation_cannot_invalidate_explicit_request(self):
        self.events['E2']['authority'] = 'assistant_inference'
        r = self.select(['E0', 'E1', 'E2'], ['R1'])
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['status'], 'current')

    def test_relation_cannot_name_a_nonexistent_field(self):
        self.relations['R1']['field'] = 'unknown_field'
        r = self.select(['E0', 'E1', 'E2'], ['R1'])
        self.assertEqual(r['status'], 'invalid_relation')

    def test_related_updates_are_selected_even_when_not_ranked(self):
        r = self.select(['E0', 'E1', 'E2', 'E3'], ['R1','R2'], seed_ids=['E1'])
        self.assertEqual(r['selected_ids'], ['E0','E1','E2','E3'])
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['evidence_ids'], ['E1','E2'])

    def test_raw_fill_cannot_sneak_an_old_field_back_in(self):
        r = self.select(['E0','E1','E2','E3'], ['R1','R2'], seed_ids=['E3','E0','E1'])
        self.assertEqual(self.field(r, 'E1', 'reminder.exact_schedule')['status'], 'needs_recheck')

    def test_byte_budget_counts_field_metadata_and_utf8(self):
        ready = self.case('S03')
        size = len(json.dumps(ready['model_input'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
        r = self.select(['E0','E1','E2','E3'], ['R1','R2'], max_history_bytes=size-1)
        self.assertEqual(r['status'], 'budget_incomplete')
        self.assertIsNone(r['model_input'])
        exact = self.select(['E0','E1','E2','E3'], ['R1','R2'], max_history_bytes=size)
        self.assertEqual(exact['status'], 'ready')

    def test_required_missing_or_future_evidence_is_not_silently_dropped(self):
        for required in ['missing', 'E2']:
            with self.subTest(required=required):
                r = self.select(['E0','E1','E2'], required_ids=[required], as_of='2030-01-07T08:15:00Z')
                self.assertEqual(r['status'], 'required_unavailable')
                self.assertIsNone(r['model_input'])

    def test_empty_duplicate_and_malformed_inputs_are_rejected(self):
        for changes in [{'id':''}, {'created_at':'2030-01-07T08:00:00'},
                        {'claims':[]}, {'text':None}, {'available_at':'2029-01-01T00:00:00Z'}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.select(['E0'], overrides={'E0':changes})
        with self.assertRaises(ValueError): self.select(['E0','E0'])
        for cap in [0,-1,True]:
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                self.select(['E0'], max_history_records=cap)

    def test_new_explicit_value_after_reopen_can_resolve_that_field(self):
        self.events['E4']['claims'] = {'reminder.exact_schedule':'daily14:00'}
        r = self.select(['E1','E2','E4'], ['R1'])
        self.assertEqual(self.field(r,'E4','reminder.exact_schedule')['status'],'current')
        self.assertEqual(self.field(r,'E1','reminder.exact_schedule')['status'],'historical')

    def test_reopen_does_not_restore_old_value_when_its_interval_expires(self):
        self.events['E2']['valid_until'] = '2030-01-07T08:30:00Z'
        r = self.select(['E1','E2'], ['R1'])
        self.assertEqual(r['status'],'ready')
        self.assertEqual(self.field(r,'E1','reminder.exact_schedule')['status'],'needs_recheck')
        self.assertEqual(self.field(r,'E2','reminder.timing_policy')['status'],'historical')

    def test_not_yet_effective_revision_has_no_current_effect(self):
        self.events['E2']['valid_from'] = '2030-01-08T00:00:00Z'
        r = self.select(['E0','E1','E2'], ['R1'])
        self.assertEqual(r['selected_ids'],['E0','E1'])
        self.assertEqual(self.field(r,'E1','reminder.exact_schedule')['status'],'current')

    def test_current_replacement_can_revise_a_known_planned_expression(self):
        self.events['E4']['valid_from'] = '2030-01-08T00:00:00Z'
        self.events['E4']['claims']['planned_workflow'] = 'weekly'
        for cutoff, workflow_status in [('2030-01-07T09:00:00Z', 'historical'),
                                         ('2030-01-08T09:00:00Z', 'current')]:
            with self.subTest(cutoff=cutoff):
                r = self.select(['E4','E5'], ['R3'], seed_ids=['E5'], as_of=cutoff)
                self.assertEqual(r['status'], 'ready')
                self.assertEqual(r['selected_ids'], ['E4','E5'])
                self.assertEqual(self.field(r,'E4','progress_report.exact_time')['status'],'historical')
                self.assertEqual(self.field(r,'E5','progress_report.exact_time')['status'],'current')
                self.assertEqual(self.field(r,'E4','planned_workflow')['status'],workflow_status)
                self.assertNotIn('E4', [e['id'] for e in r['excluded']])
        r = self.select(['E4','E5'], ['R3'], seed_ids=['E5'], max_history_records=1)
        self.assertEqual(r['status'], 'budget_incomplete')
        self.assertIsNone(r['model_input'])
        r = self.select(['E4','E5'], ['R3'], seed_ids=['E5'], required_ids=['E4'])
        self.assertEqual(r['status'], 'required_unavailable')

    def test_planned_replacement_target_still_requires_visible_source(self):
        self.events['E4'].update(valid_from='2030-01-08T00:00:00Z',
                                 available_at='2030-01-08T00:00:00Z')
        r = self.select(['E4','E5'], ['R3'], seed_ids=['E5'])
        self.assertEqual(r['status'], 'invalid_relation')
        self.assertIsNone(r['model_input'])

    def test_irrelevant_relation_with_no_sources_does_not_block_request(self):
        self.relations['R1'].update(older='absent-old', newer='absent-new',
                                   scope={'project':'OtherSyntheticProject','task':None})
        r = self.select(['E0'], ['R1'])
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(r['selected_ids'], ['E0'])

    def test_reopening_cannot_resolve_conflicting_explicit_values(self):
        self.events['E4']['created_at'] = '2030-01-07T08:55:00Z'
        self.events['E4']['available_at'] = '2030-01-07T08:55:00Z'
        self.events['E4']['claims'] = {'timing_policy':'reselect'}
        self.relations['R1'].update(older='E5', newer='E4', field='progress_report.exact_time')
        r = self.select(['E5','E6','E4'], ['R1'])
        self.assertEqual(r['status'], 'conflict')
        self.assertIsNone(r['model_input'])
        self.assertEqual({e['id'] for e in r['errors']}, {'E5','E6'})

    def test_malformed_authority_uses_declared_validation_error(self):
        for value in [[], {}, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.select(['E0'], overrides={'E0':{'authority':value}})

    def test_reopening_a_retired_value_does_not_downgrade_its_replacement(self):
        self.events['E3'].update(created_at='2030-01-07T08:58:00Z',
                                 available_at='2030-01-07T08:58:00Z',
                                 claims={'timing_policy':'recheck old choice'})
        self.relations['R1'].update(older='E4', newer='E3', field='progress_report.exact_time')
        r = self.select(['E4','E5','E3'], ['R3','R1'], seed_ids=['E5'])
        self.assertEqual(r['status'], 'ready')
        self.assertEqual(self.field(r,'E4','progress_report.exact_time')['status'],'historical')
        self.assertEqual(self.field(r,'E5','progress_report.exact_time')['status'],'current')
        self.assertEqual(self.field(r,'E5','progress_report.exact_time')['evidence_ids'],['E5'])

    def test_unsupported_recheck_deadline_cannot_silently_produce_current_claims(self):
        for value in [None, '2030-01-07T08:00:00Z', '2030-01-08T00:00:00Z']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.select(['E0'], overrides={'E0':{'recheck_after':value}})


if __name__ == '__main__':
    unittest.main()
