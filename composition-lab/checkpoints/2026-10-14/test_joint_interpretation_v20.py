import unittest
from fractions import Fraction as F
from joint_interpretation_v20 import sonorities, interpret, boundary_evidence, summary

def event(t,pitches,d=1,vi=0):
    return {'onset_q':str(F(t)),'duration_q':str(F(d)),'voice_index':vi,
            'notes':[{'midi':p,'tie':None} for p in pitches]}

def score(events):
    return {'tracks':[{'measures':[{'voices':[events]}]}]}

class JointTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(interpret(score([]),0),[])
        self.assertEqual(boundary_evidence(score([]),0),[])
    def test_chord_probabilities(self):
        x=interpret(score([event(0,[60,64,67]),event(1,[60,64,67])]),0)
        self.assertEqual(len(x),2)
        for row in x:self.assertAlmostEqual(sum(c['probability'] for c in row['candidates']),1)
    def test_uncertain_note_retained(self):
        x=interpret(score([event(0,[62])]),0)
        self.assertEqual(len(x),1)
        self.assertTrue(x[0]['unresolved'])
    def test_sustain_observed(self):
        x=sonorities(score([event(0,[60],2),event(1,[64])]),0)
        self.assertEqual(x[1]['pcs'],frozenset((0,4)))
    def test_gesture_and_harmony(self):
        s=score([event(0,[60,64,67]),event(1,[62]),event(2,[62,65,69]),event(3,[64])])
        x=boundary_evidence(s,0)
        self.assertEqual(len(x),4)
        self.assertTrue(all(0<=r['boundary_score']<=1 for r in x))
    def test_non_destructive(self):
        s=score([event(0,[60,64,67])]);before=repr(s)
        summary(s,0)
        self.assertEqual(before,repr(s))
    def test_parameter_errors(self):
        with self.assertRaises(ValueError):interpret(score([event(0,[60])]),0,temperature=0)
if __name__=='__main__':unittest.main()

class JointIntegrationTest(unittest.TestCase):
    def test_motif_repeat_support(self):
        from joint_interpretation_v20 import boundary_evidence
        s=score([event(i,[p]) for i,p in enumerate([60,62,64,60,62,64,60,62,64])])
        result=boundary_evidence(s,0)
        self.assertGreater(sum(r['motif_recurrence'] for r in result),0)
    def test_refinement_can_produce_windows_without_known_chords(self):
        from joint_interpretation_v20 import joint_phrase_windows
        s=score([event(i,[p]) for i,p in enumerate([60,62,64,65,67,69])])
        self.assertTrue(list(joint_phrase_windows(s,0)))
    def test_joint_melody_zero_is_identity(self):
        from relational_learning_v17 import plan_intervals
        s=score([event(i,[p]) for i,p in enumerate([60,62,64,65,67,69])])
        edits,stats=plan_intervals(s,0,0,joint=True)
        self.assertEqual(edits,{})
    def test_no_false_harmonic_change_for_single_notes(self):
        s=score([event(i,[p]) for i,p in enumerate([60,62,64,65,67,69])])
        self.assertTrue(all(r['harmonic_change_evidence']==0 for r in boundary_evidence(s,0)))