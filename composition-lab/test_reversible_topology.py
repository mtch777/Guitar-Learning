"""Independent topology ownership and exact notation/metric boundary tests."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
from reversible_relationships import ConstraintError
from reversible_topology import extract,encode,decode,validate,event_view


def capture(folder):
    meta=dict(songId=91,revisionId=17,artist="Fixture",title="Topology",tracks=[dict(partId=0)])
    note=lambda fret,**extra:dict(string=0,fret=fret,**extra)
    beats=[dict(duration=[1,32],graceNote=True,notes=[note(1)]),dict(duration=[1,4],notes=[note(0),dict(rest=True),note(7)]),dict(duration=[1,4],rest=True,notes=[dict(rest=True)]),dict(duration=[1,4],notes=[]),dict(duration=[1,4],notes=[note(5)])]
    part=dict(songId=91,revisionId=17,partId=0,name="Guitar",instrumentId=25,tuning=[40,45,50],measures=[dict(signature=[4,4],voices=[dict(beats=beats),dict(beats=[])]),dict(signature=[3,4],rest=True,voices=[dict(rest=True,beats=[dict(type=1,duration=[1,1],rest=True,notes=[dict(rest=True)])])]),dict(signature=[2,4],voices=[dict(beats=[dict(duration=[1,2],notes=[note(3)]),dict(duration=[1,32],graceNote=True,notes=[note(4)])])]),dict(signature=[3,4],voices=[])])
    for filename,value in (("metadata.json",meta),("track-0.json",part)):(folder/filename).write_text(json.dumps(value),encoding="utf-8")


class ReversibleTopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);capture(self.folder)
        self.facts=extract(self.folder)
    def tearDown(self):self.temp.cleanup()

    def test_exact_topology_and_event_fields_roundtrip_without_note_timing(self):
        upper=encode(self.facts);restored=decode(upper)
        self.assertEqual(restored,self.facts)
        self.assertEqual(event_view(restored),event_view(self.facts))
        self.assertTrue(all(set(n)=={"id","beat_ref","slot","base_pitch"} for n in restored["notes"]))
        self.assertEqual(len(restored["measures"]),4)
        self.assertEqual(restored["measures"][-1]["voices"],[])
        empty=next(v for v in restored["voices"] if v["id"]=="voice:91:0:1:1")
        self.assertEqual(empty["beats"],[])

    def test_empty_beat_rest_and_mixed_slots_are_not_conflated(self):
        beats={b["id"]:b for b in decode(encode(self.facts))["beats"]}
        mixed=beats["beat:91:0:1:0:1"];rest=beats["beat:91:0:1:0:2"];empty=beats["beat:91:0:1:0:3"]
        self.assertEqual(mixed["symbols"]["slots"],["note","rest_placeholder","note"])
        self.assertEqual(rest["symbols"]["slots"],["rest_placeholder"])
        self.assertIs(rest["symbols"]["rest_flag"],True)
        self.assertEqual(empty["symbols"]["slots"],[])
        self.assertIsNone(empty["symbols"]["rest_flag"])
        notes=[n for n in self.facts["notes"] if n["beat_ref"]==mixed["id"]]
        self.assertEqual([n["slot"] for n in notes],[0,2])

    def test_whole_measure_rest_has_separate_nominal_and_metric_duration(self):
        b=next(b for b in self.facts["beats"] if b["id"]=="beat:91:0:2:0:0")
        self.assertTrue(b["symbols"]["whole_measure_rest"])
        self.assertEqual(F(b["written_duration_q"]),4)
        self.assertEqual(F(b["duration_q"]),3)
        self.assertEqual(F(b["onset_q"]),4)

    def test_grace_reference_is_only_declared_same_voice_lookahead_policy(self):
        beats={b["id"]:b for b in self.facts["beats"]}
        first=beats["beat:91:0:1:0:0"];following=beats["beat:91:0:1:0:1"];tail=beats["beat:91:0:3:0:1"]
        self.assertEqual(first["next_regular_beat_ref"],following["id"])
        self.assertEqual(first["onset_q"],following["onset_q"])
        self.assertEqual(first["duration_q"],"0")
        self.assertEqual(first["written_duration_q"],"1/8")
        self.assertIsNone(tail["next_regular_beat_ref"])

    def test_pickup_and_all_grace_voice_remain_exact(self):
        part=json.loads((self.folder/"track-0.json").read_text())
        part.update(anacrusis=True,measures=[dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,8],notes=[dict(string=0,fret=0)]),dict(duration=[1,8],notes=[dict(string=0,fret=2)])])]),dict(voices=[dict(beats=[dict(duration=[1,16],graceNote=True,notes=[dict(string=0,fret=3)])])])])
        (self.folder/"track-0.json").write_text(json.dumps(part))
        facts=extract(self.folder);restored=decode(encode(facts))
        self.assertEqual(restored,facts)
        self.assertEqual(F(restored["beats"][-1]["onset_q"]),1)
        self.assertEqual(restored["beats"][-1]["duration_q"],"0")

    def test_invalid_ownership_and_hidden_note_timing_refused(self):
        mutations=[]
        f=deepcopy(self.facts);f["voices"][0]["beats"].append(f["voices"][0]["beats"][0]);mutations.append(f)
        f=deepcopy(self.facts);f["notes"][0]["onset_q"]="0";mutations.append(f)
        f=deepcopy(self.facts);f["notes"][0]["slot"]=1;mutations.append(f)
        for i,facts in enumerate(mutations):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):encode(facts)

    def test_invalid_grace_links_are_not_accepted_as_source_truth(self):
        mutations=[]
        for target in ("beat:91:0:1:0:0","beat:91:0:2:0:0","beat:91:0:1:0:4"):
            f=deepcopy(self.facts);f["beats"][0]["next_regular_beat_ref"]=target;mutations.append(f)
        f=deepcopy(self.facts);f["beats"][1]["next_regular_beat_ref"]=f["beats"][2]["id"];mutations.append(f)
        for i,facts in enumerate(mutations):
            with self.subTest(case=i):
                with self.assertRaises(ConstraintError):encode(facts)
        upper=encode(self.facts);upper["next_regular_beat_refs"]["missing-beat"]="beat:91:0:1:0:1"
        with self.assertRaises(ConstraintError):decode(upper)

    def test_measure_and_voice_flags_cannot_hide_nested_source_payload(self):
        for kind in ("measures","voices"):
            f=deepcopy(self.facts);f[kind][0]["rest_flag"]={"raw_score":[60,64,67]}
            with self.subTest(kind=kind):
                with self.assertRaises(ConstraintError):encode(f)

    def test_symbol_slots_cannot_hide_nested_source_payload(self):
        for key in ("rest_flag","grace_kind","notation_type","whole_measure_rest"):
            f=deepcopy(self.facts);f["beats"][0]["symbols"][key]={"raw_notes":[60,64,67]}
            with self.subTest(field=key):
                with self.assertRaises(ConstraintError):encode(f)


if __name__=="__main__":unittest.main()
