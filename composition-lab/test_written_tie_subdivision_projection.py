"""Typed sustain endpoints survive same-span reattacks and saved edits."""
from copy import deepcopy
import json
import unittest

import backing_pitch_ownership as backing
import connected_tier2 as connected
import material_subdivision as subdivision
import material_subdivision_projection as projection
import musical_support_material as material
import observed_expression
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents, project_documents
from technique_observation_relations import scalar_relation
from test_written_tie_pitch_ownership import beat, documents, note, ref


def build(bars):
    docs = documents(bars); lower = extract_documents(docs)
    top = connected.strip_lower(connected.analyze(lower, expression_evidence=True))
    top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
    return docs, lower, top


def plan(top, occurrence, factor=2, *, adversarial_ignore_tie_flag=False):
    fragment = deepcopy(material._arrays(top))
    if adversarial_ignore_tie_flag:
        # Test the projector's own boundary, even if a caller evades the normal
        # planner's independent incoming-tie refusal. This is not production.
        for row in fragment['source_choices']:
            if row['fact_ref'].endswith('/tie'):
                row['parameter'] = scalar_relation('boolean', source=False)
    group = next(g for g in fragment['coattacks'] if any(m['id'] == occurrence for m in g['members']))
    return subdivision.plan(fragment, {group['id']: factor})


def expected_split(docs, *, bar, beat_number, factor=2):
    result = deepcopy(docs)
    before = result['track-0.json']['measures'][bar-1]['voices'][0]['beats']
    changed = []
    for i, current in enumerate(before):
        count = factor if i == beat_number else 1
        for _ in range(count):
            child = deepcopy(current)
            if count > 1:
                child['duration'][1] *= count
            changed.append(child)
    result['track-0.json']['measures'][bar-1]['voices'][0]['beats'] = changed
    return result


class WrittenTieSubdivisionProjectionTests(unittest.TestCase):
    def test_factor_one_keeps_current_owners_exact(self):
        _, lower, top = build([[beat(note()), beat(note(tie=True)), beat(note()), beat(note())]])
        result = projection.project(top, [plan(top, ref(0), 1)])
        self.assertEqual(result, top)
        self.assertEqual(connected.realize(result), lower)

    def test_origin_split_maps_hold_to_last_child_not_first(self):
        docs, _, top = build([[beat(note(), duration=(1, 1))],
                              [beat(note(tie=True), duration=(1, 2)), beat(note()), beat(note())]])
        before = deepcopy(top)
        result = projection.project(top, [plan(top, ref(0))])
        actual = connected.realize(result)
        self.assertEqual(project_documents(actual), expected_split(docs, bar=1, beat_number=0))
        edge = result['musical_relationships']['relationships'][0]
        self.assertEqual(edge['origin_ref'], ref(1))
        self.assertEqual(edge['destination_ref'], ref(0, bar=2))
        self.assertEqual(top, before)
        self.assertEqual(result['source_origin'], top['source_origin'])
        self.assertEqual(observed_expression.evidence(result['owned_parameters']['observed_expression']),
                         observed_expression.evidence(top['owned_parameters']['observed_expression']))
        bad = deepcopy(result)
        import backing_written_tie_constraints as edge_schema
        bad['musical_relationships']['relationships'][0] = edge_schema.relation(dict(
            origin=ref(0), destination=ref(0, bar=2), kind='written_pitched_tie'))
        with self.assertRaisesRegex(ValueError, 'CLOCK_CONFLICT'):
            connected.realize(bad)

    def test_shifted_lowest_tail_preserves_fresh_upper_basis_and_later_pitch_edit(self):
        docs, _, top = build([[beat(note()), beat(note(tie=True), note(1, 3)),
                              beat(note(tie=True), note(1, 5)), beat(note(fret=7))]])
        result = projection.project(top, [plan(top, ref(0))])
        self.assertEqual(project_documents(connected.realize(result)), expected_split(docs, bar=1, beat_number=0))
        owner = result['musical_relationships']
        self.assertEqual(owner['groups'][0]['member_refs'], [ref(2), ref(2, 1)])
        self.assertEqual(owner['groups'][0]['basis_ref'], ref(2, 1))
        # Saved current last reattack is now the independent held-note origin.
        saved = json.loads(json.dumps(result))
        backing._index(saved['musical_relationships']['core'])[ref(1)][0]['bass_register_anchor'] = '48'
        current = project_documents(connected.realize(saved))['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([current[i]['notes'][0]['fret'] for i in (1, 2, 3)], [8, 8, 8])
        self.assertEqual([current[i]['notes'][1]['fret'] for i in (2, 3)], [3, 5])

    def test_saved_second_split_moves_outgoing_hold_again(self):
        docs, _, top = build([[beat(note(), duration=(1, 1))],
                              [beat(note(tie=True), duration=(1, 1))]])
        first = projection.project(top, [plan(top, ref(0))])
        saved = json.loads(json.dumps(first))
        second = projection.project(saved, [plan(saved, ref(1))])
        self.assertEqual(second['musical_relationships']['relationships'][0]['origin_ref'], ref(2))
        expected = expected_split(expected_split(docs, bar=1, beat_number=0), bar=1, beat_number=1)
        self.assertEqual(project_documents(connected.realize(second)), expected)
        self.assertEqual(observed_expression.evidence(second['owned_parameters']['observed_expression']),
                         observed_expression.evidence(top['owned_parameters']['observed_expression']))

    def test_incoming_pitched_and_dead_continuations_refuse_before_mutation(self):
        for dead in (False, True):
            kwargs = dict(dead=True) if dead else {}
            _, _, top = build([[beat(note(**kwargs)), beat(note(tie=True, **kwargs)),
                                beat(note()), beat(note())]])
            frozen = deepcopy(top)
            bad_plan = plan(top, ref(1), adversarial_ignore_tie_flag=True)
            with self.subTest(dead=dead), self.assertRaisesRegex(ValueError, 'incoming written tie'):
                projection.project(top, [bad_plan])
            self.assertEqual(top, frozen)

    def test_dead_origin_split_preserves_unknown_pitch_and_outgoing_dependency(self):
        docs, _, top = build([[beat(note(dead=True)), beat(note(dead=True, tie=True)),
                              beat(note()), beat(note())]])
        result = projection.project(top, [plan(top, ref(0))])
        self.assertEqual(result['musical_relationships']['relationships'][0]['kind'], 'written_dead_tie')
        self.assertEqual(result['musical_relationships']['relationships'][0]['origin_ref'], ref(1))
        self.assertEqual(project_documents(connected.realize(result)), expected_split(docs, bar=1, beat_number=0))

    def test_unresolved_neighborhood_split_refuses_but_other_split_readdresses_it(self):
        docs, _, top = build([[beat(note(fret=9)), beat(note()),
                              beat(note(fret=6, tie=True)), beat(note(fret=7))]])
        result = projection.project(top, [plan(top, ref(0))])
        self.assertEqual(project_documents(connected.realize(result)), expected_split(docs, bar=1, beat_number=0))
        row = result['musical_relationships']['unresolved'][0]
        self.assertEqual(row['destination_ref'], ref(3))
        self.assertEqual(row['neighborhood_refs'], [ref(2), ref(3)])
        self.assertEqual(row['context_fingerprint'], top['musical_relationships']['unresolved'][0]['context_fingerprint'])
        frozen = deepcopy(top)
        with self.assertRaisesRegex(ValueError, 'unresolved written-tie'):
            projection.project(top, [plan(top, ref(1))])
        self.assertEqual(top, frozen)


if __name__ == '__main__':
    unittest.main()
