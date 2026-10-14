import unittest
from fractions import Fraction as F
from harmonic_relative import Chord
from harmonic_continuity import expand_agreed_anchors,at_time

A=Chord(60,((1,0),(3,4),(5,7)))
B=Chord(62,((1,0),(3,3),(5,7)))
def anchor(a,b,ch):return dict(start=F(a),end=F(b),chord=ch)
class ContinuityTests(unittest.TestCase):
    def test_agreed_anchors_bridge_melodic_gap(self):
        windows,report=expand_agreed_anchors([anchor(0,1,A),anchor(3,4,A)],max_gap=4)
        self.assertEqual(len(windows),1)
        self.assertEqual(report['bridged_beats_q'],'2')
        self.assertEqual(at_time(windows,F(2))['chord'],A)
    def test_different_chords_do_not_bridge(self):
        windows,_=expand_agreed_anchors([anchor(0,1,A),anchor(3,4,B)],max_gap=4)
        self.assertIsNone(at_time(windows,F(2)))
    def test_no_extrapolation(self):
        windows,_=expand_agreed_anchors([anchor(2,3,A)],max_gap=4)
        self.assertIsNone(at_time(windows,F(1)))
        self.assertIsNone(at_time(windows,F(3)))
    def test_large_gap_stays_unresolved(self):
        windows,_=expand_agreed_anchors([anchor(0,1,A),anchor(12,13,A)],max_gap=4)
        self.assertIsNone(at_time(windows,F(5)))
    def test_invalid_window(self):
        with self.assertRaises(ValueError):expand_agreed_anchors([anchor(3,2,A)])
if __name__=='__main__':unittest.main()