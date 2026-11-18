import unittest,copy,json
from lyric_refrain_evidence import lyric_refrain_evidence,attach_lyric_evidence,feature_fingerprint
from section_functions import analyze_functions
from test_section_repeats import song,A,B

class LyricTests(unittest.TestCase):
 def setUp(self):
  self.events=[dict(start_seconds=t,text=s,timestamp_error_seconds=.01)for t,s in [(1,'Alpha'),(3,'Beta'),(9,'alpha'),(11,'beta')]]
  self.times=[dict(bar=i+1,start_seconds=i*4,end_seconds=(i+1)*4,verified=True,max_error_seconds=.1)for i in range(4)]
 def cue(self,**kwargs):return lyric_refrain_evidence(self.events,self.times,source_fingerprint=feature_fingerprint(song([A,B,A,B])),maximum_pair_gap_seconds=8,**kwargs)
 def test_positive(self):
  r=self.cue();self.assertEqual([b['repeated_pair_onsets']for b in r['bars']],[1,0,1,0]);self.assertIsNone(r['bars'][0]['confidence']);self.assertNotIn('Alpha',json.dumps(r));self.assertNotIn('alpha',json.dumps(r))
 def test_absence_not_verse(self):self.assertEqual(self.cue()['bars'][1]['alternatives'],[])
 def test_missing(self):self.assertTrue(all(b['status']=='no_lyrics'for b in lyric_refrain_evidence(None,self.times,source_fingerprint="test",maximum_pair_gap_seconds=8)['bars']))
 def test_unverified(self):
  self.times[0]['verified']=False;self.assertEqual(self.cue()['bars'][0]['status'],'alignment_unverified')
 def test_uncertain(self):
  self.times[0]['max_error_seconds']=.5;self.assertEqual(self.cue()['bars'][0]['repeated_pair_onsets'],0)
 def test_edge(self):
  self.events[0]['start_seconds']=.05;self.assertEqual(self.cue()['bars'][0]['repeated_pair_onsets'],0)
 def test_distribution(self):
  r=self.cue(candidate_distribution={'chorus':.7,'other':.3});self.assertEqual(r['bars'][0]['candidate_distribution']['other'],.3);self.assertIsNone(r['bars'][1]['candidate_distribution'])
 def test_invalid_distribution(self):
  with self.assertRaises(ValueError):self.cue(candidate_distribution={'chorus':2})
 def test_invalid_order(self):
  self.events.reverse()
  with self.assertRaises(ValueError):self.cue()
 def test_duplicate_bars(self):
  self.times[1]['bar']=1
  with self.assertRaises(ValueError):self.cue()
 def test_integration(self):
  f=song([A,B,A,B]);base=analyze_functions(f);before=copy.deepcopy(base);r=analyze_functions(f,lyric_evidence=self.cue());self.assertEqual(base,before);self.assertEqual(r['hypotheses'],base['hypotheses']);self.assertTrue(all(b['label']=='unknown'for b in r['bars']));self.assertEqual(analyze_functions(f,lyric_evidence=None),base)
 def test_overlap_is_not_second_occurrence(self):
  self.events=[dict(start_seconds=t,text='hey',timestamp_error_seconds=.01)for t in (1,2,3)];self.assertFalse(any(b['repeated_pair_onsets']for b in self.cue()['bars']))
 def test_missing_timestamp_error(self):
  for e in self.events:e.pop('timestamp_error_seconds')
  self.assertFalse(any(b['repeated_pair_onsets']for b in self.cue()['bars']))
 def test_second_occurrence_unverified(self):
  self.times[2]['verified']=False;self.assertFalse(any(b['repeated_pair_onsets']for b in self.cue()['bars']))
 def test_wrong_source(self):
  with self.assertRaises(ValueError):analyze_functions(song([B,A,B,A]),lyric_evidence=self.cue())
 def test_long_gap(self):
  self.events[1]["start_seconds"]=20;self.events[2]["start_seconds"]=30;self.events[3]["start_seconds"]=50;self.assertFalse(any(b["repeated_pair_onsets"]for b in self.cue()["bars"]))
 def test_counts_are_mutually_disjoint(self):
  self.events=[dict(start_seconds=t,text='hey',timestamp_error_seconds=.01)for t in (1,2,3,5,6)];self.assertTrue(all(n==2 for b in self.cue()['bars'] for n in b['occurrence_counts']))
 def test_identity(self):
  r=analyze_functions(song([A,B]));
  with self.assertRaises(ValueError):attach_lyric_evidence(r,self.cue())
if __name__=='__main__':unittest.main()



