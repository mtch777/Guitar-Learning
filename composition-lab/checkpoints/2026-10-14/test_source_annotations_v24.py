import unittest
from fractions import Fraction
from pathlib import Path
from source_annotations_v24 import score_annotations,review_cross_reference

BASE=Path('/mnt/data')
CHET=BASE/'Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp'
CSV=BASE/'V21_Music_Validation/V21_human_review.csv'

class ReferenceExtractionTests(unittest.TestCase):
 def test_chord_catalog_correctly_uses_item_name(self):
  a=score_annotations(CHET)
  self.assertEqual(a['chords'][0]['chord_symbol'],'Em9')
  self.assertEqual(len(a['unmapped_chord_references']),0)
 def test_source_chord_counts(self):
  a=score_annotations(CHET)
  self.assertEqual(len(a['chords']),69)
  self.assertTrue(all(not c['verified'] for c in a['chords']))
 def test_section_count(self):
  a=score_annotations(CHET)
  self.assertEqual(len(a['sections']),4)
 def test_annotation_alignment(self):
  a=score_annotations(CHET)
  rows=review_cross_reference(CSV,[a])
  self.assertEqual(len(rows),60)
  self.assertEqual(sum(r['source_gp_chord_status']=='present' for r in rows),3)
 def test_review_human_labels_unmodified(self):
  import csv
  with CSV.open(newline='') as f: orig=list(csv.DictReader(f))
  rows=review_cross_reference(CSV,[score_annotations(CHET)])
  for a,b in zip(orig,rows):
   self.assertEqual(a['human_chord_label'],b['human_chord_label'])
   self.assertEqual(a['human_phrase_boundary'],b['human_phrase_boundary'])
   self.assertEqual(b['reference_verified'],'false')
 def test_review_cannot_claim_accuracy(self):
  rows=review_cross_reference(CSV,[score_annotations(CHET)])
  self.assertFalse(any(r['human_chord_label'] for r in rows))
 def test_source_symbol_format_preserved(self):
  a=score_annotations(CHET)
  names={c['chord_symbol'] for c in a['chords']}
  self.assertTrue({'Em9','A7add13'}<=names)

if __name__=='__main__':unittest.main()