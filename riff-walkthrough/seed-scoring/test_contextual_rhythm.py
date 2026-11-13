import unittest
from contextual_rhythm import *
class T(unittest.TestCase):
 def test_weights(self):self.assertAlmostEqual(weighted({'current':100,'previous':0,'history':None,'context':50})[0],50/85*100)
 def test_missing_context_not_zero(self):self.assertEqual(weighted({'current':100,'previous':None,'history':None,'context':None}),(100,40))
 def test_position(self):self.assertEqual(context(None,2,3,3,5),100)
 def test_singleton_position_missing(self):self.assertIsNone(context(None,1,1,1,1))
 def test_spacing(self):self.assertEqual(sequence([1,1],[1,1]),100);self.assertEqual(sequence([1],[2]),50);self.assertIsNone(sequence([],[]))
 def test_features(self):
  f=features([{'start_beats':0,'end_beats':1},{'start_beats':0,'end_beats':2}],4);self.assertEqual(f,{'density':.25,'spacing':[],'rest':.5,'overlap':.25})
 def test_silence(self):self.assertEqual(features([],4),{'density':0,'spacing':[],'rest':1,'overlap':0})
 def test_metadata_does_not_affect_previous(self):
  a={'categories':{'role':'a'},'features':{'density':1,'spacing':[1],'rest':0,'overlap':0}};b=copy.deepcopy(a);b['categories']['role']='b';self.assertEqual(match(a,b)['score'],100)
 def test_missing_timing(self):self.assertIsNone(match({'features':None},{'features':None})['score'])
 def test_repeat_not_pitch_or_variation(self):
  rows=[{'Phrase #':i,'Length (beats)':2,**{k:'none' for k in L.INHERITING},'Intended same pitch sequence as (phrase #s)':'1','Intended variation of (phrase #s)':'1'} for i in [1,2]]
  self.assertEqual(repeat_roots(rows),{1:1,2:2});rows[1][L.INHERITING[1]]='1';self.assertEqual(repeat_roots(rows),{1:1,2:1})
if __name__=='__main__':unittest.main()
