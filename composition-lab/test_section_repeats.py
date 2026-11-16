import unittest, copy
from section_repeats import build_bar_features, analyze_repeats, compare_bars

C=[{'part_id':1,'instrument_id':25}]
def song(patterns, widths=None):
    bars=[];notes=[];t=0
    for i,pat in enumerate(patterns):
        d=widths[i] if widths else 4
        bars.append(dict(bar=i+1,start_q=str(t),span_q=str(d)))
        for j,p in enumerate(pat):notes.append(dict(part_id=1,start_q=str(t+j),end_q=str(t+j+1),pitch=p,attack=True))
        t+=d
    return build_bar_features(bars,notes,C)
A=[40,43,47,42];B=[42,48,43,50];D=[55,53,51,49];E=[60,57,54,50];F=[46,51,57,63]
class RepeatTests(unittest.TestCase):
    def test_three_bar_return(self):
        r=analyze_repeats(song([A,B,D,E,F,A,B,D]))
        self.assertTrue(any(c['a_bars']==[1,2,3]and c['b_bars']==[6,7,8]for c in r['candidates']))
    def test_five_bar_return(self):
        r=analyze_repeats(song([A,B,D,E,F,[80],A,B,D,E,F]))
        self.assertTrue(any(c['length_bars']==5 for c in r['candidates']))
    def test_silence(self):self.assertEqual(analyze_repeats(song([[],[],[]]))['candidates'],[])
    def test_order_matters(self):
        a,b=song([A,list(reversed(A))]);r=compare_bars(a,b)
        self.assertLess(r['features']['pitch'],1);self.assertLess(r['features']['contour'],1)
    def test_one_bar_loop_not_sections(self):
        r=analyze_repeats(song([A]*16));self.assertTrue(r['candidates'])
        self.assertTrue(all(c['interpretation']=='repeating_motif_or_loop'for c in r['candidates']))
    def test_missing_pitch(self):
        a,b=song([A,[None]*4]);r=compare_bars(a,b)
        self.assertIsNone(r['features']['pitch']);self.assertLess(r['available_weight'],1)
    def test_no_mutation(self):
        f=song([A,B,A,B]);before=copy.deepcopy(f);analyze_repeats(f);self.assertEqual(before,f)
    def test_odd_meter(self):
        a,b=song([[40],[40]],[3,4]);self.assertEqual(compare_bars(a,b)['meter_similarity'],.75)
    def test_validation(self):
        with self.assertRaises(ValueError):analyze_repeats([],threshold=2)
        with self.assertRaises(ValueError):build_bar_features([dict(bar=1,start_q='0',span_q='0')],[],C)
    def test_sustain_vs_attack(self):
        bars=[dict(bar=1,start_q='0',span_q='4'),dict(bar=2,start_q='4',span_q='4')]
        f=build_bar_features(bars,[dict(part_id=1,start_q='0',end_q='8',pitch=40,attack=True)],C)
        self.assertEqual(f[0]['attack_count'],1);self.assertEqual(f[1]['attack_count'],0)
        r=compare_bars(*f);self.assertEqual(r['features']['rhythm'],0);self.assertLess(r['score'],1)
    def test_no_overlap(self):
        for c in analyze_repeats(song([A]*10))['candidates']:self.assertLessEqual(c['a_end'],c['b_start'])
    def test_added_channel(self):
        b=[dict(bar=i+1,start_q=str(i*4),span_q='4')for i in range(2)]
        n=[dict(part_id=1,start_q=str(i*4),end_q=str(i*4+1),pitch=40)for i in range(2)]+[dict(part_id=2,start_q='4',end_q='5',pitch=60)]
        a,z=build_bar_features(b,n,C+[dict(part_id=2,instrument_id=25)])
        r=compare_bars(a,z);self.assertEqual(r['features']['pitch'],1);self.assertLess(r['features']['arrangement'],1)
    def test_aba_not_two_cycles(self):
        r=analyze_repeats(song([A,B,A,F,A,B,A]))
        c=next(c for c in r['candidates'] if c['a_bars']==[1,2,3] and c['b_bars']==[5,6,7])
        self.assertIsNone(c['internal_period_bars'])
    def test_exact_is_not_just_score(self):
        a,b=song([[None]*4,[None]*4]);r=compare_bars(a,b)
        self.assertEqual(r['score'],1);self.assertFalse(r['exact_observed_match'])
        self.assertEqual(analyze_repeats([a,b])['candidates'][0]['evidence_scope'],'rhythm_only_or_partial_pitch')
    def test_contour_does_not_claim_transposition(self):
        a,b=song([A,[p+3 for p in A]]);r=compare_bars(a,b)
        self.assertEqual(r['features']['contour'],1)
        self.assertLess(r['features']['pitch'],1);self.assertFalse(r['exact_observed_match'])
    def test_partial_channel_coverage(self):
        a,b=song([A,A]);b['pitch']['2']={'0|1|60':1}
        r=compare_bars(a,b);self.assertEqual(r['channel_coverage']['pitch'],.5)
    def test_changed_ending_is_visible(self):
        f=song([A,B,D,F,A,B,[55,53,51,70]])
        r=analyze_repeats(f)
        c=next(c for c in r['candidates'] if c['a_start']==0 and c['b_start']==4)
        self.assertTrue(c['nonexact_bar_offsets'] or c['ending_variation_alternative'])
    def test_mixed_harmony_basis(self):
        a,b=song([A,A]);b['harmony_basis']='candidate_root_weights'
        self.assertIsNone(compare_bars(a,b)['features']['harmony'])
    def test_same_accompaniment_different_lead(self):
        a,b=song([A,A]);a['pitch']['lead']={'0|4|60':1};b['pitch']['lead']={'0|4|65':1}
        a['contour']['lead']={'0|4|0':1};b['contour']['lead']={'0|4|0':1}
        r=compare_bars(a,b);self.assertEqual(r['features']['pitch'],.5)
        self.assertFalse(r['exact_observed_match']);self.assertLess(r['score'],1)
if __name__=='__main__':unittest.main()
