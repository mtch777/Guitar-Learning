"""Written-position equation, ownership and no-cache tests on synthetic captures."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from test_reversible_topology import capture
from reversible_positions import extract,encode,decode,event_view,position_equation
from reversible_relationships import solve,ConstraintError


class ReversiblePositionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);capture(self.folder)
    def tearDown(self):self.temp.cleanup()
    def change(self,**fields):
        file=self.folder/"track-0.json";part=json.loads(file.read_text());part.update(fields);file.write_text(json.dumps(part));return part
    def roundtrip(self):
        facts=extract(self.folder);upper=encode(facts)
        self.assertNotIn("pitch_patterns",upper["topology"])
        self.assertTrue(all("base_pitch" not in n for n in facts["topology"]["notes"]))
        self.assertEqual(decode(upper),facts)
        self.assertEqual(event_view(decode(upper)),event_view(facts))
        return facts,upper

    def test_nonstandard_tuning_capo_and_alternate_string_witness(self):
        part=self.change(tuning=[33,40,45],capo=2)
        notes=part["measures"][0]["voices"][0]["beats"][1]["notes"]
        notes[0].update(string=0,fret=7);notes[2].update(string=1,fret=0)
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts,upper=self.roundtrip();positions={p["id"]:p for p in decode(upper)["positions"]}
        a="event:91:0:1:0:1:0";b="event:91:0:1:0:1:2"
        pitches={p["id"]:p["pitch"] for p in event_view(facts)}
        self.assertEqual(pitches[a],"42");self.assertEqual(pitches[b],"42")
        self.assertEqual(positions[a]["string"]["value"],"0")
        self.assertEqual(positions[b]["string"]["value"],"1")
        self.assertEqual(positions[b]["fret"]["value"],"0")

    def test_missing_null_and_explicit_zero_capo_are_distinct(self):
        facts,_=self.roundtrip();self.assertEqual(facts["settings"][0]["capo"],dict(present=False,value=None,number_type=None))
        self.change(capo=None);facts,_=self.roundtrip();self.assertEqual(facts["settings"][0]["capo"],dict(present=True,value=None,number_type=None))
        self.change(capo=0);facts,_=self.roundtrip();self.assertEqual(facts["settings"][0]["capo"],dict(present=True,value="0",number_type="int"))

    def test_dead_position_is_retained_without_claiming_sounding_pitch(self):
        part=self.change();part["measures"][0]["voices"][0]["beats"][1]["notes"][0].update(dead=True,fret=5)
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts,upper=self.roundtrip();ident="event:91:0:1:0:1:0"
        self.assertIsNone(next(e for e in event_view(facts) if e["id"]==ident)["pitch"])
        pos=next(p for p in decode(upper)["positions"] if p["id"]==ident)
        self.assertEqual(pos["fret"]["value"],"5");self.assertEqual(pos["dead"],dict(present=True,value=True))

    def test_percussion_code_is_not_inferred_from_missing_tuning(self):
        self.change(tuning=[],instrumentId=1024);facts,upper=self.roundtrip()
        self.assertTrue(all(e["pitch"] is None for e in event_view(facts)))
        symbols=[s for p in upper["position_patterns"]["definitions"].values() for s in p["symbols"]]
        self.assertTrue(all(s["kind"]=="percussion" for s in symbols))
        self.change(instrumentId=25);facts,upper=self.roundtrip()
        symbols=[s for p in upper["position_patterns"]["definitions"].values() for s in p["symbols"]]
        self.assertTrue(all(s["kind"]=="unmapped_position" for s in symbols))
        self.assertTrue(all(e["pitch"] is None for e in event_view(facts)))

    def test_missing_fret_invalid_string_and_float_type_preserve_explicit_states(self):
        part=self.change();notes=part["measures"][0]["voices"][0]["beats"][1]["notes"]
        notes[0].pop("fret");notes[2].update(string=99,fret=2.5)
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts,upper=self.roundtrip();positions={p["id"]:p for p in decode(upper)["positions"]}
        self.assertEqual(positions["event:91:0:1:0:1:0"]["fret"],dict(present=False,value=None,number_type=None))
        self.assertEqual(positions["event:91:0:1:0:1:2"]["fret"],dict(present=True,value="5/2",number_type="float"))
        self.assertEqual(positions["event:91:0:1:0:1:2"]["string"]["value"],"99")

    def test_same_equation_and_changed_position_anchor(self):
        equation=position_equation()
        self.assertEqual(solve(equation,dict(open_string=40,capo=2,fret=5),["position_pitch"])["position_pitch"],47)
        self.assertEqual(solve(equation,dict(open_string=40,capo=2,position_pitch=47),["fret"])["fret"],5)
        with self.assertRaises(ConstraintError):solve(equation,dict(open_string=40,capo=2,position_pitch=47,fret=6),["fret"])
        facts,upper=self.roundtrip();old={p["id"]:p for p in facts["positions"]}
        occurrence=upper["position_patterns"]["occurrences"][0]
        occurrence["anchors"]["position_pitch"]=str(F(occurrence["anchors"]["position_pitch"])+2)
        changed=decode(upper)
        for p in changed["positions"]:
            delta=2 if p["id"] in occurrence["members"] else 0
            self.assertEqual(F(p["fret"]["value"]),F(old[p["id"]]["fret"]["value"])+delta)
            self.assertEqual(p["string"],old[p["id"]]["string"])

    def test_source_payload_and_pitch_cache_injection_refused(self):
        _,upper=self.roundtrip();cases=[]
        m=deepcopy(upper);m["topology"]["pitch_patterns"]={"raw_notes":[60,64,67]};cases.append(m)
        m=deepcopy(upper);m["settings"][0]["capo"]={"raw_score":[60,64,67]};cases.append(m)
        m=deepcopy(upper);next(iter(m["position_patterns"]["definitions"].values()))["symbols"][0]["raw_note"]={"pitch":60};cases.append(m)
        m=deepcopy(upper);m["coverage"]={"raw_score":[60,64,67]};cases.append(m)
        for i,model in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):decode(model)

    def test_position_region_must_match_actual_voice_membership(self):
        _,upper=self.roundtrip();occurrence=upper["position_patterns"]["occurrences"][0]
        other=next(v["id"] for v in upper["topology"]["voices"] if v["id"]!=occurrence["region_id"])
        occurrence["region_id"]=other
        with self.assertRaises(ConstraintError):decode(upper)


if __name__=="__main__":unittest.main()
