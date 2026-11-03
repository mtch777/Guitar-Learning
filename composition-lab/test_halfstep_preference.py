"""Literal half steps stay possible; preference is bounded and context-frozen."""
from copy import deepcopy
from pathlib import Path
import json
import random
import tempfile
import unittest

import halfstep_preference as preference
import melodic_movement_ownership as movement
from source_fact_tier1 import extract_documents
from test_melodic_movement_ownership import (
    SONG, TARGET, beat, bar, v2_documents, build_v2, v2_controls,
)


def authored(pitches, backing=None):
    rows = [dict(duration=[1, 4], notes=[dict(string=0, fret=p-40)]) for p in pitches]
    docs = {'metadata.json': dict(songId=SONG, revisionId=1, tracks=[dict(instrumentId=27)]),
            'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=27,
                tuning=[40], measures=[dict(signature=[len(rows), 4], voices=[dict(beats=rows)])])}
    if backing is not None:
        docs['metadata.json']['tracks'].append(dict(instrumentId=27))
        docs['track-1.json'] = dict(songId=SONG, revisionId=1, partId=1, instrumentId=27,
            tuning=[40], measures=[dict(signature=[len(rows), 4], voices=[dict(beats=[
                dict(duration=[1, 4], notes=[dict(rest=True)] if p is None else [dict(string=0, fret=p-40)])
                for p in backing])])])
    refs = [f'event:{SONG}:0:1:0:{i}:0' for i in range(len(rows))]
    return extract_documents(docs), [dict(attack_ref=ref, member_refs=[ref]) for ref in refs]


