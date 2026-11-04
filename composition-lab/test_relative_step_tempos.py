"""Final tempo coverage, immutable aliases, and saved successive pace choices."""
from copy import deepcopy
import json
import unittest

from relative_step_tempos import apply_ratios
from step_tempo_relations import lift, expand, written_pass_seconds_at
from source_fact_tier1 import extract_documents
from test_step_tempo_relations import documents


class RelativeStepTempoTests(unittest.TestCase):
    def setUp(self):
        self.model = lift(extract_documents(documents()))
        self.refs = [g['id'] for g in self.model['groups']]

    def test_all_regions_change_not_alias_count_and_original_is_unchanged(self):
        before = deepcopy(self.model)
        edited, report = apply_ratios(self.model, baseline=before,
            ratios={key: '2' for key in self.refs}, percent=100)
        self.assertEqual(report['original_units'], 2)
        self.assertEqual(report['changed_from_baseline'], 2)
        self.assertEqual(report['target_units'], 2)
        self.assertEqual(self.model, before)
        self.assertEqual(len(expand(edited)), 4)
        for old, new in zip(before['groups'], edited['groups']):
            self.assertEqual({k:v for k,v in old.items() if k != 'quarter_seconds'},
                             {k:v for k,v in new.items() if k != 'quarter_seconds'})
        end = edited['groups'][-1]['end_q']
        from fractions import Fraction as F
        self.assertEqual(F(written_pass_seconds_at(edited, end))*2,
                         F(written_pass_seconds_at(before, end)))

    def test_half_changes_one_of_two_regions(self):
        _, report = apply_ratios(self.model, baseline=self.model,
            ratios={self.refs[0]: '3/2'}, percent=50)
        self.assertEqual(report['changed_from_baseline'], 1)

    def test_one_region_half_rounds_up_without_meaning_half_speed(self):
        one = dict(self.model, groups=self.model['groups'][:1])
        edited, report = apply_ratios(one, baseline=one,
            ratios={self.refs[0]: '3/2'}, percent=50)
        self.assertEqual(report['target_units'], 1)
        self.assertEqual(report['rows'][0]['result_bpm'], '180')

    def test_saved_zero_locks_current_and_subsequent_edit_uses_original_baseline(self):
        first, _ = apply_ratios(self.model, baseline=self.model,
            ratios={key: '2' for key in self.refs}, percent=100)
        saved = json.loads(json.dumps(first))
        zero, report = apply_ratios(saved, baseline=self.model,
            ratios={key: '1/2' for key in self.refs}, percent=0)
        self.assertEqual(zero, saved)
        self.assertEqual(report['changed_from_current'], 0)
        self.assertEqual(report['changed_from_baseline'], 2)
        second, report = apply_ratios(saved, baseline=self.model,
            ratios={key: '3/4' for key in self.refs}, percent=100)
        self.assertEqual([r['result_bpm'] for r in report['rows']], ['180','135'])
        self.assertNotEqual(second, saved)

    def test_refuses_cancellation_and_unsupported_native_bpm_atomically(self):
        original = deepcopy(self.model)
        changed, _ = apply_ratios(self.model, baseline=self.model,
            ratios={key: '2' for key in self.refs}, percent=100)
        cases = [(changed, {key: '1/2' for key in self.refs}),
                 (self.model, {self.refs[0]:'7/11'}),
                 (self.model, {'not-a-region':'2'}),
                 (self.model, {self.refs[0]:'0'})]
        for model, ratios in cases:
            frozen = deepcopy(model)
            with self.subTest(ratios=ratios), self.assertRaises(ValueError):
                apply_ratios(model, baseline=self.model, ratios=ratios, percent=100)
            self.assertEqual(model, frozen)
        self.assertEqual(self.model, original)

    def test_missing_or_rebound_original_region_cannot_shrink_denominator(self):
        changed=deepcopy(self.model)
        changed['groups'].pop()
        with self.assertRaisesRegex(ValueError, 'identities'):
            apply_ratios(changed, baseline=self.model, ratios={}, percent=100)


if __name__ == '__main__':
    unittest.main()
