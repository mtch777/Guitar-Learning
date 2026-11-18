import unittest,copy
from recording_function_evidence import recording_evidence,attach_recording_evidence
A='a'*64;F='b'*64
class EvidenceTests(unittest.TestCase):
 def args(self):return dict(audio_sha256=A,source_fingerprint=F,recording_duration=10,model_id='SongFormer',model_revision='fixed')
 def segs(self):return [dict(start_seconds=0,end_seconds=5,candidate_weights={'verse':.6,'chorus':.4}),dict(start_seconds=5,end_seconds=9,candidate_weights={'chorus':.7,'bridge':.3})]
 def bar(self,**kw):
  d=dict(bar=1,start_seconds=1,end_seconds=3,max_error_seconds=.1,validation_status='verified',validation_method='independent anchors',audio_sha256=A,source_fingerprint=F);d.update(kw);return d
 def test_default_noop(self):
  r={'bars':[]};self.assertIs(attach_recording_evidence(r,None),r)
 def test_alternatives_and_tail(self):
  e=recording_evidence(self.segs(),bar_times=[self.bar()],**self.args());self.assertEqual(e['bars'][0]['candidate_weights'],{'verse':.6,'chorus':.4});self.assertEqual(e['bars'][0]['label'],'unknown');self.assertEqual(e['timeline'][-1]['status'],'uncovered')
 def test_unverified(self):
  for field,value in [('validation_status','corroborated'),('audio_sha256','c'*64),('source_fingerprint','d'*64),('max_error_seconds',None),('max_error_seconds',float('nan')),('max_error_seconds',.5),('validation_method','')]:
   e=recording_evidence(self.segs(),bar_times=[self.bar(**{field:value})],**self.args());self.assertEqual(e['bars'][0]['candidate_weights'],{})
 def test_boundary_uncertainty(self):
  e=recording_evidence(self.segs(),bar_times=[self.bar(end_seconds=5)],**self.args());self.assertEqual(e['bars'][0]['status'],'timing_boundary_ambiguous')
 def test_coverage(self):
  e=recording_evidence(self.segs(),bar_times=[self.bar(start_seconds=8,end_seconds=9.5)],**self.args());self.assertEqual(e['bars'][0]['status'],'model_coverage_incomplete')
 def test_missing_middle(self):
  s=self.segs();s[1]['start_seconds']=6;e=recording_evidence(s,bar_times=[self.bar(start_seconds=4,end_seconds=7)],**self.args());self.assertEqual(e['bars'][0]['status'],'model_coverage_incomplete')
 def test_mixed_bar_preserved(self):
  e=recording_evidence(self.segs(),bar_times=[self.bar(start_seconds=4,end_seconds=6,max_error_seconds=0)],**self.args());w=e['bars'][0]['candidate_weights'];self.assertAlmostEqual(w['verse'],.3);self.assertAlmostEqual(w['chorus'],.55);self.assertEqual(e['bars'][0]['label'],'unknown')
 def test_bad_segments(self):
  for a,b in [(float('nan'),2),(-1,2),(3,2),(1,11),(True,2)]:
   with self.assertRaises(ValueError):recording_evidence([dict(start_seconds=a,end_seconds=b,candidate_weights={'verse':1})],**self.args())
 def test_overlap(self):
  s=self.segs();s[1]['start_seconds']=4
  with self.assertRaises(ValueError):recording_evidence(s,**self.args())
 def test_bad_weights(self):
  for w in ({},{'verse':float('nan')},{'verse':-.1,'chorus':1.1},{'verse':.5},{'verse':True}):
   with self.assertRaises(ValueError):recording_evidence([dict(start_seconds=0,end_seconds=5,candidate_weights=w)],**self.args())
 def test_attach_identity(self):
  e=recording_evidence(self.segs(),bar_times=[self.bar()],**self.args());r={'bars':[{'bar':1,'label':'unknown'}]};before=copy.deepcopy(r);out=attach_recording_evidence(r,e,F);self.assertEqual(r,before);self.assertEqual(out['bars'],r['bars'])
  with self.assertRaises(ValueError):attach_recording_evidence(r,e,'c'*64)
  with self.assertRaises(ValueError):attach_recording_evidence({'bars':[{'bar':2}]},e,F)
 def test_duplicate_bar(self):
  with self.assertRaises(ValueError):recording_evidence(self.segs(),bar_times=[self.bar(),self.bar()],**self.args())
 def test_empty_predictions(self):
  e=recording_evidence([],bar_times=[self.bar()],**self.args());self.assertEqual(e['bars'][0]['status'],'model_coverage_incomplete')
 def test_recording_only(self):
  e=recording_evidence(self.segs(),**self.args());out=attach_recording_evidence({'bars':[{'bar':1}]},e,F);self.assertEqual(out['recording_function_evidence']['bars'],[])
 def test_loaded_and_mutated(self):
  import json
  e=recording_evidence(self.segs(),bar_times=[self.bar()],**self.args());e=json.loads(json.dumps(e));r={'bars':[{'bar':1}]};attach_recording_evidence(r,e,F)
  e['bars'][0]['candidate_weights']={'chorus':1}
  with self.assertRaises(ValueError):attach_recording_evidence(r,e,F)
 def test_method_type(self):
  for v in (True,[],{'claimed':True},' '):
   e=recording_evidence(self.segs(),bar_times=[self.bar(validation_method=v)],**self.args());self.assertEqual(e['bars'][0]['status'],'alignment_unresolved')
if __name__=='__main__':unittest.main()

