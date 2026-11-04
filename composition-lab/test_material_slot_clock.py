"""Existing-slot rhythm relationships; authored fixtures, no musical-quality claim."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import connected_tier2 as connected
import material_slot_clock as clock
import musical_support_material as material
from source_fact_tier1 import extract_documents, project_documents
from technique_observation_relations import scalar_relation
from test_written_tie_pitch_ownership import documents, note


def beat(*notes, duration=(1, 4), typ=4, **fields):
    return dict(duration=list(duration), type=typ, notes=list(notes or (note(),)), **fields)


def build(parts):
    docs = documents(parts[0])
    for part, bars in enumerate(parts[1:], 1):
        docs['metadata.json']['tracks'].append(dict(name='Guitar '+str(part), instrumentId=27))
        track = deepcopy(docs['track-0.json'])
        track['partId'] = part
        track['measures'] = [dict(signature=[4, 4], voices=[dict(beats=deepcopy(rows))]) for rows in bars]
        docs[f'track-{part}.json'] = track
    lower = extract_documents(docs)
    t2 = connected.strip_lower(connected.analyze(lower))
    definition = material.fit(t2, parts=list(range(len(parts))), first_bar=1,
                              last_bar=len(parts[0]), lower=lower)
    return docs, lower, t2, definition


def request(definition, shares, part=0, bar=1):
    lane = f'track-{part}.json#/measures/{bar-1}/voices/0/beats'
    refs = list(clock.current_lane_shares(definition)[lane])
    return {lane: dict(zip(refs, shares))}


def notation(definition):
    rows = {r['fact_ref']: r for r in material.expand(definition)['source_choices']}
    def scalar(ref):return scalar_relation('integer', parameter=rows[ref]['parameter'])
    return {s['beat_ref']: dict(duration=[scalar(s['beat_ref']+f'/duration/{i}') for i in (0, 1)],
                type=scalar(s['beat_ref']+'/type'),
                dots=scalar(s['beat_ref']+'/dots') if s['beat_ref']+'/dots' in rows else None)
            for s in definition['slots']}


class SlotClockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bar = [beat(note(fret=5+i)) for i in range(4)]
        cls.docs, cls.lower, cls.t2, cls.base = build([[deepcopy(bar)], [deepcopy(bar)]])

    def test_empty_and_current_shares_are_exact_including_optional_notation(self):
        bar = [beat(duration=(2, 8), dots=0), beat(), beat(), beat()]
        _, _, _, definition = build([[bar]])
        for choices in ({}, clock.current_lane_shares(definition)):
            saved = json.loads(json.dumps(definition))
            result, report = clock.solve(saved, choices)
            self.assertEqual(result, definition)
            self.assertEqual(saved, definition)
            self.assertFalse(report['changed'])
            self.assertEqual(report['notation_changes'], [])

    def test_selected_lane_changes_without_moving_coincident_unselected_lane(self):
        before = deepcopy(self.base)
        choices = request(self.base, ['1/8', '3/8', '1/8', '3/8'])
        changed, report = clock.solve(self.base, choices)
        self.assertTrue(report['changed'])
        self.assertEqual(len(changed['pulse_shares']), 6)
        original_groups = {g['id']: g for g in material.expand(self.base)['coattacks']}
        groups = material.expand(changed)['coattacks']
        for group in groups:
            if group['part_id'] == 1:
                self.assertEqual(group, original_groups[group['id']])
        selected = [g for g in groups if g['part_id'] == 0]
        self.assertEqual([g['onset_q'] for g in selected], ['0', '1/2', '2', '5/2'])
        self.assertEqual([g['members'][0]['duration_q'] for g in selected], ['1/2', '3/2', '1/2', '3/2'])
        for key in ('pitch_paths', 'voicings', 'bindings', 'observed_execution', 'provenance'):
            self.assertEqual(changed[key], before[key])
        for field in ('physical_positions', 'technique_declarations', 'coattacks', 'realization_order'):
            self.assertEqual(changed['lower_tier'][field], before['lower_tier'][field])
        self.assertEqual([s['fraction_scale'] for s in changed['slots']], [s['fraction_scale'] for s in before['slots']])
        self.assertEqual(self.base, before)

    def test_saved_nonzero_current_share_identity_and_subsequent_rhythm_edit(self):
        first, _ = clock.solve(self.base, request(self.base, ['1/8', '3/8', '1/8', '3/8']))
        saved = json.loads(json.dumps(first))
        identity, report = clock.solve(saved, clock.current_lane_shares(saved))
        self.assertEqual(identity, saved)
        self.assertFalse(report['changed'])
        second, _ = clock.solve(saved, request(saved, ['3/8', '1/8', '3/8', '1/8']))
        self.assertNotEqual(second['pulse_shares'], first['pulse_shares'])
        self.assertEqual(second['provenance'], self.base['provenance'])

    def test_triplet_ratio_and_group_markers_remain_explicit(self):
        bar = [beat(duration=(1, 6), tuplet=3) for _ in range(6)]
        bar[0]['tupletStart'] = True
        bar[-1]['tupletStop'] = True
        _, _, _, definition = build([[bar]])
        changed, report = clock.solve(definition, request(definition, ['1/12', '1/4']+['1/6']*4))
        values = list(notation(changed).values())
        self.assertEqual(values[:2], [dict(duration=[1, 12], type=8, dots=None), dict(duration=[1, 4], type=4, dots=1)])
        self.assertTrue(all(r['tuplet_multiplier'] == '2/3' for r in report['notation_changes']))
        self.assertEqual([r for r in changed['lower_tier']['source_choices'] if '/tuplet' in r['fact_ref']],
                         [r for r in definition['lower_tier']['source_choices'] if '/tuplet' in r['fact_ref']])

    def test_incoming_tie_and_fresh_dotted_half_can_become_two_halves(self):
        prior = [beat() for _ in range(4)]
        destination = [beat(note(tie=True), note(1, 4)),
                       beat(note(fret=7), duration=(3, 4), typ=2, dots=1)]
        docs, lower, t2, definition = build([[prior, destination]])
        changed, report = clock.solve(definition, request(definition, ['1/2', '1/2'], bar=2))
        values = [v for k, v in notation(changed).items() if '/measures/1/' in k]
        self.assertEqual(values, [dict(duration=[1, 2], type=2, dots=None), dict(duration=[1, 2], type=2, dots=0)])
        self.assertEqual(changed['observed_execution'], definition['observed_execution'])
        self.assertEqual(len(material.expand(changed)['coattacks'][-2]['members']), 2)
        expected = deepcopy(docs)
        a, b = expected['track-0.json']['measures'][1]['voices'][0]['beats']
        a.update(duration=[1, 2], type=2)
        b.update(duration=[1, 2], dots=0)
        skeleton = material._remove(t2, [definition['scope']])
        result = material.restore_fragments(skeleton, [material.expand(changed)])
        self.assertEqual(project_documents(connected.realize(connected.strip_lower(result))), expected)
        zero = material.restore_fragments(skeleton, [material.expand(clock.solve(definition, {})[0])])
        self.assertEqual(connected.realize(connected.strip_lower(zero)), lower)
        self.assertEqual(report['execution_validation'], 'REQUIRED_IN_COMPLETE_INVERSE')

    def test_rest_dead_and_complete_mixed_coattack_metadata_are_not_flattened(self):
        bar = [beat(note(), note(1, 4, dead=True), palmMute=True),
               beat(dict(rest=True), rest=True), beat(note(fret=7)), beat(note(fret=8))]
        _, _, _, definition = build([[bar]])
        changed, _ = clock.solve(definition, request(definition, ['1/8', '3/8', '1/8', '3/8']))
        for name in ('coattacks', 'technique_declarations', 'physical_positions', 'realization_order'):
            self.assertEqual(changed['lower_tier'][name], definition['lower_tier'][name])
        self.assertEqual(changed['observed_execution'], definition['observed_execution'])
        self.assertEqual(len(changed['slots']), len(definition['slots']))

    def test_single_slot_bar_accepts_one_identity_share_and_later_bar_can_change(self):
        _, _, _, definition = build([[[beat(duration=(1, 1), typ=1)], [beat(), beat(), beat(), beat()]]])
        choices = clock.current_lane_shares(definition)
        self.assertEqual(list(choices.values())[0], {'track-0.json#/measures/0/voices/0/beats/0': '1'})
        self.assertEqual(clock.solve(definition, choices)[0], definition)
        choices.update(request(definition, ['1/8', '3/8', '1/8', '3/8'], bar=2))
        changed, _ = clock.solve(definition, choices)
        self.assertEqual(list(notation(changed).values())[0], dict(duration=[1, 1], type=1, dots=None))

    def test_invalid_incomplete_noncanonical_or_unnotatable_shares_are_atomic(self):
        good = request(self.base, ['1/4']*4)
        lane = next(iter(good))
        refs = list(good[lane])
        cases = [None, [], {'unknown': good[lane]}, {lane: None}, {lane: {refs[0]: '1'}},
                 request(self.base, ['0', '1/2', '1/4', '1/4']),
                 request(self.base, ['0.25']*4), request(self.base, ['2/8']*4),
                 request(self.base, [True, '1/4', '1/4', '1/4']),
                 request(self.base, ['1/3', '1/3', '1/6', '1/6']),
                 request(self.base, ['1/8']*4)]
        before = deepcopy(self.base)
        for choices in cases:
            preserved = deepcopy(choices)
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                clock.solve(self.base, choices)
            self.assertEqual(self.base, before)
            self.assertEqual(choices, preserved)

    def test_declared_triplet_mismatch_and_unknown_tuplet_do_not_create_new_ratios(self):
        for tuplet, duration in ((3, (1, 4)), (5, (1, 4))):
            bar = [beat(duration=duration, tuplet=tuplet) for _ in range(4)]
            _, _, _, definition = build([[bar]])
            before = deepcopy(definition)
            with self.subTest(tuplet=tuplet), self.assertRaises(ValueError):
                clock.solve(definition, {})
            self.assertEqual(definition, before)


if __name__ == '__main__':
    unittest.main()
