"""Repeat control relationship tests; no performed-pass or playback assertions."""
from copy import deepcopy
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
from reversible_annotations import scalar,unpack,pack
from reversible_relationships import ConstraintError,realize_numeric,factor_numeric
import reversible_control as control


def facts(fields,ending=None):
    refs=[f"opaque-{i}" for i in range(len(fields))]
    return dict(schema="control-source-observations/1",parts=[dict(id="part",measure_refs=refs,anacrusis=dict(kind="absent"))],records=[dict(id=refs[i],fields={k:scalar(v) for k,v in f.items()}) for i,f in enumerate(fields) if f],endings=[dict(owner=refs[i],kind="array",items=[scalar(v) for v in items]) for i,items in (ending or {}).items()],unsupported=[])


class ControlTests(unittest.TestCase):
    def check(self,f):
        m=control.encode(f);self.assertEqual(control.decode(m),f);return m

    def test_paired_regions_remove_endpoint_fields_and_share_definitions(self):
        f=facts([dict(repeatStart=True),dict(repeat=2),dict(repeatStart=True),dict(repeat=2)])
        m=self.check(f);self.assertEqual(len(m["regions"]["definitions"]),1)
        self.assertEqual(unpack(m["remaining"],{}),[])
        self.assertTrue(all(set(b)=={"id","part_ref","start_ref","count_type"} for b in m["bindings"]))
        with patch("builtins.open",side_effect=AssertionError("No source")),patch.object(Path,"open",side_effect=AssertionError("No source")):
            self.assertEqual(control.decode(m),f)

    def test_same_measure_start_before_end_and_nested_pairs(self):
        m=self.check(facts([dict(repeatStart=True,repeat=3)]))
        self.assertEqual(realize_numeric(m["regions"])[0]["values"]["measure_span"],"1")
        f=facts([dict(repeatStart=True),dict(repeatStart=True),dict(repeat=2),dict(repeat=4)])
        m=self.check(f);self.assertEqual([r["values"]["measure_span"] for r in realize_numeric(m["regions"])],["2","4"])

    def test_unmatched_invalid_false_null_and_zero_remain_literal(self):
        f=facts([dict(repeat=2),dict(repeatStart=None),dict(repeatStart=False,repeat=0),dict(repeatStart=True),dict(repeat=-2),dict(repeat=1.5)])
        m=self.check(f);reasons={r["reason"] for r in m["unresolved"]}
        self.assertEqual(reasons,{"no_explicit_start","non_boolean_start","unmatched_start","invalid_repeat_count"})
        self.assertEqual(m["bindings"],[])

    def test_ending_labels_inside_and_outside_never_infer_attachment(self):
        f=facts([dict(repeatStart=True),dict(repeat=2),{}],{1:[1],2:[2]})
        m=self.check(f);g=control.ending_geometry(m)
        self.assertEqual(g[0]["containing_regions"],[0]);self.assertEqual(g[1]["containing_regions"],[])
        self.assertTrue(all(x["musical_attachment"]=="unknown" for x in g))
        f["endings"][1]["items"]=[];self.check(f)

    def test_duplicate_endpoints_bad_extent_reasons_and_cache_refused(self):
        _,base=(None,self.check(facts([dict(repeatStart=True),dict(repeat=2),{}])))
        cases=[];m=deepcopy(base);m["remaining"]=pack([dict(id="opaque-0",fields=dict(repeatStart=scalar(True)))],{});cases.append(m)
        m=deepcopy(base);m["bindings"][0]["start_ref"]="other-song";cases.append(m)
        m=deepcopy(base);m["unresolved"].append(dict(owner="opaque-0",field="repeatStart",reason="fake"));cases.append(m)
        m=deepcopy(base);m["raw_notes"]=[1,2];cases.append(m)
        m=deepcopy(base);m["parts"][0]["raw_source"]={};cases.append(m)
        for i,m in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):control.decode(m)

    def test_supported_and_unsupported_states_cannot_claim_same_field(self):
        f=facts([dict(repeatStart=True),dict(repeat=2)],{1:[1]});cases=[]
        for owner,field in [("opaque-0","repeatStart"),("opaque-1","alternateEnding"),("part","anacrusis")]:
            m=deepcopy(f);m["unsupported"].append(dict(owner=owner,field=field,source_type="dict"));cases.append(m)
        m=deepcopy(f);m["parts"][0]["anacrusis"]=dict(kind="unsupported");cases.append(m)
        m=deepcopy(f);m["unsupported"].append(dict(owner="opaque-0",field="repeat",source_type="int"));cases.append(m)
        for i,m in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):control.encode(m)
        f["parts"][0]["anacrusis"]=dict(kind="unsupported")
        f["unsupported"].append(dict(owner="part",field="anacrusis",source_type="dict"));self.check(f)

    def test_independent_raw_oracle_detects_missing_regions_fields_and_reasons(self):
        from test_reversible_ties import capture,measure,beat
        import check_reversible_control as oracle
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);capture(p,[measure([beat()],repeatStart=True),measure([beat()],repeat=2,alternateEnding=[1])])
            partpath=p/"track-0.json";part=json.loads(partpath.read_text());part["anacrusis"]={"unknown":True};partpath.write_text(json.dumps(part))
            f=control.extract(p);m=control.encode(f);upper=p/"upper.json";upper.write_text(json.dumps(m));self.assertEqual(oracle.check(p,upper)["regions"],1)
            changed=deepcopy(f);changed["endings"].clear();upper.write_text(json.dumps(control.encode(changed)))
            with self.assertRaisesRegex(ValueError,"Raw declaration"):oracle.check(p,upper)
            missing=deepcopy(f);missing["records"].clear();empty=control.encode(missing);upper.write_text(json.dumps(empty))
            with patch.object(oracle,"decode",return_value=f):
                with self.assertRaisesRegex(ValueError,"eligible-region"):oracle.check(p,upper)
            changed=deepcopy(f);changed["records"][1]["fields"]["repeat"]=scalar(3);upper.write_text(json.dumps(control.encode(changed)))
            with patch.object(oracle,"decode",return_value=f):
                with self.assertRaisesRegex(ValueError,"eligible-region"):oracle.check(p,upper)
            bad=deepcopy(m);bad["unresolved"].append(dict(owner="x",field="repeat",reason="invented"));upper.write_text(json.dumps(bad))
            with patch.object(oracle,"decode",return_value=f):
                with self.assertRaisesRegex(ValueError,"unresolved reasons"):oracle.check(p,upper)

    def test_source_extraction_preserves_pickup_and_unknown_shapes(self):
        from test_reversible_ties import capture,measure,beat
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);capture(p,[measure([beat()],repeatStart=True,alternateEnding=[1]),measure([beat()],repeat=2)])
            path=p/"track-0.json";part=json.loads(path.read_text());part["anacrusis"]=True;part["measures"][1]["alternateEnding"]={"unknown":1};path.write_text(json.dumps(part))
            f=control.extract(p);m=self.check(f)
            self.assertEqual(f["parts"][0]["anacrusis"]["value"],scalar(True));self.assertEqual(len(f["unsupported"]),1)
            self.assertEqual(len(m["bindings"]),1)


if __name__=="__main__":unittest.main()
