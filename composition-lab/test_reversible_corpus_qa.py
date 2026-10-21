"""Batch failure retention and source-integrity regression with real pipeline."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_reversible_ties import capture,measure,beat
from run_reversible_corpus_qa import batch


class CorpusQATests(unittest.TestCase):
    def test_control_mode_is_frozen_and_checked_in_same_pipeline(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus=root/"corpus";corpus.mkdir();p=corpus/"one";p.mkdir()
            m=measure([beat()]);m.update(repeatStart=True,repeat=2)
            capture(p,[m]);out=root/"out";result=batch(corpus,out,controls=True)
            self.assertEqual(result["passed"],1)
            manifest=json.loads((out/"manifest.json").read_text())
            self.assertEqual(manifest["mode"],"controls")
            self.assertIn("reversible_control.py",manifest["engine_hashes"])
            self.assertIn("check_reversible_control.py",manifest["engine_hashes"])
            summary=json.loads((out/"summary.json").read_text())
            self.assertEqual(summary["results"][0]["control"]["regions"],1)

    def test_malformed_case_is_retained_and_next_case_runs_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus=root/"corpus";corpus.mkdir()
            (corpus/"a-invalid").mkdir();valid=corpus/"b-valid";valid.mkdir()
            capture(valid,[measure([beat()])]);out=root/"results"
            result=batch(corpus,out)
            self.assertEqual(result["cases"],2);self.assertEqual(result["passed"],1)
            self.assertTrue((out/"case-a-invalid/failure.json").exists())
            summary=json.loads((out/"summary.json").read_text())
            self.assertEqual([x["id"] for x in summary["results"]],["a-invalid","b-valid"])
            self.assertEqual(result["integrity"]["source_hash_mismatches"],[]);self.assertTrue(result["integrity"]["engine_unchanged"])
            with self.assertRaises(ValueError):batch(corpus,out)

    def test_directory_addition_is_reported_outside_frozen_case_set(self):
        import run_reversible_corpus_qa as module
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus=root/"corpus";corpus.mkdir();p=corpus/"one";p.mkdir();capture(p,[measure([beat()])])
            original=module.run
            def add(*args,**kwargs):
                value=original(*args,**kwargs);(corpus/"late").mkdir();return value
            with patch.object(module,"run",side_effect=add):result=batch(corpus,root/"out")
            self.assertEqual(result["cases"],1);self.assertEqual(result["integrity"]["added_directories"],["late"])

    def test_comparison_baseline_is_sealed_before_execution(self):
        import run_reversible_corpus_qa as module
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus=root/"corpus";corpus.mkdir();p=corpus/"one";p.mkdir();capture(p,[measure([beat()])])
            prior=root/"previous/case-one/isolated";prior.mkdir(parents=True);file=prior/"tier2-only.json";file.write_text('{}')
            original=module.run
            def change(*args,**kwargs):
                value=original(*args,**kwargs);file.write_text('{"changed":true}');return value
            with patch.object(module,"run",side_effect=change):result=batch(corpus,root/"out",root/"previous")
            self.assertEqual(result["passed"],0);self.assertEqual(result["integrity"]["baseline_hash_mismatches"],["one"])
            error=json.loads((root/"out/case-one/batch-error.json").read_text())
            self.assertIn("Comparison baseline changed",error["traceback"])
            self.assertEqual(error["last_persisted_artifact"],"qa.json")

    def test_engine_change_stops_without_silently_restarting(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus=root/"corpus";corpus.mkdir();p=corpus/"one";p.mkdir();capture(p,[measure([beat()])])
            with patch("run_reversible_corpus_qa.code_hashes",side_effect=[{"a":"before"},{"a":"after"}]):
                with self.assertRaises(RuntimeError):batch(corpus,root/"out")
            self.assertTrue((root/"out/blocked.json").exists())
            self.assertFalse((root/"out/case-one").exists())


if __name__=="__main__":unittest.main()
