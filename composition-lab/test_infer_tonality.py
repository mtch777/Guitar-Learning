"""Regression tests for actual harmony inference, including conflicting bass."""
import unittest
from collections import Counter
from harmonic_inference import chords_for, analyze_measure, tonal_candidates, infer_score

class HarmonicInferenceTests(unittest.TestCase):
    def measure(self,notes,bass=None):
        return {'measure':1,'melody':Counter({x:1 for x in notes}),
                'bass':Counter({bass:2}) if bass is not None else Counter(),
                'clusters':[{'onset':0,'duration':1,'notes':tuple(notes)}] if len(notes)>1 else [],
                'ending':notes[-1] if notes else None}
    def test_root_agreement(self):
        candidates=chords_for([2,5,9],2)
        self.assertTrue(any(x['quality']=='minor' and x['root']==2 and x['bass_relation']=='root' for x in candidates))
    def test_inversion(self):
        candidates=chords_for([0,4,7],4)
        self.assertTrue(any(x['quality']=='major' and x['root']==0 and x['bass_relation']=='inversion' for x in candidates))
    def test_nonchord_bass(self):
        candidates=chords_for([0,4,7],2)
        self.assertTrue(any(x['quality']=='major' and x['root']==0 and x['bass_relation']=='pedal_or_nonchord' for x in candidates))
    def test_melody_only_cannot_claim_chord(self):
        self.assertEqual(analyze_measure(self.measure([0]))['label'],'no_explicit_chord')
    def test_empty_does_not_claim_key(self):
        self.assertEqual(tonal_candidates([self.measure([])])['status'],'insufficient_evidence')
    def test_incomplete_scale_alternatives(self):
        result=tonal_candidates([self.measure([0,4,7],0)])
        self.assertGreater(len(result['ranked']),1)
        self.assertNotIn('confidence',result['ranked'][0])
    def test_bad_settings(self):
        with self.assertRaises(ValueError):tonal_candidates([self.measure([0,4])],weights={'invalid':5})
    def test_duplicate_guitars(self):
        bar=[(0,0,.5,(60,64,67))]
        score={'song':'synthetic','measures':1,'sections':[],'tracks':[
          {'name':'Rhythm Guitar A','measures':[bar]},
          {'name':'Rhythm Guitar B','measures':[bar]}]}
        self.assertEqual(len(infer_score(score)['excluded_exact_doubles']),1)
if __name__=='__main__':unittest.main()
