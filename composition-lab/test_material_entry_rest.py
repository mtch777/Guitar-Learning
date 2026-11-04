"""Authored entry-rest integration; no source selection or audible claim."""
from copy import deepcopy
import json
import unittest

import backing_pitch_ownership as backing
import connected_tier2 as connected
import material_entry_rest as entry
from musical_support_material import _body as material_body
import observed_dynamics
import observed_expression
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents, project_documents
from test_written_tie_pitch_ownership import documents, note, ref
from test_material_slot_clock import beat

LANE = 'track-0.json#/measures/0/voices/0/beats'


def fixture(*, tied=False, optional=True):
    bars = [[beat(note(fret=5+i), note(1, 7+i)) for i in range(4)] for _ in range(2)]
    bars[0][0].update(velocity='f', palmMute=True, text=dict(text='entry', width=1))
    bars[0][1]['notes'][0]['accentuated'] = 1
    bars[1][0]['velocity'] = 'pp'
    if tied:
        bars[0][1]['notes'][0].update(fret=5, tie=True)
    docs = documents(bars)
    lower = extract_documents(docs)
    top = connected.strip_lower(connected.analyze(lower, dynamic_evidence=True,
        expression_evidence=True, note_accent_slots=optional, palm_mute_slots=optional))
    if tied:top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
    return docs, lower, top


def planned(top, fraction='1/4', lane=LANE, shares=None):
    fragment = entry._current_fragment(top)
    current = entry.current_lane_shares(fragment, [lane])[lane]
    return entry.plan(fragment, {lane: dict(entry_share=fraction, content_shares=shares or current)})


def expected_prefix(docs):
    out = deepcopy(docs)
    beats = out['track-0.json']['measures'][0]['voices'][0]['beats']
    for b in beats:b.update(duration=[3, 16], type=8, dots=1)
    beats.insert(0, dict(duration=[1, 4], type=4, rest=True, notes=[dict(rest=True)]))
    return out


