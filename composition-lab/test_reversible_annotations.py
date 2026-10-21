"""Sparse source annotation ownership and exact registered-unit tests."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from test_reversible_topology import capture
from reversible_annotations import extract,encode,decode,unit_equation
from reversible_relationships import realize_numeric,solve,ConstraintError


def curve():
    return dict(tone=50,customHeader=False,points=[dict(position=0,precisePosition=0,tone=0),dict(position=30,precisePosition=61,tone=50,vibrato=False),dict(position=30,precisePosition=61,tone=50,vibrato=False),dict(position=60,tone=0)])


class ReversibleAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);capture(self.folder)
        part=json.loads((self.folder/"track-0.json").read_text());beats=part["measures"][0]["voices"][0]["beats"]
        beats[0]["notes"][0].update(bend=curve(),vibrato=None)
        beats[1].update(tremoloBar=curve(),palmMute=False)
        beats[1]["notes"][0].update(bend=curve(),ghost=False,tone=50)
        beats[1]["notes"][2].update(vibrato=True)
        beats[4]["notes"][0].update(bend=dict(points=[]))
        (self.folder/"track-0.json").write_text(json.dumps(part))
    def tearDown(self):self.temp.cleanup()
    def roundtrip(self):
        facts=extract(self.folder);upper=encode(facts);self.assertEqual(decode(upper),facts);return facts,upper

    def test_presence_false_null_and_absence_remain_different(self):
        facts,_=self.roundtrip();byowner={m["id"]:m["fields"] for m in facts["markers"]}
        self.assertEqual(byowner["event:91:0:1:0:0:0"]["vibrato"],dict(type="NoneType",value=None))
        self.assertEqual(byowner["event:91:0:1:0:1:0"]["ghost"],dict(type="bool",value=False))
        self.assertNotIn("vibrato",byowner["event:91:0:1:0:1:0"])
        self.assertEqual(byowner["event:91:0:1:0:1:2"]["vibrato"],dict(type="bool",value=True))

    def test_note_and_beat_curves_keep_separate_owners_and_exact_points(self):
        facts,upper=self.roundtrip();byowner={c["owner"]:c for c in facts["curves"]}
        note=byowner["event:91:0:1:0:1:0"];beat=byowner["beat:91:0:1:0:1"]
        self.assertEqual((note["kind"],note["field"]),("note","bend"))
        self.assertEqual((beat["kind"],beat["field"]),("beat","tremoloBar"))
        self.assertNotEqual(note["id"],beat["id"])
        self.assertEqual(note["points"][1]["fields"],note["points"][2]["fields"])
        self.assertNotEqual(note["points"][1]["id"],note["points"][2]["id"])
        self.assertGreater(upper["curve_points"]["sharing"]["shared_definitions"],0)
        self.assertTrue(all(len(o["members"])==4 for o in upper["curve_points"]["occurrences"]))

    def test_registered_units_disagree_without_forced_equality(self):
        facts,upper=self.roundtrip();rows={r["id"]:r for r in realize_numeric(upper["curve_points"])}
        c=next(c for c in facts["curves"] if c["owner"]=="event:91:0:1:0:1:0")
        row=rows[c["points"][1]["id"]]
        self.assertEqual(F(row["values"]["tone"]),1)
        self.assertEqual(F(row["values"]["position"]),F(1,2))
        self.assertEqual(F(row["values"]["precisePosition"]),F(61,100))
        marker=next(r for r in realize_numeric(upper["markers"]) if r["id"]==c["owner"])
        self.assertEqual(F(marker["values"]["tone"]),50) # Same key outside registered curve schema has no unit conversion.
        equation=unit_equation("tone",{"tone":"50"})
        self.assertEqual(solve(equation,{"source":75},["normalized"])["normalized"],F(3,2))
        self.assertEqual(solve(equation,{"normalized":"3/2"},["source"])["source"],75)

    def test_empty_and_zero_metric_grace_curves_are_not_discarded(self):
        facts,_=self.roundtrip();empty=next(c for c in facts["curves"] if c["owner"]=="event:91:0:1:0:4:0")
        self.assertEqual(empty["points"],[]);self.assertIs(empty["points_present"],True)
        grace=next(c for c in facts["curves"] if c["owner"]=="event:91:0:1:0:0:0")
        beat=next(b for b in facts["physical"]["topology"]["beats"] if b["id"]=="beat:91:0:1:0:0")
        self.assertEqual(beat["duration_q"],"0")
        self.assertEqual(grace["points"][1]["fields"]["precisePosition"]["value"],"61")

    def test_unregistered_and_invalid_complex_fields_are_inventory_not_blobs(self):
        part=json.loads((self.folder/"track-0.json").read_text());note=part["measures"][0]["voices"][0]["beats"][1]["notes"][0]
        note["customEnvelope"]=curve();note["bend"]={"points":[{"tone":{"invalid":"nested"}}]}
        (self.folder/"track-0.json").write_text(json.dumps(part));facts,_=self.roundtrip()
        owner="event:91:0:1:0:1:0";entries=[r for r in facts["unsupported"] if r["owner"]==owner]
        self.assertEqual({e["field"] for e in entries},{"customEnvelope","bend"})
        self.assertTrue(all(set(e)=={"owner","kind","field","source_type"} for e in entries))
        self.assertFalse(any(c["owner"]==owner for c in facts["curves"]))

    def test_wrong_owner_reordered_points_and_nested_caches_refused(self):
        facts,upper=self.roundtrip();cases=[]
        m=deepcopy(upper);m["curve_memberships"][0]["owner"]="missing-owner";cases.append(m)
        m=deepcopy(upper);o=m["curve_points"]["occurrences"][0];o["members"]=list(reversed(o["members"]));cases.append(m)
        m=deepcopy(upper);next(iter(m["markers"]["definitions"].values()))["symbols"][0]["cache"]={"raw_score":[60,64,67]};cases.append(m)
        m=deepcopy(upper);m["unsupported"].append(dict(owner="event:91:0:1:0:1:0",kind="note",field="cache",source_type="dict",raw={"notes":[60,64,67]}));cases.append(m)
        for i,model in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):decode(model)
        bad=deepcopy(facts);note_ids={n["id"] for n in facts["physical"]["topology"]["notes"]}
        next(m for m in bad["markers"] if m["id"] in note_ids)["fields"]["fret"]={"type":"int","value":"2"}
        with self.assertRaises(ConstraintError):encode(bad)

    def test_rest_slot_annotations_are_captured_or_explicitly_inventory(self):
        part=json.loads((self.folder/"track-0.json").read_text())
        rest=part["measures"][0]["voices"][0]["beats"][1]["notes"][1]
        rest.update(ghost=False,customEnvelope={"points":[]})
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts,_=self.roundtrip();owner="rest-slot:beat:91:0:1:0:1:1"
        marker=next(r for r in facts["markers"] if r["id"]==owner)
        self.assertEqual(marker["fields"]["ghost"],dict(type="bool",value=False))
        self.assertIn(dict(owner=owner,kind="rest_slot",field="customEnvelope",source_type="dict"),facts["unsupported"])

    def test_duplicate_curve_or_point_and_missing_marker_owner_refused(self):
        facts,_=self.roundtrip();bad=deepcopy(facts);bad["curves"].append(deepcopy(bad["curves"][0]))
        with self.assertRaises(ConstraintError):encode(bad)
        bad=deepcopy(facts);bad["curves"][0]["points"][1]["id"]=bad["curves"][0]["points"][0]["id"]
        with self.assertRaises(ConstraintError):encode(bad)
        bad=deepcopy(facts);bad["markers"][0]["id"]="missing-owner"
        with self.assertRaises(ConstraintError):encode(bad)


if __name__=="__main__":unittest.main()
