import copy,unittest
from artist_form import fit,evaluate,plan,arrange,probability,observations,full_plan,select_length_weight
from test_corpus_composer import fixture,model_for
from corpus_composer import generate

def forms():
    return [dict(song_id=i,family='f'+str(i),artist='Artist',partition='development' if i<3 else 'held_out',flagged=False,
        sections=[dict(length=n,return_lag=lag,known_label=True) for n,lag in [(2,0),(4,0),(2,2),(4,2)]]) for i in (1,2,3)]

class ArtistFormTests(unittest.TestCase):
    def test_unsupported_content_is_not_observed_novel(self):
        data=forms();a=fit(data,'Artist');other=copy.deepcopy(data)
        for f in other:
            f['sections'].append(dict(length=8,return_lag=0,content_identity_supported=False,known_label=False))
        b=fit(other,'Artist');self.assertEqual(a['tables']['return_lag'],b['tables']['return_lag'])

    def test_all_unsupported_still_fits_lengths_but_cannot_sample_returns(self):
        data=forms()
        for f in data:
            for s in f['sections']:s['content_identity_supported']=False
        m=fit(data,'Artist')
        for sampler in (lambda:plan(m,32),lambda:full_plan(m)):
            with self.assertRaisesRegex(ValueError,'No supported return evidence'):sampler()
    def test_full_horizon_and_development_selection(self):
        m=select_length_weight(forms(),'Artist');self.assertIn(m['length_weight'],(0,.25,.5,.75,1))
        sections=full_plan(m,19);self.assertEqual(len(sections),4);self.assertEqual(sections,full_plan(m,19))
        other=copy.deepcopy(forms());other[-1]['sections']=[dict(length=99,return_lag=0)]
        self.assertEqual(m,select_length_weight(other,'Artist'))
    def test_plan_coverage_and_normalized_unknown_mass(self):
        m=fit(forms(),'Artist');self.assertEqual(plan(m,32),plan(m,32));self.assertEqual(sum(s['length'] for s in plan(m,32)),32)
        for prev in (None,2,4,99):self.assertAlmostEqual(sum(probability(m,n,prev) for n in [2,4,999]),1)
        self.assertEqual(len(evaluate(m,forms())['by_song']),1)

    def test_recurrence_has_real_synchronized_content(self):
        report,raw=fixture();core,_=generate(model_for(report,raw),8,23);saved=copy.deepcopy(core)
        sections=[dict(start=0,length=2,identity=0),dict(start=2,length=2,identity=1),dict(start=4,length=2,identity=0),dict(start=6,length=2,identity=2)]
        out=arrange(core,sections);self.assertEqual(core,saved)
        for t in out['tracks']:
            for a,b in zip(t['measures'][:2],t['measures'][4:6]):
                self.assertEqual([[e['notes'] for e in v] for v in a['voices']],[[e['notes'] for e in v] for v in b['voices']])

    def test_missing_markers_do_not_invent_returns(self):
        report,raw=fixture();composer=model_for(report,raw);track=report['songs'][0]['tracks'][0]
        track['sections']=[dict(start_q='0',end_q='4',label=None),dict(start_q='4',end_q='8',label=None)]
        obs,_=observations(report,composer);self.assertTrue(all(s['return_lag']==0 for s in obs[0]['sections']))

    def test_leakage_and_invalid_plan(self):
        m=fit(forms(),'Artist');held=forms();held[-1]['family']='f1'
        with self.assertRaises(ValueError):evaluate(m,held)
        with self.assertRaises(ValueError):plan(m,0)

if __name__=='__main__':unittest.main()
