"""Saved joint entry/content clocks, stable lines and successive edits."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import local_accents
import local_dynamics
import material_slot_clock_control as clock
import support_material_uses as uses
import test_material_expression_composition as fixture
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest

LANE='track-2.json#/measures/0/voices/0/beats'
reload=lambda model:json.loads(json.dumps(model))

def request(entry='1/8',weights=('1/7','2/7','2/7','2/7')):
    return dict(use_id=fixture.USE,scope=fixture.SPEC,
        lane_shares={LANE:{LANE+'/'+str(i):v for i,v in enumerate(weights)}},
        entry_shares={LANE:entry})

def model():
    docs,_,t2=fixture.build()
    return docs,uses.from_tier2(t2,[fixture.SPEC])

def expected(docs):
    out=deepcopy(docs);beats=out['track-2.json']['measures'][0]['voices'][0]['beats']
    beats[0].update(type=8,duration=[1,8])
    beats.insert(0,dict(duration=[1,8],type=8,rest=True,notes=[dict(rest=True)]))
    return out

class MaterialUseEntryClockTests(unittest.TestCase):
    def test_joint_final_clock_preserves_complete_score_and_unselected_relationship(self):
        docs,before=model();frozen=deepcopy(before)
        after,report=clock.apply_entry_choices(before,[request()])
        self.assertTrue(report['changed']);self.assertEqual(before,frozen)
        self.assertEqual(uses.reconstruct(reload(after),{'variation':0}),extract_documents(expected(docs)))
        self.assertEqual(after['materials'],before['materials'])
        self.assertEqual(after['lower_tier'],before['lower_tier'])
        _,_,old_ids=uses.realize_pair(before)
        _,_,new_ids=uses.realize_pair(after)
        self.assertEqual([r['identity']for r in old_ids],[r['identity']for r in new_ids])

    def test_saved_current_zero_and_second_edit_do_not_add_a_second_rest(self):
        _,before=model();first,_=clock.apply_entry_choices(before,[request()])
        zero,report=clock.apply_entry_choices(reload(first),[request()])
        self.assertEqual(zero,first);self.assertFalse(report['changed'])
        second,_=clock.apply_entry_choices(reload(first),[request('1/4',('1/4',)*4)])
        beats=project_documents(uses.reconstruct(second,{'variation':0}))['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual(len(beats),5)
        self.assertEqual([b['duration']for b in beats],[[1,4]]+[[3,16]]*4)
        self.assertEqual(second['lower_tier'],first['lower_tier'])

    def test_subdivision_then_entry_then_expression_save_and_another_clock_edit(self):
        _,before=model()
        group=next(g['id']for g in before['materials'][0]['lower_tier']['coattacks']if g['part_id']==2)
        split,_=uses.subdivision_candidate(before,{fixture.USE:[group]},percent=100)
        after,_=clock.apply_entry_choices(split,[request()])
        current=uses.expand(after)
        expressed=local_dynamics.apply(current,fixture.DYNAMIC,'pp')
        expressed=local_accents.apply(expressed,LANE+'/3/notes/0',dict(kind='absent'))
        saved=uses.pack_expression(after,expressed)
        self.assertEqual(uses.expand(reload(saved)),expressed)
        next_state,_=clock.apply_entry_choices(reload(saved),[request('1/4',('1/4',)*4)])
        beats=project_documents(uses.reconstruct(next_state,{'variation':0}))['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([b['duration']for b in beats],[[1,4],[3,32],[3,32]]+[[3,16]]*3)
        self.assertEqual(beats[1]['velocity'],'pp')
        self.assertNotIn('accentuated',beats[3]['notes'][0])
        self.assertEqual(next_state['lower_tier']['source_origin'],before['lower_tier']['source_origin'])

    def test_denied_inverse_has_only_saved_upper_and_matches_independent_expected(self):
        from run_support_use_qa import bundle
        from qa_isolation_harness import execute
        docs,before=model();after,_=clock.apply_entry_choices(before,[request()])
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as directory:
            result=execute(code,reload(after),{'variation':0},extract_documents(expected(docs)),
                Path(directory)/'denied',timeout=90,purpose='exact_zero')
        self.assertEqual(result['status'],'PASS',result)
        self.assertFalse(result['parent_expected_staged'])

    def test_invalid_joint_notation_is_atomic(self):
        _,before=model();frozen=digest(before)
        with self.assertRaises(ValueError):
            clock.apply_entry_choices(before,[request('1/3',('1/4',)*4)])
        self.assertEqual(digest(before),frozen)

    def test_existing_rest_uses_the_same_content_clock_without_another_prefix(self):
        import connected_tier2 as connected
        docs=fixture.authored_documents()
        beats=docs['track-2.json']['measures'][0]['voices'][0]['beats']
        beats[0]=dict(type=4,duration=[1,4],rest=True,notes=[dict(rest=True)])
        lower=extract_documents(docs)
        t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
            palm_mute_slots=True,dynamic_evidence=True))
        upper=uses.from_tier2(t2,[fixture.SPEC])
        changed,_=clock.apply_entry_choices(upper,[request('0',('1/8','3/8','1/8','3/8'))])
        actual=project_documents(uses.reconstruct(changed,{'variation':0}))
        result=actual['track-2.json']['measures'][0]['voices'][0]['beats']
        self.assertEqual([b['duration']for b in result],[[1,8],[3,8],[1,8],[3,8]])
        self.assertTrue(result[0]['rest']);self.assertEqual(len(result),4)

    def test_delayed_pull_off_retains_connection_through_current_held_prefix(self):
        import test_material_entry_carry as carry_fixture
        docs,_,t2=carry_fixture.fixture()
        scope=dict(parts=[0],first_bar=1,last_bar=2)
        upper=uses.from_tier2(t2,[scope])
        lane=carry_fixture.LANE
        query=dict(use_id=fixture.USE,scope=scope,entry_shares={lane:'1/4'},
            lane_shares={lane:{lane+'/'+str(i):'1/4'for i in range(4)}})
        changed,_=clock.apply_entry_choices(upper,[query])
        actual=project_documents(uses.reconstruct(reload(changed),{'variation':0}))
        beats=actual['track-0.json']['measures'][1]['voices'][0]['beats']
        self.assertTrue(beats[0]['notes'][0]['tie'])
        self.assertEqual(beats[0]['notes'][0]['fret'],docs['track-0.json']['measures'][0]['voices'][0]['beats'][-1]['notes'][0]['fret'])
        self.assertEqual(changed['materials'],upper['materials'])
        self.assertEqual(changed['lower_tier'],upper['lower_tier'])

    def test_guarded_let_ring_keeps_written_connection_without_claiming_acoustic_end(self):
        import connected_tier2 as connected
        import material_execution_locks as locks
        import test_material_entry_carry as carry_fixture
        docs,_,_=carry_fixture.fixture()
        origin=docs['track-0.json']['measures'][0]['voices'][0]['beats'][-1]
        origin['notes'][0].pop('hp');origin['letRing']=True
        lower=extract_documents(docs)
        t2=connected.strip_lower(connected.analyze(lower,note_accent_slots=True,
            palm_mute_slots=True,dynamic_evidence=True,expression_evidence=True))
        scope=dict(parts=[0],first_bar=1,last_bar=2);upper=uses.from_tier2(t2,[scope])
        definition=upper['materials'][0];refs=definition['lower_tier']['realization_order']
        v2=locks.upgrade_successor_choices(definition['unresolved_execution_locks'],lower,
            definition['observed_execution'],refs,origin_q=definition['source_start_q'])
        definition['unresolved_execution_locks']=locks.upgrade_clock_choices(v2,lower,
            definition['observed_execution'],refs,origin_q=definition['source_start_q'])
        lane=carry_fixture.LANE
        query=dict(use_id=fixture.USE,scope=scope,entry_shares={lane:'1/4'},
            lane_shares={lane:{lane+'/'+str(i):'1/4'for i in range(4)}})
        changed,_=clock.apply_entry_choices(upper,[query])
        actual=project_documents(uses.reconstruct(reload(changed),{'variation':0}))
        beats=actual['track-0.json']['measures'][1]['voices'][0]['beats']
        self.assertTrue(beats[0]['notes'][0]['tie']);self.assertNotIn('letRing',beats[0])
        self.assertEqual(changed['materials'],upper['materials'])
        self.assertEqual(changed['lower_tier'],upper['lower_tier'])

if __name__=='__main__':unittest.main()
