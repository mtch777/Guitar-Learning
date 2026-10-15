import unittest
from copy import deepcopy
from phrase_experiments import develop,audit,attacks,SPANS


def fixture():
    tracks=[]
    for ti in range(3):
        measures=[]
        for mi in range(16):
            pitch=60+(mi%3)*2 if ti==1 else 60
            e=dict(onset_q=str(mi*4),local_onset_q='0',duration_q='4',notes=[dict(midi=pitch,string=0,fret=pitch-40,tie=None,technique_tags=[])])
            measures.append(dict(number=mi+1,onset_q=str(mi*4),time_signature='4/4',voices=[[e]]))
        tracks.append(dict(index=ti,name=str(ti),tunings=[[40,45,50,55,59,64]],program=25,measures=measures))
    return dict(tracks=tracks)


class PhraseTests(unittest.TestCase):
    def test_factors_keep_accompaniment_and_timing_exact(self):
        base=fixture();frozen=deepcopy(base)
        for linked in (False,True):
            for endings in (False,True):
                result,plan=develop(base,linked,endings);report=audit(base,result)
                self.assertTrue(report['timing_and_note_counts_exact'])
                self.assertEqual(plan['phrase_end_bars'],[3,8,11,16])
                if endings:self.assertEqual(report['phrase_ends_in_accompaniment_pcs'],4)
        self.assertEqual(base,frozen)

    def test_baseline_is_unchanged_and_audit_detects_accompaniment_mutation(self):
        base=fixture();result,_=develop(base)
        self.assertEqual(result,base)
        result['tracks'][0]['measures'][0]['voices'][0][0]['duration_q']='2'
        with self.assertRaises(AssertionError):audit(base,result)

    def test_reject_wrong_form(self):
        base=fixture();base['tracks'][1]['measures'].pop()
        with self.assertRaises(ValueError):develop(base,True)


if __name__=='__main__':unittest.main()
