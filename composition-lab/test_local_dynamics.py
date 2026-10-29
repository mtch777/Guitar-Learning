from copy import deepcopy
from pathlib import Path
import random,tempfile,unittest
import local_dynamics as d
import check_local_dynamics as independent
from test_check_local_dynamics import documents,facts,TARGET
from connected_tier2 import analyze,strip_lower,realize,reconstruct


def control(strength=100,seed=0,target=TARGET):
    return dict(context_policy=d.POLICY,dynamics=strength,target_ref=target,seed=seed)


class LocalDynamicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=facts(documents());cls.upper=strip_lower(analyze(cls.before))

    def test_inventory_and_choice_population_match_independent_raw_scanner(self):
        view=d.inventory(self.before);self.assertEqual(view,independent.inventory(self.before))
        for row in view['declarations']:
            evidence=d.options(self.before,row['fact_ref'],view)
            self.assertEqual(evidence['options'],independent.choices(self.before,row['fact_ref'])['options'])

    def test_note_and_beat_scope_use_same_inverse_and_preserve_outside_facts(self):
        for target in (TARGET,'track-0.json#/measures/0/voices/0/beats/1/notes/0/velocity'):
            for seed in range(8):
                edited,decision=d.intervene(self.upper,control(seed=seed,target=target));actual=realize(edited)
                donors=decision.get('chosen',{}).get('donor_refs',[])
                self.assertEqual(independent.check(self.before,actual,target,donors,decision)['issues'],[])
                self.assertEqual(reconstruct(self.upper,control(seed=seed,target=target)),actual)

    def test_actual_source_denied_zero_and_changed_workers(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            observed=[]
            for strength in (0,50,100):
                c=control(strength,seed=0);edited,decision=d.intervene(self.upper,c);expected=realize(edited)
                result=execute(code,self.upper,c,expected,Path(folder)/str(strength),timeout=30,purpose='local_dynamics_intervention')
                self.assertEqual(result['status'],'PASS',result);observed.append(decision['changed'])
            self.assertTrue(observed[-1])

    def test_zero_literal_lock_and_reference_free_released_choice(self):
        self.assertEqual(reconstruct(self.upper,control(0)),self.before)
        expected=[]
        for level in ('ppp','mf','ff','fff'):
            perturbed=d.apply(self.upper,TARGET,level);evidence=d.options(realize(perturbed),TARGET)
            expected.append([d.sample(evidence,control(100,seed))[0]['marking']for seed in range(100)])
        self.assertTrue(all(x==expected[0]for x in expected))

    def test_release_rates_are_measured_separately_from_realized_changes(self):
        evidence=d.options(self.before,TARGET)
        for strength in (0,50,100):
            decisions=[d.sample(evidence,control(strength,i))[1]for i in range(1000)]
            release_count=sum(x['released']for x in decisions)
            self.assertEqual(release_count,sum(random.Random(i).random()<strength/100 for i in range(1000)))
            self.assertLessEqual(sum(x['changed']for x in decisions),release_count)
        self.assertTrue(any(not x['changed']for x in decisions))

    def test_unknown_boundaries_rest_notes_and_nulls(self):
        for field,value in [('velocity','unrecognized'),('velocity',None),('velocity',0)]:
            doc=documents();doc['track-0.json']['measures'][0]['voices'][0]['beats'][2][field]=value
            lower=facts(doc);self.assertEqual(d.inventory(lower),independent.inventory(lower))
        doc=documents();doc['track-0.json']['measures'][0]['voices'][0]['beats'][2]['notes']=[dict(rest=True,velocity='unknown')]
        self.assertEqual(d.inventory(facts(doc)),independent.inventory(facts(doc)))

    def test_invalid_controls_and_unauthorized_fact_changes_are_refused(self):
        for key,value in [('dynamics',True),('dynamics',101),('dynamics',float('nan')),('seed',False)]:
            c=control();c[key]=value
            with self.assertRaises(ValueError):d.intervene(self.upper,c)
        c=control();c['voicing']=100
        with self.assertRaises(ValueError):d.intervene(self.upper,c)
        target=d.options(self.before,TARGET)['target'];after=deepcopy(self.before)
        next(r for r in after['facts']if r['slot']=='fret')['value']=9
        with self.assertRaisesRegex(ValueError,'Locked source'):d.verify_effect(self.before,after,target,'f')

    def test_no_source_alternative_does_not_invent_a_level(self):
        doc=documents()
        for m in doc['track-0.json']['measures']:
            for v in m['voices']:
                for b in v['beats']:
                    if 'velocity'in b:b['velocity']='f'
        lower=facts(doc);evidence=d.options(lower,TARGET)
        self.assertEqual(evidence['status'],'NO_ADMITTED_DYNAMIC_CHANGE')
        self.assertFalse(d.sample(evidence,control())[1]['changed'])


if __name__=='__main__':unittest.main()
