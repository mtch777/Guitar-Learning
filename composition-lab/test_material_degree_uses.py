"""Integrated degree/clock/contact edits on authored complete musical material."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import backing_pitch_ownership as backing
import connected_tier2 as connected
import material_degree_paths as degrees
import material_rhythm_control as rhythm
import melodic_movement_ownership as movement
import support_material_uses as uses
import test_material_expression_composition as expression_fixture
import test_direct_support_material as direct_fixture
import test_musical_cell_development as fixture
from source_fact_tier1 import extract_documents, project_documents


USE = 'material-use:0'
SPEC = dict(parts=[2,3], first_bar=1, last_bar=1)
C = dict(id='authored-C-major', tonic_pc=0, intervals=[0,2,4,5,7,9,11])
G = dict(id='authored-G-major', tonic_pc=7, intervals=[0,2,4,5,7,9,11])


def saved(value):
    return json.loads(json.dumps(value))


def build(*, singleton=False, ambiguous=False, dead=False, dead_string=2, pitched_strings=None):
    docs = expression_fixture.authored_documents()
    if singleton or ambiguous:
        for part in (2,3):
            track = docs[f'track-{part}.json']
            if ambiguous:
                track['tuning'] = [40,35,30,25]
            for index, beat in enumerate(track['measures'][0]['voices'][0]['beats']):
                if ambiguous:
                    # C/E and E/G belong to both frozen interpretations; moving
                    # C/E one degree becomes D/F in C, but D/F-sharp in G.
                    for note, pitch in zip(beat['notes'], ((48,52),(52,55),(48,52),(52,55))[index]):
                        note['fret'] = pitch-track['tuning'][note['string']]
                if singleton:
                    beat['notes'] = beat['notes'][:1]
    if dead or pitched_strings is not None:
        for part in (2,3):
            track = docs[f'track-{part}.json']
            for beat in track['measures'][0]['voices'][0]['beats']:
                if pitched_strings is not None:
                    for note, string in zip(beat['notes'],pitched_strings):
                        pitch = track['tuning'][note['string']]+note['fret']
                        note.update(string=string, fret=pitch-track['tuning'][string])
                if dead:
                    member = dict(dead=True)
                    if dead_string is not None:member['string']=dead_string
                    beat['notes'].append(member)
    lower = extract_documents(docs)
    t2 = connected.strip_lower(connected.analyze(lower,
        note_accent_slots=True, palm_mute_slots=True, dynamic_evidence=True,
        backing_bindings=[direct_fixture.FOREIGN]))
    ordinary = uses.from_tier2(t2, [SPEC])
    refs = list(range(len(ordinary['materials'][0]['pitch_paths'])))
    model = uses.lift_degree_paths(ordinary, USE, path_refs=refs,
        interpretations={ref:deepcopy([C,G] if ambiguous else [C]) for ref in refs},
        evidence_ref='authored-frozen-collection-context')
    return docs, lower, t2, ordinary, model


def expected_up(docs):
    result = deepcopy(docs)
    # An independent authored-score expectation, not the owner's inverse.
    expected = {(50,57):(52,59), (52,59):(53,60), (53,60):(55,62)}
    for part in (2,3):
        track = result[f'track-{part}.json']
        for beat in track['measures'][0]['voices'][0]['beats']:
            notes = beat['notes']
            original = tuple(track['tuning'][note['string']]+note['fret'] for note in notes)
            target = expected[original] if len(notes)==2 else {50:52,52:53,53:55}[original[0]]
            if len(notes)==1:target=(target,)
            for note, pitch in zip(notes,target):note['fret']=pitch-track['tuning'][note['string']]
    return result


class DegreeUseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.lower, cls.t2, cls.ordinary, cls.model = build()
        cls.refs = degrees.selected_refs(cls.model['materials'][0])
        cls.up = uses.degree_path_candidate(cls.model, USE,
            displacements={ref:1 for ref in cls.refs}, octaves={})

    def test_exact_saved_zero_and_complete_source_fields(self):
        self.assertEqual(uses.expand(saved(self.model)), self.t2)
        self.assertEqual(uses.reconstruct(saved(self.model), {'variation':0}), self.lower)
        self.assertEqual(project_documents(uses.reconstruct(self.up, {'variation':0})), expected_up(self.docs))
        self.assertEqual(self.model['lower_tier'], self.ordinary['lower_tier'])

    def test_both_complete_coattacks_and_singletons_change_through_shared_relation(self):
        for singleton in (False,True):
            with self.subTest(singleton=singleton):
                docs, lower, _, _, model = build(singleton=singleton)
                refs = degrees.selected_refs(model['materials'][0])
                changed = uses.degree_path_candidate(model, USE,
                    displacements={ref:1 for ref in refs}, octaves={})
                actual = project_documents(uses.reconstruct(saved(changed), {'variation':0}))
                self.assertEqual(actual, expected_up(docs))
                self.assertEqual(uses.reconstruct(model, {'variation':0}), lower)
                for part in (2,3):
                    self.assertTrue(all(len(beat['notes'])==(1 if singleton else 2)
                        for beat in actual[f'track-{part}.json']['measures'][0]['voices'][0]['beats']))

    def test_saved_subsequent_pitch_choice_keeps_evidence_and_other_owners(self):
        result = uses.degree_path_candidate(saved(self.up), USE,
            displacements={ref:1 for ref in self.refs}, octaves={self.refs[0]:-1}, refinger=True)
        actual = project_documents(uses.reconstruct(saved(result), {'variation':0}))
        self.assertNotEqual(actual, expected_up(self.docs))
        self.assertEqual(result['materials'], self.model['materials'])
        self.assertEqual(result['slots'], self.model['slots'])
        self.assertEqual(result['lower_tier'], self.model['lower_tier'])
        self.assertEqual(uses.reconstruct(saved(result), {'variation':0}), uses.reconstruct(result, {'variation':0}))
        self.assertEqual(self.up['materials'], self.model['materials'])

    def test_rhythm_then_pitch_and_pitch_then_rhythm_keep_independent_choices(self):
        zero = rhythm.lift(self.model, USE)
        later = rhythm.candidate(zero, USE, '1/2')
        first = uses.degree_path_candidate(saved(later), USE,
            displacements={ref:1 for ref in self.refs}, octaves={})
        second = rhythm.candidate(rhythm.lift(saved(self.up), USE), USE, '1/2')
        self.assertEqual(first, second)
        actual = project_documents(uses.reconstruct(saved(first), {'variation':0}))
        self.assertEqual(actual, expression_fixture.expected_later(expected_up(self.docs)))
        self.assertEqual(first['materials'], self.model['materials'])
        reverted_clock = rhythm.candidate(saved(first), USE, '0')
        self.assertEqual(project_documents(uses.reconstruct(reverted_clock, {'variation':0})), expected_up(self.docs))

    def test_foreign_backing_relationship_still_propagates_after_saved_edit(self):
        model = saved(self.up)
        links = deepcopy(model['lower_tier']['musical_relationships']['relationships'])
        origin = deepcopy(model['lower_tier']['source_origin'])
        index = backing._index(movement._body(model['lower_tier']['musical_relationships']))
        index[fixture.FOREIGN_BACKING][0]['bass_register_anchor'] = '41'
        result = project_documents(uses.reconstruct(model, {'variation':0}))
        expected = expected_up(self.docs)
        for part, pitch in ((2,66),(3,41)):
            track = expected[f'track-{part}.json']
            note = track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            note['fret'] = pitch-track['tuning'][note['string']]
        self.assertEqual(result, expected)
        self.assertEqual(model['lower_tier']['musical_relationships']['relationships'], links)
        self.assertEqual(model['lower_tier']['source_origin'], origin)

    def test_string_lock_refuses_out_of_bounds_but_permission_recontacts_same_notes(self):
        group = next(g for g in self.model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==3)
        ref = group['id']; original = deepcopy(self.model)
        with self.assertRaises(ValueError):
            uses.degree_path_candidate(self.model, USE, displacements={}, octaves={ref:1}, refinger=False)
        self.assertEqual(self.model, original)
        changed = uses.degree_path_candidate(self.model, USE, displacements={}, octaves={ref:1}, refinger=True)
        actual = project_documents(uses.reconstruct(saved(changed), {'variation':0}))
        expected = deepcopy(self.docs)
        notes = expected['track-3.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        for note, string, fret in zip(notes, (1,0), (27,29)):
            note.update(string=string, fret=fret)
        self.assertEqual(actual, expected)
        self.assertEqual(changed['lower_tier'], original['lower_tier'])
        following = uses.degree_path_candidate(saved(changed), USE,
            displacements={ref:-1}, octaves={ref:1}, refinger=False)
        after = project_documents(uses.reconstruct(following, {'variation':0}))
        later_notes = after['track-3.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        self.assertEqual([note['string'] for note in later_notes], [1,0])
        self.assertEqual([note['fret'] for note in later_notes], [25,27])

    def test_ambiguous_choice_unknown_ids_and_nonboolean_permission_are_atomic(self):
        _, _, _, _, model = build(ambiguous=True)
        ref = degrees.selected_refs(model['materials'][0])[0]
        original = deepcopy(model)
        cases = [dict(displacements={ref:1},octaves={},refinger=False),
                 dict(displacements={'unknown':1},octaves={},refinger=False),
                 dict(displacements={},octaves={},refinger=1)]
        for request in cases:
            with self.subTest(request=request), self.assertRaises(ValueError):
                uses.degree_path_candidate(model, USE, **request)
            self.assertEqual(model, original)
        with self.assertRaises(ValueError):
            uses.degree_path_candidate(model, 'unknown-use', displacements={}, octaves={})
        self.assertEqual(model, original)

    def test_saved_octave_tamper_cannot_bypass_inverse_contact_checks(self):
        tampered = saved(self.model)
        tampered['uses'][0]['degree_octaves'] = {self.refs[0]:10}
        frozen = deepcopy(tampered)
        for inverse in (uses.expand, lambda model:uses.reconstruct(model, {'variation':0})):
            with self.subTest(inverse=inverse), self.assertRaisesRegex(ValueError, 'instrument bounds'):
                inverse(tampered)
            self.assertEqual(tampered, frozen)

    def test_mixed_dead_members_zero_and_recontact_keep_unpitched_identity(self):
        docs, lower, _, _, model = build(dead=True)
        self.assertEqual(uses.reconstruct(saved(model), {'variation':0}), lower)
        self.assertEqual(project_documents(lower), docs)
        group = next(g for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==3)
        changed = uses.degree_path_candidate(model, USE,
            displacements={}, octaves={group['id']:1}, refinger=True)
        actual = project_documents(uses.reconstruct(saved(changed), {'variation':0}))
        expected = deepcopy(docs)
        first = expected['track-3.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        for note, string, fret in zip(first[:2], (1,0), (27,29)):
            note.update(string=string, fret=fret)
        self.assertEqual(actual, expected)
        self.assertEqual(first[2], dict(dead=True,string=2))
        self.assertNotIn(group['members'][2]['id'], changed['uses'][0]['degree_strings'])
        self.assertEqual(model['materials'], changed['materials'])

    def test_dead_string_reservation_can_block_otherwise_feasible_recontact(self):
        _, lower, _, _, model = build(dead=True, dead_string=0, pitched_strings=(1,2))
        self.assertEqual(uses.reconstruct(saved(model), {'variation':0}), lower)
        group = next(g for g in model['materials'][0]['lower_tier']['coattacks'] if g['part_id']==3)
        frozen = deepcopy(model)
        # The upper target69 is physically reachable only on string0, already
        # occupied by the unchanged dead member. It cannot be silently reused.
        with self.assertRaisesRegex(ValueError, 'No distinct-string coattack'):
            uses.degree_path_candidate(model, USE,
                displacements={}, octaves={group['id']:1}, refinger=True)
        self.assertEqual(model, frozen)

    def test_unknown_dead_string_source_zero_survives_earlier_material_refusal(self):
        docs = expression_fixture.authored_documents()
        for part in (2,3):
            for beat in docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']:
                beat['notes'].append(dict(dead=True))
        lower = extract_documents(docs)
        t2 = connected.strip_lower(connected.analyze(lower,
            backing_bindings=[direct_fixture.FOREIGN]))
        frozen = deepcopy(t2)
        self.assertEqual(connected.realize(saved(t2)), lower)
        # Existing material admission refuses this unknown occupancy before a
        # degree-path/contact request exists. Do not manufacture a valid owner
        # by bypassing that guard just to exercise the later recontact branch.
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED_OVERLAPPING_STRING'):
            uses.from_tier2(t2, [SPEC])
        self.assertEqual(t2, frozen)
        self.assertEqual(connected.realize(t2), lower)

    def test_source_and_lower_absent_in_actual_frozen_inverse_worker(self):
        from qa_isolation_harness import execute
        from run_support_arrangement_qa import bundle
        code, hashes = bundle(Path(__file__).resolve().parent, boundary='source')
        self.assertIn('material_degree_paths', hashes)
        code += "\nreconstruct=sys.modules['support_material_uses'].reconstruct\n"
        with tempfile.TemporaryDirectory() as temporary:
            for name, upper, expected in (('zero',self.model,self.lower),
                    ('edited',self.up,extract_documents(expected_up(self.docs)))):
                output = Path(temporary)/name
                receipt = execute(code, saved(upper), {'variation':0}, expected,
                                  output, timeout=60, purpose='exact_zero')
                self.assertEqual(receipt['status'], 'PASS', receipt)
                self.assertFalse(receipt['parent_expected_staged'])
                self.assertEqual(set(receipt['frozen_files']), {'worker.py','relationships.py','input.json'})


if __name__ == '__main__':
    unittest.main()
