import unittest
from fractions import Fraction as F
from phrase_discovery_v19 import discover,phrase_windows

def ev(start,dur,pitch=None,tie=False):
    return {'onset_q':F(start),'duration_q':F(dur),'notes':([] if pitch is None else [{'midi':pitch,'tie': {'origin':True} if tie else None}])}

def score(measures):
    return {'tracks':[{'measures':[{'onset_q':F(m[0]),'section':m[1],'voices':[m[2]]} for m in measures]}]}

class PhraseDiscoveryTests(unittest.TestCase):
    def test_crosses_barline_without_forcing_boundary(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,62)]),(2,None,[ev(2,1,64),ev(3,1,65)])])
        self.assertEqual([len(v) for _,v in discover(s,0)],[4])
        self.assertIn(4,[len(g) for g in phrase_windows(s,0)])
    def test_section_boundary(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,62)]),(2,'B',[ev(2,1,64),ev(3,1,65)])])
        self.assertEqual([len(v) for _,v in discover(s,0)],[2,2])
    def test_rest_boundary(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1),ev(2,1,62)])])
        self.assertEqual([len(v) for _,v in discover(s,0)],[1,1])
    def test_melodic_discontinuity(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,62),ev(2,1,64),ev(3,1,96),ev(4,1,98)])])
        self.assertEqual([len(v) for _,v in discover(s,0)],[3,2])
    def test_tied_boundary(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,62,tie=True),ev(2,1,64)])])
        self.assertEqual([len(v) for _,v in discover(s,0)],[1,1])
    def test_exact_fractional_timing(self):
        s=score([(0,None,[ev(0,F(1,3),60),ev(F(1,3),F(1,3),62),ev(F(2,3),F(1,3),64)])])
        self.assertIn(3,[len(g) for g in phrase_windows(s,0)])
    def test_validation(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,61)])])
        with self.assertRaises(ValueError):list(phrase_windows(s,0,min_size=0))
        with self.assertRaises(ValueError):discover(s,0,max_events=1)
    def test_no_chord_required(self):
        s=score([(0,None,[ev(0,1,60),ev(1,1,62),ev(2,1,65)])])
        self.assertTrue(list(phrase_windows(s,0)))

if __name__=='__main__':unittest.main()