from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,realize
from test_dynamic_context import documents as dynamic_documents
import local_accents as accents

TARGET='event:93:0:1:0:1:0'

def documents():
    docs=dynamic_documents()
    for i,m in enumerate(docs['track-0.json']['measures']):
        beats=m['voices'][0]['beats'];beats[0]['velocity']='mf';del beats[1]['velocity']
        if i in(1,3):beats[1]['notes'][0]['accentuated']=1
        elif i==4:beats[1]['notes'][0]['accentuated']=0
    return docs

def controls(strength=100,seed=0):return dict(context_policy=accents.POLICY,accents=strength,target_ref=TARGET,seed=seed)

class LocalAccentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=extract_documents(documents());cls.upper=strip_lower(analyze(cls.before,note_accent_slots=True))

    def test_observed_absence_and_explicit_zero_are_separate(self):
        evidence=accents.options(self.before,TARGET)
        self.assertEqual([o['state']for o in evidence['options']],[{'kind':'absent'},{'kind':'explicit','value':0},{'kind':'explicit','value':1}])
        self.assertEqual(evidence['target']['context_key'],[0,0,'mf',[4,4],'1','1'])
        self.assertEqual(sum(len(o['donor_refs'])for o in evidence['options']),5)

    def test_every_target_coattack_is_excluded(self):
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'].append(dict(fret=4,string=0,accentuated=2))
        evidence=accents.options(extract_documents(docs),TARGET)
        self.assertTrue(all(o['sound_level']!=2 for o in evidence['observed_options']))

    def test_outcome_does_not_select_context_or_released_population(self):
        previous=None
        for value in (None,0,1,2):
            docs=documents();note=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]
            if value is not None:note['accentuated']=value
            evidence=accents.options(extract_documents(docs),TARGET);chosen,_=accents.sample(evidence,controls())
            current=(evidence['target']['context_key'],chosen['state'],chosen['donor_refs'])
            if previous is not None:self.assertEqual(current,previous)
            previous=current

    def test_zero_and_one_changed_state_preserve_every_other_fact(self):
        self.assertEqual(accents.intervene(self.upper,controls(0))[0],self.upper)
        for seed in range(32):
            edited,decision=accents.intervene(self.upper,controls(seed=seed))
            if decision['changed']and decision['chosen']['sound_level']==1:break
        else:self.fail('Fixture supported change not sampled')
        target=decision['evidence']['target'];after=realize(edited)
        self.assertEqual(accents.verify_effect(self.before,after,target['note_ref'],decision['chosen']['state'])['status'],'EXACT_SINGLE_NOTE_ACCENT_SCOPE')
        a=deepcopy(self.upper);a['owned_parameters']['optional_note_accents']=deepcopy(edited['owned_parameters']['optional_note_accents']);self.assertEqual(a,edited)
        corrupt=deepcopy(after);next(r for r in corrupt['facts']if r['id'].endswith('/fret'))['value']+=1
        with self.assertRaises(ValueError):accents.verify_effect(self.before,corrupt,target['note_ref'],decision['chosen']['state'])

    def test_noncreative_zero_is_not_used_as_an_extra_source_vote(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:m['voices'][0]['beats'][1]['notes'][0].pop('accentuated',None)
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['accentuated']=0
        evidence=accents.options(extract_documents(docs),TARGET)
        self.assertEqual(len(evidence['observed_options']),2);self.assertEqual(evidence['options'],[])

    def test_missing_context_and_technique_interactions_are_refused(self):
        for kind in ('bend','duration','dynamic'):
            docs=documents();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]
            if kind=='bend':beat['notes'][0]['bend']=[{'position':0,'value':0}]
            elif kind=='duration':beat['duration']=[1,8]
            else:beat['velocity']='unknown'
            evidence=accents.options(extract_documents(docs),TARGET)
            self.assertEqual(evidence['options'],[],kind)

    def test_actual_isolated_policy_executes_from_upper_only(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            for level in (0,50,100):
                c=controls(level);edited,_=accents.intervene(self.upper,c)
                report=execute(code,self.upper,c,realize(edited),Path(temp)/str(level),timeout=30,purpose='local_accents_intervention')
                self.assertEqual(report['status'],'PASS',report)

if __name__=='__main__':unittest.main()
