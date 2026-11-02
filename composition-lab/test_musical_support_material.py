"""Authored unequal inventories; no artist evidence or listening claims."""
from copy import deepcopy
import json
import unittest

import test_musical_cell_development as fixture
import musical_cell_development as cell
import musical_support_material as material
from source_observation_evidence import digest


def authored():
    docs=fixture.authored_score()
    for part in (2,3):
        track=docs[f'track-{part}.json'];base=track['tuning'][0]
        single=lambda pitch:dict(duration=[1,4],notes=[dict(string=0,fret=pitch-base)])
        def dyad(duration):
            return dict(duration=duration,palmMute=True,notes=[
                dict(string=0,fret=55-base),dict(string=1,fret=62-track['tuning'][1])])
        track['measures'][0]['voices'][0]['beats']=[single(p)for p in (55,57,55,57)]
        track['measures'][1]['voices'][0]['beats']=[dyad([1,2]),dict(duration=[1,4],rest=True,notes=[dict(rest=True)]),dyad([1,4])]
    docs['metadata.json']['tracks'].append(dict(name='Drums',instrumentId=128))
    track=dict(songId=fixture.SONG,revisionId=1,partId=4,instrumentId=128,tuning=[],measures=[])
    for bar in range(9):
        beats=[dict(duration=[1,4],notes=[dict(string=0,fret=key)])for key in (36,42,36,42)]if bar<2 else[dict(duration=[1,1],notes=[dict(rest=True)])]
        if bar==1:beats=[dict(duration=d,notes=[dict(string=0,fret=k)])for d,k in (([1,2],36),([1,4],42),([1,4],36))]
        if bar==2:beats.insert(0,dict(duration=[1,16],graceNote='before',notes=[dict(string=0,fret=38)]))
        track['measures'].append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    docs['track-4.json']=track
    return fixture.build(docs=docs)


class MaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.lower,cls.t2,cls.t3=authored()
        cls.specs=[dict(parts=[2,3,4],first_bar=b,last_bar=b)for b in (1,2)]
        cls.lifted=material.lift_t3(cls.t3,cls.specs)

    def test_complete_coattacks_rests_and_current_t3_restore_exactly(self):
        restored=material.expand_t3(json.loads(json.dumps(self.lifted)))
        self.assertEqual(restored,self.t3)
        self.assertEqual(cell.reconstruct(restored,{'variation':0}),self.lower)
        for owned in self.lifted['materials']:
            self.assertEqual(len(owned['pitch_paths']),1)  # two source guitar lines, one path
            self.assertTrue(all('onset_q'not in g and'bass_register_anchor'not in g for g in owned['lower_tier']['coattacks']))
            self.assertTrue(all('duration_q'not in m and'voicing_interval'not in m for g in owned['lower_tier']['coattacks']for m in g['members']))
        self.assertNotEqual(len(self.lifted['materials'][0]['lower_tier']['realization_order']),
                            len(self.lifted['materials'][1]['lower_tier']['realization_order']))

    def test_saved_prior_cell_edit_is_not_reset_by_material_ownership(self):
        changed,_=cell.intervene(self.t3,fixture.controls(seed=4))
        self.assertNotEqual(changed['relationship'],self.t3['relationship'])
        lifted=material.lift_t3(changed,self.specs)
        self.assertEqual(material.expand_t3(json.loads(json.dumps(lifted))),changed)
        self.assertEqual(lifted['observations'],self.t3['observations'])

    def test_shared_path_drives_both_parts_without_changing_drums_or_time(self):
        owned=deepcopy(self.lifted['materials'][1]);before=material.expand(owned)
        owned['pitch_paths'][0]['start']='57';after=material.expand(owned)
        for a,b in zip(before['coattacks'],after['coattacks']):
            self.assertEqual(a['onset_q'],b['onset_q']);self.assertEqual(a['members'],b['members'])
            self.assertEqual(b['bass_register_anchor'],None if a['part_id']==4 else str(int(a['bass_register_anchor'])+2))

    def test_missing_member_and_valid_but_wrong_beat_refuse(self):
        for kind in ('member','binding','duplicate-clock'):
            bad=deepcopy(self.lifted['materials'][1])
            if kind=='member':bad['lower_tier']['coattacks'][0]['members'].pop()
            elif kind=='binding':bad['bindings'][0]['beat_ref']=bad['bindings'][1]['beat_ref']
            else:bad['lower_tier']['coattacks'][0]['onset_q']='0'
            with self.subTest(kind=kind),self.assertRaises(ValueError):material.expand(bad)

    def test_overlap_or_foreign_owner_refuses_without_mutation(self):
        frozen=digest(self.t3)
        with self.assertRaises(ValueError):material.lift_t3(self.t3,[self.specs[0],self.specs[0]])
        with self.assertRaises(ValueError):material.lift_t3(self.t3,[dict(parts=[0],first_bar=1,last_bar=1)])
        with self.assertRaises(ValueError):material.lift_t3(self.t3,[dict(parts=[2],first_bar=9,last_bar=9)])
        self.assertEqual(digest(self.t3),frozen)

    def test_raw_pitch_vector_and_nested_hidden_payload_refuse(self):
        for kind in ('pitches','provenance','scope','fragment','binding'):
            bad=deepcopy(self.lifted);m=bad['materials'][0]
            if kind=='pitches':m['pitch_paths'][0]={'pitches':material.pitch_path(**m['pitch_paths'][0])['pitches']}
            elif kind=='provenance':m['provenance']['hidden_original']=self.lower
            elif kind=='scope':m['scope']['hidden']=self.lower
            elif kind=='fragment':m['lower_tier']['hidden']=self.lower
            else:m['bindings'][0]['hidden']=self.lower
            with self.subTest(kind=kind),self.assertRaises(ValueError):material.expand_t3(bad)

    def test_internal_hammer_on_direction_survives_inverse(self):
        docs,_,_,_=authored()
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp']=True
        _,_,_,t3=fixture.build(docs=docs)
        owned=material.lift_t3(t3,[self.specs[0]])
        owned['materials'][0]['pitch_paths'][0]['steps'][0]='-2'
        with self.assertRaisesRegex(ValueError,'EXECUTION_CHANGED'):
            material.expand_t3(owned)

    def test_material_clock_cannot_drift_from_unchanged_source_frame(self):
        bad=deepcopy(self.lifted);bad['materials'][0]['source_start_q']='1/2'
        with self.assertRaisesRegex(ValueError,'Source choices conflict with pitch/time relationships'):
            material.expand_t3(bad)

    def test_unbound_relationship_payload_is_not_an_extra_note_cache(self):
        bad=deepcopy(self.lifted);bad['materials'][0]['pitch_paths'].append(dict(start='88',steps=['1','2']))
        with self.assertRaisesRegex(ValueError,'Unbound material'):
            material.expand_t3(bad)


if __name__=='__main__':unittest.main()
