import unittest,json,csv,pathlib,math
import weighted_scoring as W
class WeightedTests(unittest.TestCase):
 def test_exact_approved_weights(self):
  w={f['schema_id']:f['weight'] for f in W.FIELDS}
  self.assertEqual(len(w),32);self.assertNotIn(12,w)
  self.assertEqual({i for i,v in w.items() if v==3},{5,11})
  self.assertEqual({i for i,v in w.items() if v==2},{24,25})
  self.assertEqual({i for i,v in w.items() if v==.5},{26,27,31,32,35,41,42,43,45,48,49,50})
 def test_unknown_not_match(self):
  a={f['schema_id']:None for f in W.FIELDS};self.assertIsNone(W.compare_parsed(a,a)['score'])
 def test_weighted_denominator(self):
  a={f['schema_id']:None for f in W.FIELDS};b=a.copy();a[5]='single_notes';b[5]='chords';a[11]=6.;b[11]=3.;a[13]=8.;b[13]=8.
  r=W.compare_parsed(a,b);self.assertEqual(r['comparable_weight'],7);self.assertAlmostEqual(r['score'],250/7)
 def test_known_zero(self):
  a={f['schema_id']:None for f in W.FIELDS};a[51]=0.;self.assertEqual(W.compare_parsed(a,a)['score'],100)
 def test_symmetry(self):
  a={f['schema_id']:None for f in W.FIELDS};b=a.copy();a[11]=6.;b[11]=1.5;a[27]=(28,43);b[27]=(28,40)
  self.assertEqual(W.compare_parsed(a,b),W.compare_parsed(b,a))
if __name__=='__main__':unittest.main()
