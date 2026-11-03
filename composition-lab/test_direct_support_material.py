"""Direct T3 material ownership without a separate cell or melody prerequisite.

Authored complete bars include a tied approach, unrelated backing ownership,
and an independent part. These are contract tests, not artist evidence.
"""
from copy import deepcopy
import json
import unittest

import backing_pitch_ownership as backing
import melodic_movement_ownership as movement
import musical_support_material as material
import musical_tier2 as music
import support_material_uses as uses
import test_musical_cell_development as fixture
from connected_tier2 import analyze, strip_lower
from group_rhythm_relations import VIEWS
from source_fact_tier1 import extract_documents, project_documents


USE = 'material-use:0'
SPEC = dict(parts=[2], first_bar=1, last_bar=1)
REFS = [f'event:{fixture.SONG}:2:1:0:{i}:0' for i in (1, 2, 4)]
MAJOR = dict(id='authored-C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])
LYDIAN = dict(id='authored-C-lydian', tonic_pc=0, intervals=[0, 2, 4, 6, 7, 9, 11])
FOREIGN = dict(occurrence_ref=fixture.FOREIGN, backing_ref=fixture.FOREIGN_BACKING)


def reload(value):
    return json.loads(json.dumps(value))


def authored_documents():
    # Only score construction is reused; no T3 fit/lift is called here.
    docs = fixture.authored_score()
    track = docs['track-2.json']; base = track['tuning'][0]
    track['measures'][0]['voices'][0]['beats'] = [
        dict(duration=duration, notes=[dict(string=0, fret=pitch-base,
             **({'tie': True} if tied else {}))])
        for pitch, duration, tied in [
            (55, [1, 8], False), (60, [1, 8], False),
            (62, [1, 4], False), (62, [1, 4], True), (64, [1, 4], False)]]
    other = docs['track-3.json']; base = other['tuning'][0]
    other['measures'][0]['voices'][0]['beats'] = [
        dict(duration=[1, 4], notes=[dict(string=0, fret=p-base)]) for p in (40, 43, 40, 43)]
    return docs


def build(documents, links=None):
    lower = extract_documents(documents)
    return lower, strip_lower(analyze(lower, backing_bindings=[FOREIGN] if links is None else links))


class DirectSupportMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = authored_documents()
        cls.lower, cls.t2 = build(cls.documents)
        cls.direct = uses.from_tier2(cls.t2, [SPEC])
        cls.model = uses.lift_approach(cls.direct, USE, REFS, [MAJOR], 'authored-evidence:major')
        cls.flipped = uses.approach_candidate(cls.model, USE, 'flip')

    def test_no_cell_exact_preceding_t2_and_complete_score(self):
        self.assertNotIn(movement.SLOT, self.t2['owned_parameters'])
        self.assertEqual(set(self.model), {'tier', 'schema', 'lower_tier', 'materials', 'slots', 'uses'})
        self.assertEqual(self.model['schema'], uses.DIRECT_SCHEMA)
        preceding, lower, ledger = uses.realize_pair(reload(self.model))
        self.assertEqual(preceding, self.t2)
        self.assertEqual(uses.expand(self.model), self.t2)
        self.assertEqual(lower, self.lower)
        self.assertEqual(project_documents(lower), self.documents)
        self.assertEqual(len(ledger), 5)
        self.assertEqual(self.model['lower_tier']['source_origin'], self.t2['source_origin'])
        self.assertEqual(self.model['lower_tier']['musical_relationships']['relationships'],
                         self.t2['musical_relationships']['relationships'])
        owned = self.model['materials'][0]
        self.assertEqual(owned['pitch_paths'], [dict(start='55', steps=[None, None, None, None])])
        self.assertEqual(owned['approach']['attack_groups'], [[1], [2, 3], [4]])
        self.assertEqual(owned['approach']['relation']['arrival_pitch'], '64')
        self.assertFalse(any(g['part_id'] == 2 and g['bar'] == 1
                             for g in movement._body(self.model['lower_tier']['musical_relationships'])['coattacks']))

    def test_flip_reload_revert_changes_only_selected_pitch_contacts(self):
        actual = project_documents(uses.reconstruct(reload(self.flipped), {'variation': 0}))
        expected = deepcopy(self.documents)
        track = expected['track-2.json']
        for index, pitch in ((1, 67), (2, 65), (3, 65)):
            note = track['measures'][0]['voices'][0]['beats'][index]['notes'][0]
            note['fret'] = pitch-track['tuning'][note['string']]
        self.assertEqual(actual, expected)
        for key in ('lower_tier', 'materials', 'slots'):
            self.assertEqual(self.flipped[key], self.model[key])
        restored = uses.approach_candidate(reload(self.flipped), USE, 'original')
        self.assertEqual(restored, self.model)
        self.assertEqual(uses.reconstruct(restored, {'variation': 0}), self.lower)

    def test_saved_foreign_backing_still_propagates_after_approach_edit(self):
        saved = reload(self.flipped)
        original_links = deepcopy(saved['lower_tier']['musical_relationships']['relationships'])
        original_origin = deepcopy(saved['lower_tier']['source_origin'])
        index = backing._index(movement._body(saved['lower_tier']['musical_relationships']))
        index[fixture.FOREIGN_BACKING][0]['bass_register_anchor'] = '41'
        actual = project_documents(uses.reconstruct(saved, {'variation': 0}))
        for part, pitch in ((2, 66), (3, 41)):
            track = actual[f'track-{part}.json']
            note = track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            self.assertEqual(track['tuning'][note['string']]+note['fret'], pitch)
        self.assertEqual(saved['lower_tier']['musical_relationships']['relationships'], original_links)
        self.assertEqual(saved['lower_tier']['source_origin'], original_origin)
        self.assertEqual(saved['uses'], self.flipped['uses'])

    def test_extend_saved_direct_owner_preserves_current_approach_and_old_definitions(self):
        before = reload(self.flipped)
        extended = uses.extend_materials(before, [dict(parts=[3], first_bar=1, last_bar=1)])
        self.assertEqual(extended['schema'], uses.DIRECT_SCHEMA)
        self.assertEqual(extended['materials'][:1], before['materials'])
        self.assertEqual(extended['uses'][:1], before['uses'])
        self.assertEqual(uses.expand(extended), uses.expand(before))
        self.assertEqual(uses.reconstruct(extended, {'variation': 0}), uses.reconstruct(before, {'variation': 0}))
        self.assertEqual(before, self.flipped)

    def test_unrelated_existing_t2_movement_and_observations_are_preserved(self):
        t2 = movement.lift(self.t2, fixture.ROOTS, register_controls=True)
        frozen = deepcopy(t2)
        direct = uses.from_tier2(t2, [SPEC])
        approach = uses.lift_approach(direct, USE, REFS, [MAJOR], 'authored-evidence:major')
        flipped = uses.approach_candidate(approach, USE, 'flip')
        self.assertEqual(uses.expand(direct), t2)
        self.assertEqual(flipped['lower_tier']['owned_parameters'][movement.SLOT], t2['owned_parameters'][movement.SLOT])
        self.assertEqual(flipped['lower_tier']['source_origin'], t2['source_origin'])
        self.assertEqual(uses.reconstruct(flipped, {'variation': 0}), uses.reconstruct(self.flipped, {'variation': 0}))
        self.assertEqual(t2, frozen)

    def test_ordinary_unowned_t2_views_roundtrip_and_follow_current_pitch_relations(self):
        # No backing lift and no movement owner: ordinary connected analysis
        # retains all local/ensemble/tonal views of the current composition.
        t2 = strip_lower(analyze(self.lower))
        frozen = deepcopy(t2)
        direct = uses.from_tier2(t2, [SPEC])
        model = uses.lift_approach(direct, USE, REFS, [MAJOR], 'authored-evidence:major')
        self.assertEqual(uses.expand(reload(model)), t2)
        self.assertTrue(all(g['interpretation'] is None for g in model['materials'][0]['lower_tier']['coattacks']))
        self.assertTrue(all(model['lower_tier']['musical_relationships'][name] is None for name in VIEWS))
        flipped = uses.approach_candidate(model, USE, 'flip')
        after = uses.expand(reload(flipped))
        core = after['musical_relationships']
        music.validate(core)
        for group in core['coattacks']:
            self.assertEqual(group['interpretation'], music.interpreted(group))
        self.assertEqual(core['ensemble_coattacks'], music.ensemble(core['coattacks']))
        self.assertEqual(core['nominal_written_spans'], music.written_spans(core['coattacks']))
        self.assertEqual(core['tonal_evidence'], music.tonal_evidence(core['coattacks']))
        self.assertEqual(core['temporal_tonal_evidence'], music.temporal_tonal_evidence(core['coattacks'], core['measure_geometry']))
        self.assertNotEqual(core['tonal_evidence'], t2['musical_relationships']['tonal_evidence'])
        self.assertEqual(after['source_origin'], t2['source_origin'])
        self.assertEqual(uses.reconstruct(flipped, {'variation': 0}), uses.reconstruct(self.flipped, {'variation': 0}))
        extended = uses.extend_materials(reload(flipped), [dict(parts=[3], first_bar=1, last_bar=1)])
        self.assertEqual(uses.expand(extended), after)
        reverted = uses.approach_candidate(reload(flipped), USE, 'original')
        self.assertEqual(uses.expand(reverted), t2)
        self.assertEqual(t2, frozen)

    def test_cached_or_conflicting_derived_views_are_not_accepted_as_material_authority(self):
        t2 = strip_lower(analyze(self.lower))
        model = uses.from_tier2(t2, [SPEC])
        ordinary = t2['musical_relationships']
        group = next(g for g in ordinary['coattacks'] if g['part_id'] == 2 and g['bar'] == 1)
        for kind in ('local-cache', 'ensemble-cache', 'malformed-marker'):
            bad = deepcopy(model)
            if kind == 'local-cache':
                bad['materials'][0]['lower_tier']['coattacks'][0]['interpretation'] = deepcopy(group['interpretation'])
            elif kind == 'ensemble-cache':
                bad['lower_tier']['musical_relationships']['ensemble_coattacks'] = deepcopy(ordinary['ensemble_coattacks'])
            else:
                bad['materials'][0]['lower_tier']['coattacks'][0]['interpretation'] = False
            frozen = deepcopy(bad)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'presence marker'):
                uses.reconstruct(bad, {'variation': 0})
            self.assertEqual(bad, frozen)
        conflicting = deepcopy(t2)
        group = next(g for g in conflicting['musical_relationships']['coattacks'] if g['part_id'] == 2 and g['bar'] == 1)
        group['interpretation']['bass_pc'] = '99'
        frozen = deepcopy(conflicting)
        with self.assertRaisesRegex(ValueError, 'interpretation conflicts'):
            material.fit(conflicting, lower=self.lower, **SPEC)
        self.assertEqual(conflicting, frozen)

    def test_zero_half_full_are_release_choices_and_zero_locks_current(self):
        for level, seed, released, changed in [(0, 0, False, False), (50, 0, True, True),
                                                (50, 1, False, False), (100, 0, True, True),
                                                (100, 2, True, False)]:
            with self.subTest(level=level, seed=seed):
                result, report = uses.intervene_approach(self.model, USE, dict(release=level, mode='flip', seed=seed))
                self.assertEqual((report['released'], report['changed']), (released, changed))
                self.assertEqual(result, self.flipped if changed else self.model)
        result, report = uses.intervene_approach(reload(self.flipped), USE, dict(release=0, mode='original', seed=0))
        self.assertEqual(result, self.flipped)
        self.assertFalse(report['changed'])

    def test_unknown_schemas_hidden_cell_and_missing_approach_choice_refuse_atomically(self):
        for kind in ('unknown', 'cell', 'mode', 'parent', 'source-cache', 'derived-cache'):
            bad = deepcopy(self.model)
            if kind == 'unknown': bad['schema'] = 'unregistered-material-use/999'
            elif kind == 'cell': bad['relationship'] = {'invented': True}
            elif kind == 'mode': del bad['uses'][0]['approach_mode']
            elif kind == 'parent': bad['lower_tier']['schema'] = 'unknown-t2/999'
            elif kind == 'source-cache': bad['lower_tier']['input'] = self.lower
            else: bad['lower_tier']['derived_views'] = {}
            frozen = deepcopy(bad)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                uses.reconstruct(bad, {'variation': 0})
            self.assertEqual(bad, frozen)
        for specs in ([], None, [SPEC, SPEC]):
            frozen = deepcopy(self.t2)
            with self.subTest(specs=specs), self.assertRaises(ValueError):
                uses.from_tier2(self.t2, specs)
            self.assertEqual(self.t2, frozen)

    def test_crossing_owners_and_technique_chains_refuse_without_mutation(self):
        active_backing = f'event:{fixture.SONG}:3:1:0:0:0'
        _, bound = build(self.documents, [FOREIGN, dict(occurrence_ref=REFS[0], backing_ref=active_backing)])
        frozen = deepcopy(bound)
        with self.assertRaisesRegex(ValueError, 'backing owner'):
            uses.from_tier2(bound, [SPEC])
        self.assertEqual(bound, frozen)
        docs = deepcopy(self.documents)
        docs['track-2.json']['measures'][1]['voices'][0]['beats'] = [
            dict(duration=[1, 1], notes=[dict(string=0, fret=14, tie=True)])]
        _, tied = build(docs)
        frozen = deepcopy(tied)
        # Zero material ownership preserves the crossing tie. A creative
        # approach cannot claim that incomplete attack and must refuse it.
        direct = uses.from_tier2(tied, [SPEC])
        self.assertEqual(uses.expand(direct), tied)
        direct_before = deepcopy(direct)
        with self.assertRaisesRegex(ValueError, 'complete tied-attack suffix'):
            uses.lift_approach(direct, USE, REFS, [MAJOR], 'authored-evidence:major')
        self.assertEqual(direct, direct_before)
        self.assertEqual(tied, frozen)

    def test_ambiguous_interpretations_preserve_original_and_refuse_conflicting_flip(self):
        model = uses.lift_approach(self.direct, USE, REFS, [MAJOR, LYDIAN], 'authored-evidence:ambiguous')
        self.assertEqual(uses.expand(model), self.t2)
        frozen = deepcopy(model)
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            uses.approach_candidate(model, USE, 'flip')
        self.assertEqual(model, frozen)


if __name__ == '__main__':
    unittest.main()
