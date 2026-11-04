"""Shared current rhythm, saved expression, ties and independent owners."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import connected_tier2 as connected
import material_rhythm_control as displacement
import material_slot_clock_control as clock
import support_material_uses as uses
import test_material_expression_composition as fixture
from source_fact_tier1 import extract_documents, project_documents

USE=fixture.USE
LANE='track-2.json#/measures/0/voices/0/beats'
reload=lambda value:json.loads(json.dumps(value))

def request(scope,lanes,use=USE):
    return dict(use_id=use,scope=deepcopy(scope),lane_shares=lanes)

def shares(lane,values):
    return {lane+'/'+str(i):v for i,v in enumerate(values)}

class MaterialSlotClockControlTests(unittest.TestCase):
    def test_current_identity_and_displacement_migration_preserve_unselected_lane(self):
        docs,lower,t2=fixture.build()
        model=uses.from_tier2(t2,[fixture.SPEC])
        shifted=displacement.candidate(displacement.lift(model,USE),USE,'1/2')
        before=deepcopy(shifted)
        current=shares(LANE,['3/8','1/4','1/4','1/8'])
        same,report=clock.apply_shares(shifted,[request(fixture.SPEC,{LANE:current})])
        self.assertEqual(same,shifted);self.assertFalse(report['changed'])
        changed,report=clock.apply_shares(shifted,[request(fixture.SPEC,
            {LANE:shares(LANE,['1/8','3/8','1/8','3/8'])})])
        self.assertTrue(report['changed']);self.assertEqual(shifted,before)
        self.assertNotIn('rhythm_offset_q',changed['uses'][0])
        self.assertEqual(changed['materials'],model['materials'])
        self.assertEqual(changed['lower_tier'],model['lower_tier'])
        expected=fixture.expected_later(docs)
        beats=expected['track-2.json']['measures'][0]['voices'][0]['beats']
        for i,b in enumerate(beats):
            if i%2:b.update(type=4,duration=[3,8],dots=1)
            else:
                b.update(type=8,duration=[1,8]);b.pop('dots',None)
        with patch('builtins.open',side_effect=AssertionError('Hidden source read')),patch.object(Path,'open',side_effect=AssertionError('Hidden source read')):
            self.assertEqual(uses.reconstruct(reload(changed),{'variation':0}),extract_documents(expected))
        saved=reload(changed)
        same,_=clock.apply_shares(saved,[request(fixture.SPEC,
            {LANE:shares(LANE,['1/8','3/8','1/8','3/8'])})])
        self.assertEqual(same,saved)

    def test_incoming_tie_and_fresh_note_share_one_changed_boundary(self):
        docs=fixture.authored_documents(tied=True)
        for part in (2,3):
            beats=docs[f'track-{part}.json']['measures'][1]['voices'][0]['beats']
            beats[:]=[beats[0],dict(type=2,dots=1,duration=[3,4],notes=beats[1]['notes'])]
        lower=extract_documents(docs)
        t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
            palm_mute_slots=True,dynamic_evidence=True))
        scope=dict(parts=[2,3],first_bar=1,last_bar=2)
        model=uses.from_tier2(t2,[scope]);frozen=deepcopy(model)
        lanes={}
        expected=deepcopy(docs)
        for part in (2,3):
            lane=f'track-{part}.json#/measures/1/voices/0/beats'
            lanes[lane]=shares(lane,['1/2','1/2'])
            b=expected[f'track-{part}.json']['measures'][1]['voices'][0]['beats']
            b[0].update(type=2,duration=[1,2])
            b[1].update(type=2,duration=[1,2],dots=0)
        changed,_=clock.apply_shares(model,[request(scope,lanes)])
        self.assertEqual(model,frozen)
        self.assertEqual(uses.reconstruct(reload(changed),{'variation':0}),extract_documents(expected))
        self.assertEqual(changed['materials'],model['materials'])
        for before,after in zip(uses.expand(model)['musical_relationships'].get('relationships',[]),
                                uses.expand(changed)['musical_relationships'].get('relationships',[])):
            self.assertEqual(before,after)

    def test_saved_expression_and_following_edit_keep_the_current_clock(self):
        docs,_,t2=fixture.build()
        model=uses.from_tier2(t2,[fixture.SPEC])
        changed,_=clock.apply_shares(model,[request(fixture.SPEC,
            {LANE:shares(LANE,['1/8','3/8','1/8','3/8'])})])
        current=uses.expand(changed)
        expressed=fixture.expression(current)
        packed=uses.pack_expression(changed,expressed)
        self.assertEqual(uses.expand(reload(packed)),expressed)
        moved,_=clock.apply_shares(reload(packed),[request(fixture.SPEC,
            {LANE:shares(LANE,['3/8','1/8','3/8','1/8'])})])
        actual=project_documents(uses.reconstruct(moved,{'variation':0}))
        b=actual['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual(b[0]['velocity'],'pp')
        self.assertNotIn('accentuated',b[1]['notes'][0])
        self.assertEqual([v['duration'] for v in b],[[3,8],[1,8],[3,8],[1,8]])
        self.assertEqual(moved['lower_tier']['source_origin'],model['lower_tier']['source_origin'])

    def test_invalid_and_competing_clock_owners_are_atomic(self):
        _,_,t2=fixture.build();model=uses.from_tier2(t2,[fixture.SPEC]);before=deepcopy(model)
        for values in (['1/2']*4,['0','1/2','1/4','1/4'],['0.25']*4):
            with self.subTest(values=values),self.assertRaises(ValueError):
                clock.apply_shares(model,[request(fixture.SPEC,{LANE:shares(LANE,values)})])
            self.assertEqual(model,before)
        changed=deepcopy(model)
        changed['uses'][0].update(rhythm_offset_q='0',rhythm_lane_shares={})
        with self.assertRaisesRegex(ValueError,'Two active material clock'):
            uses.expand(changed)

if __name__=='__main__':unittest.main()
