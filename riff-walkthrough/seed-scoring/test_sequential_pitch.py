import unittest
import tonal_scale_sets as T
from sequential_pitch import exact_roots,EXACT
class Tests(unittest.TestCase):
 def test_84_aliases_12_collections(self):self.assertEqual(len(T.ALL),12);self.assertEqual(sum(map(len,T.ALIASES.values())),84)
 def test_relative_keys_equal(self):
  a,_=T.estimated({'Provisional tonal center/key (riff; mapped)':'C','Compatible modes (phrase; mapped; provisional riff tonic)':'["Ionian"]'})
  b,_=T.estimated({'Provisional tonal center/key (riff; mapped)':'A','Compatible modes (phrase; mapped; provisional riff tonic)':'["Aeolian"]'})
  self.assertEqual(a,b)
 def test_monotonic(self):
  a=T.from_notes([{'midi_pitch':28}]);b=T.from_notes([{'midi_pitch':30}],a);self.assertTrue(set(b)<=set(a));self.assertTrue(b)
 def test_chromatic_no_fit(self):self.assertEqual(T.from_notes([{'midi_pitch':p} for p in range(60,72)]),())
 def test_exact_only_not_rhythm(self):
  rows=[{'Phrase #':1,EXACT:'3','Intended same rhythm and holds as (phrase #s)':'2'},{'Phrase #':2,EXACT:'none'},{'Phrase #':3,EXACT:'1'}]
  self.assertEqual(exact_roots(rows),{1:1,2:2,3:1})
 def test_unknown_not_link(self):self.assertEqual(exact_roots([{'Phrase #':1,EXACT:'unknown comparisons: 2'},{'Phrase #':2,EXACT:'none'}]),{1:1,2:2})
 def test_chain_earliest(self):self.assertEqual(exact_roots([{'Phrase #':1,EXACT:'3'},{'Phrase #':2,EXACT:'3'},{'Phrase #':3,EXACT:'2'}]),{1:1,2:1,3:1})
 def test_candidate_missing_key(self):self.assertFalse(T.estimated({})[0]);self.assertIsNotNone(T.estimated({})[1])
if __name__=='__main__':unittest.main()
