"""Exercise policy entry guards; do not infer coverage from decorator presence."""
from contextlib import ExitStack
from copy import deepcopy
from importlib import import_module
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents
import local_dynamics
from test_check_local_dynamics import documents


# The 13 direct intervene entry points expose 16 distinct relevant release knobs.
# Semantic eligibility is deliberately irrelevant: unsafe evidence must fail
# before any donor query, including when a target does not exist in this fixture.
POLICIES = (
    ('local_dynamics', 'source_local_dynamic_level', ('dynamics',), 'track-0.json#/measures/0/voices/0/beats/0/velocity', {}),
    ('dynamic_context', 'source_local_dynamic_transition', ('dynamics',), 'track-0.json#/measures/0/voices/0/beats/0/velocity', {}),
    ('local_accents', 'source_local_note_accent', ('accents',), 'event:93:0:1:0:1:0', {}),
    ('local_palm_mutes', 'source_local_palm_mute', ('palm_mute',), 'coattack:0:0', {}),
    ('local_group_rhythm', 'source_complete_group_rhythm', ('rhythm',), 'source-beam:0:0', {}),
    ('local_step_tempos', 'source_rhythmic_component_tempo', ('tempo',), 'global-tempo:0', {'component_ref': 'part:0:voice:0'}),
    ('melodic_contour_intervention', 'source_local_melodic_contour', ('melody',), 'event:93:0:1:0:1:0', {}),
    ('melodic_figure_intervention', 'source_local_melodic_figure', ('melody',), 'event:93:0:1:0:1:0', {}),
    ('voicing_register', 'joint_source_fingering', ('voicing', 'register', 'physical'), 'coattack:0:0', {}),
    ('voicing_gestures', 'source_gesture_context', ('voicing', 'physical'), 'coattack:0:0', {'register': 0}),
    ('declared_degree_choices', 'declared_degree_allocation', ('voicing',), 'coattack:0:0', {'register': 0}),
    ('inner_voicing', 'source_inner_degree_component', ('voicing',), 'coattack:0:0', {'register': 0}),
    ('unlabeled_inner_voicing', 'all_hypothesis_inner_preview', ('voicing',), 'coattack:0:0', {'register': 0}),
)


def requests():
    for module_name, policy, knobs, target, extra in POLICIES:
        base = dict(context_policy=policy, target_ref=target, seed=0, **extra)
        base.update({knob: 0 for knob in knobs})
        for knob in knobs:
            yield module_name, knob, dict(base, **{knob: 100})


def trap_queries(stack, module):
    traps = []
    for name in ('inventory', 'options', 'package_options', 'catalog', 'prepare'):
        if callable(getattr(module, name, None)):
            traps.append(stack.enter_context(patch.object(module, name, side_effect=AssertionError('Donor query ran before admission: ' + module.__name__ + '.' + name))))
    return traps


class SourceObservationGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = extract_documents(documents())
        cls.original = strip_lower(analyze(cls.before))
        cls.changed = local_dynamics.apply(cls.original, 'track-0.json#/measures/0/voices/0/beats/0/velocity', 'mf')
        cls.changed_facts = realize(cls.changed)
        assert cls.changed_facts != cls.before

    def test_all_entry_points_refuse_changed_origin_before_donor_query(self):
        self.assertEqual(len(POLICIES), 13)
        self.assertEqual(len(list(requests())), 16)
        for module_name, knob, request in requests():
            with self.subTest(module=module_name, knob=knob), ExitStack() as stack:
                module = import_module(module_name)
                traps = trap_queries(stack, module)
                score = deepcopy(self.changed)
                snapshot = deepcopy(score)
                with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
                    module.intervene(score, request)
                for trap in traps:
                    trap.assert_not_called()
                self.assertEqual(score, snapshot)
                self.assertEqual(realize(score), self.changed_facts)

    def test_all_entry_points_require_origin_for_nonzero_legacy_calls(self):
        for module_name, knob, request in requests():
            with self.subTest(module=module_name, knob=knob), ExitStack() as stack:
                module = import_module(module_name)
                traps = trap_queries(stack, module)
                score = deepcopy(self.original)
                score.pop('source_origin')
                snapshot = deepcopy(score)
                with self.assertRaisesRegex(ValueError, 'MISSING_ORIGINAL_OBSERVATIONS'):
                    module.intervene(score, request)
                for trap in traps:
                    trap.assert_not_called()
                self.assertEqual(score, snapshot)

    def test_null_control_mapping_is_refused_before_queries(self):
        for module_name, *_ in POLICIES:
            with self.subTest(module=module_name), ExitStack() as stack:
                module = import_module(module_name)
                traps = trap_queries(stack, module)
                score = deepcopy(self.original)
                snapshot = deepcopy(score)
                with self.assertRaises(ValueError):
                    module.intervene(score, None)
                for trap in traps:
                    trap.assert_not_called()
                self.assertEqual(score, snapshot)

    def test_null_nan_and_boolean_release_values_are_not_valid_zero_or_nonzero(self):
        for module_name, knob, request in requests():
            for invalid in (None, float('nan'), False, True):
                with self.subTest(module=module_name, knob=knob, invalid=invalid), ExitStack() as stack:
                    module = import_module(module_name)
                    traps = trap_queries(stack, module)
                    score = deepcopy(self.original)
                    snapshot = deepcopy(score)
                    with self.assertRaises(ValueError):
                        module.intervene(score, dict(request, **{knob: invalid}))
                    for trap in traps:
                        trap.assert_not_called()
                    self.assertEqual(score, snapshot)


if __name__ == '__main__':
    unittest.main()
