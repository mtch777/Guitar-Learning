import csv
import tempfile
import unittest
from pathlib import Path
from reference_validation_v22 import evaluate_rows,evaluate_file,parse_chord

class ReviewEvaluation(unittest.TestCase):
    def row(self,i,**kwargs):
        x=dict(source_file='test.gp',track_index='0',onset_q=str(i),candidate_chord='D minor',
               human_chord_label='',predicted_phrase_boundary='false',human_phrase_boundary='',
               candidate_score_uncalibrated='0.8')
        x.update(kwargs);return x

    def test_blank_is_unknown_not_zero_accuracy(self):
        r=evaluate_rows([self.row(0),self.row(1)])
        self.assertIsNone(r['chord']['top1_accuracy'])
        self.assertIsNone(r['phrase_boundary']['precision'])
        self.assertEqual(r['chord']['reviewed'],0)

    def test_chord_enharmonics(self):
        self.assertEqual(parse_chord('Db minor7'),parse_chord('C# minor7'))
        self.assertNotEqual(parse_chord('D minor'),parse_chord('D major'))

    def test_mixed_labels(self):
        rows=[self.row(0,human_chord_label='D minor',human_phrase_boundary='yes',predicted_phrase_boundary='true'),
              self.row(1,human_chord_label='D major',human_phrase_boundary='no',predicted_phrase_boundary='true'),
              self.row(2,human_chord_label='unknown',human_phrase_boundary='yes',predicted_phrase_boundary='false'),
              self.row(3,human_chord_label='D minor',human_phrase_boundary='no',predicted_phrase_boundary='false')]
        v=evaluate_rows(rows)
        self.assertEqual(v['chord']['reviewed'],3)
        self.assertEqual(v['chord']['top1_accuracy'],0.6667)
        self.assertEqual(v['phrase_boundary']['tp'],1)
        self.assertEqual(v['phrase_boundary']['fp'],1)
        self.assertEqual(v['phrase_boundary']['fn'],1)
        self.assertEqual(v['phrase_boundary']['tn'],1)
        self.assertEqual(v['phrase_boundary']['f1'],0.5)

    def test_reject_duplicate(self):
        v=evaluate_rows([self.row(0),self.row(0)])
        self.assertEqual(len(v['invalid_rows']),1)

    def test_invalid_label_is_not_counted(self):
        v=evaluate_rows([self.row(0,human_phrase_boundary='perhaps')])
        self.assertEqual(len(v['invalid_rows']),1)
        self.assertEqual(v['phrase_boundary']['reviewed'],0)

    def test_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.csv';d=self.row(0,human_chord_label='D minor')
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=d.keys());w.writeheader();w.writerow(d)
            self.assertEqual(evaluate_file(p)['chord']['top1_accuracy'],1.0)

if __name__=='__main__':unittest.main()