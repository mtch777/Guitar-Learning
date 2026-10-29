from copy import deepcopy
from pathlib import Path
import random,tempfile,unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
import dynamic_context as context
import local_dynamics

TARGET='track-0.json#/measures/0/voices/0/beats/1/velocity'


def documents():
    measures=[]
    for mark in ('mp','mf','mp','mf','mf','mp'):
        beats=[dict(duration=[1,4],notes=[dict(string=0,fret=0)])for _ in range(4)]
        beats[0]['velocity']='f';beats[1]['velocity']=mark
        measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=93,revisionId=1,title='Context fixture',artist='Synthetic',tracks=[dict(instrumentId=25)]),
        'track-0.json':dict(songId=93,revisionId=1,partId=0,instrumentId=25,tuning=[60],measures=measures)}


def controls(strength=100,seed=0):
    return dict(context_policy=context.POLICY,dynamics=strength,target_ref=TARGET,seed=seed)


class DynamicContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=extract_documents(documents());cls.upper=strip_lower(analyze(cls.before))

    def test_incoming_state_and_disjoint_full_dependencies(self):
        evidence=context.options(self.before,TARGET);c=evidence['context']
        self.assertEqual(c['incoming_marking'],'f');self.assertEqual(c['position_q'],'1')
        self.assertEqual(c['context_key'],[0,0,'beat','f',4,'1','1'])
        self.assertEqual([o['marking']for o in evidence['options']],['mf','mp'])
        self.assertEqual(len(evidence['witness_pair']),2)
        self.assertIn(dict(fact_ref=TARGET,reason='SELF_DECLARATION'),evidence['excluded'])
        self.assertTrue(any(r['reason']=='REUSED_TARGET_DEPENDENCY'for r in evidence['excluded']))
        rows={r['fact_ref']:r for r in context.inventory(self.before)['contexts']}
        for o in evidence['options']:
            for ref in o['donor_refs']:self.assertFalse(set(c['dependency_refs'])&set(rows[ref]['dependency_refs']))
        a,b=(rows[r]for r in evidence['witness_pair']);self.assertNotEqual(a['outcome_marking'],b['outcome_marking'])
        self.assertFalse(set(a['dependency_refs'])&set(b['dependency_refs']))

    def test_target_outcome_cannot_steer_context_or_released_choice(self):
        previous=None
        for mark in ('ppp','mp','f','fff'):
            edited=local_dynamics.apply(self.upper,TARGET,mark)
            e=context.options(realize(edited),TARGET)
            observed=(e['context']['context_key'],[(o['marking'],o['donor_refs'])for o in e['options']],
                [context.sample(e,controls(seed=i))[0]['marking']for i in range(64)])
            if previous is not None:self.assertEqual(previous,observed)
            previous=observed

    def test_same_owner_inverse_and_literal_zero(self):
        self.assertEqual(reconstruct(self.upper,controls(0)),self.before)
        for seed in range(8):
            edited,decision=context.intervene(self.upper,controls(seed=seed));actual=realize(edited)
            self.assertEqual(reconstruct(self.upper,controls(seed=seed)),actual)
            if decision['chosen']:
                local_dynamics.verify_effect(self.before,actual,decision['evidence']['target'],decision['chosen']['marking'])

    def test_actual_isolated_worker_has_no_source_or_lower_payload(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            for strength in (0,50,100):
                c=controls(strength,seed=1);expected=reconstruct(self.upper,c)
                result=execute(code,self.upper,c,expected,Path(temp)/str(strength),timeout=30,purpose='local_dynamics_intervention')
                self.assertEqual(result['status'],'PASS',result)

    def test_measured_release_uses_existing_probability_not_change_distance(self):
        e=context.options(self.before,TARGET)
        for strength in (0,50,100):
            results=[context.sample(e,controls(strength,i))[1]for i in range(300)]
            self.assertEqual(sum(r['released']for r in results),sum(random.Random(i).random()<strength/100 for i in range(300)))
            self.assertLessEqual(sum(r['changed']for r in results),sum(r['released']for r in results))

    def test_single_level_evidence_is_retained_but_not_a_fabricated_choice(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:m['voices'][0]['beats'][1]['velocity']='mp'
        evidence=context.options(extract_documents(docs),TARGET)
        self.assertEqual(len(evidence['observed_options']),1);self.assertEqual(evidence['options'],[])
        self.assertEqual(evidence['status'],'NO_INDEPENDENT_CONTEXTUAL_MULTI_CHOICE')
        chosen,decision=context.sample(evidence,controls());self.assertIsNone(chosen);self.assertFalse(decision['changed'])

    def test_unknown_incoming_and_grace_refuse_context(self):
        for kind in ('unknown','grace'):
            docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
            if kind=='unknown':beats[0]['velocity']='mystery'
            else:beats[1]['graceNote']=True
            evidence=context.options(extract_documents(docs),TARGET)
            self.assertEqual(evidence['options'],[])
            self.assertIn('UNKNOWN_INCOMING_DYNAMIC'if kind=='unknown'else'GRACE_SOURCE_CONTEXT',evidence['context']['reasons'])

    def test_default_and_conflicted_meter_are_not_source_evidence(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:del m['signature']
        with self.assertRaisesRegex(ValueError,'Missing source meter'):
            context.options(extract_documents(docs),TARGET)
        docs['track-0.json']['measures'][0]['signature']=[4,4]
        known=context.options(extract_documents(docs),TARGET)
        self.assertNotIn('UNKNOWN_SOURCE_METER',known['context']['reasons'])
        self.assertEqual(known['context']['meter_source_refs'],['track-0.json#/measures/0/signature'])
        docs['track-1.json']=deepcopy(docs['track-0.json']);docs['track-1.json']['partId']=1
        docs['metadata.json']['tracks'].append(dict(instrumentId=25))
        docs['track-1.json']['measures'][0]['signature']=[3,4]
        docs['track-0.json']['measures'][2]['signature']=[4,4]
        with self.assertRaisesRegex(ValueError,'Conflicting source meter'):
            context.inventory(extract_documents(docs))


if __name__=='__main__':unittest.main()
