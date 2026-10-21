"""Shared written origins: source-free inverse, uncertainty and rejection tests."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_reversible_ties import capture,measure,beat
import reversible_song as song
import reversible_temporal as temporal
import reversible_written_clock as clock
from reversible_relationships import ConstraintError


class WrittenClockTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def upper(self,measures):
        capture(self.path,measures)
        return song.encode(song.extract(self.path,controls=True))

    def test_roundtrip_removes_only_origins_and_does_not_read_source(self):
        prior=self.upper([measure([beat()]),measure([beat()])]);saved=deepcopy(prior)
        with patch.object(Path,"open",side_effect=AssertionError("No source")):
            model=clock.encode(prior)
            self.assertTrue(all("onset_q" not in o["anchors"] for o in clock.topology(model["lower"])["beat_patterns"]["occurrences"]))
            self.assertEqual(clock.decode(model),prior)
        self.assertEqual(prior,saved)
        expected=deepcopy(prior)
        for o in clock.topology(expected)["beat_patterns"]["occurrences"]:del o["anchors"]["onset_q"]
        self.assertEqual(model["lower"],expected)
        self.assertEqual([f["start_q"] for f in clock.context(model["lower"])[0]],["0","4"])

    def test_poly_part_short_pickup_ignores_whole_rest_and_grace(self):
        capture(self.path,[measure([beat()]),measure([beat()])])
        p=self.path/"track-0.json";first=json.loads(p.read_text());first["anacrusis"]=True
        second=deepcopy(first);second["partId"]=1;second.pop("anacrusis")
        grace=beat(duration=(1,1));grace["graceNote"]="beforeBeat"
        second["measures"][0]["voices"][0]["beats"]=[grace,beat(duration=(1,2))]
        second["measures"][0]["rest"]=True
        second["measures"][0]["voices"].append(dict(rest=True,beats=[dict(rest=True,type=1,duration=[1,1],notes=[dict(rest=True)])]))
        p.write_text(json.dumps(first));(self.path/"track-1.json").write_text(json.dumps(second))
        meta=json.loads((self.path/"metadata.json").read_text());meta["tracks"].append(dict(partId=1));(self.path/"metadata.json").write_text(json.dumps(meta))
        prior=song.encode(song.extract(self.path,controls=True));model=clock.encode(prior)
        frames,_=clock.context(model["lower"])
        self.assertEqual(frames[0]["span_q"],"2");self.assertEqual(frames[0]["status"],"observed_short_pickup")
        self.assertEqual(frames[1]["start_q"],"2");self.assertEqual(clock.decode(model),prior)

    def test_pickup_flag_without_occupancy_does_not_invent_shortening(self):
        rest=dict(rest=True,type=1,duration=[1,1],notes=[dict(rest=True)])
        m=dict(signature=[5,8],rest=True,voices=[dict(rest=True,beats=[rest])])
        capture(self.path,[m,measure([beat()])]);p=self.path/"track-0.json";part=json.loads(p.read_text());part["anacrusis"]=True;p.write_text(json.dumps(part))
        prior=song.encode(song.extract(self.path,controls=True));model=clock.encode(prior)
        frames,_=clock.context(model["lower"])
        self.assertEqual(frames[0]["span_q"],"5/2")
        self.assertEqual(frames[0]["status"],"pickup_flag_without_independent_occupancy")
        self.assertEqual(clock.decode(model),prior)

    def test_overflow_never_moves_next_nominal_bar(self):
        bars=[measure([beat() for _ in range(4)]),measure([beat()])]
        for m in bars:m["signature"]=[3,4]
        prior=self.upper(bars)
        model=clock.encode(prior);frames,_=clock.context(model["lower"])
        self.assertEqual(frames[1]["start_q"],"3");self.assertEqual(clock.decode(model),prior)

    def test_missing_initial_meter_and_invalid_meter_refuse_default(self):
        m=measure([beat()]);m.pop("signature");prior=self.upper([m])
        with self.assertRaisesRegex(ConstraintError,"initial meter"):clock.encode(prior)
        prior=self.upper([measure([beat()])]);facts=temporal.decode(prior["temporal"])
        facts["records"][0]["fields"]["numerator"]["value"]="0";prior["temporal"]=temporal.encode(facts)
        with self.assertRaisesRegex(ConstraintError,"Unusable meter"):clock.encode(prior)

    def test_empty_voices_do_not_require_fabricated_origins(self):
        prior=self.upper([dict(signature=[4,4],voices=[dict(beats=[])])])
        model=clock.encode(prior);self.assertEqual(clock.decode(model),prior)
        self.assertEqual(clock.topology(model["lower"])["beat_patterns"]["occurrences"],[])

    def test_conflicting_declarations_refuse_a_sorted_first_winner(self):
        capture(self.path,[measure([beat()])]);part=json.loads((self.path/"track-0.json").read_text());part["partId"]=1
        (self.path/"track-1.json").write_text(json.dumps(part))
        meta=json.loads((self.path/"metadata.json").read_text());meta["tracks"].append(dict(partId=1));(self.path/"metadata.json").write_text(json.dumps(meta))
        prior=song.encode(song.extract(self.path,controls=True));facts=temporal.decode(prior["temporal"])
        facts["records"][1]["fields"]["numerator"]["value"]="3"
        prior["temporal"]=temporal.encode(facts);song.validate(prior)
        with self.assertRaisesRegex(ConstraintError,"Conflicting written meter"):clock.encode(prior)

    def test_tempo_addresses_link_without_guessing_missing_positions(self):
        capture(self.path,[measure([beat()]),measure([beat()])]);p=self.path/"track-0.json";part=json.loads(p.read_text())
        part["measures"][0]["voices"][0]["beats"][0]["tempo"]=dict(bpm=120,type=4)
        part["automations"]=dict(tempo=[dict(bpm=120,type=4,measure=1,position=0.25),dict(bpm=120,type=4,measure=0),dict(bpm=120,type=4,measure=9,position=0),dict(bpm=120,type=4,measure=0,position=None)])
        p.write_text(json.dumps(part));model=clock.encode(song.encode(song.extract(self.path,controls=True)))
        view=clock.timing_view(model);addresses=view["tempo_addresses"]
        self.assertEqual(addresses[0]["event_q"],"0")
        self.assertEqual(addresses[1]["event_q"],"5")
        self.assertEqual(addresses[2]["status"],"missing_source_address")
        self.assertEqual(addresses[3]["status"],"source_measure_out_of_range")
        self.assertEqual(addresses[4]["status"],"unsupported_source_address")
        from check_reversible_written_clock import check
        self.assertEqual(check(self.path,model)["status"],"pass")
        self.assertEqual(view["seconds"],"NOT_IMPLEMENTED")

    def test_unknown_pickup_types_are_not_silently_false(self):
        for value in [1,0,"yes",{},[]]:
            capture(self.path,[measure([beat()])]);p=self.path/"track-0.json";part=json.loads(p.read_text());part["anacrusis"]=value;p.write_text(json.dumps(part))
            prior=song.encode(song.extract(self.path,controls=True))
            with self.assertRaisesRegex(ConstraintError,"Unverified pickup"):clock.encode(prior)

    def test_existing_guarded_runner_reverses_clock_highest_only(self):
        capture(self.path,[measure([beat()]),measure([beat()])])
        from run_reversible_tier_qa import run
        out=self.path/"clock-qa";report=run(self.path,out,clock=True)
        self.assertEqual(report["status"],"pass_declared_scope")
        self.assertEqual(report["clock_parent_roundtrip"],"pass")
        self.assertEqual(report["owned_song_roundtrip"],"pass")
        self.assertEqual(report["independent_clock_check"]["frames"],2)
        highest=json.loads((out/"isolated/tier2-only.json").read_text())
        self.assertEqual(highest["schema"],"shared-written-clock/1")
        restored=json.loads((out/"isolated/reconstructed.json").read_text())
        self.assertEqual(restored["scope"],"shared-written-clock/1")
        trace=json.loads((out/"isolated/read-audit.json").read_text())
        reads=[e for e in trace["open_events"] if e["operation"]=="read"]
        runtime=Path(trace["runtime_root"]);isolated=(out/"isolated").resolve()
        successful=[Path(e["path"]) for e in reads if e["allowed"]]
        self.assertTrue(all(p.is_relative_to(runtime) or p.parent==isolated and (p.suffix==".py" or p.name=="tier2-only.json") for p in successful))
        # Importers may try a bytecode cache; the guard correctly DENIES it and
        # Python then reads the explicitly permitted source module instead.
        denied=[Path(e["path"]) for e in reads if not e["allowed"]]
        self.assertTrue(all(p.parent.name=="__pycache__" and p.parent.parent==isolated for p in denied))
        self.assertFalse(any(Path(e["path"]).name in {"track-0.json","metadata.json","tier1-checker-only.json","owned-checker-only.json"} for e in reads))

    def test_raw_oracle_detects_bad_derived_views_independently(self):
        prior=self.upper([measure([beat()]),measure([beat()])]);model=clock.encode(prior)
        import check_reversible_written_clock as oracle
        view=clock.timing_view(model);bad=deepcopy(view);bad["frames"][1]["start_q"]="5"
        with patch.object(oracle,"timing_view",return_value=bad):
            with self.assertRaisesRegex(ValueError,"frame mismatch"):oracle.check(self.path,model)
        self.assertEqual(oracle.check(self.path,model)["frames"],2)

    def test_duplicate_origin_cache_and_malformed_parent_are_rejected(self):
        model=clock.encode(self.upper([measure([beat()])]))
        bad=deepcopy(model);clock.topology(bad["lower"])["beat_patterns"]["occurrences"][0]["anchors"]["onset_q"]="0"
        with self.assertRaisesRegex(ConstraintError,"Duplicated"):clock.decode(bad)
        bad=deepcopy(model);bad["raw_cache"]={}
        with self.assertRaises(ConstraintError):clock.decode(bad)
        bad=deepcopy(model);definition=next(iter(clock.topology(bad["lower"])["beat_patterns"]["definitions"].values()));definition["parameters"]["onset_q"]=[]
        with self.assertRaises(ConstraintError):clock.decode(bad)
        bad=deepcopy(model);bad["lower"]["cache"]={}
        with self.assertRaises(ConstraintError):clock.decode(bad)


if __name__=="__main__":unittest.main()
