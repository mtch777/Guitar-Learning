import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent.parent/'weighted-scoring'))
import opening_rhythm as R
from fractions import Fraction
class RhythmTests(unittest.TestCase):
 def row(self,role='phrase',texture='single_notes',accent='unassigned'):
  return {'Phrase role':role,'Category - dominant texture':texture,'Accent function':'phrase function: '+accent+'; source note accents: 3/8'}
 def test_source_pool_known_roles_only_without_same_role_or_self_gate(self):
  first={'seed':self.row(),'different':self.row(role='accent'),'unknown':self.row(role='unresolved')}
  self.assertEqual(R.source_pool_ids(first),{'seed','different'})
 def test_exact_weights(self):self.assertEqual(R.WEIGHTS,{'role':3,'texture':3,'accent':2,'source_riff_similarity':1})
 def test_unknown_accent_omitted(self):
  a=R.score(self.row(),self.row(),90);self.assertEqual(a['known_weight'],7);self.assertAlmostEqual(a['score'],690/7)
 def test_unknown_role_omitted(self):
  a=R.score(self.row(),self.row(role='unresolved'),90);self.assertEqual(a['known_weight'],4);self.assertAlmostEqual(a['score'],97.5)
 def test_known_mismatch_zero_not_missing(self):
  a=R.score(self.row(),self.row(role='accent'),90);self.assertEqual(a['known_weight'],7);self.assertAlmostEqual(a['score'],390/7)
 def test_known_accent(self):
  a=R.score(self.row(accent='fill'),self.row(accent='fill'),90);self.assertEqual(a['known_weight'],9);self.assertAlmostEqual(a['score'],890/9)
 def test_no_pitch_copy_and_exact_fraction(self):
  src={'complete':True,'length_beats':'6','notes':[{'start_beats':'1/3','duration_beats':'2/3','end_beats':'1','pitch':60,'fret':3,'voice':1},{'start_beats':'1/2','duration_beats':'1','end_beats':'3/2'}]}
  n,e=R.validated_notes(src,Fraction(6));self.assertFalse(e);self.assertEqual(n[0]['duration_exact'],'2/3');self.assertNotIn('pitch',n[0]);self.assertNotIn('fret',n[0]);self.assertEqual(n[1]['end_exact'],'3/2')
 def test_missing_rejected(self):
  _,e=R.validated_notes({'complete':False,'length_beats':6,'notes':[]},Fraction(6));self.assertTrue(e)
 def test_bad_timing_rejected(self):
  _,e=R.validated_notes({'complete':True,'length_beats':6,'notes':[{'start_beats':0,'duration_beats':1,'end_beats':2}]},Fraction(6));self.assertTrue(e)
 def test_complete_silence_valid(self):
  n,e=R.validated_notes({'complete':True,'length_beats':6,'notes':[]},Fraction(6));self.assertEqual(n,[]);self.assertFalse(e)
 def test_missing_voice_valid(self):
  n,e=R.validated_notes({'complete':True,'length_beats':6,'notes':[{'start_beats':0,'duration_beats':1,'end_beats':1}]},Fraction(6));self.assertFalse(e);self.assertIsNone(n[0]['voice'])
 def test_missing_source_score_omitted(self):
  a=R.score(self.row(),self.row(),None);self.assertEqual(a['known_weight'],6);self.assertEqual(a['score'],100);self.assertNotIn('source_riff_similarity',a['components'])
 def test_known_zero_source_not_missing(self):
  a=R.score(self.row(),self.row(),0);self.assertEqual(a['known_weight'],7);self.assertEqual(a['components']['source_riff_similarity'],0)
 def test_source_fact_warning_not_auto_rejection(self):
  n,e=R.validated_notes({'complete':True,'exact_fact_timing_match':False,'length_beats':6,'notes':[{'start_beats':0,'duration_beats':1,'end_beats':1}]},Fraction(6));self.assertFalse(e)
 def test_exact_length_required(self):
  _,e=R.validated_notes({'complete':True,'length_beats':5,'notes':[{'start_beats':0,'duration_beats':1,'end_beats':1}]},Fraction(6));self.assertTrue(e)
if __name__=='__main__':unittest.main()
