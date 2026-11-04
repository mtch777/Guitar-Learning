"""Output quotas count real attacks while preserving complete musical owners."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import connected_tier2 as connected
import local_dynamics as dynamics
import material_rhythm_control as rhythm
import rhythm_output_control as control
import support_material_uses as uses
import test_material_expression_composition as expression
import test_direct_support_material as direct
from source_fact_tier1 import extract_documents, project_documents


SCOPES = [dict(parts=[2, 3], first_bar=b, last_bar=b) for b in (1, 4)]


def reload(value):
    return json.loads(json.dumps(value))


def build(kind='ordinary'):
    docs = expression.authored_documents()
    for part in (2, 3):
        beats = docs[f'track-{part}.json']['measures'][3]['voices'][0]['beats']
        for beat in beats:
            beat['notes'] = beat['notes'][:1]
        if kind == 'dead':
            beats[1]['notes'][0].update(dead=True, fret=-1)
        elif kind in ('rest_and_tie', 'rest_start'):
            beats[0]['notes'] = [dict(rest=True)]
            if kind == 'rest_and_tie':
                beats[2]['notes'][0].update(fret=beats[1]['notes'][0]['fret'], tie=True)
        elif kind == 'empty':
            for beat in beats:
                beat['notes'] = [dict(rest=True)]
    # Current backing eighth-note attacks provide the existing offset vocabulary.
    meta = docs['metadata.json']
    meta['tracks'].append(dict(name='Authored pulse', instrumentId=128))
    docs['track-4.json'] = dict(songId=meta['songId'], revisionId=meta['revisionId'],
        partId=4, instrumentId=128, tuning=[], measures=[
            dict(signature=[4, 4], voices=[dict(beats=[
                dict(type=8, duration=[1, 8], notes=[dict(string=0, fret=36)])
                for _ in range(8)])]) for _ in range(9)])
    lower = extract_documents(docs)
    t2 = connected.strip_lower(connected.analyze(lower, note_accent_slots=True,
        palm_mute_slots=True, dynamic_evidence=True, backing_bindings=[direct.FOREIGN]))
    current = expression.expression(t2)
    return docs, lower, t2, uses.from_tier2(current, SCOPES)


def requests(intention='later'):
    return [dict(use_id=f'material-use:{i}', scope=deepcopy(s), intention=intention)
            for i, s in enumerate(SCOPES)]


def feature(report):
    return report['output']['features'][control.FEATURE]


class RhythmOutputControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.lower, cls.original_t2, cls.model = build()
        cls.changed, cls.report = control.intervene(cls.model, requests(), 50)

    def test_half_counts_attacks_not_equally_weighted_uses(self):
        self.assertEqual(self.report['status'], 'SATISFIED')
        self.assertEqual(feature(self.report)['total_count'], 24)
        self.assertEqual(feature(self.report)['target_count'], 12)
        self.assertEqual(feature(self.report)['changed_count'], 12)
        self.assertEqual([len(g['attacks']) for g in self.report['groups']], [16, 8])
        self.assertEqual(self.report['offsets'], [dict(use_id='material-use:0',
            scope=SCOPES[0], offset_q='1/2')])
        # Independent source expectation: first quarter grows by half a beat,
        # the last shrinks by half; both complete coattacks move together.
        expected = expression.expected_later(expression.expression_documents(self.docs))
        actual = project_documents(uses.reconstruct(self.changed, {'variation': 0}))
        self.assertEqual(actual, expected)
        self.assertEqual(self.changed['lower_tier'], self.model['lower_tier'])
        self.assertEqual(self.changed['materials'], self.model['materials'])
        self.assertEqual(self.changed['slots'], self.model['slots'])

    def test_current_zero_save_and_original_reconstruction_are_distinct(self):
        saved = reload(self.changed)
        locked, report = control.intervene(saved, requests('earlier'), 0)
        self.assertEqual(locked, saved)
        self.assertTrue(report['output']['satisfied'])
        self.assertEqual(feature(report)['changed_count'], 0)
        self.assertEqual(report['groups'], [])
        self.assertEqual(project_documents(uses.reconstruct(locked, {'variation': 0})),
                         expression.expected_later(expression.expression_documents(self.docs)))
        original = uses.from_tier2(self.original_t2, SCOPES)
        self.assertEqual(uses.reconstruct(original, {'variation': 0}), self.lower)

    def test_hundred_cannot_hide_protected_boundary_attacks(self):
        before = deepcopy(self.model)
        out, report = control.intervene(self.model, requests(), 100)
        self.assertEqual(out, before)
        self.assertEqual(self.model, before)
        self.assertFalse(report['output']['satisfied'])
        self.assertEqual(feature(report)['total_count'], 24)
        self.assertEqual(report['search']['clock_reachable_changed_counts'], [0, 6, 12, 18])
        self.assertEqual(len(report['fixed_attack_ids']), 6)
        self.assertEqual(report['search']['checked_combinations'], 0)
        self.assertEqual(report['status'], 'TARGET_UNREACHABLE_WITH_DECLARED_CLOCK_OPTIONS')

    def test_saved_offset_to_zero_counts_as_real_change(self):
        # Offset zero restores this material's source clock; relative to an
        # already early current clock it is a nonzero, later musical change.
        early = rhythm.candidate_many(self.model, [dict(use_id='material-use:0',
            scope=SCOPES[0], offset_q='-1/2')])
        out, report = control.intervene(reload(early), requests(), 50, seed=0)
        self.assertTrue(report['output']['satisfied'])
        self.assertEqual(feature(report)['changed_count'], 12)
        self.assertEqual(report['offsets'][0]['offset_q'], '0')
        self.assertEqual(project_documents(uses.reconstruct(out, {'variation': 0})),
                         expression.expression_documents(self.docs))
        self.assertEqual(out['lower_tier'], early['lower_tier'])

    def test_expression_edit_between_saved_rhythm_operations_survives(self):
        saved = reload(self.changed)
        t2 = uses.expand(saved)
        edited = dynamics.apply(t2, expression.DYNAMIC, 'f')
        packed = uses.pack_expression(saved, edited)
        out, report = control.intervene(packed, requests('earlier'), 50)
        self.assertTrue(report['satisfied'])
        self.assertEqual(feature(report)['changed_count'], 12)
        self.assertEqual(out['lower_tier'], packed['lower_tier'])
        actual = project_documents(uses.reconstruct(out, {'variation': 0}))
        beats = actual['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual(beats[0]['velocity'], 'f')
        self.assertNotIn('accentuated', beats[1]['notes'][0])

    def test_unknown_tie_and_grace_are_not_silently_removed(self):
        docs = deepcopy(self.docs)
        beats = docs['track-2.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes'][0]['tie'] = 'unknown'
        beats[1]['graceNote'] = True
        # The pure inventory receives normalized written occurrences. It must
        # retain these explicitly uncertain attacks before feasibility admission.
        events = control.extract_documents(self.docs)['events']
        inventory, exclusions = control._inventory(docs, events, requests())
        kinds = [a['kind'] for rows in inventory.values() for a in rows]
        self.assertEqual(sum(map(len, inventory.values())), 24)
        self.assertEqual(kinds.count('unknown_tie'), 1)
        self.assertEqual(kinds.count('grace'), 2)
        self.assertEqual(exclusions, [])

    def test_measurement_of_realized_output_uses_same_frozen_occurrences(self):
        lower = uses.reconstruct(self.changed, {'variation': 0})
        measured = control.measurements(lower, requests())
        result = control.evaluate_targets(self.report['target_contract'], measured)
        self.assertEqual(result, self.report['output'])

    def test_dead_attack_stays_in_denominator_and_blocks_its_group(self):
        _, _, _, model = build('dead')
        out, report = control.intervene(model, requests(), 50)
        self.assertTrue(report['output']['satisfied'])
        self.assertEqual(feature(report)['total_count'], 24)
        blocked = report['groups'][1]
        self.assertEqual(sum(a['kind'] == 'dead' for a in blocked['attacks']), 2)
        self.assertEqual(len(blocked['fixed_attack_ids']), 8)
        self.assertTrue(blocked['rejected'])
        before = project_documents(uses.reconstruct(model, {'variation': 0}))
        after = project_documents(uses.reconstruct(out, {'variation': 0}))
        for part in (2, 3):
            self.assertEqual(before[f'track-{part}.json']['measures'][3],
                             after[f'track-{part}.json']['measures'][3])

    def test_rests_and_tied_continuations_are_structural_not_deleted_attacks(self):
        _, _, _, model = build('rest_and_tie')
        out, report = control.intervene(model, requests(), 50)
        self.assertEqual(out, model)
        self.assertEqual(feature(report)['total_count'], 20)
        reasons = [r['reason'] for r in report['structural_exclusions']]
        self.assertEqual(reasons.count('explicit_rest'), 2)
        self.assertEqual(reasons.count('tied_continuation_not_new_attack'), 2)
        self.assertEqual(len(report['groups'][1]['attacks']), 4)
        self.assertFalse(report['output']['satisfied'])

    def test_hundred_succeeds_when_every_attack_can_actually_move(self):
        _, _, _, model = build('rest_start')
        out, report = control.intervene(model, requests()[1:], 100)
        self.assertTrue(report['satisfied'])
        self.assertEqual(feature(report)['total_count'], 6)
        self.assertEqual(feature(report)['changed_count'], 6)
        self.assertEqual(report['fixed_attack_ids'], [])
        before = project_documents(uses.reconstruct(model, {'variation': 0}))
        after = project_documents(uses.reconstruct(out, {'variation': 0}))
        for part in (2, 3):
            self.assertEqual(before[f'track-{part}.json']['measures'][0],
                             after[f'track-{part}.json']['measures'][0])

    def test_empty_attack_scope_is_not_a_successful_zero_request(self):
        _, _, _, model = build('empty')
        out, report = control.intervene(model, requests()[1:], 0)
        self.assertEqual(out, model)
        self.assertEqual(report['status'], 'NOT_APPLICABLE')
        self.assertFalse(report['satisfied'])
        self.assertEqual(feature(report)['total_count'], 0)

    def test_same_count_alternatives_survive_full_inverse_refusal(self):
        early = rhythm.candidate_many(self.model, [dict(use_id='material-use:0',
            scope=SCOPES[0], offset_q='-1/2')])
        original = rhythm.candidate_many
        calls = []
        def refuse_first(model, rows):
            calls.append(deepcopy(rows))
            if len(calls) == 1:
                raise ValueError('Authored dependent execution refuses this complete choice')
            return original(model, rows)
        frozen = deepcopy(early)
        with patch.object(rhythm, 'candidate_many', side_effect=refuse_first):
            out, report = control.intervene(early, requests(), 50, max_combinations=2)
        self.assertEqual(early, frozen)
        self.assertTrue(report['output']['satisfied'])
        self.assertEqual(report['search']['target_matching_vectors'], 2)
        self.assertEqual(report['search']['checked_combinations'], 2)
        self.assertEqual(len(report['search']['failures']), 1)
        self.assertNotEqual(calls[0], calls[1])
        self.assertNotEqual(out, early)

    def test_search_budget_and_exhaustive_refusal_remain_distinct(self):
        early = rhythm.candidate_many(self.model, [dict(use_id='material-use:0',
            scope=SCOPES[0], offset_q='-1/2')])
        frozen = deepcopy(early)
        for budget, status in ((1, 'COMBINATION_BUDGET_EXHAUSTED'),
                               (2, 'TARGET_REFUSED_BY_COMPLETE_INVERSE')):
            with self.subTest(budget=budget), patch.object(rhythm, 'candidate_many',
                    side_effect=ValueError('Authored complete-choice dependency refusal')):
                out, report = control.intervene(early, requests(), 50, max_combinations=budget)
                self.assertEqual(out, frozen)
                self.assertEqual(early, frozen)
                self.assertEqual(report['status'], status)
                self.assertEqual(report['search']['exhaustive_for_target'], budget == 2)
                self.assertEqual(feature(report)['changed_count'], 0)

    def test_invalid_requests_are_atomic(self):
        bad = []
        duplicated = requests(); duplicated.append(deepcopy(duplicated[0])); bad.append(duplicated)
        unknown = requests(); unknown[0]['use_id'] = 'missing'; bad.append(unknown)
        wrong = requests(); wrong[0]['scope']['last_bar'] = 2; bad.append(wrong)
        invalid = requests(); invalid[0]['intention'] = 'random'; bad.append(invalid)
        frozen = deepcopy(self.model)
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                control.intervene(self.model, rows, 50)
            self.assertEqual(self.model, frozen)

    def test_shared_option_helper_matches_existing_public_options(self):
        lower = uses.reconstruct(self.model, {'variation': 0})
        docs = project_documents(lower)
        events = control.extract_documents(docs)['events']
        for row in requests():
            self.assertEqual(rhythm.options(self.model, row['use_id']),
                rhythm._options_from_context(self.model, row['use_id'], docs, events))


if __name__ == '__main__':
    unittest.main()
