import unittest
import section_variant_repeats as V
class VariantTests(unittest.TestCase):
 def f(self,items):
  return {'pitch':{'0':{f'{t}|{d}|{p}':1 for t,d,p in items}}}
 def test_durations_do_not_change_sequence(self):
  self.assertEqual(V.sequence(self.f([(0,1,40),(1,1,42)]),'0'),V.sequence(self.f([(0,.5,40),(.5,.5,42)]),'0'))
 def test_consecutive_same_attacks_condense(self):
  self.assertEqual(V.sequence(self.f([(0,1,40),(1,1,40),(2,1,42)]),'0'),[(40.,),(42.,)])
 def test_polyphonic_groups_preserved(self):
  self.assertEqual(V.sequence(self.f([(0,1,40),(0,1,47),(1,1,42)]),'0'),[(40.,47.),(42.,)])
 def test_reordering_is_not_identity(self):
  self.assertLess(V.similarity([(40,),(42,),(44,)],[(40,),(44,),(42,)]),1)
 def test_missing_is_not_match(self):self.assertIsNone(V.similarity([],[]))
if __name__=='__main__':unittest.main()
