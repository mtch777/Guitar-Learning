import unittest
from fractions import Fraction as F
from harmonic_relative import Chord
from contextual_harmony import supplement_anchors

C = Chord(60, ((1,0),(3,4),(5,7),(7,10)))
D = Chord(62, ((1,0),(3,3),(5,7),(7,10)))
def anchor(a,b,c): return {'start':F(a),'end':F(b),'chord':c,'beat_id':str(a),'voice':0}
def event(a,b,pitches,voice=0):
    return {'onset_q':str(F(a)),'duration_q':str(F(b)), 'beat_id':str(a), 'voice_index':voice,
            'notes':[{'midi':p} for p in pitches]}
def score(*events):return {'tracks':[{'measures':[{'voices':[list(events)]}]}]}
class ContextTests(unittest.TestCase):
    def test_rootless_seventh_partial_between_matching_anchors(self):
        source=score(event(1,1,[64,67,70]))
        a, r=supplement_anchors(source,0,[anchor(0,1,C),anchor(2,3,C)])
        self.assertEqual(r['contextually_completed_chords'],1)
        self.assertTrue(any(x.get('contextual') for x in a))
    def test_disagreeing_neighbors_not_promoted(self):
        a,r=supplement_anchors(score(event(1,1,[64,67,70])),0,[anchor(0,1,C),anchor(2,3,D)])
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_nonaligned_pitches_not_promoted(self):
        a,r=supplement_anchors(score(event(1,1,[64,67,71])),0,[anchor(0,1,C),anchor(2,3,C)])
        self.assertEqual(r['contextually_completed_chords'],0)
    def test_single_note_not_promoted(self):
        a,r=supplement_anchors(score(event(1,1,[67])),0,[anchor(0,1,C),anchor(2,3,C)])
        self.assertEqual(r['contextually_completed_chords'],0)
if __name__=='__main__':unittest.main()