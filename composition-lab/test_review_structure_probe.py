"""Unit checks for the read-only V23 structural diagnostic."""
import unittest
from review_structure_probe import confusion,features
class StructureProbeTests(unittest.TestCase):
 def test_confusion(self):
  self.assertEqual(confusion([(True,True),(True,False),(False,False),(False,True)]),
                   {'tp':1,'fp':1,'tn':1,'fn':1})
 def test_midphrase_note_not_promoted_to_boundary(self):
  row={'onset_q':'5/2','measure':'1'}
  events=[{'t':2.5,'end':3.,'voice':0},{'t':2.,'end':2.5,'voice':0}]
  result=features(row,events,{1},{1})
  self.assertFalse(result['structural_candidate'])
  self.assertEqual(result['gap'],0)
 def test_section_start_at_barline(self):
  row={'onset_q':'4','measure':'2'}
  result=features(row,[{'t':4.,'end':4.5,'voice':0}],set(),{2})
  self.assertTrue(result['structural_candidate'])
if __name__=='__main__':unittest.main()
