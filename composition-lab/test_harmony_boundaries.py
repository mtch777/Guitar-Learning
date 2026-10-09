"""Unit tests for multi-track harmony and novelty helpers."""
import unittest
from collections import Counter
from harmony_boundaries import _cosine_gap,_pitched,_signature
class HarmonyBoundaryTests(unittest.TestCase):
    def test_pitch_context_duration(self):
        self.assertEqual(_pitched([(0,0,.5,(40,52)),(0,.5,.25,(43,))]),Counter({4:1.,7:.25}))
    def test_identical_profiles_no_novelty(self):
        self.assertAlmostEqual(_cosine_gap(Counter({0:2,7:1}),Counter({0:4,7:2})),0)
    def test_disjoint_pitch_profiles(self):
        self.assertAlmostEqual(_cosine_gap(Counter({0:1}),Counter({1:1})),1)
    def test_empty(self):
        self.assertEqual(_cosine_gap(Counter(),Counter()),0)
    def test_duplicate_signature(self):
        self.assertEqual(_signature([(0,0,.25,(40,)),(1,0,.5,(45,))]),((0,.25,(40,)),))
if __name__=='__main__':unittest.main()
