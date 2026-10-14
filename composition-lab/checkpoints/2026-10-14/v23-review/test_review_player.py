import csv, json, subprocess, unittest
from pathlib import Path
from fractions import Fraction
import sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,'/mnt/data/V22_Reference_Validation')
from build_review import collect,build
from reference_validation_v22 import evaluate_rows

class ReviewPlayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=collect()
    def test_sixty_review_cases(self): self.assertEqual(len(self.data['rows']),60)
    def test_unique_identifiers(self):
        ids=[(r['source_file'],r['track_index'],r['onset_q']) for r in self.data['rows']]
        self.assertEqual(len(ids),len(set(ids)))
    def test_all_song_sources_present(self): self.assertEqual(len(self.data['scores']),5)
    def test_tracks_and_timing(self):
        for r in self.data['rows']:
            sc=self.data['scores'][r['source_file']]
            t=float(Fraction(r['onset_q']));track=int(r['track_index'])
            self.assertEqual(sc['tracks'][track],r['track_name'])
            self.assertTrue(any(e['track']==track and abs(e['t']-t)<.00001 for e in sc['notes']),r)
    def test_review_csv_v22_compatibility(self):
        report=evaluate_rows(self.data['rows'])
        self.assertFalse(report['invalid_rows'])
        self.assertIsNone(report['chord']['top1_accuracy'])
        self.assertIsNone(report['phrase_boundary']['f1'])
    def test_html_embedded_payload(self):
        html=build().read_text(encoding='utf-8')
        self.assertIn('const DATA={"rows":',html)
        self.assertIn('V23_reviewed_ground_truth.csv',html)
        self.assertNotIn('/*__PAYLOAD__*/',html)
    def test_js_syntax(self):
        html=build().read_text(encoding='utf-8')
        script=html.split('<script>',1)[1].split('</script>',1)[0]
        path=ROOT/'_syntax_test.js';path.write_text(script,encoding='utf-8')
        try:
            run=subprocess.run(['node','--check',str(path)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
        finally:path.unlink(missing_ok=True)

if __name__=='__main__':unittest.main()