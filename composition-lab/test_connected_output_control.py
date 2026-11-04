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

    def test_material_can_own_clock_without_replacing_existing_melody(self):
        full=uses.expand(self.model);snapshot=deepcopy(full)
        together=uses.from_tier2(full,[dict(parts=[0],first_bar=1,last_bar=1)])
        self.assertEqual(uses.expand(together),full)
        self.assertEqual(full,snapshot)
        self.assertEqual(together['lower_tier']['owned_parameters'][movement.SLOT],
                         full['owned_parameters'][movement.SLOT])
        self.assertFalse(together['materials'][0]['pitch_paths'])
        self.assertEqual(len(together['materials'][0]['external_pitch_refs']),4)

    def overlap_fixture(self,coattack=False):
        docs=deepcopy(self.docs)
        part=2 if coattack else 0
        beats=docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
        if coattack:
            beats=beats[1:4]
            # Leave the upper string free for a higher register. The first
            # fixture had its locked lower note on that string, legitimately
            # making the requested simultaneous contact impossible.
            tuning=docs[f'track-{part}.json']['tuning']
            for beat in beats:
                for note,string in zip(beat['notes'],(2,0)):
                    pitch=tuning[note['string']]+note['fret']
                    note.update(string=string,fret=pitch-tuning[string])
        for beat in beats[:3]:beat.update(type=4,duration=[1,4])
        docs[f'track-{part}.json']['measures'][0]['voices'][0]['beats']=[
            dict(type=8,duration=[1,8],notes=[dict(rest=True)])]+beats[:3]+[
            dict(type=8,duration=[1,8],notes=[dict(rest=True)])]
        roots=[f'event:{fixture.SONG}:{part}:1:0:{i}:{1 if coattack else 0}' for i in (1,2,3)]
        lower=extract_documents(docs)
        t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
            palm_mute_slots=True,dynamic_evidence=True,backing_bindings=[direct.FOREIGN]))
        t2=movement.lift(t2,roots,register_controls=True)
        spec=dict(parts=[part],first_bar=1,last_bar=1)
        model=uses.from_tier2(t2,[spec])
        requests=[dict(use_id='material-use:0',scope=spec,intention='later')]
        return model,requests,roots

    def test_same_notes_change_movement_register_and_rhythm_then_reload_and_edit(self):
        model,requests,roots=self.overlap_fixture();frozen=deepcopy(model)
        changed,report=control.intervene(model,request(),requests,100)
        self.assertTrue(report['satisfied'],report)
        features=report['output']['features']
        self.assertEqual(features['melody']['changed_count'],2)
        self.assertEqual(features['register']['changed_count'],3)
        self.assertEqual(features['attack_onset_q']['changed_count'],3)
        self.assertEqual(model,frozen)
        self.assertEqual(changed['materials'],model['materials'])
        saved=json.loads(json.dumps(changed));current=uses.expand(saved)
        original=uses.expand(model)
        self.assertEqual(current['owned_parameters'][movement.SLOT]['observations'],
                         original['owned_parameters'][movement.SLOT]['observations'])
        self.assertEqual(current['musical_relationships']['relationships'],
                         original['musical_relationships']['relationships'])
        zero,report0=control.intervene(saved,request(0,0),requests,0)
        self.assertTrue(report0['satisfied']);self.assertEqual(zero,saved)
        # A later register edit operates on the same occurrence identities and
        # keeps the changed rhythm, rather than rebuilding source material.
        second,report2=control.intervene(saved,dict(request(0,100),register_direction='down'),requests,0)
        self.assertTrue(report2['satisfied'],report2)
        self.assertEqual(second['materials'],saved['materials'])
        self.assertEqual(second['uses'],saved['uses'])
        self.assertEqual(uses.expand(second)['owned_parameters'][movement.SLOT]['attacks'],
                         original['owned_parameters'][movement.SLOT]['attacks'])

    def test_timing_reconciliation_cannot_excuse_changed_expression(self):
        model,requests,_=self.overlap_fixture()
        full=uses.expand(model);other=deepcopy(full)
        group=next(g for g in other['owned_parameters']['optional_note_accents']['groups']
                   if g['note_structure']['id']=='track-0.json#/measures/0/voices/0/beats/1/notes/0')
        group['state']=dict(kind='explicit',value=1,child_index=len(group['note_structure']['children']))
        with self.assertRaisesRegex(ValueError,'protected pitch execution or notation'):
            movement.retime_from_parent(full,other,movement._shape(full)[1])

    def test_upper_chord_member_and_shared_rhythm_preserve_lower_pitches(self):
        model,requests,roots=self.overlap_fixture(coattack=True)
        changed,report=control.intervene(model,request(),requests,100)
        self.assertTrue(report['satisfied'],report)
        actual=project_documents(uses.reconstruct(changed,{'variation':0}))
        before=project_documents(uses.reconstruct(model,{'variation':0}))
        track=actual['track-2.json'];old=before['track-2.json']
        for i in (1,2,3):
            notes=track['measures'][0]['voices'][0]['beats'][i]['notes']
            old_notes=old['measures'][0]['voices'][0]['beats'][i]['notes']
            self.assertEqual(notes[0],old_notes[0])
            pitch=track['tuning'][notes[1]['string']]+notes[1]['fret']
            self.assertEqual(pitch,69)
        self.assertEqual([b['duration'] for b in track['measures'][0]['voices'][0]['beats']],
                         [[1,4],[1,4],[1,4],[1,8],[1,8]])
        self.assertEqual(report['output']['features']['attack_onset_q']['changed_count'],6)
        self.assertEqual(changed['materials'],model['materials'])

    def test_impossible_shared_count_refuses_without_partial_pitch_change(self):
        model,requests,_=self.overlap_fixture();snapshot=deepcopy(model)
        unchanged,report=control.intervene(model,request(),requests,50)
        self.assertFalse(report['satisfied']);self.assertEqual(unchanged,snapshot)
        self.assertEqual(model,snapshot)

    def test_shared_timing_rechecks_held_pitch_in_its_final_tonal_context(self):
        import stable_pitch_policy as policy
        from test_stable_pitch_policy import context, C_MAJOR
        model,requests,roots=self.overlap_fixture()
        full=uses.expand(model)
        tonal=context(full,[C_MAJOR])
        tonal['contexts']=[
            dict(id='before-change',start_q='0',end_q='5/2',candidates=[C_MAJOR]),
            dict(id='after-change',start_q='5/2',end_q='12',candidates=[
                dict(id='D-major',tonic_pc=2,intervals=[0,2,4,5,7,9,11])])]
        full=policy.attach(full,context=tonal,held_refs=roots)
        model=uses.from_tier2(full,[requests[0]['scope']]);snapshot=deepcopy(model)
        # The octave-only change preserves G/C/G in the original contexts.
        # Delaying the middle C crosses into D major, which excludes C; the result
        # must reconsider that new time coverage, not reuse the pitch-only pass.
        controls=request(0,100)
        candidates,_=melodic.candidates(full,controls)
        self.assertTrue(candidates)
        import material_rhythm_control as timing
        pitched=control.pack_movement(model,candidates[0][0]);frozen=deepcopy(pitched)
        with self.assertRaisesRegex(ValueError,'OUT_OF_COLLECTION'):
            timing.candidate_many(pitched,[dict(
                use_id='material-use:0',scope=requests[0]['scope'],offset_q='1/2')])
        with self.assertRaisesRegex(ValueError,'OUT_OF_COLLECTION'):
            timing.candidate(timing.lift(pitched,'material-use:0'),'material-use:0','1/2')
        self.assertEqual(pitched,frozen)
        unchanged,report=control.intervene(model,controls,requests,100)
        self.assertFalse(report['satisfied'],report)
        self.assertEqual(unchanged,snapshot);self.assertEqual(model,snapshot)


if __name__=='__main__':unittest.main()
