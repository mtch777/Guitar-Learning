import unittest,copy,tempfile,json,pathlib
import engine as E
class FakeEngine(E.Engine):
 def __init__(self):
  self.artists=['A','B'];self.roles=['phrase'];self.eligible=['r1','r2']
  self.first={r:{'Riff ID':r,'Artist':'A','Phrase #':'1','Phrase role':'phrase','Length (quarter-note beats)':'4','Category - dominant texture':'chug'} for r in self.eligible}
  self.rhythm=type('Rhythm',(),{'items':{(r,1):{'notes':[{'start_beats':0,'end_beats':1,'duration_beats':1}],'reasons':[]} for r in self.eligible}})()
 def reference_audio(self,rid,phrase_numbers,label):return {'label':label,'notes':[]}
class TestSeed(unittest.TestCase):
 def setUp(self):self.e=FakeEngine()
 def test_determinism(self):
  p=copy.deepcopy(E.DEFAULTS['1']);p['random_seed']='123';self.assertEqual(self.e.stage1(p),self.e.stage1(p))
 def test_full_pool(self):self.assertEqual(self.e.stage1(E.DEFAULTS['1'])['details']['candidate_count'],2)
 def test_invalid_inputs(self):
  for value in [-1,float('nan'),float('inf'),True]:
   p=copy.deepcopy(E.DEFAULTS);p['3']['opening_weights']['role']=value
   with self.assertRaises(ValueError):self.e.validate(p)
 def test_drafts_copy(self):
  p=copy.deepcopy(E.DEFAULTS);q=self.e.validate(p);q['3']['opening_weights']['role']=9;self.assertEqual(p['3']['opening_weights']['role'],3)
 def test_no_candidate(self):
  p=copy.deepcopy(E.DEFAULTS['1']);p['artist']='B'
  with self.assertRaisesRegex(ValueError,'No eligible'):self.e.stage1(p)
 def test_no_global_mutation(self):
  old=copy.deepcopy(E.W.FIELDS)
  with E.settings(fields={k:1 for k in E.DEFAULT_FIELD_WEIGHTS}):self.assertTrue(all(x['weight']==1 for x in E.W.FIELDS))
  self.assertEqual(old,E.W.FIELDS)
if __name__=='__main__':unittest.main()
