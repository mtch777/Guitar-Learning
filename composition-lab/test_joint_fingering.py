"""Joint control contracts; fixture geometry is not a playability verdict."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize,reconstruct
from voicing_register import inventory,intervene,empirical_options


def documents():
    tuning=[64,59,55,50,45,40]
    def measure(pitches,strings):
        return dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[
            dict(string=s,fret=p-tuning[s]) for p,s in zip(pitches,strings)])])])
    return {'metadata.json':dict(songId=82,revisionId=1,artist='Fixture',title='Joint choices',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=82,revisionId=1,partId=0,instrumentId=25,tuning=tuning,frets=36,measures=[
            measure([64,67,71],[0,1,2]),measure([64,67,71],[1,2,3]),measure([76,79,83],[0,1,2])])}


class JointFingeringTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower));catalog=inventory(lower,'joint_source_fingering')
        target=catalog['units'][0]['id']
        return lower,upper,catalog,dict(voicing=0,register=0,physical=100,target_ref=target,seed=9427,context_policy='joint_source_fingering')

    def test_physical_only_preserves_every_pitch_and_other_fact(self):
        lower,upper,catalog,controls=self.fixture();edited,decision=intervene(upper,controls);after=realize(edited)
        self.assertTrue(decision['changed']);self.assertEqual(decision['original']['anchor'],decision['chosen']['realization']['anchor'])
        a=project_documents(lower);b=project_documents(after)
        for i,note in enumerate(b['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']):
            old=a['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][i]
            self.assertEqual(a['track-0.json']['tuning'][old['string']]+old['fret'],b['track-0.json']['tuning'][note['string']]+note['fret'])
        b['track-0.json']['measures'][0]=a['track-0.json']['measures'][0]
        self.assertEqual(a,b)

    def test_all_zero_exact_and_fixed_strings_lock(self):
        lower,upper,catalog,controls=self.fixture()
        self.assertEqual(reconstruct(upper,dict(controls,physical=0)),lower)
        for seed in range(10):
            edited,decision=intervene(upper,dict(controls,physical=0,voicing=100,register=100,seed=seed))
            after=project_documents(realize(edited))
            self.assertEqual([n['string'] for n in after['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes']],[0,1,2])

    def test_joint_can_change_pitch_and_strings_without_mutating_input(self):
        lower,upper,catalog,controls=self.fixture();saved=deepcopy(upper)
        results=[intervene(upper,dict(controls,voicing=100,register=100,seed=s))[1] for s in range(20)]
        self.assertTrue(any(r['chosen']['realization']['anchor']!=r['original']['anchor'] for r in results))
        self.assertEqual(upper,saved)

    def test_actual_stripped_worker_nonzero(self):
        lower,upper,catalog,controls=self.fixture();expected=reconstruct(upper,controls)
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:
            result=execute(code,upper,controls,expected,Path(temp)/'worker',timeout=30,purpose='voicing_register_intervention')
        self.assertEqual(result['status'],'PASS',result)

    def test_explicit_physical_scope_required(self):
        _,upper,_,controls=self.fixture()
        for bad in (dict(controls,physical=True),dict(controls,physical=101),{k:v for k,v in controls.items() if k!='physical'}):
            with self.assertRaises(ValueError):intervene(upper,bad)

    def test_new_string_cannot_collide_with_sustaining_other_voice(self):
        docs=documents()
        for measure in docs['track-0.json']['measures']:
            measure['voices'].append(dict(beats=[dict(duration=[1,4],rest=True,notes=[]),
                dict(duration=[3,4],notes=[dict(string=3,fret=20)])]))
        catalog=inventory(extract_documents(docs),'joint_source_fingering')
        target=catalog['units'][0]
        self.assertEqual(target['occupied_strings'],[3])
        evidence=empirical_options(catalog,target['id'],'joint_source_fingering')
        self.assertTrue(any(r['reason']=='OVERLAPPING_STRING_OCCUPIED' for r in evidence['rejected']))
        self.assertFalse(any(3 in o['realization']['strings'] for o in evidence['options']))

    def test_source_anomaly_preserved_but_not_used_as_safe_donor(self):
        docs=documents();docs['track-0.json']['frets']=15
        lower=extract_documents(docs);upper=strip_lower(analyze(lower))
        self.assertEqual(reconstruct(upper,dict(variation=0)),lower)
        catalog=inventory(lower,'joint_source_fingering');target=catalog['units'][0]
        evidence=empirical_options(catalog,target['id'],'joint_source_fingering')
        self.assertFalse(evidence['options'])
        self.assertTrue(any(r['reason']=='INVALID_OBSERVED_FRET' for r in evidence['rejected']))

    def test_full_release_allows_observed_coincidence(self):
        docs=documents();docs['track-0.json']['measures'].append(deepcopy(docs['track-0.json']['measures'][0]))
        lower=extract_documents(docs);upper=strip_lower(analyze(lower));catalog=inventory(lower,'joint_source_fingering')
        controls=dict(voicing=100,register=100,physical=100,target_ref=catalog['units'][0]['id'],seed=0,context_policy='joint_source_fingering')
        draws=[intervene(upper,dict(controls,seed=s))[1] for s in range(20)]
        self.assertTrue(any(d['changed'] for d in draws))
        self.assertTrue(any(d['status']=='OBSERVED_COINCIDENCE' for d in draws))


if __name__=='__main__':unittest.main()
