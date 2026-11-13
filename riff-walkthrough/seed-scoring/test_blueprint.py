import csv,pathlib,unittest,os
import blueprint as B
P=pathlib.Path(__file__).parent
class BlueprintTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  path=pathlib.Path(os.environ.get('RIFF_CSV',str(P.parent/'csv-current/all_riffs_phrase_composition.csv')))
  cls.ref=[]
  with path.open(encoding='utf-8-sig') as f:
   for row in csv.DictReader(f):
    if row['Riff ID']=='riff:c5c293d7d754bac1dba8' and row['Phrase #']=='1':cls.seed=row
    if row['Riff ID']=='riff:df675241626b482a53a0':cls.ref.append(row)
  cls.rows,cls.meta=B.build(cls.seed,cls.ref)
 def test_shape(self):self.assertEqual(len(self.rows),24);self.assertEqual(self.meta['blueprint_total_beats'],54.0)
 def test_seed_core(self):
  self.assertEqual(self.rows[0]['Length (beats)'],6);self.assertEqual(self.rows[0]['Phrase role'],self.seed['Phrase role'])
 def test_all_reference_targets_preserved(self):
  for row,ref in zip(self.rows,self.ref):
   for key,original in B.RELATION_FIELDS.items():self.assertEqual(row[key],ref[original])
 def test_no_detail_fields(self):
  allowed={'Phrase #','Length (beats)','Phrase role','Accent function','Dominant texture','Relationship status','Length conflict','Original length (beats)','Start position (beats)','End position (beats)','Length source phrase #','Length resolution'}|set(B.RELATION_FIELDS)
  for row in self.rows:self.assertEqual(set(row),allowed)
  self.assertFalse(self.meta['notes_or_rhythm_copied']);self.assertFalse(self.meta['optional_scaffold_features_copied'])
 def test_accent_no_note_detail(self):
  self.assertTrue(all('source note' not in r['Accent function'] for r in self.rows))
 def test_three_seed_targets_inherit_length(self):
  self.assertEqual({c['phrase'] for c in self.meta['length_changes']},{4,13,16})
  self.assertFalse(self.meta['length_conflicts'])
  self.assertTrue(all(self.rows[i-1]['Length (beats)']==6 for i in [1,4,13,16]))
  self.assertEqual(self.rows[-1]['End position (beats)'],54)
 def test_plans_not_identity_claim(self):
  self.assertTrue(all('Intended targets only; unverified' in r['Relationship status'] for r in self.rows))
if __name__=='__main__':unittest.main()
