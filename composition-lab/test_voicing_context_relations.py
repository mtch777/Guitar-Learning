from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
import voicing_context_relations as v


def documents():
    measures=[]
    for bar in range(4):
        beats=[]
        for beat in range(4):
            at=bar*4+beat;upper=21 if at==11 else 9
            notes=[dict(string=2,fret=upper)]
            if at in (3,11):notes=[dict(string=3,fret=10)]+notes+[dict(string=1,fret=8)]
            beats.append(dict(duration=[1,4],notes=notes))
        measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=39,revisionId=1,title='Controlled source motion',artist='Fixture',tracks=[dict(instrumentId=25)]),
        'track-0.json':dict(songId=39,revisionId=1,partId=0,instrumentId=25,frets=24,tuning=[64,59,55,50,45,40],measures=measures)}


def joint_documents():
    docs=documents()
    for bar in docs['track-0.json']['measures']:
        for beat in bar['voices'][0]['beats']:
            if any(n['fret']==21 for n in beat['notes']):
                for n in beat['notes']:
                    if n['fret']==21:n.update(string=0,fret=12)
    for at in (0,1,5,6,8,9,13,14):
        docs['track-0.json']['measures'][at//4]['voices'][0]['beats'][at%4]['notes'].append(dict(string=0,fret=0))
    return docs


class ContextRelationTests(unittest.TestCase):
    def fixture(self):
        from voicing_register import inventory
        lower=extract_documents(documents());g=v.graph(lower);catalog=inventory(lower,'transposed_voicing_family')
        target=next(r for r in catalog['units']if r['bar']==1 and len(r['member_refs'])==3)
        donor=next(r for r in catalog['units']if r['bar']==3 and len(r['member_refs'])==3)
        value=dict(target['realization'],intervals=donor['realization']['intervals'],strings=donor['fixed_output_strings'])
        return lower,g,target,value

    def test_positive_source_motion_and_whole_neighborhood_excluded(self):
        lower,g,target,value=self.fixture();result=v.check_paths(g,target,value)
        self.assertEqual(result['status'],'PASS_OBSERVED_INCIDENT_MOTION',result)
        self.assertEqual(len(result['witnesses']),5)
        self.assertEqual({r['kind']for r in result['witnesses']},{'edge','triple'})
        for r in result['witnesses']:
            self.assertTrue(all(not set(w)&set(result['excluded_neighborhood'])for w in r['source_witness_refs']))

    def test_cached_relation_and_candidate_index_have_identical_decisions(self):
        from voicing_register import inventory
        lower,g,target,value=self.fixture();cat=inventory(lower,v.POLICY)
        cached=v.options(cat,target['id']);uncached=deepcopy(cat)
        for key in('source_path_relations','source_path_index','candidate_pools'):uncached.pop(key)
        self.assertEqual(v.options(uncached,target['id']),cached)
        self.assertEqual(v.check_paths(g,target,value),v.check_paths(g,target,value,v.evidence(g)))

    def test_wrong_motion_missing_neighbor_or_source_gap_refused(self):
        lower,g,target,value=self.fixture();ref='event:39:0:3:0:2:0'
        for field,new in (('pitch','65'),('duration_q','1/2'),('onset_q','19/2')):
            altered=deepcopy(g);altered['nodes'][ref][field]=new
            self.assertEqual(v.check_paths(altered,target,value)['status'],'REFUSED')
        altered=deepcopy(g);del altered['nodes'][ref]
        self.assertEqual(v.check_paths(altered,target,value)['status'],'REFUSED')

    def test_execution_unknown_grace_or_nominal_overlap_refuses(self):
        lower,g,target,value=self.fixture();ref='event:39:0:1:0:2:0'
        for reason in ('UNKNOWN_PITCH','GRACE_OR_NONPOSITIVE_DURATION','NOTE_DEPENDENCY:slide'):
            altered=deepcopy(g);altered['nodes'][ref]['reasons']=[reason]
            self.assertEqual(v.check_paths(altered,target,value)['status'],'REFUSED')
        altered=deepcopy(g);altered['nodes'][ref]['duration_q']='2'
        self.assertIn('AMBIGUOUS_OR_OVERLAPPING_LANE',v.check_paths(altered,target,value)['reasons'])

    def test_no_target_as_own_witness_and_no_boundary_skip(self):
        lower,g,target,value=self.fixture()
        for node in g['nodes'].values():
            if node['bar']>=3:node['reasons']=['QUARANTINED']
        self.assertEqual(v.check_paths(g,target,value)['status'],'REFUSED')
        # A new lane-start shape cannot borrow an interior source path.
        lower,g,target,value=self.fixture()
        for ref in list(g['nodes']):
            if g['nodes'][ref]['bar']==1 and g['nodes'][ref]['onset_q']!='3':del g['nodes'][ref]
        self.assertEqual(v.check_paths(g,target,value)['status'],'REFUSED')

    def test_fixed_strings_and_literal_zero(self):
        lower,g,target,value=self.fixture();changed=deepcopy(value);changed['strings'][1]=0
        self.assertEqual(v.check_paths(g,target,changed)['reasons'],['STRINGS_LOCKED'])
        original=dict(target['realization'],strings=target['fixed_output_strings'])
        self.assertEqual(v.check_paths(g,target,original)['status'],'PASS_UNCHANGED_PITCH_RELATIONSHIPS')

    def test_beat_declarations_and_unknown_intervening_lane_not_skipped(self):
        lower,g,target,value=self.fixture();altered=deepcopy(g)
        altered['nodes']['event:39:0:3:0:2:0']['articulation']['beat']['palmMute']=True
        self.assertEqual(v.check_paths(altered,target,value)['status'],'REFUSED')
        altered=deepcopy(g);node=deepcopy(altered['nodes']['event:39:0:1:0:2:0'])
        node.update(id='unknown',string=None,onset_q='5/2',reasons=['UNKNOWN_STRING_LANE']);altered['nodes']['unknown']=node
        self.assertIn('UNKNOWN_INTERVENING_LANE',v.check_paths(altered,target,value)['reasons'])
        altered['nodes']['unknown'].update(onset_q='0',duration_q='8')
        self.assertIn('UNKNOWN_INTERVENING_LANE',v.check_paths(altered,target,value)['reasons'])

    def test_full_inverse_and_isolated_zero_and_source_selected_change(self):
        from pathlib import Path
        import tempfile
        from connected_tier2 import analyze,strip_lower,reconstruct
        from voicing_register import inventory,select_target,intervene
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(documents());upper=strip_lower(analyze(lower,families=True))
        cat=inventory(lower,v.POLICY);selection=select_target(cat,v.POLICY)
        self.assertIsNotNone(selection['target_ref'])
        control=dict(context_policy=v.POLICY,voicing=100,register=0,physical=0,seed=9427,target_ref=selection['target_ref'])
        edited,decision=intervene(upper,control);self.assertTrue(decision['changed'])
        after=reconstruct(edited,dict(variation=0));self.assertNotEqual(after,lower)
        from check_voicing_context import check
        oracle=check(lower,after,decision['member_refs'],decision['chosen']['donor_refs'])
        self.assertEqual(oracle['status'],'PASS_INDEPENDENT_VOICING_CONTEXT',oracle)
        code,_=bundle(Path(__file__).parent)
        for c,want,purpose in ((dict(variation=0),lower,'exact_zero'),(dict(control,voicing=0),lower,'voicing_register_intervention'),(control,after,'voicing_register_intervention')):
            with tempfile.TemporaryDirectory()as temp:
                proof=execute(code,upper,c,want,Path(temp)/'proof',timeout=30,purpose=purpose)
            self.assertEqual(proof['status'],'PASS',proof)
        with self.assertRaises(ValueError):intervene(upper,dict(control,physical=100))

    def test_full_runner_on_authored_capture(self):
        import json,tempfile
        from pathlib import Path
        from run_lane_voicing_qa import run
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp)/'local-artifacts';capture=root/'capture';capture.mkdir(parents=True)
            for name,data in documents().items():(capture/name).write_text(json.dumps(data))
            frozen=root/'freeze.json';frozen.write_text(json.dumps(dict(code_hashes={})))
            result=run(capture,root/'result',frozen)
            self.assertEqual(result['status'],'PASS_BOUNDED_LANE_RELATION_QA',result)
            self.assertGreater(result['counts'].get('pitch_changing_choices',0),0)

    def test_joint_rewiring_checks_old_and_new_lane_neighbors(self):
        from voicing_register import inventory,intervene
        from connected_tier2 import analyze,strip_lower,realize
        from check_voicing_context import check
        lower=extract_documents(joint_documents());cat=inventory(lower,v.JOINT_POLICY)
        target=next(r for r in cat['units']if r['id']=='event:39:0:1:0:3:0')
        donor=next(r for r in cat['units']if r['id']=='event:39:0:3:0:3:0')
        value=dict(donor['realization'],strings=donor['fixed_output_strings'])
        g=v.graph(lower);proof=v.check_paths(g,target,value,allow_string_changes=True)
        self.assertEqual(proof['status'],'PASS_OBSERVED_INCIDENT_MOTION',proof)
        # These paths do NOT contain the moved occurrence after the edit.
        moved='event:39:0:1:0:3:1'
        self.assertTrue(any(moved not in w['after_refs']for w in proof['witnesses']))
        for ref in ('event:39:0:3:0:2:0','event:39:0:3:0:1:1'):
            altered=deepcopy(g);altered['nodes'][ref]['pitch']='65'
            self.assertEqual(v.check_paths(altered,target,value,allow_string_changes=True)['status'],'REFUSED')
        upper=strip_lower(analyze(lower,families=True))
        control=dict(context_policy=v.JOINT_POLICY,voicing=100,register=0,physical=100,target_ref=target['id'],seed=9427)
        edited,decision=intervene(upper,control);self.assertTrue(decision['changed'])
        after=realize(edited);oracle=check(lower,after,target['member_refs'],decision['chosen']['donor_refs'],allow_string_changes=True)
        self.assertEqual(oracle['status'],'PASS_INDEPENDENT_VOICING_CONTEXT',oracle)
        fixed,_=intervene(upper,dict(control,physical=0));self.assertEqual(realize(fixed),lower)
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            actual=execute(code,upper,control,after,Path(temp)/'joint',timeout=30,purpose='voicing_register_intervention')
        self.assertEqual(actual['status'],'PASS',actual)


if __name__=='__main__':unittest.main()
