import copy,unittest
from test_corpus_composer import fixture,model_for
from corpus_composer import generate
from artist_form import arrange
from form_returns import apply,plan_returns


def case():
    report,raw=fixture();core,_=generate(model_for(report,raw),4,23)
    plan=[dict(start=0,length=2,identity=0),dict(start=2,length=2,identity=0)]
    return arrange(core,plan),plan,['harmony','melody','bass']


class ReturnTests(unittest.TestCase):
    def test_zero_preserves_equivalent_rational_timing_spellings(self):
        from fractions import Fraction as F
        score,plan,roles=case()
        for t in score['tracks']:
            for mi,m in enumerate(t['measures']):
                for v in m['voices']:
                    for e in v:
                        e['onset_q']=str(float(F(e['onset_q'])))
                        if mi>=2:
                            for field in ('local_onset_q','duration_q'):e[field]=str(float(F(e[field])))
        self.assertEqual(apply(score,plan,roles,{})[0],score)

    def test_zero_preserves_omitted_default_note_fields(self):
        score,plan,roles=case()
        for t in score['tracks']:
            for m in t['measures'][2:]:
                for v in m['voices']:
                    for e in v:
                        for n in e['notes']:n.pop('tie',None);n.pop('technique_tags',None)
        self.assertEqual(apply(score,plan,roles,{})[0],score)

    def test_return_can_reference_an_older_occurrence_not_only_the_latest(self):
        score,_,roles=case()
        plan=[dict(start=i,length=1,identity=0,return_lag=i) for i in range(4)]
        score=arrange(score,plan)
        actual,audit=apply(score,plan,roles,{})
        self.assertEqual(actual,score);self.assertEqual(len(audit['returns']),3)

    def test_zero_exact_and_new_material_reused_with_rational_clock(self):
        score,plan,roles=case();zero,audit=apply(score,plan,roles,{})
        self.assertEqual(zero,score);self.assertEqual(audit['changed_track_bars'],0)
        proposal=copy.deepcopy(score)
        for bar in (0,1):
            for e in proposal['tracks'][1]['measures'][bar]['voices'][0]:
                for n in e['notes']:n['fret']+=1;n['midi']+=1
        result,audit=apply(proposal,plan,roles,{'melody':100})
        for bar in (0,1):
            a=result['tracks'][1]['measures'][bar]['voices'][0]
            b=result['tracks'][1]['measures'][bar+2]['voices'][0]
            self.assertEqual([e['notes'] for e in a],[e['notes'] for e in b])
        self.assertEqual(audit['changed_track_bars'],2)
        self.assertEqual(result['tracks'][0],score['tracks'][0])

    def test_incompatible_zero_lock_and_intermediate_masks_rejected(self):
        score,plan,roles=case();score['tracks'][1]['measures'][2]['voices'][0][0]['notes'][0]['midi']+=1
        score['tracks'][1]['measures'][2]['voices'][0][0]['notes'][0]['fret']+=1
        with self.assertRaisesRegex(ValueError,'literal melody'):apply(score,plan,roles,{})
        with self.assertRaisesRegex(ValueError,'at0or100'):apply(score,plan,roles,{'melody':50})

    def test_invalid_plan_and_topology_rejected(self):
        score,plan,roles=case()
        bad=copy.deepcopy(plan);bad[1]['start']=3
        with self.assertRaises(ValueError):plan_returns(score,bad)
        bad=copy.deepcopy(plan);bad[1]['return_lag']=0
        with self.assertRaisesRegex(ValueError,'lag'):plan_returns(score,bad)
        score['tracks'][1]['measures'][2]['voices'][0][0]['notes']=[]
        with self.assertRaisesRegex(ValueError,'topology'):plan_returns(score,plan)


if __name__=='__main__':unittest.main()
