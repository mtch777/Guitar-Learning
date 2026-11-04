"""Current material instances allocate through live relationships, not note copies."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import connected_tier2 as connected
import material_degree_paths as degrees
import support_arrangement as arrangement
import support_material_uses as uses
import test_direct_support_material as fixture
from source_fact_tier1 import extract_documents,project_documents

SOURCE='material-use:0'
DESTINATION='material-use:1'
COLLECTION=dict(id='authored-C',tonic_pc=0,intervals=[0,2,4,5,7,9,11])

def saved(value):return json.loads(json.dumps(value))

def build(*,different_dynamic=False,nonempty=False):
    documents=fixture.authored_documents()
    track=documents['track-2.json']
    for index,pitch in enumerate((60,64,62)):
        track['measures'][index]=dict(signature=[4,4],voices=[dict(beats=[dict(
            type=1,duration=[1,1],notes=[dict(string=0,fret=pitch-track['tuning'][0],accentuated=index%2)],
            palmMute=bool(index%2),**({'velocity':'f'}if index==0 else{}))])])
    for index in (3,4,5):
        track['measures'][index]=dict(signature=[4,4],rest=True,voices=[dict(rest=True,beats=[dict(
            type=1,duration=[1,1],rest=True,notes=[dict(rest=True)],
            **({'velocity':'p'}if different_dynamic and index==3 else{}))])])
    if nonempty:
        for index in (3,4):
            track['measures'][index]=dict(signature=[4,4],voices=[dict(beats=[dict(
                type=1,duration=[1,1],notes=[dict(string=0,fret=5+index,accentuated=int(index==4))],
                palmMute=False)])])
    lower=extract_documents(documents)
    t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
        palm_mute_slots=True,dynamic_evidence=True,expression_evidence=True,backing_bindings=[fixture.FOREIGN]))
    direct=uses.from_tier2(t2,[dict(parts=[2],first_bar=1,last_bar=3),dict(parts=[2],first_bar=4,last_bar=6)])
    refs=list(range(len(direct['materials'][0]['pitch_paths'])))
    direct=uses.lift_degree_paths(direct,SOURCE,path_refs=refs,
        interpretations={ref:[deepcopy(COLLECTION)]for ref in refs},evidence_ref='authored-collection')
    selected=degrees.selected_refs(direct['materials'][0])
    current=uses.degree_path_candidate(direct,SOURCE,displacements={ref:1 for ref in selected},octaves={})
    return documents,lower,t2,current,selected

class DirectCurrentArrangementTests(unittest.TestCase):
    def test_current_zero_without_cell_keeps_envelope_and_all_rest_use(self):
        _,_,_,current,_=build(different_dynamic=True)
        before=deepcopy(current)
        t4=arrangement.lift_use(current,DESTINATION,[SOURCE])
        self.assertEqual(arrangement.expand(saved(t4)),current)
        self.assertEqual(arrangement.reconstruct(saved(t4),{'variation':0}),uses.reconstruct(current,{'variation':0}))
        self.assertEqual(current,before)

    def test_current_binding_owns_parameters_once_and_rejects_wrong_source_identity(self):
        _,_,_,current,_=build()
        t4=arrangement.lift_use(current,DESTINATION,[SOURCE])
        self.assertEqual(set(next(u for u in t4['lower_tier']['uses']if u['id']==DESTINATION)),{'id','slot_ref'})
        for name in ('source','material','cycle','duplicate_owner'):
            bad=saved(t4)
            if name=='source':bad['constraints']['lower_origin']='0'*64
            elif name=='material':bad['lower_tier']['materials'].reverse()
            elif name=='cycle':bad['allocation']['instance']=dict(kind='live',source_use_id=DESTINATION)
            else:next(u for u in bad['lower_tier']['uses']if u['id']==DESTINATION)['material_ref']=1
            before=deepcopy(bad)
            with self.subTest(name=name),self.assertRaises(ValueError):arrangement.reconstruct(bad,{'variation':0})
            self.assertEqual(bad,before)

    def test_live_reference_cycle_does_not_recurse_or_pick_an_arbitrary_order(self):
        from current_use_allocation import resolve
        _,_,_,current,_=build()
        for source,destination in ((SOURCE,DESTINATION),(DESTINATION,SOURCE)):
            target=next(u for u in current['uses']if u['id']==destination)
            original=target['material_ref'];slot=target['slot_ref']
            target.clear();target.update(id=destination,slot_ref=slot,source_use_ref=source,
                destination_material_ref=original,expression=[])
        frozen=deepcopy(current)
        with self.assertRaisesRegex(ValueError,'Cyclic'):resolve(current)
        self.assertEqual(current,frozen)

    def test_live_source_choices_fill_empty_destination_and_follow_saved_later_edit(self):
        _,_,_,current,refs=build()
        t4=arrangement.lift_use(current,DESTINATION,[SOURCE])
        changed=arrangement.candidate_use(t4,SOURCE)
        after=project_documents(arrangement.reconstruct(saved(changed),{'variation':0}))
        beats=lambda docs,bar:docs['track-2.json']['measures'][bar-1]['voices'][0]['beats']
        for source,target in zip((1,2,3),(4,5,6)):
            self.assertEqual(beats(after,source)[0]['notes'],beats(after,target)[0]['notes'])
            self.assertEqual(beats(after,source)[0]['palmMute'],beats(after,target)[0]['palmMute'])
            self.assertFalse(after['track-2.json']['measures'][target-1]['rest'])
            self.assertFalse(after['track-2.json']['measures'][target-1]['voices'][0]['rest'])
        edited=uses.degree_path_candidate(arrangement.expand(saved(changed)),SOURCE,
            displacements={ref:2 for ref in refs},octaves={})
        again=project_documents(uses.reconstruct(saved(edited),{'variation':0}))
        for source,target in zip((1,2,3),(4,5,6)):
            self.assertEqual(beats(again,source)[0]['notes'],beats(again,target)[0]['notes'])
        self.assertNotEqual(after,again)
        self.assertEqual(changed['lower_tier']['materials'],current['materials'])

    def test_destination_dynamics_and_original_evidence_survive_real_allocation(self):
        import observed_expression as expression
        import observed_dynamics as dynamics
        _,_,_,current,_=build(different_dynamic=True)
        changed=arrangement.candidate_use(arrangement.lift_use(current,DESTINATION,[SOURCE]),SOURCE)
        preceding,lower,identities=uses.realize_pair(arrangement.expand(saved(changed)))
        original=current['lower_tier']['owned_parameters'];actual=preceding['owned_parameters']
        self.assertEqual(expression.evidence(actual['observed_expression']),expression.evidence(original['observed_expression']))
        self.assertEqual(dynamics.evidence(actual['observed_dynamics']),dynamics.evidence(original['observed_dynamics']))
        events=expression._lineage(actual['observed_expression'])['event_map']
        for source,target in zip((1,2,3),(4,5,6)):
            donor=f'event:980213:2:{source}:0:0:0';old=f'event:980213:2:{target}:0:0:0'
            self.assertEqual(events[old],[])
            self.assertEqual(expression.original_refs(actual['observed_expression'],[old],require_all=True),{donor})
        self.assertEqual(len({r['identity']for r in identities}),len(identities))
        self.assertEqual(len({r['current_address']for r in identities}),len(identities))
        docs=project_documents(lower)
        self.assertEqual(docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['velocity'],'f')
        self.assertEqual(docs['track-2.json']['measures'][3]['voices'][0]['beats'][0]['velocity'],'p')
        influences=actual['observed_dynamics']['current_influence']['assignments']
        self.assertIn('event:980213:2:5:0:0:0',influences['track-2.json#/measures/3/voices/0/beats/0/velocity'])

    def test_saved_unrelated_backing_dependency_still_propagates(self):
        import backing_pitch_ownership as backing
        import melodic_movement_ownership as movement
        _,_,_,current,_=build(different_dynamic=True)
        changed=arrangement.candidate_use(arrangement.lift_use(current,DESTINATION,[SOURCE]),SOURCE)
        original=deepcopy(changed['lower_tier']['lower_tier']['musical_relationships']['relationships'])
        edited=saved(changed)
        parent=edited['lower_tier']['lower_tier']
        backing._index(movement._body(parent['musical_relationships']))[fixture.FOREIGN['backing_ref']][0]['bass_register_anchor']='41'
        docs=project_documents(arrangement.reconstruct(edited,{'variation':0}))
        for part,pitch in ((2,66),(3,41)):
            track=docs[f'track-{part}.json'];note=track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            self.assertEqual(track['tuning'][note['string']]+note['fret'],pitch)
        self.assertEqual(parent['musical_relationships']['relationships'],original)

    def test_three_into_two_does_not_reassign_the_second_accent(self):
        _,_,_,current,_=build(nonempty=True)
        t4=arrangement.lift_use(current,DESTINATION,[SOURCE]);frozen=deepcopy(t4)
        with self.assertRaisesRegex(ValueError,'SEMANTIC_CORRESPONDENCE'):
            arrangement.candidate_use(t4,SOURCE)
        self.assertEqual(t4,frozen)

    def test_actual_denied_inverse_and_complete_independent_expected_score(self):
        from run_support_arrangement_qa import bundle
        from qa_isolation_harness import execute
        _,_,_,current,_=build(different_dynamic=True)
        expected=project_documents(uses.reconstruct(current,{'variation':0}))
        for source,target in zip((1,2,3),(4,5,6)):
            measure=expected['track-2.json']['measures'][target-1]
            copied=deepcopy(expected['track-2.json']['measures'][source-1]['voices'][0]['beats'])
            copied[0].pop('velocity',None)
            if target==4:copied[0]['velocity']='p'
            measure['voices'][0]['beats']=copied
            measure['rest']=measure['voices'][0]['rest']=False
        changed=arrangement.candidate_use(arrangement.lift_use(current,DESTINATION,[SOURCE]),SOURCE)
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as directory:
            result=execute(code,saved(changed),{'variation':0},extract_documents(expected),
                Path(directory)/'inverse',timeout=90,purpose='exact_zero')
        self.assertEqual(result['status'],'PASS',result)
        self.assertFalse(result['parent_expected_staged'])

    def test_saved_contact_and_joint_clock_edits_keep_live_instances_and_evidence(self):
        from material_slot_clock_control import apply_entry_choices
        import observed_dynamics as dynamics
        import observed_expression as expression
        _,_,_,current,_=build(different_dynamic=True)
        t4=arrangement.candidate_use(arrangement.lift_use(current,DESTINATION,[SOURCE]),SOURCE)
        direct=arrangement.expand(saved(t4))
        members=direct['materials'][0]['lower_tier']['realization_order']
        moved=uses.degree_choices_candidate(direct,{},contact_strings={SOURCE:{members[0]:1}})
        lanes={f'track-2.json#/measures/{bar}/voices/0/beats':
            {f'track-2.json#/measures/{bar}/voices/0/beats/0':'1'}for bar in (0,1,2)}
        timed,_=apply_entry_choices(saved(moved),[dict(use_id=SOURCE,scope=current['slots'][0]['scope'],
            lane_shares=lanes,entry_shares={lane:'1/4'for lane in lanes})])
        parent,lower,_=uses.realize_pair(saved(timed))
        docs=project_documents(lower)
        for source,target in zip((1,2,3),(4,5,6)):
            left=docs['track-2.json']['measures'][source-1]['voices'][0]['beats']
            right=docs['track-2.json']['measures'][target-1]['voices'][0]['beats']
            self.assertTrue(left[0]['notes'][0]['rest']);self.assertTrue(right[0]['notes'][0]['rest'])
            self.assertEqual(left[1]['notes'],right[1]['notes'])
            self.assertEqual(left[1]['duration'],[3,4]);self.assertEqual(right[1]['duration'],[3,4])
        original=current['lower_tier']['owned_parameters'];actual=parent['owned_parameters']
        self.assertEqual(expression.evidence(actual['observed_expression']),expression.evidence(original['observed_expression']))
        self.assertEqual(dynamics.evidence(actual['observed_dynamics']),dynamics.evidence(original['observed_dynamics']))
        witness=actual['observed_dynamics']['current_influence']['allocations'][0]
        self.assertEqual(witness['assigned_refs'],[f'event:980213:2:{bar}:0:1:0'for bar in (4,5,6)])
        frozen=deepcopy(timed)
        with self.assertRaisesRegex(ValueError,'live allocated use'):
            uses.degree_choices_candidate(timed,{},contact_strings={DESTINATION:{members[0]:0}})
        self.assertEqual(timed,frozen)

    def test_current_lineage_witnesses_cannot_hide_missing_or_out_of_scope_members(self):
        import observed_expression as expression
        import observed_dynamics as dynamics
        _,_,_,current,_=build(different_dynamic=True)
        t4=arrangement.candidate_use(arrangement.lift_use(current,DESTINATION,[SOURCE]),SOURCE)
        parent=uses.expand(arrangement.expand(t4));parameters=parent['owned_parameters']
        broken=saved(parameters['observed_dynamics'])
        broken['current_influence']['allocations'][0]['assigned_refs']=['event:980213:2:4:0:999:0']
        with self.assertRaisesRegex(ValueError,'missing current note'):dynamics.validate(broken)
        broken=saved(parameters['observed_expression'])
        broken.pop('allocation_witnesses')
        with self.assertRaisesRegex(ValueError,'Nonempty'):expression.validate(broken)
        broken=saved(parameters['observed_expression'])
        broken['allocation_witnesses'][0]['scope']=dict(parts=[2],first_bar=7,last_bar=9)
        with self.assertRaisesRegex(ValueError,'escaped allocation scope'):expression.validate(broken)

if __name__=='__main__':unittest.main()
