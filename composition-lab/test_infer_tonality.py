import unittest
from collections import Counter
from infer_tonality import Settings, chord_hypotheses, candidate_evidence, collect, infer

class TonalityTests(unittest.TestCase):
    def test_root_agreement(self):
        matches=chord_hypotheses([62,65,69],bass=38)
        self.assertEqual(matches[0]['quality'],'minor')
        self.assertEqual(matches[0]['root'],2)
        self.assertEqual(matches[0]['bass_relation'],'root')
    def test_inversion_instead_of_false_root(self):
        matches=chord_hypotheses([60,64,67],bass=40)
        self.assertTrue(any(c['root']==0 and c['quality']=='major' and c['bass_relation']=='inversion' for c in matches))
    def test_disagreement_is_not_rejected(self):
        matches=chord_hypotheses([60,64,67],bass=38)
        self.assertTrue(any(c['root']==0 and c['quality']=='major' and c['bass_relation']=='nonchord_or_pedal' for c in matches))
    def test_no_harmony(self):
        m=[{'number':1,'notes':Counter(),'bass':Counter(),'chords':[],'melody_last':None}]
        self.assertEqual(candidate_evidence(m,Settings())['status'],'insufficient_evidence')
    def test_mode_ambiguity_not_forced(self):
        m=[{'number':1,'notes':Counter({0:3,2:2,4:2,5:2,7:3,9:2,11:2}),
            'bass':Counter({0:4}),'chords':[],'melody_last':0}]
        result=candidate_evidence(m,Settings(),[1])
        self.assertIn(result['status'],('mode_ambiguous','tonic_ambiguous','tentative_tonic_and_mode'))
        self.assertGreaterEqual(len(result['ranked']),2)
    def test_custom_weights(self):
        self.assertEqual(Settings.load({'bass':4}).bass,4)
        with self.assertRaises(ValueError):Settings.load({'unknown':3})
        with self.assertRaises(ValueError):Settings.load({'bass':-1})
    def test_duplicate_tracking(self):
        bar=[(0,0,.25,(40,43,47))]
        score={'measures':1,'tracks':[{'name':'Rhythm Guitar L','measures':[bar]},
             {'name':'Rhythm Guitar R','measures':[bar]},
             {'name':'Drums','measures':[bar]}]}
        measures,excluded=collect(score)
        self.assertEqual(len(excluded),1)
        self.assertEqual(measures[0]['notes'][40%12],.25)

if __name__=='__main__':unittest.main()