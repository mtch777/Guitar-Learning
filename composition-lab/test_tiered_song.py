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
        self.assertEqual(graph["scope"]["bar"],2)
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

    def test_graph_record_kinds_are_types_not_occurrence_ids(self):
        graph=[n for n in layers(self.package)[2]["records"] if n.get("origin",{}).get("document")=="extended/relational_graph" and n["origin"]["pointer"].startswith("/nodes/") and n["origin"]["pointer"].count("/")==2]
        self.assertTrue(graph)
        self.assertTrue(all(n["kind"] in {"relational_note","relational_beat","relational_track","relational_voice","relational_measure","relational_section","relational_hypothesis"} for n in graph))

    def test_rich_source_repeats_tuplets_polyphony_curves_and_ties(self):
        from fractions import Fraction as F
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);fixture(folder)
            part=json.loads((folder/"track-0.json").read_text())
            curve=dict(tone=50,points=[dict(position=0,tone=0),dict(position=30,precisePosition=51,tone=50,vibrato=True),dict(position=60,tone=0)])
            def beat(fret,duration=(1,4),**fields):return dict(duration=list(duration),notes=[dict(string=0,fret=fret,**fields)])
            first=[beat(0,(1,12),hp=True),beat(1,(1,12)),beat(2,(1,12)),beat(3,bend=curve),beat(4,slide="legato"),beat(4)]
            second=[beat(4,tie=True),beat(6,leftHandVibrato=True),beat(4,hp=True),beat(0)]
            part["measures"]=[dict(signature=[4,4],marker="A",repeatStart=True,voices=[dict(beats=first),dict(beats=[dict(duration=[1,1],notes=[dict(string=1,fret=0),dict(string=2,fret=2)])])]),dict(marker="B",repeat=2,voices=[dict(beats=second),dict(rest=True,beats=[dict(duration=[1,1],rest=True,notes=[dict(rest=True)])])])]
            (folder/"track-0.json").write_text(json.dumps(part),encoding="utf-8")
            drums=json.loads((folder/"track-1.json").read_text());drums["measures"][0]["repeatStart"]=True;drums["measures"][1]["repeat"]=2
            (folder/"track-1.json").write_text(json.dumps(drums),encoding="utf-8")
            package,outputs=build(folder);verify(package,outputs,folder)
            notes=[r for r in layers(package)[1]["records"] if r.get("event_id")]
            self.assertTrue(any(n["values"]["duration_q"]=="1/3" for n in notes))
            self.assertTrue(any(n["values"]["tie_destination"] for n in notes))
            self.assertEqual(len(package["indexes"]["playback_time"]),4)
            raw=next(d["payload"] for d in layers(package)[0]["documents"] if d["filename"]=="track-0.json")
            self.assertEqual(raw["measures"][0]["voices"][0]["beats"][3]["notes"][0]["bend"],curve)

    def test_analysis_snapshot_identity_is_reproducible_and_not_source_identity(self):
        package,outputs=build(self.folder)
        self.assertEqual(package["source_id"],self.package["source_id"])
        self.assertEqual(package["package_id"],self.package["package_id"])
        self.assertNotEqual(package["package_id"],package["source_id"])
        self.assertEqual(len(package["analysis_revision"]),64)
        self.assertTrue(all(e["source_gp"] is None for e in outputs["evidence_examples"]["examples"]))

    def test_source_pointer_preserves_empty_keys_and_escaped_delimiters(self):
        self.assertEqual(pointer({"parent":{"":3}},"/parent/"),3)
        self.assertEqual(pointer({"a/b":{"~":4}},"/a~1b/~0"),4)
        for path in ("not-absolute","/~2"):
            with self.assertRaises(ValueError):pointer({},path)

    def test_source_containers_walk_to_contained_field_users(self):
        from walk_tiered_song import SongWalk
        walk=SongWalk(self.package)
        root_users=walk.source_users("source:track-0.json","")
        measure_users=walk.source_users("source:track-0.json","/measures/0")
        self.assertTrue(root_users);self.assertTrue(measure_users)
        self.assertTrue(any(u["query_relation"]=="user_of_contained_field" for u in measure_users))

    def test_silent_beats_connect_to_existing_graph_relationships(self):
        from walk_tiered_song import SongWalk
        walk=SongWalk(self.package)
        for beat_id in ("beat:1:0:1:0:3","beat:1:1:2:0:0"):
            reachable=walk.walk(beat_id,"up",2)["records"]
            self.assertTrue(any(n["kind"]=="relational_beat" for n in reachable),beat_id)
        changed=deepcopy(self.package)
        state=layers(changed)[2]
        edge=next(e for e in state["links"] if e["type"]=="mentions_written_beat" and e["to_id"]=="beat:1:0:1:0:3" and "/nodes/" in e["from_id"])
        state["links"].remove(edge)
        with self.assertRaisesRegex(AssertionError,"Missing graph-to-source beat bridge"):verify(changed,self.outputs)

    def test_graph_note_clocks_and_groups_use_only_actual_members(self):
        from walk_tiered_song import SongWalk
        walk=SongWalk(self.package)
        for alias,occurrence in self.outputs["extended"]["projection"]["aliases"].items():
            if not isinstance(occurrence,str):continue
            graph=walk.nodes["r:extended/relational_graph:/nodes/"+alias]
            event=walk.nodes["event:1:"+occurrence]
            self.assertEqual(graph["time"]["spans"],event["time"]["spans"])
            self.assertEqual(graph["scope"]["part_id"],event["scope"]["part_id"])
            self.assertFalse(any(e["type"]=="scope_contains_event" for e in walk.forward[graph["id"]]))
        graph_note="r:extended/relational_graph:/nodes/t0:m0:v0:b1:n0"
        self.assertNotIn(graph_note,walk.at_time("3/2"))
        measure=walk.nodes["r:extended/relational_graph:/nodes/measure:(0, 0)"]
        members=[walk.nodes[e["to_id"]] for e in walk.forward[measure["id"]] if e["type"]=="graph_group_member"]
        self.assertTrue(members)
        self.assertTrue(all(m["scope"]["part_id"]==0 and m["scope"]["bar"]==1 for m in members))

    def test_sounding_lanes_link_to_sustains_and_written_occurrences(self):
        from walk_tiered_song import SongWalk
        walk=SongWalk(self.package)
        for i,lane in enumerate(self.outputs["extended"]["sounding_graph"]["lanes"]):
            ident=f"r:extended/sounding_graph:/lanes/{i}"
            linked=[e["to_id"] for e in walk.forward[ident] if e["type"]=="inferred_lane_member"]
            self.assertEqual(len(linked),len(lane["members"]))
            self.assertTrue(all(walk.nodes[s]["kind"]=="sounding_sustain" for s in linked))
            self.assertTrue(walk.nodes[ident]["time"]["spans"])
            down=walk.walk(ident,"down",2)["records"]
            self.assertTrue(any(n.get("event_id") for n in down))

    def test_actual_method_inputs_are_materialized_for_reexecution(self):
        import harmonic_inference,relational_graph
        exact=materialize(self.package,"r:extended/analysis_inputs:/exact_score")
        rounded=materialize(self.package,"r:extended/analysis_inputs:/rounded_score")
        self.assertEqual(relational_graph.build_graph(exact),self.outputs["extended"]["relational_graph"])
        self.assertEqual(harmonic_inference.infer_score(rounded),self.outputs["extended"]["harmony_hypotheses"])

    def test_calculation_search_population_cannot_silently_include_future_notes(self):
        changed=deepcopy(self.package)
        nodes={n["id"]:n for s in layers(changed).values() for n in s["records"]}
        history=next(n for n in nodes.values() if n["kind"]=="conditional_calculation_input" and n["values"].get("source_scope")=="prior_eligible_bar_patterns" and n["values"]["before_bar"]==1)
        event=next(n for n in nodes.values() if n.get("event_id"))
        layers(changed)[3]["links"].append(dict(type="prior_pattern_search_population",from_id=history["id"],to_id=event["id"]))
        with self.assertRaisesRegex(AssertionError,"Calculation search population differs"):verify(changed,self.outputs)

    def test_removing_classifier_calculation_input_is_rejected(self):
        changed=deepcopy(self.package)
        state=layers(changed)[3]
        edge=next(e for e in state["links"] if e["type"]=="existing_classifier_or_mechanic_input")
        state["links"].remove(edge)
        with self.assertRaisesRegex(AssertionError,"Exact classifier/mechanical input link differs"):verify(changed,self.outputs)

    def test_count_units_cannot_gain_unrelated_scope_notes(self):
        changed=deepcopy(self.package)
        witness=next(n for n in layers(changed)[2]["records"] if n["kind"]=="counted_observation_witness")
        linked={e["to_id"] for e in layers(changed)[2]["links"] if e["from_id"]==witness["id"] and e["type"]=="observed_unit_member"}
        unrelated=next(n["id"] for n in layers(changed)[1]["records"] if n.get("event_id") and n["id"] not in linked)
        layers(changed)[2]["links"].append(dict(type="observed_unit_member",from_id=witness["id"],to_id=unrelated))
        with self.assertRaisesRegex(AssertionError,"Count witness contains scope notes"):verify(changed,self.outputs)

    def test_mixed_section_groups_do_not_create_false_next_attack(self):
        from types import SimpleNamespace
        from build_tiered_song import connect_count_contexts
        for mixed_origin in (True,False):
            source=deepcopy(self.outputs["core"]["songs"][0])
            rows=source["tracks"][0]["rows"]
            for i,r in enumerate(rows):
                r["onset_q"]="0" if i<2 else "1"
                r["section_start"]=1 if i%2==0 else 2
            if not mixed_origin:
                rows[0]["section_start"]=rows[1]["section_start"]=1
            else:
                rows[2]["section_start"]=rows[3]["section_start"]=1
            nodes={n["id"]:deepcopy(n) for s in layers(self.package).values() for n in s["records"]}
            descriptor=dict(predicate="no_next_attack_in_same_section",source_scope="eligible_attack_groups",part_id=0,after_members=[r["occurrence"] for r in rows[:2]])
            nodes["test-context"]=dict(values=descriptor)
            mapper=SimpleNamespace(song=source,nodes=nodes,links=[],event_ids={r["occurrence"]:f"event:1:{r['occurrence']}" for t in source["tracks"] for r in t["rows"]})
            connect_count_contexts(mapper,self.outputs,["test-context"])
            self.assertEqual(mapper.nodes["test-context"]["query"]["result_members"],[])

    def test_pointer_rejects_python_negative_index_shortcut(self):
        for path in ("/-1","/01","/2"):
            with self.assertRaises(ValueError):pointer([1,2],path)


if __name__=="__main__":unittest.main()
