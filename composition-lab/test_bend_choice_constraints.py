"""Authored arrival/hold tests; no private score or selected musical answer."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import bend_choice_constraints as bends
from source_fact_tier1 import extract_documents


REF = 'event:987601:0:1:0:0:0'
MAJOR = dict(id='declared-C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])
MINOR = dict(id='declared-C-minor', tonic_pc=0, intervals=[0, 2, 3, 5, 7, 8, 10])


def fixture(points, tone=100, **extra):
    bend = dict(tone=tone, points=[dict(position=x, tone=y) for x, y in points], **extra)
    docs = {'metadata.json': dict(songId=987601), 'track-0.json': dict(partId=0,
        measures=[dict(voices=[dict(beats=[dict(notes=[dict(string=0, fret=0, bend=bend)])])])])}
    return extract_documents(docs)


def capture(points=((0, 0), (60, 100)), tone=100, hypotheses=None):
    return bends.capture(fixture(points, tone), {REF: hypotheses or [MAJOR]})[REF]


class BendChoiceConstraintsTests(unittest.TestCase):
    def test_simple_rise_same_additive_target_and_full_step(self):
        c = capture()
        self.assertEqual(c['targets'], [dict(position='1', offset='2', roles=['arrival'])])
        self.assertEqual(bends.evaluate(c, 60)['targets'][0]['pitch'], '62')
        self.assertTrue(bends.evaluate(c, 60)['admissible'])
        self.assertFalse(bends.evaluate(c, 64)['admissible'])

    def test_plateau_and_endpoint_both_retained(self):
        c = capture(((0, 0), (15, 50), (60, 50)), 50)
        self.assertEqual(c['targets'][0], dict(position='1/4', offset='1', roles=['plateau'], until_position='1'))
        self.assertEqual(c['targets'][1]['roles'], ['arrival'])
        self.assertTrue(bends.evaluate(c, 64)['admissible'])  # E to F.
        self.assertFalse(bends.evaluate(c, 60)['admissible'])  # C to C#.

    def test_chromatic_intermediate_travel_is_not_a_held_target(self):
        c = capture(((0, 0), (30, 50), (60, 100)))
        self.assertEqual(len(c['targets']), 1)
        self.assertTrue(bends.evaluate(c, 60)['admissible'])  # Pass through C# to D.

    def test_chromatic_plateau_cannot_be_hidden_by_valid_final_target(self):
        c = capture(((0, 0), (15, 50), (30, 50), (60, 100)))
        result = bends.evaluate(c, 60)
        self.assertFalse(result['admissible'])
        self.assertEqual([r['pitch'] for r in result['targets']], ['61', '62'])

    def test_positive_prebend_release_and_turns_share_same_equation(self):
        c = capture(((0, 100), (60, 0)))
        self.assertEqual([r['roles'] for r in c['targets']], [['prebend'], ['arrival']])
        self.assertTrue(bends.evaluate(c, 60)['admissible'])
        turn = capture(((0, 0), (30, 50), (60, 0)), 50)
        self.assertFalse(bends.evaluate(turn, 60)['admissible'])
        self.assertEqual(turn['targets'][0]['roles'], ['turn'])

    def test_conditional_interpretation_disagreement_remains_visible(self):
        c = capture(hypotheses=[MAJOR, MINOR])
        result = bends.evaluate(c, 62)  # D -> E, outside C minor.
        self.assertFalse(result['admissible'])
        self.assertEqual(result['targets'][0]['interpretations'], [
            dict(interpretation_id=MAJOR['id'], in_collection=True),
            dict(interpretation_id=MINOR['id'], in_collection=False)])

    def test_negative_or_unknown_curve_refuses_explicitly_without_mutation(self):
        lowers = [fixture(((0, 0), (60, -50)), 50), fixture(((0, 0), (30, 50)), 50),
                  fixture(((0, 0), (60, 50)), 100), fixture(((0, 0), (60, 50)), 50, mystery=1)]
        for lower in lowers:
            before = deepcopy(lower)
            with self.assertRaisesRegex(ValueError, 'BEND_CURVE_UNSUPPORTED'):
                bends.capture(lower, {REF: [MAJOR]})
            self.assertEqual(lower, before)

    def test_missing_or_duplicate_context_refuses_instead_of_omitting_bend(self):
        lower = fixture(((0, 0), (60, 100)))
        with self.assertRaisesRegex(ValueError, 'BEND_CONTEXT_MISSING'):
            bends.capture(lower, {})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            bends.capture(lower, {REF: [MAJOR, MAJOR]})

    def test_precise_source_time_uses_existing_normalized_unit(self):
        lower = fixture(((0, 0), (60, 100)))
        docs = {'metadata.json': dict(songId=987601), 'track-0.json': dict(partId=0,
            measures=[dict(voices=[dict(beats=[dict(notes=[dict(bend=dict(tone=100,
            points=[dict(precisePosition=0, tone=0), dict(precisePosition=100, tone=100)]))])])])])}
        self.assertEqual(bends.capture(extract_documents(docs), {REF: [MAJOR]}),
                         bends.capture(lower, {REF: [MAJOR]}))

    def test_save_reload_filter_is_pure_preserves_order_metadata_and_has_no_source_access(self):
        c = json.loads(json.dumps(capture()))
        choices = [dict(pitch=64, string=1, fret=9, degree_delta=3),
                   dict(pitch=60, string=1, fret=5, degree_delta=1),
                   dict(pitch=72, string=0, fret=12, degree_delta=8)]
        before = deepcopy((c, choices))
        with patch('builtins.open', side_effect=AssertionError('No source access')):
            result = bends.filter_choices(c, choices)
        self.assertEqual(result['admitted'], choices[1:])
        self.assertEqual(result['rejected'][0]['choice'], choices[0])
        self.assertEqual((c, choices), before)
        result['admitted'][0]['pitch'] = 99
        self.assertEqual((c, choices), before)


if __name__ == '__main__':
    unittest.main()
