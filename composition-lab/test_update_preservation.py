"""Protect a complete saved model, not just the notes it currently produces."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from source_observation_evidence import assert_only_parameter_changes
from test_coattack_treatment_ownership import model, controls
import coattack_treatment_ownership as treatment
from connected_tier2 import realize

PATHS = [('musical_relationships', 'parameters', 'residual'),
         ('musical_relationships', 'parameters', 'follow')]


class UpdatePreservationTests(unittest.TestCase):
    def test_saved_successive_intents_preserve_complete_other_state(self):
        _, initial = model()
        snapshot = deepcopy(initial)
        first, _ = treatment.intervene(initial, controls())
        saved = json.loads(json.dumps(first))
        second, _ = treatment.intervene(saved, controls(intent=treatment.INTENTS[1]))
        assert_only_parameter_changes(initial, first, PATHS)
        assert_only_parameter_changes(saved, second, PATHS)
        self.assertEqual(initial, snapshot)
        self.assertEqual(treatment.intervene(second, controls(0))[0], second)
        self.assertNotEqual(realize(first), realize(second))

    def test_updater_rejects_loss_outside_relationship_wrapper(self):
        _, initial = model()
        # Fault injection tests the boundary, not a fabricated musical result.
        # A future deepcopy/rebuild helper drops an owned parameter outside
        # the musical_relationships wrapper. The incoming model is valid.
        snapshot = deepcopy(initial)
        def dropping_copy(value):
            result = deepcopy(value)
            if value is initial:
                result['owned_parameters'].pop(next(iter(result['owned_parameters'])))
            return result
        with patch.object(treatment, 'deepcopy', side_effect=dropping_copy):
            with self.assertRaisesRegex(ValueError, 'UPDATE_CHANGED_PROTECTED_STATE'):
                treatment.intervene(initial, controls())
        self.assertEqual(initial, snapshot)

    def test_evidence_owner_identity_and_obligation_loss_rejected(self):
        _, initial = model()
        changed, _ = treatment.intervene(initial, controls())
        for field in ('source_origin', 'owned_parameters', 'musical_relationships'):
            corrupt = deepcopy(changed)
            del corrupt[field]
            with self.assertRaises(ValueError):
                assert_only_parameter_changes(initial, corrupt, PATHS)
        corrupt = deepcopy(changed)
        corrupt['musical_relationships']['observations']['coattack_count'] += 1
        with self.assertRaisesRegex(ValueError, 'UPDATE_CHANGED_PROTECTED_STATE'):
            assert_only_parameter_changes(initial, corrupt, PATHS)

    def test_only_existing_scalar_leaves_can_be_permitted(self):
        initial = {'owner': {'parameter': 1, 'members': ['a', 'b']}, 'flag': True}
        for paths in ([('owner',)], [('owner', 'members')], [('owner', 'absent')],
                      [('owner', 'members', True)], [['owner', 'parameter']]):
            with self.assertRaises(ValueError):
                assert_only_parameter_changes(initial, initial, paths)
        removed = deepcopy(initial); del removed['owner']['parameter']
        with self.assertRaises(ValueError):
            assert_only_parameter_changes(initial, removed, [('owner', 'parameter')])
        corrupt = deepcopy(initial); corrupt['flag'] = 1
        with self.assertRaisesRegex(ValueError, 'UPDATE_CHANGED_PROTECTED_STATE'):
            assert_only_parameter_changes(initial, corrupt, [('owner', 'parameter')])


if __name__ == '__main__': unittest.main()
