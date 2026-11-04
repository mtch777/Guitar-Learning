"""Actual same-model movement/register/rhythm composition on authored music."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import connected_output_control as control
import connected_tier2 as connected
import melodic_movement_ownership as movement
import movement_output_control as melodic
import support_material_uses as uses
from source_fact_tier1 import extract_documents, project_documents
from test_material_expression_composition import authored_documents
import test_direct_support_material as direct
import test_musical_cell_development as fixture


ROOTS=[f'event:{fixture.SONG}:0:1:0:{i}:0' for i in range(4)]
SPECS=[dict(parts=[2,3],first_bar=b,last_bar=b) for b in (1,2)]
REQUESTS=[dict(use_id=f'material-use:{i}',scope=deepcopy(s),intention='later')
          for i,s in enumerate(SPECS)]


def build():
    docs=authored_documents()
    # Two ordinary complete bars with edge rests: every pitched attack can
    # move, while the written bar endpoints stay fixed. Existing coattacks,
    # optional expression and unrelated backing ownership remain present.
    for part in (2,3):
        for bar in (1,2):
            old=docs[f'track-{part}.json']['measures'][bar-1]['voices'][0]['beats']
            notes=deepcopy(old[:3])
            for beat in notes:beat.update(type=4,duration=[1,4])
            new=[dict(type=8,duration=[1,8],notes=[dict(rest=True)])]+notes+[
                dict(type=8,duration=[1,8],notes=[dict(rest=True)])]
            docs[f'track-{part}.json']['measures'][bar-1]['voices'][0]['beats']=new
    # The independent part supplies an actual half-beat pulse; no desired
    # offset or output pitches are inserted into a production candidate.
    for bar in (1,2):
        old=docs['track-1.json']['measures'][bar-1]['voices'][0]['beats']
        new=[]
        for beat in old:
            for _ in range(2):
                child=deepcopy(beat);child.update(type=8,duration=[1,8]);new.append(child)
        docs['track-1.json']['measures'][bar-1]['voices'][0]['beats']=new
    lower=extract_documents(docs)
    t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
        palm_mute_slots=True,dynamic_evidence=True,backing_bindings=[direct.FOREIGN]))
    t2=movement.lift(t2,ROOTS,register_controls=True)
    return docs,lower,uses.from_tier2(t2,SPECS)


def request(melody=100,register=100):
    return dict(melody=melody,register=register,intent='repeat_start',register_direction='up',seed=7)


class ConnectedOutputControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs,cls.lower,cls.model=build()

    def test_nonzero_joint_counts_same_inverse_and_saved_zero(self):
        frozen=deepcopy(self.model)
        changed,report=control.intervene(self.model,request(),REQUESTS,50,seed=11)
        self.assertTrue(report['satisfied'],report)
        rows=report['output']['features']
        self.assertEqual((rows['melody']['changed_count'],rows['melody']['total_count']),(3,3))
        self.assertEqual((rows['register']['changed_count'],rows['register']['total_count']),(4,4))
        self.assertEqual((rows['attack_onset_q']['changed_count'],rows['attack_onset_q']['total_count']),(12,24))
        saved=json.loads(json.dumps(changed))
        lower=uses.reconstruct(saved,{'variation':0})
        t2=uses.expand(saved)
        self.assertEqual(connected.realize(t2),lower)
        actual=project_documents(lower)
        pitches=[]
        for beat in actual['track-0.json']['measures'][0]['voices'][0]['beats']:
            n=beat['notes'][0];pitches.append(actual['track-0.json']['tuning'][n['string']]+n['fret'])
        self.assertEqual(pitches,[79]*4)
        for key in ('materials','slots'):self.assertEqual(saved[key],self.model[key])
        self.assertEqual(t2['source_origin'],self.model['lower_tier']['source_origin'])
        self.assertEqual(t2['owned_parameters'][movement.SLOT]['observations'],
                         self.model['lower_tier']['owned_parameters'][movement.SLOT]['observations'])
        zero,zero_report=control.intervene(saved,request(0,0),REQUESTS,0,seed=11)
        self.assertEqual(zero,saved);self.assertTrue(zero_report['satisfied'])
        self.assertEqual(uses.reconstruct(zero,{'variation':0}),lower)
        again,again_report=control.intervene(self.model,request(),REQUESTS,50,seed=11)
        self.assertEqual((again,again_report),(changed,report))
        self.assertEqual(self.model,frozen)

    def test_failed_rhythm_commits_no_partial_movement(self):
        # Each group moves twelve attack occurrences together: six of24 is
        # impossible in this finite vocabulary even though movement succeeds.
        frozen=deepcopy(self.model)
        unchanged,report=control.intervene(self.model,request(),REQUESTS,25)
        self.assertEqual(unchanged,frozen);self.assertEqual(self.model,frozen)
        self.assertFalse(report['satisfied']);self.assertFalse(report['changed'])
        self.assertEqual(report['status'],'JOINT_TARGET_UNSATISFIED_WITHIN_SEARCH')
        self.assertTrue(report['movement']['admitted_candidates'])
        self.assertTrue(report['attempts'])

    def test_saved_unrelated_dependency_propagates_after_joint_edit(self):
        changed,report=control.intervene(self.model,request(),REQUESTS,100)
        self.assertTrue(report['satisfied'],report)
        saved=json.loads(json.dumps(changed));before=project_documents(uses.reconstruct(saved,{'variation':0}))
        links=deepcopy(saved['lower_tier']['musical_relationships']['relationships'])
        core=movement._body(saved['lower_tier']['musical_relationships'])
        group=next(g for g in core['coattacks'] if any(m['id']==fixture.FOREIGN_BACKING for m in g['members']))
        group['bass_register_anchor']='41'
        expected=deepcopy(before)
        for part,pitch in ((2,66),(3,41)):
            track=expected[f'track-{part}.json'];note=track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            note['fret']=pitch-track['tuning'][note['string']]
        self.assertEqual(project_documents(uses.reconstruct(saved,{'variation':0})),expected)
        self.assertEqual(saved['lower_tier']['musical_relationships']['relationships'],links)

    def test_packing_maps_contacts_by_identity_not_skeleton_list_position(self):
        model=deepcopy(self.model)
        # Stored lower fragments need not have the restored complete array's
        # ordering. Restoration establishes the complete canonical order.
        parent=model['lower_tier']['owned_parameters']
        parent['physical_positions'].reverse();parent['source_choices'].reverse()
        self.assertEqual(uses.reconstruct(model,{'variation':0}),self.lower)
        full=uses.expand(model)
        child,_=melodic.intervene(full,request())
        old_index=next(i for i,p in enumerate(parent['physical_positions']) if p['occurrence_ref']==ROOTS[0])
        new_index=next(i for i,p in enumerate(child['owned_parameters']['physical_positions']) if p['occurrence_ref']==ROOTS[0])
        self.assertNotEqual(old_index,new_index)
        changed=control.pack_movement(model,child)
        self.assertEqual(uses.expand(changed),child)
        self.assertEqual(changed['materials'],model['materials'])
        self.assertEqual(changed['slots'],model['slots']);self.assertEqual(changed['uses'],model['uses'])

    def test_unrelated_valid_edit_cannot_enter_movement_packer(self):
        full=uses.expand(self.model);other=deepcopy(full)
        core=movement._body(other['musical_relationships'])
        group=next(g for g in core['coattacks'] if any(m['id']==fixture.FOREIGN_BACKING for m in g['members']))
        group['bass_register_anchor']='41'
        connected.realize(other)
        frozen=deepcopy(self.model)
        with self.assertRaises(ValueError):control.pack_movement(self.model,other)
        self.assertEqual(self.model,frozen)

    def test_movement_material_overlap_still_refuses_without_a_new_owner_path(self):
        full=uses.expand(self.model);snapshot=deepcopy(full)
        with self.assertRaises(ValueError):
            uses.from_tier2(full,[dict(parts=[0],first_bar=1,last_bar=1)])
        self.assertEqual(full,snapshot)


if __name__=='__main__':unittest.main()
