"""Sampling freezes candidate choice and preserves failures without real scores."""
import json
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch
from sample_reversible_qa_song import sample


class SamplingTests(unittest.TestCase):
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
