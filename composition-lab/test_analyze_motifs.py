"""Regression tests for pitch-invariant and rhythm-flex motif matching."""
import unittest
from analyze_motifs import motif_signature, repeat_groups

class MotifTests(unittest.TestCase):
    def test_transposition_same_rhythm(self):
        a=[(0,0,.25,(40,)),(0,.25,.25,(43,)),(0,.5,.25,(45,)),(0,.75,.25,(47,))]
        b=[(0,0,.25,(45,)),(0,.25,.25,(48,)),(0,.5,.25,(50,)),(0,.75,.25,(52,))]
        self.assertEqual(motif_signature(a),motif_signature(b))
        self.assertEqual(repeat_groups([motif_signature(a),motif_signature(b)]),[[1,2]])
    def test_rhythm_change_is_flexible_only(self):
        a=[(0,0,.25,(40,)),(0,.25,.25,(43,)),(0,.5,.25,(45,)),(0,.75,.25,(47,))]
        b=[(0,0,.5,(40,)),(0,.5,.125,(43,)),(0,.625,.125,(45,)),(0,.75,.25,(47,))]
        self.assertNotEqual(motif_signature(a),motif_signature(b))
        self.assertEqual(motif_signature(a,True),motif_signature(b,True))
    def test_no_false_match_for_sparse(self):
        self.assertIsNone(motif_signature([(0,0,.25,(40,))]))
        self.assertEqual(repeat_groups([None,None]),[])
    def test_diff_pitch_pattern(self):
        a=[(0,i,.25,(40+i,)) for i in range(4)]
        b=[(0,i,.25,(40+2*i,)) for i in range(4)]
        self.assertNotEqual(motif_signature(a,True),motif_signature(b,True))

if __name__=="__main__":
    unittest.main()
