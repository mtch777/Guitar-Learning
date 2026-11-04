"""Output change is neither a draw nor a count of modified parameters."""
from copy import deepcopy
import json
import unittest

from output_change_targets import freeze_targets, evaluate_targets, target_count


class OutputChangeTargetsTests(unittest.TestCase):
    def test_actual_half_and_all_with_frozen_scope(self):
        values = {'pitch_class': {'a': 0, 'b': 2, 'c': 4}}
        contract = freeze_targets(values, {'pitch_class': 50})
        self.assertEqual(target_count(3, 50), 2)
        self.assertFalse(evaluate_targets(contract, values)['satisfied'])
        report = evaluate_targets(contract, {'pitch_class': {'a': 1, 'b': 3, 'c': 4}})
        self.assertTrue(report['satisfied'])
        self.assertEqual(report['features']['pitch_class']['achieved_fraction'], '2/3')
        self.assertFalse(evaluate_targets(freeze_targets(values, {'pitch_class': 100}),
            {'pitch_class': {'a': 1, 'b': 3, 'c': 4}})['satisfied'])

    def test_octave_does_not_credit_contour_and_final_cancellation_is_unchanged(self):
        before = {'octave': {'a': 4, 'b': 4}, 'steps': {'a->b': 2}}
        contract = freeze_targets(before, {'octave': 100, 'steps': 100})
        report = evaluate_targets(contract, {'octave': {'a': 5, 'b': 5}, 'steps': {'a->b': 2}})
        self.assertFalse(report['satisfied'])
        self.assertEqual(report['features']['steps']['changed_count'], 0)
        # An up edit followed by a down edit is evaluated only in its final state.
        self.assertEqual(evaluate_targets(contract, before)['features']['octave']['changed_count'], 0)

    def test_original_direction_return_and_relation_cannot_all_flip(self):
        before = {'earlier': {'phrase': 1}, 'return': {'phrase': 1}, 'relation': {'pair': 1}}
        contract = freeze_targets(before, dict.fromkeys(before, 100))
        for earlier in (-1, 1):
            for returning in (-1, 1):
                realized = {'earlier': {'phrase': earlier}, 'return': {'phrase': returning},
                            'relation': {'pair': earlier * returning}}
                self.assertFalse(evaluate_targets(contract, realized)['satisfied'])

    def test_unknown_and_empty_never_manufacture_a_pass(self):
        for value in (None, 1):
            contract = freeze_targets({'pitch': {'a': None}}, {'pitch': 100})
            report = evaluate_targets(contract, {'pitch': {'a': value}})
            self.assertFalse(report['satisfied'])
            self.assertEqual(report['features']['pitch']['total_count'], 1)
        contract = freeze_targets({'pitch': {}}, {'pitch': 100})
        self.assertEqual(evaluate_targets(contract, {'pitch': {}})['features']['pitch']['status'], 'NOT_APPLICABLE')

    def test_baseline_save_reload_immutable_and_denominator_cannot_shrink(self):
        values = {'onset': {'a': '0', 'b': '1'}}
        contract = freeze_targets(values, {'onset': 100})
        values['onset']['a'] = '2'
        saved = json.loads(json.dumps(contract))
        self.assertTrue(evaluate_targets(saved, {'onset': {'a': '1', 'b': '2'}})['satisfied'])
        with self.assertRaisesRegex(ValueError, 'identities'):
            evaluate_targets(saved, {'onset': {'a': '1'}})
        broken = deepcopy(saved)
        broken['baseline']['onset'].pop('b')
        with self.assertRaisesRegex(ValueError, 'modified'):
            evaluate_targets(broken, {'onset': {'a': '1'}})

    def test_all_features_are_explicit_and_zero_is_a_current_output_lock(self):
        values = {'pitch': {'a': 72}, 'velocity': {'a': 90}}
        with self.assertRaises(ValueError):
            freeze_targets(values, {'pitch': 0})
        contract = freeze_targets(values, {'pitch': 0, 'velocity': 100})
        self.assertTrue(evaluate_targets(contract, {'pitch': {'a': 72}, 'velocity': {'a': 95}})['satisfied'])
        self.assertFalse(evaluate_targets(contract, {'pitch': {'a': 60}, 'velocity': {'a': 95}})['satisfied'])
        for invalid in (True, -1, 101, 50.0):
            with self.assertRaises(ValueError):
                target_count(3, invalid)


if __name__ == '__main__':
    unittest.main()
