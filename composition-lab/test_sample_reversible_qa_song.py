"""Sampling freezes candidate choice and preserves failures without real scores."""
import json
from pathlib import Path
import random
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch
from sample_reversible_qa_song import ARTIST_PROTOCOL, sample
from three_gate_qa import freeze_valid, portability, run


class SamplingTests(unittest.TestCase):
    # Persistent acceptance checklist: unchanged legacy replay; artist-filtered
    # single-draw replay; frozen population before capture; retained failures;
    # independent source/artist check. All fixtures below are authored, no network.
    def fake_client(self, output, records, *, metadata_artist="Invent Animate", failure=None):
        calls = []
        class Client:
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def search(self, pattern, size=100):
                calls.append(("search", pattern, size))
                return records
            def meta(self, sid):
                calls.append(("meta", sid))
                frozen = json.loads((output / "selection.json").read_text())
                assert frozen["status"] == "selected_before_capture"
                assert frozen["selected_song_id"] == sid
                if "sampling_protocol" in frozen:
                    assert frozen["returned_population"] == [
                        dict(songId=r["songId"], artist=r["artist"]) for r in records]
                    assert frozen["candidate_ids"] == sorted(set(frozen["candidate_ids"]))
                if failure == "meta": raise RuntimeError("authored metadata failure")
                return dict(songId=sid, revisionId=7, image="authored", artist=metadata_artist,
                            artistId=99, title="Authored fixture", tracks=[{}])
            def track(self, sid, revision, image, part):
                calls.append(("track", sid, part))
                if failure == "track": raise RuntimeError("authored track failure")
                return dict(songId=sid, revisionId=revision, partId=part, tuning=[40], measures=[
                    dict(signature=[4, 4], voices=[dict(beats=[
                        dict(duration=[1, 1], notes=[dict(string=0, fret=3)])])])])
        module = ModuleType("songsterr_dl.client")
        module.SongsterrClient = Client
        return module, calls

    def test_legacy_success_end_to_end_keeps_letter_draw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "old"
            module, calls = self.fake_client(output, [dict(songId=i) for i in (11, 12, 13)], metadata_artist="Fixture")
            with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                receipt = sample(output, root, seed=19)
            rng = random.Random(19)
            self.assertEqual(calls[0], ("search", rng.choice("abcdefghijklmnopqrstuvwxyz"), 100))
            self.assertEqual(receipt["selected_song_id"], rng.choice([11, 12, 13]))
            self.assertNotIn("sampling_protocol", receipt)
            self.assertEqual(freeze_valid(receipt), [])
            self.assertEqual(portability(output / "capture", output / "selection.json")["status"], "PASS")

    def test_artist_selection_and_independent_three_gate_pipeline(self):
        records = [dict(songId=19, artist="Wrong artist", title="Invent Animate"),
                   dict(songId=12, artist=" INVENT,  ANIMATE "),
                   dict(songId=11, artist="Invent Animate"),
                   dict(songId=12, artist="invent animate"),
                   dict(songId=13, artist="Invent Animate"),
                   dict(songId=14, artist="Invent Animate"),
                   dict(songId=15, artist="Invent Animate")]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "new"; corpus = root / "corpus"
            (corpus / "13").mkdir(parents=True)
            prior = root / "previous.json"; prior.write_text(json.dumps(dict(selected_song_id=14)))
            module, calls = self.fake_client(output, records, metadata_artist="invent, ANIMATE")
            with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                receipt = sample(output, root, corpus, 19, [prior], [15], artist=" INVENT, animate ")
            self.assertEqual(calls[0], ("search", "Invent Animate", 100))
            self.assertEqual(receipt["sampling_protocol"], ARTIST_PROTOCOL)
            self.assertEqual(receipt["candidate_ids"], [11, 12])
            self.assertEqual(receipt["excluded_ids"], [13, 14, 15])
            self.assertEqual(receipt["selected_song_id"], random.Random(19).choice([11, 12]))
            self.assertEqual(len(receipt["returned_population"]), len(records))
            self.assertEqual(freeze_valid(receipt), [])
            report = run(output / "capture", output / "selection.json", root / "qa")
            self.assertEqual(report["gates"]["1_portability"]["status"], "PASS", report)
            self.assertFalse(report["completion_allowed"])
            self.assertEqual(report["gates"]["2_exact_reversal"]["status"], "NOT RUN")

    def test_all_allowed_artist_names_normalize(self):
        for requested, actual, query in (("currents", " CURRENTS ", "Currents"), (" erra ", "ERRA", "ERRA")):
            with self.subTest(requested=requested), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); output = root / "new"
                module, calls = self.fake_client(output, [dict(songId=11, artist=actual)], metadata_artist=actual)
                with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                    receipt = sample(output, root, seed=19, artist=requested)
                self.assertEqual(calls[0], ("search", query, 100))
                self.assertEqual(freeze_valid(receipt), [])

    def test_artist_wrong_metadata_and_capture_failure_are_retained_without_replacement(self):
        for artist, failure in (("Currents", None), ("Invent Animate", "meta"), ("Invent Animate", "track")):
            with self.subTest(artist=artist, failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); output = root / "new"
                records = [dict(songId=i, artist="Invent Animate") for i in (11, 12)]
                module, calls = self.fake_client(output, records, metadata_artist=artist, failure=failure)
                with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                    with self.assertRaises((ValueError, RuntimeError)):
                        sample(output, root, seed=19, artist="Invent Animate")
                receipt = json.loads((output / "selection.json").read_text())
                self.assertEqual(receipt["status"], "failed_selection_or_capture")
                self.assertEqual(receipt["selected_song_id"], random.Random(19).choice([11, 12]))
                self.assertEqual(sum(c[0] == "search" for c in calls), 1)
                self.assertEqual(sum(c[0] == "meta" for c in calls), 1)
                if artist == "Currents": self.assertFalse(any(c[0] == "track" for c in calls))
                self.assertTrue(freeze_valid(receipt))
                report = run(output / "capture", output / "selection.json", root / "qa")
                self.assertEqual(report["gates"]["1_portability"]["status"], "FAIL")
                with self.assertRaisesRegex(ValueError, "Fresh"):
                    sample(output, root, seed=19, artist="Invent Animate")

    def test_empty_artist_population_and_bad_rows_fail_before_metadata(self):
        cases = [[], [dict(songId=11, artist="Invent Animate Cover Band")],
                 [dict(songId=11, artist="Invent Animate"), dict(songId=11, artist="Currents")],
                 [dict(songId=True, artist="Invent Animate")], [dict(songId=11, artist=None)],
                 [dict(songId=i + 1, artist="Invent Animate") for i in range(101)]]
        for records in cases:
            with self.subTest(records=records[:2]), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); output = root / "new"
                module, calls = self.fake_client(output, records)
                with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                    with self.assertRaises(ValueError): sample(output, root, seed=19, artist="Invent Animate")
                receipt = json.loads((output / "selection.json").read_text())
                self.assertEqual(receipt["status"], "failed_selection_or_capture")
                self.assertEqual(receipt["returned_population"], records)
                self.assertEqual(len(calls), 1)

    def test_unapproved_artist_rejected_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "new"
            module, calls = self.fake_client(output, [])
            with patch.dict("sys.modules", {"songsterr_dl.client": module}):
                with self.assertRaisesRegex(ValueError, "Only Invent Animate"):
                    sample(output, root, seed=19, artist="Gary Moore")
            self.assertEqual(calls, [])
            self.assertEqual(json.loads((output / "selection.json").read_text())["status"], "failed_selection_or_capture")

    def test_selection_frozen_before_metadata_and_failure_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);output=root/"sample";excluded=root/"old";excluded.mkdir();(excluded/"12").mkdir()
            class Client:
                def __init__(self,**kwargs):pass
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def search(self,*args,**kwargs):return [dict(songId=i) for i in (11,12,13)]
                def meta(self,sid):
                    frozen=json.loads((output/"selection.json").read_text())
                    assert frozen["status"]=="selected_before_capture" and frozen["selected_song_id"]==sid
                    raise RuntimeError("deliberate capture failure")
            module=ModuleType("songsterr_dl.client");module.SongsterrClient=Client
            with patch.dict("sys.modules",{"songsterr_dl.client":module}):
                with self.assertRaisesRegex(RuntimeError,"deliberate"):sample(output,root,excluded,19)
            result=json.loads((output/"selection.json").read_text())
            self.assertEqual(result["candidate_ids"],[11,13]);self.assertEqual(result["status"],"failed_selection_or_capture")
            self.assertIn(result["selected_song_id"],[11,13])
            with self.assertRaisesRegex(ValueError,"Fresh"):sample(output,root,seed=19)


if __name__=="__main__":unittest.main()
