"""Approach ownership inside a previously edited, connected musical model.

Authored fixtures cover a preserved prefix, a tied middle attack, another
material containing percussion, an existing cell edit, and a foreign dependency.
"""
from copy import deepcopy
import json
import unittest

import backing_pitch_ownership as backing
import melodic_movement_ownership as movement
import musical_cell_development as cell
import musical_support_material as material
import support_material_uses as uses
import test_musical_cell_development as fixture
import test_musical_support_material as support_fixture
from source_fact_tier1 import project_documents


USE = 'material-use:0'
MAJOR = dict(id='authored-C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])
LYDIAN = dict(id='authored-C-lydian', tonic_pc=0, intervals=[0, 2, 4, 6, 7, 9, 11])
REFS = [f'event:{fixture.SONG}:2:1:0:{i}:0' for i in (1, 2, 4)]


def reload(model):
    return json.loads(json.dumps(model))


def pitches(document, bar=1):
    return [document['tuning'][note['string']] + note['fret']
            for beat in document['measures'][bar-1]['voices'][0]['beats']
            for note in beat['notes'] if not note.get('rest')]


class SupportApproachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        docs, _, _, _ = support_fixture.authored()
        track = docs['track-2.json'];base = track['tuning'][0]
        # Prefix G, then C -> D (tied for two beats) -> E: three attacks,
        # four written members. The complete bar still lasts four beats.
        track['measures'][0]['voices'][0]['beats'] = [
            dict(duration=duration, notes=[dict(string=0, fret=pitch-base,
                 **({'tie': True} if tied else {}))])
            for pitch, duration, tied in [
                (55, [1, 8], False), (60, [1, 8], False),
                (62, [1, 4], False), (62, [1, 4], True), (64, [1, 4], False)]]
        _, _, _, original = fixture.build(docs=docs)
        cls.current, report = cell.intervene(original, fixture.controls(seed=fixture.changed_seed()))
        assert report['changed']
        cls.lower = cell.reconstruct(cls.current, {'variation': 0})
        cls.t2 = cell.expand(cls.current)
        cls.documents = project_documents(cls.lower)
        cls.before = uses.lift(material.lift_t3(cls.current, [
            dict(parts=[2], first_bar=1, last_bar=1),
            dict(parts=[3, 4], first_bar=1, last_bar=1)]))
        cls.model = uses.lift_approach(cls.before, USE, REFS, [MAJOR], 'authored-evidence:major')
        cls.flipped = uses.approach_candidate(cls.model, USE, 'flip')

    def test_original_restores_exact_t2_source_and_current_cell_edit(self):
        self.assertEqual(uses.expand(reload(self.model)), self.t2)
        self.assertEqual(uses.reconstruct(self.model, {'variation': 0}), self.lower)
        self.assertEqual(project_documents(uses.reconstruct(self.model, {'variation': 0})), self.documents)
        for field in ('lower_tier', 'relationship', 'instance_attack_refs', 'observations', 'slots'):
            self.assertEqual(self.model[field], self.before[field])
        self.assertEqual(self.model['materials'][1:], self.before['materials'][1:])

    def test_selected_path_parameters_are_removed_and_tie_membership_is_explicit(self):
        owned = self.model['materials'][0]
        self.assertEqual(owned['pitch_paths'], [dict(start='55', steps=[None, None, None, None])])
        self.assertEqual(owned['approach']['attack_groups'], [[1], [2, 3], [4]])
        self.assertEqual(owned['approach']['relation']['arrival_pitch'], '64')
        self.assertEqual(owned['approach']['relation']['count'], 3)
        self.assertEqual(set(owned['approach']['relation']),
                         {'schema', 'count', 'original_direction', 'arrival_pitch', 'interpretations'})

    def test_flip_reload_preserves_complete_score_except_declared_pitch_contacts(self):
        actual = project_documents(uses.reconstruct(reload(self.flipped), {'variation': 0}))
        self.assertEqual(pitches(actual['track-2.json']), [55, 67, 65, 65, 64])
        expected = deepcopy(self.documents)
        track = expected['track-2.json']
        for index, pitch in ((1, 67), (2, 65), (3, 65)):
            note = track['measures'][0]['voices'][0]['beats'][index]['notes'][0]
            note['fret'] = pitch - track['tuning'][note['string']]
        self.assertEqual(actual, expected)
        self.assertTrue(actual['track-2.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['tie'])
        for field in ('lower_tier', 'relationship', 'instance_attack_refs', 'observations', 'materials', 'slots'):
            self.assertEqual(self.flipped[field], self.model[field])
        self.assertEqual(self.flipped['uses'][1:], self.model['uses'][1:])

    def test_saved_revert_restores_exact_current_original_not_preexisting_cell_edit(self):
        reverted = uses.approach_candidate(reload(self.flipped), USE, 'original')
        self.assertEqual(reverted, self.model)
        self.assertEqual(uses.reconstruct(reverted, {'variation': 0}), self.lower)

    def test_foreign_dependency_still_propagates_after_flip_save_and_subsequent_edit(self):
        saved = reload(self.flipped)
        relations = deepcopy(saved['lower_tier']['musical_relationships']['relationships'])
        index = backing._index(movement._body(saved['lower_tier']['musical_relationships']))
        index[fixture.FOREIGN_BACKING][0]['bass_register_anchor'] = '41'
        actual = project_documents(uses.reconstruct(saved, {'variation': 0}))
        self.assertEqual(pitches(actual['track-2.json'], 9), [66])
        self.assertEqual(pitches(actual['track-3.json'], 9), [41])
        self.assertEqual(pitches(actual['track-2.json']), [55, 67, 65, 65, 64])
        self.assertEqual(saved['lower_tier']['musical_relationships']['relationships'], relations)
        self.assertEqual(saved['observations'], self.model['observations'])

    def test_duplicate_authority_and_partial_tie_closure_refuse_atomically(self):
        for kind in ('duplicate-step', 'duplicate-start', 'partial-tie'):
            bad = deepcopy(self.model);owned = bad['materials'][0]
            if kind == 'duplicate-step':
                owned['pitch_paths'][0]['steps'][1] = '2'
            elif kind == 'duplicate-start':
                owned['pitch_paths'][0]['pitches'] = ['55', '60', '62', '62', '64']
            else:
                # Same complete ordinal list, wrong logical tie membership.
                owned['approach']['attack_groups'] = [[1, 2], [3], [4]]
            frozen = deepcopy(bad)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                uses.approach_candidate(bad, USE, 'flip')
            self.assertEqual(bad, frozen)
        wrong_root = [REFS[0], f'event:{fixture.SONG}:2:1:0:3:0', REFS[2]]
        frozen = deepcopy(self.before)
        with self.assertRaises(ValueError):
            uses.lift_approach(self.before, USE, wrong_root, [MAJOR], 'authored-evidence:major')
        self.assertEqual(self.before, frozen)

    def test_ambiguous_flip_refuses_without_losing_exact_original(self):
        model = uses.lift_approach(self.before, USE, REFS, [MAJOR, LYDIAN], 'authored-evidence:ambiguous')
        frozen = deepcopy(model)
        self.assertEqual(uses.reconstruct(model, {'variation': 0}), self.lower)
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            uses.approach_candidate(model, USE, 'flip')
        self.assertEqual(model, frozen)

    def test_zero_half_full_release_and_current_state_lock(self):
        for level, seed, released, changed in [(0, 0, False, False), (50, 0, True, True),
                                                (50, 1, False, False), (100, 0, True, True),
                                                (100, 2, True, False)]:
            with self.subTest(level=level, seed=seed):
                actual, report = uses.intervene_approach(self.model, USE, dict(release=level, seed=seed, mode='flip'))
                self.assertEqual(report['released'], released)
                self.assertEqual(report['changed'], changed)
                self.assertEqual(actual, self.flipped if changed else self.model)
        locked, report = uses.intervene_approach(reload(self.flipped), USE, dict(release=0, seed=0, mode='original'))
        self.assertEqual(locked, self.flipped)
        self.assertFalse(report['changed'])
        self.assertFalse(report['released'])

    def test_foreign_owner_and_repeated_constructor_refuse_without_mutation(self):
        frozen = deepcopy(self.model)
        with self.assertRaises(ValueError):
            uses.lift_approach(self.model, USE, REFS, [MAJOR], 'replacement-is-not-an-update')
        with self.assertRaises(ValueError):
            uses.extend_materials(self.model, [dict(parts=[2], first_bar=9, last_bar=9)])
        self.assertEqual(self.model, frozen)


if __name__ == '__main__':
    unittest.main()
