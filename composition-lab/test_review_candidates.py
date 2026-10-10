"""Review candidates stay UNREVIEWED until a human explicitly labels them."""
import csv,tempfile,unittest
from pathlib import Path
from review_candidates import audit_rows,write_audit,score_reviews

class ReviewTests(unittest.TestCase):
    def sample(self):
        motifs=[{"file":"a.gp","tracks":[{"track":"Guitar","candidate_variant_motifs":[
            {"bars":[2,8],"length_bars":2,"edit_distance":.1,
             "notes":[9,10],"first_pitch_shift":2}]}]}]
        structure=[{"file":"a.gp","blind_boundary_candidates":[{
            "measure":5,"score":.8,"harmonic_change":.7,"density_change":.3}],
            "harmonic_context":[{"measure":1,"bass_root_hypothesis":"E",
                "chord_candidates":[{"name":"E minor","score":.8},
                {"name":"E power","score":.75}],
                "pitch_class_weights":{"E":2,"G":1}}]}]
        return motifs,structure
    def test_candidate_rows(self):
        rows=audit_rows(*self.sample())
        self.assertEqual({r["kind"] for r in rows},
                         {"motif","section_boundary","chord"})
        self.assertTrue(all(r["review_label"]=="" for r in rows))
    def test_score_requires_reviews(self):
        rows=audit_rows(*self.sample())
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"audit.csv";write_audit(rows,path)
            report=score_reviews(path)
            self.assertIsNone(report["chord"]["confirmed_share_of_reviewed"])
            self.assertEqual(report["chord"]["unreviewed"],1)
    def test_explicit_review(self):
        rows=audit_rows(*self.sample())
        rows[0]["review_label"]="confirmed"
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"audit.csv";write_audit(rows,path)
            report=score_reviews(path)
            self.assertEqual(report["motif"]["confirmed"],1)
            self.assertEqual(report["motif"]["confirmed_share_of_reviewed"],1.0)

if __name__=="__main__":
    unittest.main()
