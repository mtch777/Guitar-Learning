"""Tie continuity solves removed coordinates; ambiguous source stays explicit."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from reversible_annotations import extract,unpack
from reversible_relationships import ConstraintError,realize_numeric
from reversible_ties import encode,decode


def capture(folder,measures):
    meta=dict(songId=77,revisionId=3,artist="Fixture",title="Ties",tracks=[dict(partId=0)])
    part=dict(songId=77,revisionId=3,partId=0,name="Guitar",instrumentId=25,tuning=[40,45],measures=measures)
    (folder/"metadata.json").write_text(json.dumps(meta));(folder/"track-0.json").write_text(json.dumps(part))


def beat(fret=5,duration=(1,4),**extra):return dict(duration=list(duration),notes=[dict(string=0,fret=fret,**extra)])
def measure(beats,**extra):return dict(signature=[4,4],voices=[dict(beats=beats)],**extra)


class ReversibleTieTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_case(self,measures):
        capture(self.folder,measures);facts=extract(self.folder);model=encode(facts)
        self.assertEqual(decode(model),facts)
        return facts,model

    def test_chain_crosses_bars_and_removes_actual_destination_coordinates(self):
        facts,model=self.run_case([measure([beat(duration=(1,1))]),measure([beat(duration=(1,1),tie=True)]),measure([beat(duration=(1,1),tie=True)])])
        self.assertEqual(len(model["links"]),2);self.assertEqual(model["unresolved"],[])
        rows={r["id"]:r for r in realize_numeric(model["lower"]["physical"]["position_patterns"])}
        for link in model["links"]:self.assertIsNone(rows[link["destination"]]["values"]["position_pitch"])
        self.assertEqual(sum(r["values"]["position_pitch"] is not None for r in rows.values()),1)
        self.assertFalse(any(m["fields"].get("tie")=={"type":"bool","value":True} for m in unpack(model["lower"]["markers"],{})))
        self.assertEqual(sum(m["fields"].get("tie")=={"type":"bool","value":True} for m in decode(model)["markers"]),2)

    def test_false_null_and_numeric_one_are_not_coerced_to_true_ties(self):
        _,model=self.run_case([measure([beat(),beat(tie=False),beat(tie=None),beat(tie=1)])])
        self.assertEqual(model["links"],[]);self.assertEqual(model["unresolved"],[])
        values=[m["fields"]["tie"] for m in unpack(model["lower"]["markers"],{}) if "tie" in m["fields"]]
        self.assertEqual({v["type"] for v in values},{"bool","NoneType","int"})

    def test_string_and_voice_separation_do_not_invent_predecessors(self):
        changed=beat(tie=True);changed["notes"][0]["string"]=1
        _,model=self.run_case([measure([beat(),changed])])
        self.assertEqual(model["links"],[]);self.assertEqual(model["unresolved"][0]["reason"],"no_predecessor")
        m=measure([beat()]);m["voices"].append(dict(beats=[beat(tie=True)]))
        _,model=self.run_case([m]);self.assertEqual(model["links"],[])
        self.assertEqual(model["unresolved"][0]["reason"],"no_predecessor")

    def test_grace_missing_position_and_changed_pitch_remain_unresolved(self):
        grace=beat(tie=True);grace["graceNote"]=True
        _,model=self.run_case([measure([beat(),grace])]);self.assertEqual(model["unresolved"][0]["reason"],"zero_metric_duration")
        missing=beat(tie=True);missing["notes"][0].pop("fret")
        _,model=self.run_case([measure([beat(),missing])]);self.assertEqual(model["unresolved"][0]["reason"],"unmapped_position")
        _,model=self.run_case([measure([beat(),beat(fret=7,tie=True)])]);self.assertEqual(model["unresolved"][0]["reason"],"different_written_position")
        _,model=self.run_case([measure([beat(),beat(tie=True,dead=True)])]);self.assertEqual(model["unresolved"][0]["reason"],"dead_transition")

    def test_ambiguous_same_string_coattack_and_rest_gap_not_repaired(self):
        ambiguous=beat();ambiguous["notes"].append(dict(string=0,fret=5))
        _,model=self.run_case([measure([ambiguous,beat(tie=True)])]);self.assertEqual(model["links"],[])
        self.assertEqual(model["unresolved"][0]["reason"],"no_predecessor")
        rest=dict(duration=[1,4],rest=True,notes=[dict(rest=True)])
        _,model=self.run_case([measure([beat(),rest,beat(tie=True)])]);self.assertEqual(model["unresolved"][0]["reason"],"noncontiguous")

    def test_dead_tie_is_written_position_relation_not_sounding_pitch(self):
        _,model=self.run_case([measure([beat(dead=True),beat(dead=True,tie=True)])])
        self.assertEqual(model["links"][0]["kind"],"written_dead_tie")

    def test_missing_duplicate_reversed_or_extra_tie_data_refused(self):
        _,base=self.run_case([measure([beat(),beat(tie=True),beat(tie=True)])]);cases=[]
        m=deepcopy(base);m["links"].pop();cases.append(m)
        m=deepcopy(base);m["links"].append(deepcopy(m["links"][0]));cases.append(m)
        m=deepcopy(base);m["links"][0]["origin"],m["links"][0]["destination"]=m["links"][0]["destination"],m["links"][0]["origin"];cases.append(m)
        m=deepcopy(base);m["links"][0]["original_pitch"]="45";cases.append(m)
        m=deepcopy(base);m["unresolved"].append(dict(destination="missing",reason="no_predecessor"));cases.append(m)
        for i,model in enumerate(cases):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):decode(model)

    def test_negative_fret_is_preserved_but_not_promoted_to_a_tie_relation(self):
        facts,model=self.run_case([measure([beat(fret=-1),beat(fret=-1,tie=True)])])
        self.assertEqual(model["links"],[])
        self.assertEqual(model["unresolved"][0]["reason"],"invalid_written_position")
        self.assertTrue(all(p["fret"]["value"]=="-1" for p in decode(model)["physical"]["positions"]))

    def test_self_links_and_unanchored_cycles_fail_without_guessing(self):
        _,base=self.run_case([measure([beat(),beat(tie=True),beat(tie=True)])])
        self_link=deepcopy(base);self_link["links"][0]["origin"]=self_link["links"][0]["destination"]
        with self.assertRaises(ConstraintError):decode(self_link)
        cycle=deepcopy(base)
        cycle["links"][0]["origin"]=cycle["links"][1]["destination"]
        cycle["links"][1]["origin"]=cycle["links"][0]["destination"]
        with self.assertRaises(ConstraintError):decode(cycle)

    def test_lane_identity_does_not_depend_on_parsing_note_ids(self):
        capture(self.folder,[measure([beat(),beat(tie=True),beat(tie=True)])]);facts=extract(self.folder)
        ids={n["id"]:f"opaque-note-{i}" for i,n in enumerate(facts["physical"]["topology"]["notes"])}
        for n in facts["physical"]["topology"]["notes"]:n["id"]=ids[n["id"]]
        for p in facts["physical"]["positions"]:p["id"]=ids[p["id"]]
        for marker in facts["markers"]:
            if marker["id"] in ids:marker["id"]=ids[marker["id"]]
        facts["markers"]=sorted(facts["markers"],key=lambda m:m["id"])
        model=encode(facts);self.assertEqual(len(model["links"]),2);self.assertEqual(decode(model),facts)


if __name__=="__main__":unittest.main()
