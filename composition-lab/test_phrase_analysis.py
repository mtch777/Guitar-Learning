"""Regression tests for motif transposition, edited phrases and non-overlap."""
import unittest
from phrase_analysis import distance, representative

class PhraseAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.base=[(0,i*.25,.25,p) for i,p in enumerate([40,43,45,47,50,47])]
    def test_pitch_transposition(self):
        transposed=[(voice,t,d,p+5) for voice,t,d,p in self.base]
        self.assertEqual(distance(self.base,transposed),0)
    def test_insertion(self):
        added=self.base[:3]+[(0,.625,.125,46)]+self.base[3:]
        self.assertGreater(distance(self.base,added),0)
        self.assertLess(distance(self.base,added),.28)
    def test_different_shape(self):
        different=[(0,i*.25,.25,40+2*i) for i in range(6)]
        self.assertGreater(distance(self.base,different),.28)
    def test_chord_representation(self):
        measures=[[(0,0,.25,(40,47,52)),(1,0,.25,(60,))],[(0,0,.5,(43,))]]
        self.assertEqual(representative(measures,0,2),[(0,0,.25,40),(1,0,.5,43)])

if __name__=='__main__':
    unittest.main()
