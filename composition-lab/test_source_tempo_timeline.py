import unittest
from source_tempo_timeline import source_tempo_timeline as build
class TempoTests(unittest.TestCase):
 def bars(self):return [{'bar':1,'start_q':'0','span_q':'4'},{'bar':2,'start_q':'4','span_q':'3'},{'bar':3,'start_q':'7','span_q':'4'}]
 def events(self):return [{'measure':0,'bpm':120},{'measure':2,'bpm':60}]
 def test_piecewise(self):
  r=build(self.bars(),self.events(),measure_index_base=0);self.assertEqual(r['score_duration_seconds'],7.5);self.assertEqual([v['bpm']for v in r['visits']],[120,120,60]);self.assertEqual(r['visits'][-1]['validation_status'],'unverified_score_clock')
 def test_one_based(self):
  e=[dict(v,measure=v['measure']+1)for v in self.events()];self.assertEqual(build(self.bars(),e,measure_index_base=1)['score_duration_seconds'],7.5)
 def test_repeat_requires_order(self):
  b=self.bars();b[0]['repeat_start']=True
  with self.assertRaises(ValueError):build(b,self.events(),measure_index_base=0)
 def test_navigation_requires_order(self):
  with self.assertRaises(ValueError):build(self.bars(),self.events(),measure_index_base=0,navigation_present=True)
 def test_repeat_visits(self):
  r=build(self.bars(),self.events(),measure_index_base=0,playback_order=[1,2,3,1,2,3]);self.assertEqual(r['score_duration_seconds'],15);self.assertEqual(len(r['visits']),6);self.assertEqual(r['visits'][3]['bpm'],120)
 def test_explicit_omission(self):self.assertEqual(build(self.bars(),self.events(),measure_index_base=0,playback_order=[1,3])['score_duration_seconds'],6)
 def test_no_initial_default(self):
  with self.assertRaises(ValueError):build(self.bars(),[{'measure':1,'bpm':120}],measure_index_base=0)
 def test_unsupported(self):
  for e in [{'measure':0,'bpm':120,'position':.5},{'measure':0,'bpm':120,'linear':True},{'measure':0,'bpm':120,'type':8},{'measure':8,'bpm':120}]:
   with self.assertRaises(ValueError):build(self.bars(),[e],measure_index_base=0)
 def test_bad_bpm(self):
  for bpm in (0,-1,True,float('nan'),float('inf'),'120'):
   with self.assertRaises(ValueError):build(self.bars(),[{'measure':0,'bpm':bpm}],measure_index_base=0)
 def test_conflict(self):
  with self.assertRaises(ValueError):build(self.bars(),[{'measure':0,'bpm':120},{'measure':0,'bpm':121}],measure_index_base=0)
 def test_invalid_order(self):
  for order in ([],[9],[True]):
   with self.assertRaises(ValueError):build(self.bars(),self.events(),measure_index_base=0,playback_order=order)
 def test_gaps(self):
  b=self.bars();b[1]['start_q']='5'
  with self.assertRaises(ValueError):build(b,self.events(),measure_index_base=0)
 def test_bad_base(self):
  for b in (None,True,2):
   with self.assertRaises(ValueError):build(self.bars(),self.events(),measure_index_base=b)
 def test_skipped_tempo_is_ambiguous(self):
  with self.assertRaises(ValueError):build(self.bars(),[{'measure':0,'bpm':120},{'measure':1,'bpm':60}],measure_index_base=0,playback_order=[1,3])
 def test_repeat_to_unmarked_different_tempo(self):
  with self.assertRaises(ValueError):build(self.bars(),self.events(),measure_index_base=0,playback_order=[1,2,3,2])
 def test_same_tempo_jump_unambiguous(self):
  self.assertEqual(build(self.bars(),[{'measure':0,'bpm':120}],measure_index_base=0,playback_order=[1,3])['score_duration_seconds'],4)
if __name__=='__main__':unittest.main()

