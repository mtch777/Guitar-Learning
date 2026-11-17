import unittest
from unittest.mock import patch
import section_boundary_proposals as P
class BoundaryTests(unittest.TestCase):
 def test_no_features(self):self.assertEqual(P.context_boundaries([]),([0.],[None]))
 def test_two_homogeneous_contexts(self):
  fs=[{'observed':True,'v':x} for x in [0,0,0,0,1,1,1,1]]
  with patch.object(P.B,'compare_bars',lambda a,b:{'score':float(a['v']==b['v'])}):
   v,s=P.context_boundaries(fs)
  self.assertEqual(v[4],1);self.assertEqual(s[4],2)
 def test_refinement_bounds_and_order(self):
  fs=[{}]*12; c={'a_start':0,'a_end':5,'b_start':6,'b_end':11}
  with patch.object(P,'context_boundaries',return_value=([1,0,0,0,1,0,1,0,0,0,1,0,1],[None]*13)):
   out=P.refine(fs,[c],extension=0)['proposals'][0]
  self.assertEqual([out[k] for k in ['a_start','a_end','b_start','b_end']],[0,4,6,10])
 def test_single_bar_is_not_section_refined(self):
  with patch.object(P,'context_boundaries',return_value=([1,0,1],[None]*3)):
   self.assertEqual(P.refine([{},{}],[{'a_start':0,'a_end':1,'b_start':1,'b_end':2}])['proposals'],[])
if __name__=='__main__':unittest.main()
