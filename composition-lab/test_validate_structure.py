"""Regression tests for label-independent novelty and chord candidates."""
import unittest
from collections import Counter
from validate_structure import gap, chord_candidates

class StructureTests(unittest.TestCase):
    def test_equal_pitch_distributions(self):
        self.assertAlmostEqual(gap(Counter({0:2,7:1}),Counter({0:4,7:2})),0)
    def test_disjoint_pitch_distributions(self):
        self.assertAlmostEqual(gap(Counter({0:1}),Counter({7:1})),1)
    def test_major_triad_candidate(self):
        names=[c['name'] for c in chord_candidates(Counter({0:8,4:7,7:7}))]
        self.assertIn('C major',names)
    def test_empty_chord(self):
        self.assertEqual(chord_candidates(Counter()),[])

if __name__=='__main__':unittest.main()
