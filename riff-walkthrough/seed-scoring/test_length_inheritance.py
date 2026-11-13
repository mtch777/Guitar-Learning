import unittest
import length_inheritance as L
A,B=L.INHERITING
def rows(lengths,edges={},rhythm={}):return [{'Phrase #':i,'Length (beats)':l,A:edges.get(i,'none'),B:rhythm.get(i,'none'),'Intended same pitch sequence as (phrase #s)':'none','Intended variation of (phrase #s)':'none'} for i,l in enumerate(lengths,1)]
class InheritanceTests(unittest.TestCase):
 def test_reciprocal_earliest(self):
  r=rows([6,2,9],{2:'3',3:'2'});m=L.resolve(r);self.assertEqual(r[2]['Length (beats)'],2);self.assertEqual(r[2]['Length source phrase #'],2)
 def test_directed_later_target_chain(self):
  r=rows([6,2,3,4],{2:'3',3:'4'});L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,4,4,4])
 def test_seed_authoritative(self):
  r=rows([6,2,3],{1:'2',2:'3'});L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,6,6])
 def test_rhythm_chain(self):
  r=rows([6,2,3],rhythm={2:'1',3:'2'});L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,6,6])
 def test_pitch_and_variation_no_inheritance(self):
  r=rows([6,2,3]);r[1]['Intended same pitch sequence as (phrase #s)']='1';r[2]['Intended variation of (phrase #s)']='1';L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,2,3])
 def test_conflicting_sources(self):
  r=rows([6,2,3,4],{4:'2; 3'});m=L.resolve(r);self.assertTrue(m['source_conflicts']);self.assertEqual([x['Length (beats)'] for x in r],[6,2,3,4])
 def test_unknown_count_not_target(self):
  r=rows([6,2,3],{3:'1; unknown comparisons: 2'});m=L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,2,6]);self.assertTrue(m['unknown_link_warnings'])
 def test_invalid_targets(self):
  for value in ['99','-1','0','2']:
   r=rows([6,2],{2:value})
   with self.assertRaises(ValueError):L.resolve(r)
 def test_cycle_earliest(self):
  r=rows([6,2,3,4],{2:'3',3:'4',4:'2'});L.resolve(r);self.assertEqual([x['Length (beats)'] for x in r],[6,2,2,2])
 def test_positions_and_labels(self):
  r=rows([6,1.5,2],{2:'1'});old=r[1][A];L.resolve(r);self.assertEqual(r[1][A],old);self.assertEqual([(x['Start position (beats)'],x['End position (beats)']) for x in r],[(0,6),(6,12),(12,14)])
if __name__=='__main__':unittest.main()
