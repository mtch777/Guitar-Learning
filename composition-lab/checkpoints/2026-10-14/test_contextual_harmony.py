import unittest
from fractions import Fraction as F
from harmonic_relative import Chord
from contextual_harmony import supplement_anchors

A=Chord(60,((1,0),(3,4),(5,7),(7,11)))
B=Chord(62,((1,0),(3,3),(5,7)))
def a(t,ch):return {'start':F(t),'end':F(t+1),'chord':ch,'beat_id':str(t),'voice':0}
def ev(t,pitches,voice=0):
    return {'onset_q':str(F(t)),'duration_q':'1','notes':[{'midi':p} for p in pitches],
            'beat_id':str(t),'voice_index':voice}
def score(events):return {'tracks':[{'measures':[{'voices':[events]}]}]}
class ContextualTests(unittest.TestCase):
    def test_rootless_partial_inferred_between_matching_anchors(self):
        result,report=supplement_anchors(score([ev(2,[64,71])]),0,[a(0,A),a(4,A)])
        self.assertEqual(report['contextually_completed_chords'],1)
        self.assertTrue(result[1]['contextual'])
    def test_unrelated_notes_rejected(self):
        _,r=supplement_anchors(score([ev(2,[64,70])]),0,[a(0,A),a(4,A)])
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_different_neighbor_chords_rejected(self):
        _,r=supplement_anchors(score([ev(2,[64,71])]),0,[a(0,A),a(4,B)])
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_no_extrapolation(self):
        _,r=supplement_anchors(score([ev(2,[64,71])]),0,[a(0,A)])
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_gap_limit(self):
        _,r=supplement_anchors(score([ev(2,[64,71])]),0,[a(0,A),a(10,A)],max_gap=4)
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_conflicting_simultaneous_voice(self):
        s={'tracks':[{'measures':[{'voices':[[ev(2,[64,71])],[ev(2,[66],1)]]}]}]}
        _,r=supplement_anchors(s,0,[a(0,A),a(4,A)])
        self.assertEqual(r['contextually_completed_chords'],0)
if __name__=='__main__':unittest.main()