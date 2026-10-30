"""Bounded synthetic composition checks, not joint-lever musical acceptance.

Use existing per-policy calls and their existing inverse. No multi-control API,
real-song execution, or arbitrary combination compatibility is implied here.
"""
from copy import deepcopy
from itertools import product
import unittest

from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents, project_documents
from test_group_rhythm_relations import documents as rhythm_documents
import local_accents as accents
import local_dynamics as dynamics
import local_group_rhythm as rhythm
import melodic_contour_choices as melody_choices
import melodic_contour_intervention as melody


OUTSIDE = 'event:77:0:1:0:4:0'
INSIDE = 'event:77:0:1:0:0:0'
DYNAMIC = 'track-0.json#/measures/4/voices/0/beats/0/velocity'


def documents():
    docs = rhythm_documents()
    measures = docs['track-0.json']['measures']
    measures.extend([deepcopy(m) for m in (measures[0], measures[0], measures[1])])
    # Source-observed accent alternatives at the target's unchanged offset2q.
    measures[1]['voices'][0]['beats'][4]['notes'][0]['accentuated'] = 1
    # Source-observed alternatives for both possible first-note durations.
    # These groups are deliberately NOT admitted by the plain rhythm owner.
    measures[3]['voices'][0]['beats'][0]['notes'][0]['accentuated'] = 1
    measures[5]['voices'][0]['beats'][0]['notes'][0]['accentuated'] = 1
    measures[4]['voices'][0]['beats'][0]['velocity'] = 'mf'
    return docs


def control(module, key, target, value=100, seed=0):
    return dict(context_policy=module.POLICY, target_ref=target, seed=seed, **{key: value})


def changed_seed(module, evidence, key, target, *, predicate=lambda choice: True):
    for seed in range(64):
        choice, decision = module.sample(evidence, control(module, key, target, seed=seed))
        if decision['changed'] and predicate(choice):
            return seed
    raise AssertionError('Fixture did not provide a supported changed draw')


class LocalLeverCombinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = extract_documents(documents())
        cls.upper = strip_lower(analyze(cls.before, rhythm_groups=True, note_accent_slots=True))
        cls.rhythm_ref = cls.upper['musical_relationships']['groups'][0]['id']

    def test_all_four_zero_locks_compose_exactly_in_both_orders(self):
        operations = [
            (accents.intervene, control(accents, 'accents', OUTSIDE, 0)),
            (dynamics.intervene, control(dynamics, 'dynamics', DYNAMIC, 0)),
            (rhythm.intervene, control(rhythm, 'rhythm', self.rhythm_ref, 0)),
            (melody.intervene, control(melody_choices, 'melody', OUTSIDE, 0)),
        ]
        for sequence in (operations, operations[::-1]):
            upper = deepcopy(self.upper)
            for operation, controls in sequence:
                upper, decision = operation(upper, controls)
                self.assertFalse(decision['changed'])
                self.assertEqual(decision['status'], 'EXACT_ZERO_LOCK')
            self.assertEqual(upper, self.upper)
            self.assertEqual(realize(upper), self.before)

    def test_disjoint_rhythm_and_accent_match_in_both_orders_at_zero_fifty_hundred(self):
        rhythm_evidence = rhythm.options(self.before, self.rhythm_ref)
        accent_evidence = accents.options(self.before, OUTSIDE)
        rhythm_seed = changed_seed(rhythm, rhythm_evidence, 'rhythm', self.rhythm_ref)
        accent_seed = changed_seed(accents, accent_evidence, 'accents', OUTSIDE)
        self.assertNotIn(accent_evidence['target']['beat_ref'], rhythm_evidence['target']['closure_refs'])
        for rhythm_value, accent_value in product((0, 50, 100), repeat=2):
            with self.subTest(rhythm=rhythm_value, accents=accent_value):
                r = control(rhythm, 'rhythm', self.rhythm_ref, rhythm_value, rhythm_seed)
                a = control(accents, 'accents', OUTSIDE, accent_value, accent_seed)
                r_first, rd = rhythm.intervene(self.upper, r)
                ra, ad = accents.intervene(r_first, a)
                a_first, ad2 = accents.intervene(self.upper, a)
                ar, rd2 = rhythm.intervene(a_first, r)
                self.assertEqual(realize(ra), realize(ar))
                self.assertEqual(ra, ar)
                self.assertEqual((rd['changed'], ad['changed']), (rd2['changed'], ad2['changed']))
                if rhythm_value == accent_value == 100:
                    self.assertTrue(rd['changed'] and ad['changed'])
                # Independently compose only the two allowed source changes.
                expected = project_documents(realize(r_first))
                accent_only = project_documents(realize(a_first))
                expected['track-0.json']['measures'][0]['voices'][0]['beats'][4]['notes'][0] = deepcopy(
                    accent_only['track-0.json']['measures'][0]['voices'][0]['beats'][4]['notes'][0])
                self.assertEqual(project_documents(realize(ra)), expected)

    def test_accent_inside_owned_plain_rhythm_is_refused_without_mutating_input(self):
        rseed = changed_seed(rhythm, rhythm.options(self.before, self.rhythm_ref), 'rhythm', self.rhythm_ref)
        rhythm_changed, _ = rhythm.intervene(self.upper, control(rhythm, 'rhythm', self.rhythm_ref, seed=rseed))
        for upper in (self.upper, rhythm_changed):
            with self.subTest(rhythm_already_changed=upper != self.upper):
                preserved = deepcopy(upper)
                evidence = accents.options(realize(upper), INSIDE)
                seed = changed_seed(accents, evidence, 'accents', INSIDE,
                                    predicate=lambda c: c['sound_level'] == 1)
                # Donors support the accent; the current rhythm ownership does
                # not permit adding it. Keep that distinction explicit.
                self.assertTrue(evidence['witness_pair'])
                with self.assertRaisesRegex(ValueError, 'Rhythm group not supported by reconstructed source'):
                    accents.intervene(upper, control(accents, 'accents', INSIDE, seed=seed))
                self.assertEqual(upper, preserved)
                self.assertEqual(realize(upper), realize(preserved))


if __name__ == '__main__':
    unittest.main()
