from copy import deepcopy
import unittest
from source_fact_tier1 import extract_documents
from check_dynamic_context import Oracle,POLICY

TARGET='track-0.json#/measures/0/voices/0/beats/1/velocity'
def documents(bars=8,split=False):
    measures=[]
    for mi in range(bars):
        durations=[[1,4]]*4;at=1
        if split and mi==5:durations=[[1,8],[1,8],[1,4],[1,4],[1,4]];at=2
        beats=[dict(duration=d,notes=[dict(string=0,fret=0)])for d in durations]
        beats[0]['velocity']='f';beats[at]['velocity']='mp'if mi%2==0 else'mf';measures.append(dict(signature=[4,4],voices=[dict(beats=beats)]))
    return {'metadata.json':dict(songId=94,revisionId=1,title='Source transitions',artist='Authored',tracks=[dict(instrumentId=25)]),'track-0.json':dict(songId=94,revisionId=1,partId=0,instrumentId=25,tuning=[60],measures=measures)}
def facts(d):return extract_documents(d)
def modified(d,marking):
    d=deepcopy(d);d['track-0.json']['measures'][0]['voices'][0]['beats'][1]['velocity']=marking;return facts(d)
def controls(seed=0,strength=100):return dict(context_policy=POLICY,dynamics=strength,target_ref=TARGET,seed=seed)

class IndependentDynamicContextTests(unittest.TestCase):
 def test_complete_conditional_source_population_and_pair(self):
    oracle=Oracle(facts(documents()));e=oracle.options(TARGET)
    self.assertEqual(e['status'],'CONTEXT_SUPPORTED_DYNAMIC_CHOICES');self.assertEqual({o['marking']for o in e['options']},{'mp','mf'})
    self.assertEqual(e['context']['context_key'],[0,0,'beat','f',4,'1','1'])
    self.assertNotIn(TARGET,{r for o in e['options']for r in o['donor_refs']})
    contexts={c['fact_ref']:c for c in oracle.inventory()['contexts']};a,b=map(contexts.get,e['witness_pair']);self.assertNotEqual(a['outcome_marking'],b['outcome_marking']);self.assertFalse(set(a['dependency_refs'])&set(b['dependency_refs']))
 def test_missing_incoming_and_dependent_only_levels_keep_no_choice(self):
    no=Oracle(facts(documents(4)));e=no.options(TARGET)
    self.assertEqual(len(e['observed_options']),2);self.assertEqual(e['options'],[]);self.assertEqual(e['status'],'NO_INDEPENDENT_CONTEXTUAL_MULTI_CHOICE')
    initial=no.options('track-0.json#/measures/0/voices/0/beats/0/velocity');self.assertEqual(initial['status'],'NO_SUPPORTED_DYNAMIC_CONTEXT');self.assertIn('MISSING_INCOMING_DYNAMIC',initial['context']['reasons'])
    result=no.check(facts(documents(4)),TARGET,[],dict(status='NO_ADMITTED_CHOICE',released=True,changed=False));self.assertEqual(result['issues'],[])
 def test_target_outcome_does_not_change_context_or_donor_votes(self):
    d=documents();a=Oracle(facts(d)).options(TARGET);b=Oracle(modified(d,'f')).options(TARGET)
    self.assertEqual(a['context']['context_key'],b['context']['context_key'])
    identity=lambda e:[(o['marking'],o['donor_refs'])for o in e['options']]
    self.assertEqual(identity(a),identity(b));self.assertEqual(a['witness_pair'],b['witness_pair'])
 def test_raw_fraction_position_matches_different_source_beat_indices(self):
    e=Oracle(facts(documents(split=True))).options(TARGET)
    self.assertIn('track-0.json#/measures/5/voices/0/beats/2/velocity',{r for o in e['options']for r in o['donor_refs']})
 def test_strict_complete_options_and_corruptions(self):
    oracle=Oracle(facts(documents()));e=oracle.options(TARGET);self.assertEqual(oracle.check_options(TARGET,e)['issues'],[])
    for mutate in [lambda x:x['witness_pair'].clear(),lambda x:x['context']['context_key'].__setitem__(-1,'0'),lambda x:x['options'][0]['donor_refs'].append(TARGET),lambda x:x['observed_options'].pop()]:
        bad=deepcopy(e);mutate(bad);self.assertEqual(oracle.check_options(TARGET,bad)['status'],'FAIL')
 def test_actual_raw_effect_check_and_outside_corruption(self):
    d=documents();before=facts(d);oracle=Oracle(before);e=oracle.options(TARGET);o=next(o for o in e['options']if o['marking']=='mf');decision=dict(released=True,changed=True,chosen=o,evidence=e);after=modified(d,'mf')
    self.assertEqual(oracle.check(after,TARGET,o['donor_refs'],decision)['issues'],[])
    wrong=deepcopy(after);next(f for f in wrong['facts']if f['id'].endswith('/notes/0/fret'))['value']=1
    self.assertEqual(oracle.check(wrong,TARGET,o['donor_refs'],decision)['status'],'FAIL')
    self.assertEqual(oracle.check(after,TARGET,[],decision)['status'],'FAIL')
 def test_independent_rng_draws_and_reference_only_changed_flag(self):
    from dynamic_context import sample
    oracle=Oracle(facts(documents()));e=oracle.options(TARGET)
    for strength in (0,50,100):
        for seed in range(32):
            c=controls(seed,strength);chosen,decision=sample(e,c);r=oracle.check_sample(TARGET,c,chosen,decision);self.assertEqual(r['issues'],[],r)
    chosen,decision=sample(e,controls());bad=deepcopy(decision);bad['changed']=not bad['changed'];self.assertEqual(oracle.check_sample(TARGET,controls(),chosen,bad)['status'],'FAIL')
 def test_observed_coincidence_and_unreleased_change_are_distinct(self):
    d=documents();before=facts(d);oracle=Oracle(before);o=next(o for o in oracle.options(TARGET)['options']if o['marking']=='mp')
    self.assertEqual(oracle.check(before,TARGET,o['donor_refs'],dict(released=True,changed=False,chosen=o))['issues'],[])
    changed=next(o for o in oracle.options(TARGET)['options']if o['marking']=='mf')
    self.assertEqual(oracle.check(modified(d,'mf'),TARGET,changed['donor_refs'],dict(released=False,changed=True,chosen=changed))['status'],'FAIL')
 def test_meter_provenance_carries_without_becoming_dependency_or_key(self):
    d=documents()
    for m in d['track-0.json']['measures'][1:]:m.pop('signature')
    oracle=Oracle(facts(d));view=oracle.inventory();e=oracle.options(TARGET)
    self.assertTrue(e['options']);ref='track-0.json#/measures/0/signature'
    for c in view['contexts']:
        self.assertEqual(c['meter_source_refs'],[ref]);self.assertNotIn(ref,c['dependency_refs']);self.assertNotIn(ref,c['context_key']or[])
 def test_missing_or_conflicting_meter_is_hard_refused_by_existing_source_guard(self):
    d=documents()
    for m in d['track-0.json']['measures']:m.pop('signature')
    with self.assertRaises(ValueError):Oracle(facts(d))
    d=documents();other=deepcopy(d['track-0.json']);other['partId']=1;other['measures'][1]['signature']=[3,4];d['track-1.json']=other;d['metadata.json']['tracks'].append(dict(instrumentId=25))
    with self.assertRaises(ValueError):Oracle(facts(d))
if __name__=='__main__':unittest.main()
