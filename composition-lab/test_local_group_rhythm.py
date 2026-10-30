import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from test_group_rhythm_relations import documents
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
import local_group_rhythm as rhythm


def controls(ref,value=100,seed=0):return dict(context_policy=rhythm.POLICY,rhythm=value,target_ref=ref,seed=seed)


class GroupRhythmPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=extract_documents(documents());cls.upper=strip_lower(analyze(cls.before,rhythm_groups=True))
        cls.ref=cls.upper['musical_relationships']['groups'][0]['id']

    def test_supported_context_and_disjoint_evidence(self):
        ev=rhythm.options(self.before,self.ref)
        self.assertEqual(len(ev['options']),2);self.assertEqual(len(ev['witness_pair']),2)
        for option in ev['options']:self.assertNotIn(self.ref,option['donor_refs'])
        self.assertEqual({tuple(o['shares'])for o in ev['options']},{('1/2','1/4','1/4'),('1/4','1/4','1/2')})

    def test_zero_fifty_hundred_and_unrelated_locks(self):
        ev=rhythm.options(self.before,self.ref);counts={}
        for value in(0,50,100):
            draws=[rhythm.sample(ev,controls(self.ref,value,s))[1]for s in range(256)]
            counts[value]=sum(d['released']for d in draws)
        self.assertEqual(counts[0],0);self.assertEqual(counts[100],256)
        self.assertTrue(100<counts[50]<156,counts)
        self.assertEqual(reconstruct(self.upper,controls(self.ref,0)),self.before)
        chosen_seed=next(s for s in range(256)if rhythm.sample(ev,controls(self.ref,100,s))[1]['changed'])
        edited,report=rhythm.intervene(self.upper,controls(self.ref,100,chosen_seed))
        self.assertTrue(report['changed']);self.assertNotEqual(realize(edited),self.before)
        tampered=deepcopy(realize(edited));next(r for r in tampered['facts']if r['id'].endswith('/notes/0/fret'))['value']+=1
        with self.assertRaises(ValueError):rhythm.verify_effect(self.before,tampered,ev['target'],report['chosen']['shares'])

    def test_no_original_preference_at_hundred(self):
        a=rhythm.options(self.before,self.ref)
        other=rhythm.apply(self.upper,self.ref,['1/4','1/4','1/2']);b=rhythm.options(realize(other),self.ref)
        for seed in range(64):
            x,_=rhythm.sample(a,controls(self.ref,100,seed));y,_=rhythm.sample(b,controls(self.ref,100,seed))
            self.assertEqual((x['shares'],x['donor_refs']),(y['shares'],y['donor_refs']))

    def test_no_choice_and_invalid_controls(self):
        docs=documents();docs['track-0.json']['measures']=docs['track-0.json']['measures'][:1]
        before=extract_documents(docs);up=strip_lower(analyze(before,rhythm_groups=True))
        _,r=rhythm.intervene(up,controls(self.ref));self.assertFalse(r['changed']);self.assertEqual(r['status'],'NO_ADMITTED_CHOICE')
        for value in(-1,101,True,float('nan')):
            with self.assertRaises(ValueError):rhythm.validate_controls(controls(self.ref,value))
        with self.assertRaises(ValueError):rhythm.validate_controls({**controls(self.ref),'pitch':50})

    def test_actual_source_denied_policy_not_just_edited_parameter(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        ev=rhythm.options(self.before,self.ref);seed=next(s for s in range(64)if rhythm.sample(ev,controls(self.ref,100,s))[1]['changed'])
        code,_=bundle(Path(__file__).parent);ctl=controls(self.ref,100,seed)
        with TemporaryDirectory()as tmp:
            report=execute(code,self.upper,ctl,reconstruct(self.upper,ctl),Path(tmp)/'changed',timeout=45,purpose='local_group_rhythm_intervention')
            self.assertEqual(report['status'],'PASS',report)


if __name__=='__main__':unittest.main()
