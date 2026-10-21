"""Previous-input-only stage composition and structural ownership gates."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_reversible_ties import capture,measure,beat
from reversible_relationships import ConstraintError
import reversible_song as song


class OwnedSongTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        b=beat();b["tempo"]=dict(bpm=120,type=4)
        capture(self.path,[measure([b,beat(tie=True)])])
        p=self.path/"track-0.json";part=json.loads(p.read_text());part["automations"]=dict(tempo=[dict(bpm=120,type=4,measure=0,position=0)])
        p.write_text(json.dumps(part));self.facts=song.extract(self.path)
    def tearDown(self):self.temp.cleanup()

    def test_control_stage_is_source_free_and_preserves_other_slots(self):
        path=self.path/"track-0.json";part=json.loads(path.read_text())
        part["measures"][0].update(repeatStart=True,repeat=2,alternateEnding=[1])
        path.write_text(json.dumps(part));facts=song.extract(self.path,controls=True)
        original=deepcopy(facts)
        with patch.object(Path,"open",side_effect=AssertionError("Late source read")):
            prior=song.lift_temporal(song.lift_music(facts));upper=song.lift_control(prior)
            for key in ["music","temporal","identity","registry"]:self.assertEqual(prior[key],upper[key])
            self.assertEqual(song.decode(upper),facts)
        self.assertEqual(facts,original);self.assertEqual(upper["schema"],"owned-song-stages/2")
        self.assertEqual(upper["stage"],"control")
        self.assertEqual(len(upper["control"]["bindings"]),1)
        from run_reversible_tier_qa import run
        report=run(self.path,self.path/"controls-qa",controls=True)
        self.assertEqual(report["status"],"pass_declared_scope")
        self.assertEqual(report["independent_control_check"]["regions"],1)
        self.assertEqual(report["owned_song_roundtrip"],"pass")

    def test_control_version_stage_and_ownership_are_strict(self):
        facts=song.extract(self.path,controls=True)
        with self.assertRaises(ConstraintError):song.lift_control(facts)
        with self.assertRaises(ConstraintError):song.lift_control(song.encode(self.facts))
        for change in ["schema","owner","extent","extra"]:
            bad=deepcopy(facts)
            if change=="schema":bad["schema"]="owned-song-stages/1"
            elif change=="owner":bad["control"]["parts"][0]["id"]="other"
            elif change=="extent":bad["control"]["parts"][0]["measure_refs"].append("other")
            else:bad["unowned_cache"]={}
            with self.assertRaises(ConstraintError):song.encode(bad)
        # Legacy envelope keeps its original shape and result.
        self.assertNotIn("control",song.encode(self.facts))
        self.assertEqual(song.decode(song.encode(self.facts)),self.facts)

    def test_all_lifts_and_inverse_are_prior_input_only(self):
        original=deepcopy(self.facts)
        with patch("builtins.open",side_effect=AssertionError("Late source read")),patch.object(Path,"open",side_effect=AssertionError("Late source read")):
            music=song.lift_music(self.facts)
            self.assertEqual(song.digest(music["temporal"]),song.digest(self.facts["temporal"]))
            upper=song.lift_temporal(music)
            self.assertEqual(song.digest(upper["music"]),song.digest(music["music"]))
            self.assertNotIn("records",upper["temporal"])
            self.assertEqual(song.decode(upper),self.facts)
        self.assertEqual(self.facts,original)

    def test_existing_isolated_worker_reconstructs_entire_owned_scope(self):
        from run_reversible_tier_qa import run
        output=self.path/"qa";report=run(self.path,output,song=True)
        self.assertEqual(report["status"],"pass_declared_scope")
        self.assertEqual(report["owned_song_roundtrip"],"pass")
        self.assertEqual(report["independent_temporal_check"]["status"],"pass")
        upper=json.loads((output/"isolated/tier2-only.json").read_text())
        self.assertEqual(upper["schema"],"owned-song-stages/1")
        self.assertNotIn("records",upper["temporal"])
        restored=json.loads((output/"isolated/reconstructed.json").read_text())
        self.assertEqual(restored["owned_song"],self.facts)
        trace=json.loads((output/"isolated/read-audit.json").read_text())
        forbidden={str((self.path/name).resolve()) for name in ["metadata.json","track-0.json"]}
        self.assertFalse(any(x["path"] in forbidden for x in trace["open_events"]))

    def test_invalid_stage_order_and_arbitrary_cache_fields_refused(self):
        with self.assertRaises(ConstraintError):song.lift_temporal(self.facts)
        m=song.encode(self.facts);m["raw_notes"]=[1,2]
        with self.assertRaises(ConstraintError):song.decode(m)
        m=deepcopy(self.facts);m["registry"][0]["raw_source"]={"notes":[1]}
        with self.assertRaises(ConstraintError):song.encode(m)

    def test_missing_cross_song_and_wrong_kind_owners_refused(self):
        for change in ["missing",self.facts["registry"][0]["id"]]:
            m=deepcopy(self.facts);m["temporal"]["records"][0]["owner"]=change
            with self.assertRaises(ConstraintError):song.encode(m)
        m=deepcopy(self.facts);m["registry"][0]["measure_refs"].clear()
        with self.assertRaises(ConstraintError):song.encode(m)
        m=deepcopy(self.facts);m["registry"][0]["settings_ref"]="other-song-settings"
        with self.assertRaises(ConstraintError):song.encode(m)

    def test_unsupported_automation_slots_have_explicit_part_ordinal_ownership(self):
        p=self.path/"track-0.json";part=json.loads(p.read_text())
        part["automations"]["tempo"]=[None,dict(bpm=120,type=4,text={"value":"tempo"})]
        p.write_text(json.dumps(part));f=song.extract(self.path)
        self.assertEqual(len(f["registry"][0]["automation_slots"]),2)
        self.assertEqual(song.decode(song.encode(f)),f)
        bad=deepcopy(f);bad["temporal"]["unsupported"][0]["ordinal"]=9
        with self.assertRaises(ConstraintError):song.encode(bad)
        from run_reversible_tier_qa import run
        self.assertEqual(run(self.path,self.path/"malformed-qa",song=True)["status"],"pass_declared_scope")

    def test_multiple_parts_and_empty_measures_keep_actual_source_ownership(self):
        first=json.loads((self.path/"track-0.json").read_text());first["measures"].append(dict(signature=[4,4],voices=[]))
        second=deepcopy(first);second["partId"]=1
        second["automations"]["tempo"][0]["bpm"]=90
        for name,part in [("track-0.json",first),("track-1.json",second)]:(self.path/name).write_text(json.dumps(part))
        meta=json.loads((self.path/"metadata.json").read_text());meta["tracks"].append(dict(partId=1));(self.path/"metadata.json").write_text(json.dumps(meta))
        f=song.extract(self.path);self.assertEqual(song.decode(song.encode(f)),f)
        self.assertEqual([len(p["measure_refs"]) for p in f["registry"]],[2,2])
        from check_reversible_temporal import check_ownership
        self.assertEqual(check_ownership(self.path,f["registry"],f["identity"])["status"],"pass")
        bad=deepcopy(f)
        bad["registry"][0]["measure_refs"][0],bad["registry"][1]["measure_refs"][0]=bad["registry"][1]["measure_refs"][0],bad["registry"][0]["measure_refs"][0]
        with self.assertRaises(ConstraintError):song.encode(bad)
        bad=deepcopy(f)
        bad["registry"][0]["measure_refs"][1],bad["registry"][1]["measure_refs"][1]=bad["registry"][1]["measure_refs"][1],bad["registry"][0]["measure_refs"][1]
        with self.assertRaises(ValueError):check_ownership(self.path,bad["registry"],bad["identity"])

    def test_owner_ids_are_opaque_not_parsed(self):
        f=deepcopy(self.facts);old=f["registry"][0]["id"];f["registry"][0]["id"]="opaque-part"
        for r in f["temporal"]["records"]:
            if r["owner"]==old:r["owner"]="opaque-part"
        self.assertEqual(song.decode(song.encode(f)),f)


if __name__=="__main__":unittest.main()