class EntryRestTests(unittest.TestCase):
    def test_rest_and_complete_chords_follow_current_expression_without_new_evidence(self):
        docs, lower, top = fixture()
        before = deepcopy(top)
        out, report = entry.project(top, [planned(top)])
        self.assertEqual(project_documents(connected.realize(out)), expected_prefix(docs))
        self.assertEqual(out['source_origin'], top['source_origin'])
        self.assertEqual(observed_dynamics.evidence(out['owned_parameters']['observed_dynamics']),
                         observed_dynamics.evidence(top['owned_parameters']['observed_dynamics']))
        self.assertEqual(observed_expression.evidence(out['owned_parameters']['observed_expression']),
                         observed_expression.evidence(top['owned_parameters']['observed_expression']))
        self.assertEqual(len(report['maps']['events']), 8)
        self.assertTrue(all(len(v) == 1 for v in report['maps']['events'].values()))
        self.assertEqual(len(report['generated_rests']), 1)
        self.assertEqual(top, before)

    def test_zero_entry_and_current_content_are_exact_without_new_structure(self):
        _, lower, top = fixture()
        out, report = entry.project(top, [planned(top, '0')])
        self.assertEqual(out, top)
        self.assertFalse(report['changed'])
        self.assertEqual(connected.realize(out), lower)

    def test_zero_entry_can_retime_content_without_new_rest(self):
        docs, _, top = fixture(optional=False)
        current = entry.current_lane_shares(entry._current_fragment(top), [LANE])[LANE]
        shares = dict(zip(current, ['1/8', '3/8', '1/8', '3/8']))
        out, report = entry.project(top, [planned(top, '0', shares=shares)])
        expected = deepcopy(docs)
        for i,b in enumerate(expected['track-0.json']['measures'][0]['voices'][0]['beats']):
            b.update(duration=[1 if i%2 == 0 else 3, 8], type=8 if i%2 == 0 else 4)
            if i%2:b['dots'] = 1
        self.assertEqual(project_documents(connected.realize(out)), expected)
        self.assertEqual(report['generated_rests'], [])

    def test_joint_final_notation_can_pass_unnotatable_normalized_intermediate(self):
        _, _, top = fixture(optional=False)
        current = entry.current_lane_shares(entry._current_fragment(top), [LANE])[LANE]
        shares = dict(zip(current, ['1/7', '2/7', '2/7', '2/7']))
        out, _ = entry.project(top, [planned(top, '1/8', shares=shares)])
        beats = project_documents(connected.realize(out))['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([b['duration'] for b in beats], [[1, 8], [1, 8], [1, 4], [1, 4], [1, 4]])

    def test_saved_tie_identity_and_later_pitch_edit_propagate(self):
        docs, _, top = fixture(tied=True)
        out, _ = entry.project(top, [planned(top)])
        self.assertEqual(project_documents(connected.realize(out)), expected_prefix(docs))
        saved = json.loads(json.dumps(out))
        binding = saved['musical_relationships']['relationships'][0]
        self.assertEqual((binding['origin_ref'], binding['destination_ref']), (ref(1), ref(2)))
        group, member = backing._index(saved['musical_relationships']['core'])[ref(1)]
        group['bass_register_anchor'] = str(int(group['bass_register_anchor'])+2)
        current = project_documents(connected.realize(saved))['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual(current[1]['notes'][0]['fret'], 7)
        self.assertEqual(current[2]['notes'][0]['fret'], 7)
        self.assertEqual(current[3], expected_prefix(docs)['track-0.json']['measures'][0]['voices'][0]['beats'][3])

    def test_incoming_tie_refuses_prefix_but_not_zero(self):
        docs, _, _ = fixture()
        before = docs['track-0.json']['measures'][0]['voices'][0]['beats'][-1]['notes'][0]
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0].update(fret=before['fret'], tie=True)
        lower = extract_documents(docs)
        top = connected.strip_lower(connected.analyze(lower))
        top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
        lane = 'track-0.json#/measures/1/voices/0/beats'
        saved = deepcopy(top)
        with self.assertRaisesRegex(ValueError, 'INCOMING_TIE'):planned(top, lane=lane)
        self.assertEqual(entry.project(top, [planned(top, '0', lane)])[0], top)
        self.assertEqual(top, saved)

    def test_tampered_maps_and_conflicting_owner_refuse_atomically(self):
        _, _, top = fixture()
        proposal = planned(top)
        bad = deepcopy(proposal)
        bad['maps']['events'][ref(0)] = [ref(2)]
        before = deepcopy(top)
        with self.assertRaisesRegex(ValueError, 'differs from current'):entry.project(top, [bad])
        with self.assertRaisesRegex(ValueError, 'Overlapping'):entry.project(top, [proposal, proposal])
        conflict = deepcopy(top)
        conflict['owned_parameters']['unknown_owner'] = dict(member=ref(0))
        preserved = deepcopy(conflict)
        with self.assertRaisesRegex(ValueError, 'OWNER_PROJECTION_REQUIRED'):entry.project(conflict, [proposal])
        self.assertEqual(conflict, preserved)
        self.assertEqual(top, before)

    def test_after_subdivision_keeps_child_lineage_and_original_expression_counts(self):
        import material_subdivision as subdivision
        import material_subdivision_projection as projection
        _, _, top = fixture()
        original_evidence = observed_expression.evidence(top['owned_parameters']['observed_expression'])
        piece = entry._current_fragment(top)
        first = piece['coattacks'][0]['id']
        split = projection.project(top, [subdivision.plan(piece, {first: 2})])
        saved = json.loads(json.dumps(split))
        before = project_documents(connected.realize(saved))
        out, report = entry.project(saved, [planned(saved)])
        actual = project_documents(connected.realize(out))
        rows = actual['track-0.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([r['duration'] for r in rows], [[1, 4], [3, 32], [3, 32], [3, 16], [3, 16], [3, 16]])
        self.assertEqual([r['notes'] for r in rows[1:]], [r['notes'] for r in before['track-0.json']['measures'][0]['voices'][0]['beats']])
        model = out['owned_parameters']['observed_expression']
        self.assertEqual(observed_expression.evidence(model), original_evidence)
        self.assertEqual(model['lineage']['event_map'][ref(0)], [ref(1), ref(2)])
        self.assertEqual(len(report['maps']['events']), 10)

    def test_unrelated_backing_dependency_survives_saved_entry_and_later_pitch_edit(self):
        import test_material_expression_composition as fixture_with_backing
        import test_musical_cell_development as backing_fixture
        docs, _, top = fixture_with_backing.build()
        lane = 'track-2.json#/measures/0/voices/0/beats'
        links = deepcopy(top['musical_relationships']['relationships'])
        out, _ = entry.project(top, [planned(top, lane=lane)])
        self.assertEqual(out['musical_relationships']['relationships'], links)
        saved = json.loads(json.dumps(out))
        group, _ = backing._index(material_body(saved['musical_relationships']))[backing_fixture.FOREIGN_BACKING]
        group['bass_register_anchor'] = '41'
        actual = project_documents(connected.realize(saved))
        for part, pitch in ((2, 66), (3, 41)):
            track = actual[f'track-{part}.json']
            n = track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            self.assertEqual(n['fret'], pitch-track['tuning'][n['string']])
        self.assertEqual(saved['source_origin'], top['source_origin'])

    def test_outgoing_cross_bar_tie_keeps_destination_and_saved_propagation(self):
        docs, _, _ = fixture()
        previous = docs['track-0.json']['measures'][0]['voices'][0]['beats'][-1]['notes'][0]
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0].update(fret=previous['fret'], tie=True)
        lower = extract_documents(docs)
        top = connected.strip_lower(connected.analyze(lower))
        top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
        out, _ = entry.project(top, [planned(top)])
        self.assertEqual(project_documents(connected.realize(out)), expected_prefix(docs))
        link = out['musical_relationships']['relationships'][0]
        self.assertEqual((link['origin_ref'], link['destination_ref']), (ref(4), ref(0, bar=2)))
        saved = json.loads(json.dumps(out))
        group, _ = backing._index(saved['musical_relationships']['core'])[ref(4)]
        group['bass_register_anchor'] = str(int(group['bass_register_anchor'])+1)
        current = project_documents(connected.realize(saved))['track-0.json']['measures']
        self.assertEqual(current[0]['voices'][0]['beats'][4]['notes'][0]['fret'], 9)
        self.assertEqual(current[1]['voices'][0]['beats'][0]['notes'][0]['fret'], 9)

    def test_cross_bar_legato_and_pull_off_keep_endpoints_and_refuse_new_incoming_gap(self):
        import backing_execution_constraints as execution
        for field, value, kind in (('slide', 'legato', 'slide'), ('hp', True, 'hopo')):
            docs, _, _ = fixture(optional=False)
            docs['track-0.json']['measures'][0]['voices'][0]['beats'][-1]['notes'][0][field] = value
            lower = extract_documents(docs)
            top = connected.strip_lower(connected.analyze(lower))
            records = execution._snapshot(execution.encoded(lower))['records']
            saved = deepcopy(top)
            with self.assertRaisesRegex(ValueError, 'CURRENT_EXECUTION_CONTEXT_REQUIRED'):
                entry.project(top, [planned(top)])
            out, _ = entry.project(top, [planned(top)], execution_records=records)
            actual = connected.realize(out)
            self.assertEqual(project_documents(actual), expected_prefix(docs))
            slides = [r for r in execution._snapshot(execution.encoded(actual))['records'] if r['kind'] == kind]
            self.assertEqual([(r['origin_ref'], r['destination_ref']) for r in slides], [(ref(4), ref(0, bar=2))])
            lane = 'track-0.json#/measures/1/voices/0/beats'
            with self.assertRaisesRegex(ValueError, 'SEPARATES_CONTINUOUS_GESTURE'):
                entry.project(top, [planned(top, lane=lane)], execution_records=records)
            self.assertEqual(top, saved)


if __name__ == '__main__':
    unittest.main()
