"""Whole-source mapping invariants and corruption tests, using authored fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from build_tiered_song import build,layers,pointer,materialize
from verify_tiered_song import verify
from artist_relationship_profiles import build_relationship_profile
from test_artist_relationship_profiles import row,song


def fixture(folder):
    meta=dict(songId=1,revisionId=2,artist="Fixture Artist",title="Source Fixture",aiGenerated=False,isJunk=False,tracks=[dict(partId=0),dict(partId=1)])
    beats=[dict(duration=[1,32],graceNote=True,notes=[dict(string=0,fret=1)]),dict(duration=[1,4],notes=[dict(string=0,fret=0,hp=True)]),dict(duration=[1,4],notes=[dict(string=0,fret=2)]),dict(duration=[1,4],notes=[dict(rest=True)]),dict(duration=[1,4],notes=[dict(string=0,fret=0)])]
    for name,payload in [("metadata.json",meta),("track-0.json",dict(partId=0,name="Guitar",instrumentId=25,tuning=[40,45,50],capo=0,opaqueFixture=dict(keep=[False,None,0,"value"]),measures=[dict(signature=[4,4],marker="Intro",voices=[dict(beats=beats)]),dict(voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=0,fret=3)])])])])),("track-1.json",dict(partId=1,name="Drums",instrumentId=128,tuning=[],measures=[dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=0,fret=36)])])]),dict(voices=[dict(beats=[dict(duration=[1,1],notes=[])])])]))]:
        (folder/name).write_text(json.dumps(payload),encoding="utf-8")


class TieredSongTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name);fixture(cls.folder)
        cls.package,cls.outputs=build(cls.folder)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_whole_source_graph_and_output_roundtrip(self):
        result=verify(self.package,self.outputs,self.folder)
        self.assertEqual(result["status"],"pass")
        self.assertEqual(result["checks"]["tracks"],2)
        self.assertEqual(result["checks"]["canonical_note_occurrences"],6)
        self.assertEqual(list(layers(self.package)),[5,4,3,2,1,0])

    def test_raw_unknowns_preserved_and_grace_is_not_metric_time(self):
        states=layers(self.package)
        raw=next(d["payload"] for d in states[0]["documents"] if d["filename"]=="track-0.json")
        self.assertEqual(raw["opaqueFixture"],dict(keep=[False,None,0,"value"]))
        grace=next(n for n in states[1]["records"] if n["kind"]=="grace_note")
        span=grace["time"]["spans"][0]
        self.assertEqual(span["start"],span["end"])
        self.assertNotIn("next_monophonic_interval",{k for k,v in grace["values"].items() if not isinstance(v,dict)})

    def test_corrupt_source_and_dangling_link_rejected(self):
        changed=deepcopy(self.package)
        layers(changed)[0]["documents"][0]["payload"]["title"]="changed"
        with self.assertRaisesRegex(AssertionError,"Source payload"):verify(changed,self.outputs)
        changed=deepcopy(self.package)
        layers(changed)[2]["links"].append(dict(type="test",from_id="missing",to_id="missing"))
        with self.assertRaisesRegex(AssertionError,"Dangling"):verify(changed,self.outputs)

    def test_missing_occurrence_and_invalid_clock_rejected(self):
        changed=deepcopy(self.package)
        state=layers(changed)[1]
        note=next(n for n in state["records"] if n.get("event_id"));state["records"].remove(note)
        with self.assertRaises(AssertionError):verify(changed,self.outputs)
        changed=deepcopy(self.package)
        timed=next(n for n in layers(changed)[1]["records"] if n["time"])
        timed["time"]["spans"][0]=dict(start="2",end="1")
        with self.assertRaisesRegex(AssertionError,"Negative"):verify(changed,self.outputs)

    def test_complete_support_logging_changes_no_statistics(self):
        report=dict(songs=[song(1,[row(i,i,pitch=40+i%3) for i in range(8)])])
        support=[]
        baseline=build_relationship_profile(report,{},"A")
        observed=build_relationship_profile(report,{},"A",support_sink=support.append)
        self.assertEqual(baseline,observed)
        self.assertEqual(len(support),sum(t["eligible_count"] for t in observed["tables"]))
        self.assertTrue(all(unit["support"] for unit in support))
        self.assertGreater(len(support),2)

    def test_complete_cell_memberships_cannot_be_truncated(self):
        changed=deepcopy(self.package)
        state=layers(changed)[5]
        edge=next(e for e in state["links"] if e["type"]=="derived_from_complete_units")
        state["links"].remove(edge)
        with self.assertRaisesRegex(AssertionError,"Truncated conditional evidence"):verify(changed,self.outputs)

    def test_legacy_graph_index_scope_and_clock_domains(self):
        states=layers(self.package)
        graph=next(n for n in states[2]["records"] if n["origin"]["document"]=="extended/relational_graph" and isinstance(n["values"],dict) and n["values"].get("measure")==1)
        self.assertEqual(graph["scope"]["measure"],2)
        self.assertTrue(self.package["indexes"]["playback_time"])
        self.assertTrue(all(x["basis"]=="playback_quarter_notes" for x in self.package["indexes"]["playback_time"]))
        self.assertTrue(all(x["basis"]=="written_quarter_notes" for x in self.package["indexes"]["written_time"]))

    def test_parsed_entrypoints_are_the_same_existing_algorithms(self):
        from unittest.mock import patch
        import api_analysis_views,phrase_analysis,harmony_boundaries,validate_structure
        source=[d for d in layers(self.package)[0]["documents"]]
        original=self.outputs["core"]["songs"][0]
        _,compact,_=api_analysis_views.project(original,source)
        phrase=dict(compact,sections=[dict(measure=n,label=l) for n,l in compact["sections"]])
        with patch.object(phrase_analysis,"parse",return_value=phrase):self.assertEqual(phrase_analysis.scan("unused"),phrase_analysis.scan_score(phrase))
        ensemble=dict(file="fixture",tracks=[dict(track=t["name"],measures=t["measures"]) for t in compact["tracks"]],meter=[None]*compact["measures"],sections=compact["sections"])
        for module in (harmony_boundaries,validate_structure):
            with patch.object(module,"parsed_tracks",return_value=ensemble):self.assertEqual(module.analyze("unused"),module.analyze_score(ensemble))

    def test_resolved_events_have_no_future_relationship_fields(self):
        states=layers(self.package)
        for node in states[1]["records"]:
            if node.get("event_id"):
                self.assertNotIn("next_monophonic_interval",node["values"])
                self.assertNotIn("next_attack_gap_q",node["values"])
        intervals=[n for n in states[2]["records"] if n["kind"]=="next_monophonic_interval"]
        self.assertTrue(intervals)
        ids={n["id"] for n in states[1]["records"]}
        self.assertTrue(all(set(n["endpoints"].values())<=ids for n in intervals))

    def test_actual_graph_is_walkable_in_both_directions_and_clocks(self):
        from walk_tiered_song import SongWalk
        walk=SongWalk(self.package)
        event=next(n for n in layers(self.package)[1]["records"] if n.get("event_id"))
        up=walk.walk(event["id"],"up",2)
        self.assertGreater(len(up["records"]),1)
        source=event["source"]
        self.assertTrue(any(x["record"]==event["id"] and x["exact_field"] for x in walk.source_users(source["document"],source["pointer"])))
        self.assertIn(event["id"],walk.at_time(event["values"]["onset_q"]))
        self.assertTrue(walk.at_time("0","playback_quarter_notes"))
        self.assertNotIn(event["id"],walk.at_time("0","playback_quarter_notes"))

    def test_pointer_rejects_python_negative_index_shortcut(self):
        for path in ("/-1","/01","/2"):
            with self.assertRaises(ValueError):pointer([1,2],path)


if __name__=="__main__":unittest.main()
