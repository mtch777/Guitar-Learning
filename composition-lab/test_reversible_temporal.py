"""Isolated temporal prototype gates; no integrated song/GP inverse claim."""
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from reversible_annotations import scalar,unpack,pack
from reversible_relationships import ConstraintError
from reversible_temporal import encode,decode,extract,interpretation_status


def record(ident,kind,**fields):return dict(id=ident,owner="opaque-owner",kind=kind,fields={k:scalar(v) for k,v in fields.items()})
def facts(*rows):return dict(schema="temporal-source-observations/1",records=list(rows),unsupported=[])


class TemporalTests(unittest.TestCase):
    def check(self,source):
        model=encode(source);self.assertEqual(decode(model),source)
        return {r["id"]:r["fields"] for r in unpack(model["parameters"],{})},model

    def test_meter_and_tempo_use_same_exact_relations_and_preserve_types(self):
        rows,model=self.check(facts(record("m","meter",numerator=6,denominator=16),record("t","automation_tempo",bpm=90.0,type=4,measure=2,position=0.125,linear=False)))
        self.assertEqual(rows["m"]["nominal_span_q"]["value"],"3/2")
        self.assertEqual(rows["t"]["quarter_bpm"]["value"],"90")
        self.assertEqual(rows["t"]["position_q"]["value"],"1/2")
        self.assertNotIn("bpm",rows["t"])
        changed=deepcopy(model)
        # Type witnesses may not carry arbitrary numeric payloads.
        changed["bindings"][0]["source_numeric_types"]["numerator"]="cache"
        with self.assertRaises(ConstraintError):decode(changed)

    def test_reverse_uses_only_parameters_and_same_meter_equation(self):
        source=facts(record("m","meter",numerator=6,denominator=16))
        _,model=self.check(source)
        rows=unpack(model["parameters"],{})
        self.assertNotIn("numerator",rows[0]["fields"])
        rows[0]["fields"]["nominal_span_q"]["value"]="3"
        model["parameters"]=pack(rows,{})
        with patch("builtins.open",side_effect=AssertionError("Source access forbidden")),patch.object(Path,"open",side_effect=AssertionError("Source access forbidden")):
            restored=decode(model)
        self.assertEqual(restored["records"][0]["fields"]["numerator"],scalar(12))
        # Pure algebraic edit, not a validated meter/style lever.

    def test_absence_false_null_and_missing_tempo_unit_do_not_default(self):
        rows,_=self.check(facts(record("a","beat_tempo",bpm=100),record("b","beat_tempo",bpm=None,type=4,visible=False),record("c","automation_tempo",bpm=110,type=7,linear=True)))
        self.assertIn("bpm",rows["a"]);self.assertNotIn("quarter_bpm",rows["a"])
        self.assertEqual(rows["b"]["bpm"],scalar(None))
        self.assertIn("bpm",rows["c"]);self.assertEqual(rows["c"]["linear"],scalar(True))

    def test_agreeing_conflicting_and_redundant_tempos_remain_individual(self):
        source=facts(record("auto0","automation_tempo",bpm=120,type=4,measure=0,position=0),record("beat0","beat_tempo",bpm=120,type=4),record("conflict0","beat_tempo",bpm=90,type=4),record("reset1","automation_tempo",bpm=120,type=4,measure=1,position=0))
        rows,model=self.check(source);self.assertEqual(len(model["bindings"]),4)
        self.assertEqual(rows["auto0"]["quarter_bpm"],rows["reset1"]["quarter_bpm"])
        self.assertNotEqual(rows["beat0"]["quarter_bpm"],rows["conflict0"]["quarter_bpm"])
        # This preserves contradictory observations; it does not choose precedence.

    def test_invalid_values_unverified_units_and_ramps_have_explicit_status(self):
        _,model=self.check(facts(record("zero","beat_tempo",bpm=0,type=4),record("unit8","beat_tempo",bpm=90,type=8),record("ramp","automation_tempo",bpm=100,type=4,linear=True),record("badmeter","meter",numerator=-3,denominator=4)))
        status={r["id"]:r for r in interpretation_status(model)}
        self.assertEqual(status["zero"]["unit_conversion"],"unsupported")
        self.assertIn("unverified_or_missing_tempo_unit",status["unit8"]["reasons"])
        self.assertIn("ramp_execution_unresolved",status["ramp"]["reasons"])
        self.assertEqual(status["badmeter"]["unit_conversion"],"unsupported")
        self.assertTrue(all(r["playback"]=="not_implemented" for r in status.values()))

    def test_unverified_or_invalid_normalized_alias_is_refused(self):
        for row,old,new in [(record("t","beat_tempo",bpm=120,type=8),"bpm","quarter_bpm"),(record("m","meter",numerator=-3,denominator=4),"numerator","nominal_span_q")]:
            _,model=self.check(facts(row));rows=unpack(model["parameters"],{})
            rows[0]["fields"][new]=rows[0]["fields"].pop(old)
            model["parameters"]=pack(rows,{})
            with self.assertRaises(ConstraintError):decode(model)
        _,model=self.check(facts(record("x","beat_tempo",bpm=None,type=4)))
        rows=unpack(model["parameters"],{});rows[0]["fields"]["quarter_bpm"]=rows[0]["fields"].pop("bpm");model["parameters"]=pack(rows,{})
        with self.assertRaises(ConstraintError):decode(model)

    def test_eligible_raw_alias_cannot_bypass_normalized_representation(self):
        _,model=self.check(facts(record("m","meter",numerator=6,denominator=8)))
        rows=unpack(model["parameters"],{});rows[0]["fields"]["numerator"]=rows[0]["fields"].pop("nominal_span_q")
        model["parameters"]=pack(rows,{})
        with self.assertRaises(ConstraintError):decode(model)

    def test_extraction_covers_both_tempo_owners_and_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"metadata.json").write_text(json.dumps(dict(songId=7)))
            part=dict(partId=2,automations=dict(tempo=[dict(bpm=120,type=4,measure=0,position=0)]),measures=[dict(signature=[3,4],voices=[dict(beats=[dict(tempo=dict(bpm=90,type=4,text={"value":"x"}))])]),dict(voices=[])])
            (p/"track-2.json").write_text(json.dumps(part));source=extract(p)
            self.check(source);self.assertEqual(len(source["records"]),3)
            self.assertEqual([r["kind"] for r in source["records"]],["meter","beat_tempo","automation_tempo"])
            self.assertEqual(len(source["unsupported"]),1)

    def test_independent_raw_checker_detects_omitted_declarations_and_types(self):
        from check_reversible_temporal import check
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"metadata.json").write_text(json.dumps(dict(songId=7)))
            part=dict(partId=0,measures=[dict(signature=[3,4],voices=[dict(beats=[dict(tempo=dict(bpm=None,type=4,visible=False))])])])
            (p/"track-0.json").write_text(json.dumps(part));f=extract(p);upper=p/"upper.json"
            upper.write_text(json.dumps(encode(f)));self.assertEqual(check(p,upper)["status"],"pass")
            missing=deepcopy(f);missing["records"].pop();upper.write_text(json.dumps(encode(missing)))
            with self.assertRaises(ValueError):check(p,upper)
            changed=deepcopy(f);changed["records"][0]["fields"]["numerator"]=scalar(3.0);upper.write_text(json.dumps(encode(changed)))
            with self.assertRaises(ValueError):check(p,upper)

    def test_corrupt_duplicate_memberships_and_payloads_refused(self):
        _,model=self.check(facts(record("t","beat_tempo",bpm=120,type=4)))
        for mutate in (lambda m:m["bindings"].append(deepcopy(m["bindings"][0])),lambda m:m.update(raw_notes=[1,2]),lambda m:m["unsupported"].append(dict(owner="x",field="x",source_type="dict",raw_notes=[1,2])),lambda m:m["bindings"][0].update(cache=[1,2])):
            m=deepcopy(model);mutate(m)
            with self.assertRaises(ConstraintError):decode(m)


if __name__=="__main__":unittest.main()
