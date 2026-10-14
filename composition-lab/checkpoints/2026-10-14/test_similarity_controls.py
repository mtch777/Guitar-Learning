import unittest
from fractions import Fraction as F
from harmonic_relative import Chord,analyze_note
from similarity_controls import Controls,transform

DM=Chord(50,((1,0),(3,3),(5,7)))
FMA=Chord(53,((1,0),(3,4),(5,7)))
H=[{'start':F(0),'end':F(4),'chord':DM}]
E=[{'onset':F(1,3),'duration':F(2,3),'pitches':(50,53,57),'tag':'same'}]

class TestControls(unittest.TestCase):
 def test_all_zero_identity(self):
  result=transform(E,H,controls=Controls(0,0,0))
  self.assertEqual(result['events'],E)
  self.assertEqual(result['harmony'][0]['target'],DM)
 def test_chords_only_preserves_roles_and_timing(self):
  result=transform(E,H,controls=Controls(100,0,0),chord_pool=[FMA],seed=8)
  new=result['events'][0]
  self.assertEqual(new['pitches'],(53,57,60))
  self.assertEqual(new['onset'],E[0]['onset'])
  self.assertEqual(new['duration'],E[0]['duration'])
  self.assertEqual([analyze_note(p,FMA).degree for p in new['pitches']],[1,3,5])
 def test_melody_only_preserves_harmony_timing(self):
  result=transform(E,H,controls=Controls(0,100,0),melody_offsets=[1])
  self.assertEqual(result['events'][0]['pitches'],(51,54,58))
  self.assertEqual(result['harmony'][0]['target'],DM)
  self.assertEqual(result['events'][0]['duration'],F(2,3))
 def test_rhythm_only_preserves_pitches_harmony(self):
  result=transform(E,H,controls=Controls(0,0,100),rhythm_patterns=[(F(1,3),F(1,2))])
  self.assertEqual(result['events'][0]['pitches'],E[0]['pitches'])
  self.assertEqual(result['events'][0]['onset'],F(2,3))
  self.assertEqual(result['events'][0]['duration'],F(1,2))
 def test_missing_chord_remains_unchanged(self):
  e=[{'onset':F(7),'duration':F(1),'pitches':(69,)}]
  result=transform(e,H,controls=Controls(100,0,0),chord_pool=[FMA])
  self.assertEqual(result['events'],e)
  self.assertEqual(result['report']['events_without_harmonic_evidence'],1)
 def test_no_chord_candidates_reports(self):
  result=transform(E,H,controls=Controls(100,0,0))
  self.assertEqual(result['report']['unavailable_chord_variations'],1)
  self.assertEqual(result['events'],E)
 def test_rhythm_boundary_protected(self):
  r=transform(E,H,controls=Controls(0,0,100),rhythm_patterns=[(F(5),F(1))])
  self.assertEqual(r['events'],E)
  self.assertEqual(len(r['report']['conflicts']),1)
 def test_invalid_controls(self):
  with self.assertRaises(ValueError):Controls(-1,0,0)
  with self.assertRaises(ValueError):Controls(0,101,0)
 def test_repeatable(self):
  a=transform(E,H,controls=Controls(60,80,100),chord_pool=[FMA],rhythm_patterns=[(F(1,6),F(1,2))],seed=42)
  b=transform(E,H,controls=Controls(60,80,100),chord_pool=[FMA],rhythm_patterns=[(F(1,6),F(1,2))],seed=42)
  self.assertEqual(a,b)

if __name__=='__main__':unittest.main()