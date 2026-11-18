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





class CoreTests(unittest.TestCase):
 def setUp(self):
  self.times=[dict(bar=i+1,start_seconds=i,end_seconds=i+1,verified=True,max_error_seconds=.1)for i in range(16)]
  self.events=[dict(start_seconds=t,text=s,timestamp_error_seconds=.1)for t,s in[(1.2,'alpha'),(4.8,'beta'),(9.2,'alpha'),(12.8,'beta')]]
 def result(self):
  from lyric_refrain_evidence import lyric_refrain_core_evidence
  return lyric_refrain_core_evidence(self.events,self.times,source_fingerprint='synthetic',maximum_pair_gap_seconds=8)
 def test_supported_envelope(self):
  r=self.result();self.assertEqual([b['bar']for b in r['bars']if b['core_envelope_ids']],[3,4,11,12]);self.assertTrue(all(not b['continuous_singing_verified']for b in r['bars']));self.assertNotIn('alpha',json.dumps(r))
 def test_no_guessed_last_line_end(self):self.assertLess(self.result()['core_envelopes'][0]['end_seconds'],4.8)
 def test_unverified_matching_occurrence(self):
  self.times[9]['verified']=False;self.assertFalse(self.result()['core_envelopes'])
 def test_missing_lyrics(self):
  self.events=[];self.assertFalse(self.result()['core_envelopes'])
 def test_long_gap_not_filled(self):
  self.events[1]['start_seconds']=9.3;self.events[2]['start_seconds']=10;self.events[3]['start_seconds']=19;self.assertFalse(self.result()['core_envelopes'])
 def test_uncertainty_gap_rejected(self):
  self.events[0]['start_seconds']=1.9;self.times=[b for b in self.times if b['bar']!=3];self.assertFalse(self.result()['core_envelopes'])
 def test_uncertainty_expansion_rechecked(self):
  self.events[0]['start_seconds']=1.9;self.times[2]['max_error_seconds']=.2;self.times[3]['verified']=False;self.events[0]['timestamp_error_seconds']=1.0;self.assertFalse(self.result()['core_envelopes'])
 def test_unverified_status_preserved(self):
  self.times[0]['verified']=False;self.assertEqual(self.result()['bars'][0]['status'],'alignment_unverified')
 def test_repeated_verse_remains_possible(self):
  b=next(b for b in self.result()['bars']if b['core_envelope_ids']);self.assertIn('verse',b['alternatives']);self.assertIn('outro',b['alternatives']);self.assertIsNone(b['confidence'])

if __name__=='__main__':unittest.main()

