"""Authored collection/shape counterexamples, not artist or listening evidence."""
from copy import deepcopy
import json
import unittest

from connected_tier2 import analyze, strip_lower
from source_fact_tier1 import extract_documents
import musical_support_material as material
import material_degree_paths as degree
import test_musical_cell_development as fixture


C = dict(id='C-major', tonic_pc=0, intervals=[0,2,4,5,7,9,11])
G = dict(id='G-major', tonic_pc=7, intervals=[0,2,4,5,7,9,11])


def authored(*, paired=True, ambiguous=False, singleton=False, dead=False):
    docs = fixture.authored_score()
    sequence = [(60,64), (60,67), (64,67), (67,71)] if ambiguous else [
        (59,60), (60,67), (62,65), (64,67)]
    for part in (2,3):
        track = docs[f'track-{part}.json']
        track['tuning'] = [50,45,40,35,30,25]
        values = sequence if paired or part == 2 else [(55,59), (57,60), (55,62), (57,64)]
        track['measures'][0]['voices'][0]['beats'] = [
            dict(duration=[1,4], palmMute=True, velocity='f', notes=[
                dict(string=i, fret=p-track['tuning'][i])
                for i,p in enumerate(pitches[:1] if singleton else pitches)])
            for pitches in values]
        if dead:
            for beat in track['measures'][0]['voices'][0]['beats']:
                beat['notes'].append(dict(string=2, dead=True))
    lower = extract_documents(docs)
    t2 = strip_lower(analyze(lower))
    return material.fit(t2, parts=[2,3], first_bar=1, last_bar=2, lower=lower)


def lift(original, hypotheses=None, path_refs=None):
    refs = list(range(len(original['pitch_paths']))) if path_refs is None else path_refs
    return degree.fit(original, path_refs=refs,
        interpretations={p:deepcopy(hypotheses or [C]) for p in refs}, evidence_ref='authored-frozen-context')


def pitches(definition):
    result = material.expand(definition)
    return {g['id']:[None if m['voicing_interval'] is None else
        int(g['bass_register_anchor']) + int(m['voicing_interval']) for m in g['members']]
        for g in result['coattacks']}


class DegreeMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = authored()
        cls.owned = lift(cls.original)

    def test_zero_saved_reconstruction_and_no_duplicate_pitch_authority(self):
        restored = degree.expand(json.loads(json.dumps(self.owned)))
        self.assertEqual(restored, self.original)
        self.assertEqual(material.expand(restored), material.expand(self.original))
        self.assertTrue(all(path is None for path in self.owned['pitch_paths']))
        selected = set(degree.selected_refs(self.owned))
        self.assertTrue(all(b['voicing_ref'] is None for b in self.owned['bindings']
                            if b['coattack_ref'] in selected))
        self.assertNotIn('pitches', json.dumps(self.owned['degree_paths']))

    def test_complete_dyads_keep_degree_shape_not_semitone_width(self):
        refs = degree.selected_refs(self.owned)
        changed = degree.expand(self.owned, {ref:1 for ref in refs})
        actual = pitches(changed)
        expected = [notes for notes in [[60,62], [62,69], [64,67], [65,69]] for _ in range(2)]
        self.assertEqual([actual[ref] for ref in refs], expected)
        # B-C (one semitone) becomes C-D (two); C-G fifth remains D-A fifth.
        self.assertEqual(actual[refs[0]][1]-actual[refs[0]][0], 2)
        self.assertEqual(actual[refs[2]][1]-actual[refs[2]][0], 7)
        shapes = self.owned['degree_paths']['shapes']
        self.assertIn([0,1], shapes)
        self.assertIn([0,4], shapes)
        self.assertNotEqual(shapes.index([0,1]), shapes.index([0,4]))

    def test_occurrence_controls_can_split_a_shared_path_without_retargeting(self):
        refs = degree.selected_refs(self.owned)
        before = pitches(self.original)
        changed = degree.expand(self.owned, {refs[0]:1}, {refs[0]:1})
        after = pitches(changed)
        self.assertEqual(after[refs[0]], [72,74])
        self.assertEqual({k:v for k,v in after.items() if k != refs[0]},
                         {k:v for k,v in before.items() if k != refs[0]})
        self.assertEqual([b['coattack_ref'] for b in changed['bindings']],
                         [b['coattack_ref'] for b in self.original['bindings']])
        self.assertGreater(len(changed['pitch_paths']), len(self.original['pitch_paths']))

    def test_unselected_path_notation_techniques_and_clock_survive(self):
        original = authored(paired=False)
        selected_path = original['bindings'][0]['pitch_path_ref']
        owned = lift(original, path_refs=[selected_path])
        changed = degree.expand(owned, {ref:-1 for ref in degree.selected_refs(owned)})
        self.assertEqual(changed['lower_tier'], original['lower_tier'])
        for key in ('slots','pulse_shares','bar_spans_q','observed_execution','scope'):
            self.assertEqual(changed[key], original[key])
        before, after = pitches(original), pitches(changed)
        selected = set(degree.selected_refs(owned))
        self.assertEqual({k:v for k,v in before.items() if k not in selected},
                         {k:v for k,v in after.items() if k not in selected})

    def test_singletons_use_the_same_relation(self):
        original = authored(singleton=True)
        owned = lift(original)
        refs = degree.selected_refs(owned)
        actual = pitches(degree.expand(owned, {ref:1 for ref in refs}))
        self.assertEqual([actual[ref] for ref in refs], [[p] for p in (60,62,64,65) for _ in range(2)])
        self.assertEqual(degree.expand(owned), original)

    def test_all_hypotheses_exact_at_zero_but_changed_disagreement_refuses(self):
        original = authored(ambiguous=True)
        owned = lift(original, [C,G])
        saved = deepcopy(owned)
        self.assertEqual(degree.expand(owned), original)
        ref = degree.selected_refs(owned)[0]
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            degree.expand(owned, {ref:1})  # C/E -> D/F versus D/F-sharp
        self.assertEqual(owned, saved)
        self.assertEqual(pitches(degree.expand(owned, octaves={ref:1}))[ref], [72,76])

    def test_controls_types_identity_and_duplicate_authority_refuse_atomically(self):
        ref = degree.selected_refs(self.owned)[0]
        for controls in ({ref:True}, {ref:1.0}, {'other':1}, [1]):
            saved = deepcopy(self.owned)
            with self.subTest(controls=controls), self.assertRaises(ValueError):
                degree.expand(self.owned, controls)
            self.assertEqual(self.owned, saved)
        for kind in ('path','voicing','binding','payload'):
            bad = deepcopy(self.owned)
            if kind == 'path':bad['pitch_paths'][0] = deepcopy(self.original['pitch_paths'][0])
            elif kind == 'voicing':bad['voicings'][0] = deepcopy(self.original['voicings'][0])
            elif kind == 'binding':bad['degree_paths']['bindings'][0]['member_refs'].reverse()
            else:bad['degree_paths']['paths'][0]['hidden_pitch_stream'] = ['59','60','62','64']
            with self.subTest(kind=kind), self.assertRaises(ValueError):degree.expand(bad)

    def test_constructor_does_not_replace_existing_owner(self):
        with self.assertRaisesRegex(ValueError, 'ordinary unowned'):
            lift(self.owned)
        original = deepcopy(self.original)
        first = original['lower_tier']['coattacks'][0]['members'][0]['id']
        original['external_pitch_refs'] = [dict(occurrence_ref=first,kind='upper_member')]
        saved = deepcopy(original)
        with self.assertRaises(ValueError):lift(original)
        self.assertEqual(original,saved)

    def test_dead_members_and_rest_bar_survive_without_becoming_pitch_choices(self):
        original = authored(dead=True)
        owned = lift(original)
        refs = degree.selected_refs(owned)
        changed = degree.expand(owned, {ref:1 for ref in refs})
        self.assertTrue(all(values[-1] is None for values in pitches(changed).values() if len(values)>1))
        self.assertEqual(changed['lower_tier'], original['lower_tier'])
        self.assertEqual(changed['slots'], original['slots'])
        self.assertEqual(degree.expand(owned), original)

    def test_malformed_saved_owner_refuses(self):
        for value in (None, [], {}, dict(schema=degree.SCHEMA)):
            with self.subTest(value=value), self.assertRaises(ValueError):degree.expand(value)
        bad = deepcopy(self.owned)
        bad['degree_paths']['owned_voicing_refs'][0] = False
        with self.assertRaises(ValueError):degree.expand(bad)

    def test_outside_collection_original_is_not_rounded_to_fit(self):
        original = deepcopy(self.original)
        original['pitch_paths'][0]['start'] = '58'
        with self.assertRaisesRegex(ValueError, 'outside this reference collection'):
            lift(original)

    def test_shared_definition_remains_immutable_across_saved_variations(self):
        saved = deepcopy(self.owned)
        refs = degree.selected_refs(self.owned)
        first = degree.expand(self.owned, {refs[0]:1})
        second = degree.expand(json.loads(json.dumps(self.owned)), {refs[0]:-1})
        self.assertNotEqual(pitches(first), pitches(second))
        self.assertEqual(self.owned, saved)
        self.assertEqual(degree.expand(self.owned), self.original)


if __name__ == '__main__':
    unittest.main()
