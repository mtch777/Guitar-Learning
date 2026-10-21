"""Rhythm lift recovers the exact canonical parent without any onset payload."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_reversible_ties import capture,measure,beat
import reversible_song as song
import reversible_written_clock as clock
import reversible_rhythm as rhythm
from reversible_relationships import ConstraintError


class RhythmTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def parent(self,bars):
        capture(self.path,bars)
        return clock.encode(song.encode(song.extract(self.path,controls=True)))

    def test_source_free_exact_parent_and_no_onset_channel_or_hashes(self):
        parent=self.parent([measure([beat(duration=(1,8)),beat(duration=(3,8))]),measure([beat(duration=(1,8)),beat(duration=(3,8))])]);saved=deepcopy(parent)
        with patch.object(Path,"open",side_effect=AssertionError("No source")),patch("builtins.open",side_effect=AssertionError("No source")):
            upper=rhythm.encode(parent);restored=rhythm.decode(upper)
        self.assertEqual(parent,saved);self.assertEqual(restored,parent)
        old=clock.topology(parent["lower"])["beat_patterns"];new=clock.topology(upper["lower"]["lower"])["beat_patterns"]
        self.assertNotIn("onset_q",json.dumps(new))
        self.assertTrue(set(new["definitions"]).isdisjoint(old["definitions"]))
        expected=deepcopy(parent);clock.topology(expected["lower"])["beat_patterns"]=new
        self.assertEqual(upper["lower"],expected)

    def test_grace_rest_empty_voice_and_overflow_keep_exact_parent(self):
        grace=beat(duration=(1,16));grace["graceNote"]="beforeBeat"
        rest=dict(duration=[1,4],rest=True,notes=[dict(rest=True)])
        first=measure([grace,beat(duration=(1,2)),rest,beat(duration=(1,2))]);first["signature"]=[3,4]
        first["voices"].append(dict(beats=[]))
        parent=self.parent([first,measure([beat()])]);self.assertEqual(rhythm.decode(rhythm.encode(parent)),parent)

    def test_full_bar_rest_and_short_pickup_do_not_need_absolute_onsets(self):
        parent=self.parent([dict(signature=[5,8],rest=True,voices=[dict(rest=True,beats=[dict(rest=True,type=1,duration=[1,1],notes=[dict(rest=True)])])]),measure([beat()])])
        self.assertEqual(rhythm.decode(rhythm.encode(parent)),parent)
        capture(self.path,[measure([beat(duration=(1,8))]),measure([beat()])]);p=self.path/"track-0.json";part=json.loads(p.read_text());part["anacrusis"]=True;p.write_text(json.dumps(part))
        parent=clock.encode(song.encode(song.extract(self.path,controls=True)))
        self.assertEqual(rhythm.decode(rhythm.encode(parent)),parent)

    def test_cached_onsets_extra_fields_and_wrong_predecessor_refused(self):
        upper=rhythm.encode(self.parent([measure([beat()])]))
        for kind in ["channel","payload","predecessor"]:
            bad=deepcopy(upper)
            if kind=="channel":clock.topology(bad["lower"]["lower"])["beat_patterns"]["channels"]["onset_q"]=dict(translated=True,scale="unit")
            elif kind=="payload":bad["onset_cache"]=["0"]
            else:bad["lower"]["schema"]="other"
            with self.assertRaises(ConstraintError):rhythm.decode(bad)

    def test_same_guarded_runner_accepts_highest_rhythm_only(self):
        capture(self.path,[measure([beat(),beat(duration=(1,8))]),measure([beat()])])
        from run_reversible_tier_qa import run
        out=self.path/"rhythm-qa";report=run(self.path,out,rhythm=True)
        self.assertEqual(report["status"],"pass_declared_scope")
        for key in ["rhythm_parent_roundtrip","clock_parent_roundtrip","owned_song_roundtrip"]:self.assertEqual(report[key],"pass")
        highest=json.loads((out/"isolated/tier2-only.json").read_text())
        self.assertEqual(highest["schema"],"rhythm-driven-clock/1")
        self.assertNotIn("onset_q",json.dumps(clock.topology(highest["lower"]["lower"])["beat_patterns"]))
        self.assertEqual(json.loads((out/"isolated/reconstructed.json").read_text())["scope"],"rhythm-driven-clock/1")

    def test_parent_with_nonchronological_offset_is_not_silently_repaired(self):
        parent=self.parent([measure([beat(),beat()])]);patterns=clock.topology(parent["lower"])["beat_patterns"]
        definition=next(iter(patterns["definitions"].values()));definition["parameters"]["onset_q"][1]="2"
        with self.assertRaisesRegex(ConstraintError,"exact canonical parent"):rhythm.encode(parent)


if __name__=="__main__":unittest.main()