class HalfstepPreferenceTests(unittest.TestCase):
    def test_observed_melodic_halfstep_has_no_penalty(self):
        source, attacks = authored([60, 61, 64])
        candidate, _ = authored([60, 61, 60])
        context = preference.freeze(source, attacks)
        self.assertEqual(preference.evaluate(candidate, context)['weight'], '1')

    def test_absent_melodic_halfstep_is_discounted_once_and_still_reachable(self):
        source, attacks = authored([60, 64, 67, 72])
        candidate, _ = authored([60, 61, 60, 61])
        context = preference.freeze(source, attacks); original = deepcopy(context)
        plain = preference.evaluate(source, context)
        changed = preference.evaluate(candidate, context)
        self.assertEqual(changed['weight'], '19/20')
        self.assertEqual(changed['discount_count'], 1)
        self.assertEqual(len(changed['candidate']['melodic']), 3)
        chosen = [preference.choose([plain, changed], random.Random(seed)) for seed in range(2000)]
        self.assertEqual(set(chosen), {0, 1})
        self.assertEqual(context, original)
        self.assertFalse(context['supported']['melodic'])

    def test_melodic_and_simultaneous_precedents_are_separate(self):
        source, attacks = authored([60, 64, 67], [61, 40, 40])
        candidate, _ = authored([60, 61, 62], [61, 40, 40])
        context = preference.freeze(source, attacks)
        self.assertEqual(context['supported'], dict(melodic=False, simultaneous=True))
        more_vertical, _ = authored([60, 64, 67], [61, 65, 68])
        self.assertEqual(preference.evaluate(more_vertical, context)['weight'], '1')
        evaluation = preference.evaluate(candidate, context)
        self.assertEqual(evaluation['introduced_categories'], ['melodic'])
        self.assertEqual(evaluation['weight'], '19/20')
        source, attacks = authored([60, 61, 64], [40, 40, 40])
        candidate, _ = authored([60, 61, 64], [61, 40, 40])
        evaluation = preference.evaluate(candidate, preference.freeze(source, attacks))
        self.assertEqual(evaluation['introduced_categories'], ['simultaneous'])

    def test_many_vertical_and_melodic_halfsteps_share_one_discount(self):
        source, attacks = authored([60, 64, 67], [40, 40, 40])
        candidate, _ = authored([60, 61, 62], [61, 62, 63])
        result = preference.evaluate(candidate, preference.freeze(source, attacks))
        self.assertEqual(result['introduced_categories'], ['melodic', 'simultaneous'])
        self.assertEqual(result['weight'], '19/20')
        self.assertEqual(result['discount_count'], 1)

    def test_octave_equivalent_classes_are_not_literal_adjacency(self):
        source, attacks = authored([60, 64], [40, 40])
        context = preference.freeze(source, attacks)
        for pitches, backing in (([60, 73], [71, 40]), ([73, 60], [60, 71])):
            candidate, _ = authored(pitches, backing)
            result = preference.evaluate(candidate, context)
            self.assertEqual(result['weight'], '1')
            self.assertFalse(result['candidate']['melodic'])
            self.assertFalse(result['candidate']['simultaneous'])

    def test_original_reference_evidence_and_current_context_are_not_conflated(self):
        source, attacks = authored([60, 64, 67])
        candidate, _ = authored([60, 61, 62])
        original_context = preference.freeze(source, attacks, original_reference_steps=['1', '2'],
                                             source_origin={'fixture': 'unchanged'})
        self.assertEqual(preference.evaluate(candidate, original_context)['weight'], '1')
        self.assertEqual(original_context['original_reference_halfstep_indices'], [0])
        no_reference = preference.freeze(source, attacks)
        self.assertEqual(preference.evaluate(candidate, no_reference)['weight'], '19/20')
        later = preference.freeze(candidate, attacks)
        self.assertEqual(preference.evaluate(candidate, later)['weight'], '1')
        self.assertEqual(later['evidence_role'], 'CURRENT_INPUT_TARGET_AND_DECLARED_REFERENCE_CONTEXT')
        self.assertEqual(later['original_reference_halfstep_indices'], [])

    def test_equal_weights_preserve_legacy_seed_draws(self):
        for seed in range(100):
            rows = [dict(weight='1') for _ in range(4)]
            self.assertEqual(preference.choose(rows, random.Random(seed)), random.Random(seed).randrange(4))
        with self.assertRaises(ValueError):
            preference.choose([dict(weight='0')], random.Random(0))

    def test_active_complete_candidate_wiring_and_saved_zero(self):
        docs = v2_documents()
        docs['track-1.json']['measures'][1] = bar([beat(p, tuning=40) for p in (40, 66, 40)]+[beat()])
        _, lower, _, upper = build_v2(docs)
        original = deepcopy(upper)
        changed = None
        for seed in (0, 1, 2, 3):
            output, report = movement.intervene(upper, v2_controls(100, 0, seed=seed))
            candidates = report['decisions']['melody']['halfstep_candidates']
            self.assertEqual([row['weight'] for row in candidates], ['1', '19/20'])
            self.assertEqual(candidates[1]['introduced_categories'], ['simultaneous'])
            self.assertEqual(candidates[1]['candidate']['simultaneous'][0]['member_refs'],
                             sorted([TARGET[1], f'event:{SONG}:1:2:0:1:0']))
            self.assertEqual(report['released'], dict(melody=True, register=False))
            self.assertEqual(report['halfstep_preference']['final_output'],
                             preference.evaluate(movement._realize(output), report['halfstep_preference']['context']))
            self.assertEqual(output['owned_parameters'][movement.SLOT]['observations'],
                             upper['owned_parameters'][movement.SLOT]['observations'])
            if report['decisions']['melody']['selected_index'] == 1:
                changed = output
        self.assertIsNotNone(changed, 'A discounted complete candidate must remain reachable')
        saved = json.loads(json.dumps(changed))
        locked, report = movement.intervene(saved, v2_controls())
        self.assertEqual(locked, saved)
        self.assertIsNone(report['halfstep_preference'])
        self.assertEqual(movement._realize(upper), lower)
        self.assertEqual(upper, original)

    def test_actual_source_denied_worker_and_saved_current_zero(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        docs = v2_documents()
        docs['track-1.json']['measures'][1] = bar([beat(p, tuning=40) for p in (40, 66, 40)]+[beat()])
        _, original, _, upper = build_v2(docs)
        controls = v2_controls(100, 0, seed=1)
        changed, report = movement.intervene(upper, controls)
        self.assertEqual(report['decisions']['melody']['halfstep_candidates'][1]['weight'], '19/20')
        self.assertTrue(report['changed'])
        expected = movement._realize(changed)
        code, hashes = bundle(Path(__file__).parent)
        self.assertIn('halfstep_preference', hashes)
        with tempfile.TemporaryDirectory() as folder:
            for label, model, request, wanted in (
                    ('original', upper, {'variation': 0}, original),
                    ('nonzero', upper, controls, expected),
                    ('saved-current-zero', json.loads(json.dumps(changed)), {'variation': 0}, expected)):
                with self.subTest(label=label):
                    receipt = execute(code, model, request, wanted, Path(folder)/label, timeout=30,
                        purpose='melodic_movement' if label == 'nonzero' else 'exact_zero')
                    self.assertEqual(receipt['status'], 'PASS', receipt)


if __name__ == '__main__':
    unittest.main()
