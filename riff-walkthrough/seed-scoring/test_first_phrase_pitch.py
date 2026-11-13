import unittest,tempfile,pathlib
from unittest.mock import patch
from first_phrase_pitch import alignment,midi,MULTIPLIERS,Engine,CENTER,MODES_FIELD
import opening_rhythm as R
class Tests(unittest.TestCase):
 def test_no_tonal_evidence_required_or_used(self):
  row={'Riff ID':'seed','Phrase #':'1','Artist':'test','Phrase role':'phrase','Category - dominant texture':'single_notes','Accent function':'none assigned','Unknowns and warnings':''}
  rhythm={'selection_performed':True,'selected_rhythm':[{'note_slot':1,'start_exact':'0','start_beats':0,'duration_beats':1,'end_beats':1,'overlaps_note_slots':''}]}
  with tempfile.TemporaryDirectory() as temp:
   root=pathlib.Path(temp);p=root/'fixture.csv';p.write_text('fixture')
   e=Engine.__new__(Engine);e.csv_path=p;e.first={'seed':row};e.parsed={'seed':{}};e.refs=[(row,[[28]],[1])]
   with patch('first_phrase_pitch.W.compare_parsed',return_value={'score':80}):
    a=e.run('seed',rhythm,root/'absent',123)
    row[CENTER]='unknown';row[MODES_FIELD]='NOT VALID JSON'
    b=e.run('seed',rhythm,root/'malformed',123)
   self.assertTrue(a['selection_performed']);self.assertTrue(b['selection_performed']);self.assertEqual(a['notes'],b['notes']);self.assertEqual(a['selected']['weight'],b['selected']['weight']);self.assertEqual(a['notes'][0]['midi_pitch'],28)
 def test_unresolved_role_filter(self):
  self.assertTrue(R.unresolved_role({'Phrase role':'unresolved'}));self.assertFalse(R.unresolved_role({'Phrase role':'phrase'}));self.assertFalse(R.unresolved_role({'Phrase role':'accent'}));self.assertFalse(R.unresolved_role({'Phrase role':'some other label'}))
 def test_exact(self):self.assertEqual(alignment([1,2,1],[1,2,1]),(1,[0,1,2]))
 def test_permutation(self):self.assertEqual(alignment([1,2,1],[2,1,1]),(2,[1,0,2]))
 def test_contiguous(self):self.assertEqual(alignment([1,2],[4,1,2,1,2]),(3,[1,2]))
 def test_subsequence(self):self.assertEqual(alignment([1,2],[1,4,2]),(4,[0,2]))
 def test_no_match(self):self.assertIsNone(alignment([3,3],[1,2,3]))
 def test_unknown_outside_subset(self):self.assertEqual(alignment([1,2],[4,1,2],[False,True,True]),(3,[1,2]))
 def test_unknown_inside(self):self.assertIsNone(alignment([1,2],[1,2],[True,False]))
 def test_earliest_valid(self):self.assertEqual(alignment([1,2],[1,2,1,2],[False,True,True,True]),(3,[2,3]))
 def test_not_equal_totals_only(self):self.assertIsNone(alignment([1,3],[2,2]))
 def test_midi(self):self.assertEqual(midi('E1'),28);self.assertEqual(midi('C-1'),0);self.assertIsNone(midi('?'))
 def test_weights(self):self.assertEqual(MULTIPLIERS,{1:1.,2:.75,3:.5,4:.25})
if __name__=='__main__':unittest.main()
