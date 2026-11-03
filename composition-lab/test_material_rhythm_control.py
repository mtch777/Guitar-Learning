"""Authored integrated timing changes, existing dependencies and saved updates."""
from copy import deepcopy
import json
import unittest

import test_musical_cell_development as fixture
import musical_support_material as material
import support_material_uses as uses
import support_arrangement as arrangement
import section_arrangements as sections
import thematic_return as theme
import material_rhythm_control as rhythm
import backing_pitch_ownership as backing
import melodic_movement_ownership as movement
from source_fact_tier1 import project_documents

USE = 'material-use:0'


def build():
    docs = fixture.authored_score()
    for part in (2, 3):
        track = docs[f'track-{part}.json']
        for bar in (1, 4):
            track['measures'][bar-1]['voices'][0]['beats'] = [
                dict(type=4, duration=[1,4], velocity='f', palmMute=True,
                     notes=[dict(string=0, fret=p+(2 if bar==4 else 0)-track['tuning'][0]),
                            dict(string=1, fret=p+7+(2 if bar==4 else 0)-track['tuning'][1])])
                for p in (50, 52, 50, 53)]
    # A separate part supplies half-quarter attack spacing. No selected outcome
    # is hidden in this source; its current events merely define candidate shifts.
    docs['metadata.json']['tracks'].append(dict(name='Authored drum pulse', instrumentId=128))
    docs['track-4.json'] = dict(songId=fixture.SONG, revisionId=1, partId=4, instrumentId=128,
        tuning=[], measures=[dict(signature=[4,4], voices=[dict(beats=[
            dict(type=8, duration=[1,8], notes=[dict(string=0,fret=36)]) for _ in range(8)])])
            for _ in range(9)])
    _, lower, _, cell = fixture.build(docs=docs)
    model = uses.lift(material.lift_t3(cell, [dict(parts=[2,3],first_bar=b,last_bar=b) for b in (1,4)]))
    return lower, model


def reload(value):
    return json.loads(json.dumps(value))


class MaterialRhythmControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lower, cls.original = build()
        cls.zero = rhythm.lift(cls.original, USE)
        cls.changed = rhythm.candidate(cls.zero, USE, '1/2')

    def test_zero_and_saved_revert_restore_complete_preceding_model(self):
        self.assertEqual(uses.expand(self.zero), uses.expand(self.original))
        self.assertEqual(uses.reconstruct(reload(self.zero), {'variation':0}), self.lower)
        self.assertEqual(rhythm.candidate(reload(self.changed), USE, '0'), self.zero)
        self.assertEqual(self.changed['materials'], self.original['materials'])
        self.assertEqual(self.changed['observations'], self.original['observations'])

    def test_both_coattacks_move_together_and_only_notation_changes(self):
        before = project_documents(self.lower)
        after = project_documents(uses.reconstruct(self.changed, {'variation':0}))
        expected = deepcopy(before)
        for part in (2, 3):
            beats = expected[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            beats[0].update(type=4,duration=[3,8],dots=1)
            beats[-1].update(type=8,duration=[1,8])
        self.assertEqual(after, expected)
        self.assertEqual(after['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'],
                         before['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'])

    def test_preserved_backing_dependency_survives_save_and_later_edit(self):
        model = reload(self.changed)
        core = movement._body(model['lower_tier']['musical_relationships'])
        index = {m['id']:g for g in core['coattacks'] for m in g['members']}
        index[fixture.FOREIGN_BACKING]['bass_register_anchor'] = '41'
        restored = uses.expand(model)
        self.assertEqual(restored['musical_relationships']['relationships'],
                         uses.expand(self.original)['musical_relationships']['relationships'])
        docs = project_documents(uses.reconstruct(model, {'variation':0}))
        def pitch(part):
            track=docs[f'track-{part}.json']
            note=track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            return track['tuning'][note['string']]+note['fret']
        self.assertEqual(pitch(2),66)
        self.assertEqual(pitch(2)-pitch(3),25)

    def test_current_zero_fifty_hundred_and_observed_candidates(self):
        evidence = rhythm.options(self.zero, USE)
        self.assertEqual({a['offset_q'] for a in evidence['attempts']}, {'-1/2','0','1/2'})
        self.assertTrue(evidence['witnesses'])
        released = set(); changed = set()
        for level, seed in ((0,0),(50,0),(50,3),(50,4),(100,0),(100,1),(100,2)):
            out, report = rhythm.intervene(self.zero, USE, dict(release=level,intention='later',seed=seed))
            self.assertEqual(report['changed'],out!=self.zero)
            if level==0:self.assertEqual(out,self.zero)
            if level==100:self.assertTrue(report['released'])
            if level==50:released.add(report['released'])
            changed.add(report['changed'])
        self.assertEqual(released,{False,True}); self.assertEqual(changed,{False,True})
        locked, _ = rhythm.intervene(reload(self.changed), USE, dict(release=0,intention='earlier',seed=0))
        self.assertEqual(locked,self.changed)

    def test_section_and_return_keep_timing_independent_and_other_owners_exact(self):
        t4 = arrangement.lift(self.original, USE, [0,1])
        all_sections = sections.extend(t4, [], [dict(use_id='material-use:1',eligible_materials=[1])])
        # Allocate the first idea at its later use; the second vocabulary option
        # has genuinely different pitches, so the subsequent edit is nontrivial.
        all_sections['choices'][1]['allocation']['material_ref'] = 0
        all_sections['choices'][1]['constraints']['eligible_materials'] = [0,1]
        sections.reconstruct(all_sections,{'variation':0})
        t5 = theme.fit(all_sections, USE, 'material-use:1')
        lifted = rhythm.lift_composed(t5, 'material-use:1')
        changed = rhythm.candidate_composed(lifted, 'material-use:1', '1/2')
        self.assertEqual(changed['relationship'],t5['relationship'])
        self.assertEqual(changed['lower_tier']['choices'],t5['lower_tier']['choices'])
        self.assertEqual(rhythm.candidate_composed(reload(changed),'material-use:1','0'),lifted)
        # A later material intention must preserve the independently owned phase.
        recalled = theme.candidate(reload(changed),'recall')
        self.assertEqual(rhythm.expand_uses(recalled)['uses'][1]['rhythm_offset_q'],'1/2')
        self.assertNotIn('rhythm_offset_q',rhythm.expand_uses(recalled)['uses'][0])
        before = project_documents(theme.reconstruct(recalled,{'variation':0}))
        following = theme.change_source(reload(recalled),1)
        after = project_documents(theme.reconstruct(following,{'variation':0}))
        for part in (2,3):
            for bar in (0,3):
                a=before[f'track-{part}.json']['measures'][bar]['voices'][0]['beats']
                b=after[f'track-{part}.json']['measures'][bar]['voices'][0]['beats']
                self.assertEqual([v['duration'] for v in a],[v['duration'] for v in b])
                self.assertEqual([n['fret']+2 for v in a for n in v['notes']],
                                 [n['fret'] for v in b for n in v['notes']])
        self.assertEqual(rhythm.expand_uses(following)['uses'][1]['rhythm_offset_q'],'1/2')

    def test_unsupported_or_unrelated_updates_are_atomic(self):
        frozen = deepcopy(self.zero)
        for offset in ('1','-1','0.5'):
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                rhythm.candidate(self.zero,USE,offset)
            self.assertEqual(self.zero,frozen)
        with self.assertRaises(ValueError):rhythm.lift(self.zero,USE)
        corrupted = deepcopy(self.changed)
        corrupted['observations']['extra'] = 'not original'
        with self.assertRaises(ValueError):rhythm.embed_uses(self.zero,corrupted,USE)


if __name__ == '__main__':
    unittest.main()
