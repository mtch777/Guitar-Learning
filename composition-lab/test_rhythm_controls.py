import copy,unittest
from test_corpus_composer import fixture,model_for
from corpus_composer import generate
from rhythm_controls import apply,locked_context,propose

class RhythmControlTests(unittest.TestCase):
    def setup(self):
        report,raw=fixture();model=model_for(report,raw);score,_=generate(model,4,23)
        for fs in model['parts'].values():
            for records in fs.values():
                for p in records:
                    for e,d in zip(p['events'],('1/2','3/2','1/2','3/2')):e['duration_q']=d
        return model,score,['harmony','melody','bass']

    def test_zero_literal_and_other_dimensions_locked(self):
        model,score,roles=self.setup();out,a=apply(score,{},roles,0);self.assertEqual(score,out)
        out,a=apply(score,model,roles,100);self.assertTrue(any(d['changed'] for d in a['units']))
        self.assertEqual([n for t in score['tracks'] for m in t['measures'] for v in m['voices'] for e in v for n in e['notes']],
                         [n for t in out['tracks'] for m in t['measures'] for v in m['voices'] for e in v for n in e['notes']])

    def test_100_hides_reference_timing(self):
        model,score,roles=self.setup();perturbed=copy.deepcopy(score)
        for t in perturbed['tracks']:
            for m in t['measures']:
                cursor=0
                for e,d in zip(m['voices'][0],('1/2','3/2','1/2','3/2')):
                    from fractions import Fraction as F
                    e.update(duration_q=d,local_onset_q=str(cursor),onset_q=str(F(m['onset_q'])+cursor));cursor+=F(d)
        self.assertEqual(locked_context(score,roles),locked_context(perturbed,roles))
        self.assertEqual(apply(score,model,roles,100)[0],apply(perturbed,model,roles,100)[0])

    def test_incompatible_support_fails_closed(self):
        model,score,roles=self.setup();model['parts']['harmony']={}
        with self.assertRaises(ValueError):apply(score,model,roles,100)

if __name__=='__main__':unittest.main()
