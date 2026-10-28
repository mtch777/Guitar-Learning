from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from declared_degree_choices import catalog,options,apply,sample
from test_check_declared_allocation import fixture


class DeclaredDegreeChoiceTests(unittest.TestCase):
    def test_cli_reports_failure_as_nonzero(self):
        from unittest.mock import patch
        from run_declared_allocation_qa import main
        for status,expected in [('FAIL_RETAINED',1),('PASS_DECLARED_ALLOCATION_QA',0)]:
            with patch('run_declared_allocation_qa.run',return_value=dict(status=status)),patch('builtins.print'):
                self.assertEqual(main(['capture','output','freeze']),expected)
    def prepared(self):
        docs,expected,refs,donors=fixture();lower=extract_documents(docs)
        upper=strip_lower(analyze(lower,declared_chords=True));c=catalog(upper)
        target=next(u for u in c['units'] if u['member_refs']==refs)
        return lower,upper,c,target,extract_documents(expected)

    def test_observed_degrees_same_inverse_and_source_motion(self):
        before,upper,c,target,wanted=self.prepared();e=options(upper,target['id'],c)
        choices=[o for o in e['options'] if o['changed']]
        self.assertEqual(len(choices),1,e['rejected'])
        after=reconstruct(apply(upper,target,choices[0]['roles']),{'variation':0})
        self.assertEqual(after,wanted)
        self.assertEqual(choices[0]['motion']['status'],'PASS_OBSERVED_INCIDENT_MOTION')

    def test_control_release_zero_partial_full_does_not_force_difference(self):
        before,upper,c,target,wanted=self.prepared();e=options(upper,target['id'],c)
        controls=dict(voicing=0,register=0,target_ref=target['id'],seed=0,context_policy='declared_degree_allocation')
        self.assertEqual(reconstruct(upper,controls),before)
        outcomes=[]
        for strength in (0,50,100):
            result=[sample(e,dict(controls,voicing=strength,seed=i))[1] for i in range(1000)]
            released=sum(r['released'] for r in result);changed=sum(r['changed'] for r in result)
            outcomes.append((released,changed))
        self.assertEqual(outcomes[0],(0,0));self.assertTrue(450<outcomes[1][0]<550)
        self.assertEqual(outcomes[2][0],1000);self.assertTrue(0<outcomes[2][1]<1000)

    def test_donor_note_order_is_not_string_correspondence_and_width_is_locked(self):
        docs,expected,refs,_=fixture()
        for data in (docs,expected):
            data['track-0.json']['measures'][3]['voices'][0]['beats'][0]['notes'].reverse()
            for m in data['track-0.json']['measures']:
                for b in m['voices'][0]['beats']:b['chord']['width']=31.5
        upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=catalog(upper)
        target=next(u for u in c['units'] if u['member_refs']==refs);e=options(upper,target['id'],c)
        choice=next(o for o in e['options'] if o['changed'])
        self.assertEqual(reconstruct(apply(upper,target,choice['roles']),{'variation':0}),extract_documents(expected))

    def test_missing_paths_and_locked_parameters_refuse(self):
        docs,_,refs,_=fixture()
        for i in (11,13):docs['track-0.json']['measures'][i//4]['voices'][0]['beats'][i%4]['notes'][0]['fret']=9
        upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=catalog(upper)
        target=next(u for u in c['units'] if u['member_refs']==refs);e=options(upper,target['id'],c)
        self.assertFalse(any(o['changed'] for o in e['options']))
        self.assertTrue(any('NO_INDEPENDENT_SOURCE_' in o['reason'] for o in e['rejected']))
        with self.assertRaises(ValueError):reconstruct(upper,dict(voicing=100,register=1,target_ref=target['id'],seed=0,context_policy='declared_degree_allocation'))

    def test_actual_isolated_changed_reconstruction(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper,c,target,wanted=self.prepared();e=options(upper,target['id'],c)
        controls=dict(voicing=100,register=0,target_ref=target['id'],seed=0,context_policy='declared_degree_allocation')
        seed=next(i for i in range(1000) if sample(e,dict(controls,seed=i))[1]['changed'])
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute(code,upper,dict(controls,seed=seed),wanted,Path(tmp)/'changed',timeout=30,purpose='voicing_register_intervention')
            self.assertEqual(result['status'],'PASS',result)

    def test_earlier_pedal_refuses_and_unchanged_outside_uncertainty_remains_unknown(self):
        docs,_,refs,_=fixture();docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['sustainPedal']=True
        upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=catalog(upper)
        target=next(u for u in c['units'] if u['member_refs']==refs)
        self.assertIn('UNKNOWN_PEDAL_SOUNDING_END',target['reasons'])
        self.assertEqual(options(upper,target['id'],c)['status'],'REFUSED_TARGET')
        docs,_,refs,_=fixture();part=deepcopy(docs['track-0.json']);part['partId']=1
        for measure in part['measures']:
            for beat in measure['voices'][0]['beats']:
                beat['notes']=beat['notes'][:1];beat.pop('chord',None);beat['notes'][0]['vibrato']=True
        docs['track-1.json']=part
        docs['metadata.json']['tracks'].append(dict(instrumentId=26))
        upper=strip_lower(analyze(extract_documents(docs),declared_chords=True));c=catalog(upper)
        target=next(u for u in c['units'] if u['member_refs']==refs);e=options(upper,target['id'],c)
        changed=next(o for o in e['options'] if o['changed'])
        proof=changed['motion']['written_vertical_invariance']
        self.assertTrue(proof['unchanged_outside_uncertainty'])
        self.assertFalse(proof['acoustic_harmony_verified'])


if __name__=='__main__':unittest.main()
