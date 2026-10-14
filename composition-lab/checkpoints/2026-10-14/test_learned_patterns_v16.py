import unittest
from fractions import Fraction as F
from harmonic_relative import Chord
from learned_patterns_v16 import learn,plan_melody,plan_rhythm

def event(i,on,dur,pitches):
    return {'beat_id':str(i),'onset_q':F(on),'duration_q':F(dur),'notes':[{'midi':p,'note_id':f'{i}_{k}','tie':None} for k,p in enumerate(pitches)]}

def fixture():
    # Two distinct two-note phrases, equal event shapes and each inside a single C major chord.
    v=[event(1,0,1,[60]),event(2,1,1,[64]),event(3,2,1,[67]),event(4,3,1,[72])]
    score={'tracks':[{'measures':[{'voices':[v]}]}]}
    spans=[{'start':F(0),'end':F(4),'chord':Chord(60,((1,0),(3,4),(5,7)))}]
    return score,spans

class TestV16(unittest.TestCase):
    def test_learns_relative_not_absolute(self):
        score,spans=fixture();melody,_=learn(score,0,spans)
        self.assertTrue(melody)
        self.assertTrue(any(roles==(((0,1,0),),((4,3,0),)) for _,roles in melody))

    def test_phrase_changes_keep_event_timing(self):
        score,spans=fixture();targets=[{**w,'target':w['chord']} for w in spans]
        planned,stats=plan_melody(score,0,spans,targets,100,seed=9)
        self.assertGreater(stats['learned_melody_phrases'],0)
        self.assertGreaterEqual(len(planned),2)
        self.assertEqual([e['duration_q'] for e in score['tracks'][0]['measures'][0]['voices'][0]],[1,1,1,1])

    def test_zero_leaves_events(self):
        score,spans=fixture();targets=[{**w,'target':w['chord']} for w in spans]
        self.assertEqual(plan_melody(score,0,spans,targets,0)[0],{})
        self.assertEqual(plan_rhythm(score,0,spans,0)[0],{})

    def test_learned_rhythm_changes_and_total(self):
        v=[event(1,0,1, [60]),event(2,1,2,[64]),event(3,3,2,[67]),event(4,5,1,[72])]
        score={'tracks':[{'measures':[{'voices':[v]}]}]}
        spans=[]
        planned,stats=plan_rhythm(score,0,spans,100,seed=4)
        self.assertGreater(stats['learned_rhythm_phrases'],0)
        self.assertGreaterEqual(len(planned),2)
        self.assertTrue(set(planned).issubset({'1','2','3','4'}))

    def test_no_crossing_harmonic_boundary(self):
        score,spans=fixture()
        score['tracks'][0]['measures'][0]['voices'][0][0]['duration_q']=F(1,2)
        planned,stats=plan_rhythm(score,0,spans,100)
        self.assertEqual(planned,{})

if __name__=='__main__':unittest.main()