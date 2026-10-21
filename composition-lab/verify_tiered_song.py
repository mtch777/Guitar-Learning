"""Independent integrity/coverage checks for the private tiered song artifact."""
import argparse
from collections import Counter,defaultdict,deque
from fractions import Fraction as F
import json
import hashlib
from pathlib import Path
from build_tiered_song import layers,read,digest,pointer,materialize
from verify_count_contexts import verify_contexts


def verify(package,outputs,source_folder=None):
    states=layers(package)
    assert list(states)==[5,4,3,2,1,0], "Hierarchy must be physically nested 5 through 0"
    records=[r for s in states.values() for r in s["records"]]
    nodes={r["id"]:r for r in records}
    assert len(nodes)==len(records),"Duplicate record identities"
    docs={d["id"]:d for d in states[0]["documents"]}
    checks=Counter()
    if "analysis_revision" in package:
        revision=digest(dict(outputs_sha256=digest(outputs),implementation_registry_sha256=digest(package["implementation_registry"]),source_inputs=[dict(byte_sha256=d["byte_sha256"],payload_sha256=d["payload_sha256"]) for d in states[0]["documents"]],schema=package["schema"]))
        assert package["analysis_revision"]==revision,"Analysis snapshot identity differs"
        assert package["package_id"]==package["source_id"]+":analysis:"+revision,"Qualified package identity differs"
        checks["analysis_snapshot_identity"]+=1
    for doc in docs.values():
        assert digest(doc["payload"])==doc["payload_sha256"],"Source payload changed"
        if source_folder:
            source=Path(source_folder)/doc["filename"]
            assert read(source)==doc["payload"],"Captured JSON differs"
            assert hashlib.sha256(source.read_bytes()).hexdigest()==doc["byte_sha256"],"Captured source bytes differ"
        checks["source_documents"]+=1
    forward=defaultdict(list);reverse=defaultdict(list)
    for state in states.values():
        for edge in state.get("links",[]):
            assert edge["from_id"] in nodes,"Dangling edge origin"
            if "to_id" in edge:
                assert edge["to_id"] in nodes,"Dangling edge target"
                assert nodes[edge["to_id"]]["tier"]<=nodes[edge["from_id"]]["tier"],"Lower tier depends on higher tier"
                reverse[edge["to_id"]].append(edge)
            else:
                ref=edge["to_source"]
                pointer(docs[ref["document"]]["payload"],ref["pointer"])
                checks["source_links"]+=1
            forward[edge["from_id"]].append(edge)
            checks["edges"]+=1
    def embedded_refs(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in ("$record","$count_cell","$count_witness","$count_context"):yield item
                else:yield from embedded_refs(item)
        elif isinstance(value,list):
            for item in value:yield from embedded_refs(item)
    # Every existing graph beat, silent or sounding, must resolve to its exact
    # source beat. A parent graph container is not an occurrence-level bridge.
    aliases=outputs["extended"]["projection"]["aliases"]
    for alias,locator in aliases.items():
        graph_id="r:extended/relational_graph:/nodes/"+alias.replace("~","~0").replace("/","~1")
        if isinstance(locator,str):
            target=nodes[f"event:{package['scope']['song_id']}:{locator}"]
            assert nodes[graph_id]["time"]["spans"]==target["time"]["spans"],"Graph note clock differs from canonical event"
            assert nodes[graph_id]["scope"].get("part_id")==target["scope"]["part_id"],"Graph note track scope differs"
            assert not any(e["type"]=="scope_contains_event" for e in forward[graph_id]),"Graph note has whole-bar population"
            checks["exact_graph_note_clocks"]+=1
            continue
        if not isinstance(locator,dict):continue
        beat_id=f"beat:{package['scope']['song_id']}:{locator['part_id']}:{locator['bar']}:{locator['voice']}:{locator['beat']}"
        assert any(e.get("to_id")==beat_id and e["type"]=="mentions_written_beat" for e in forward[graph_id]),"Missing graph-to-source beat bridge"
        assert nodes[graph_id]["time"]["spans"]==nodes[beat_id]["time"]["spans"],"Graph beat clock differs from canonical beat"
        checks["grounded_graph_beats"]+=1
    sounding=outputs["extended"]["sounding_graph"]
    for index,lane in enumerate(sounding["lanes"]):
        ident=f"r:extended/sounding_graph:/lanes/{index}"
        expected_members={"r:extended/sounding_graph:/sustains/"+s.replace("~","~0").replace("/","~1") for s in lane["members"]}
        actual_members={e["to_id"] for e in forward[ident] if e["type"]=="inferred_lane_member"}
        assert actual_members==expected_members,"Sounding lane sustain membership differs"
        assert nodes[ident]["time"]["spans"]==[dict(start=sounding["sustains"][s]["onset_q"],end=sounding["sustains"][s]["end_q"]) for s in lane["members"]],"Inferred lane clock differs"
        checks["grounded_sounding_lanes"]+=1
    for ti,result in enumerate(outputs["extended"]["pattern_hypotheses"]["phrases"]):
        track=next(t for t in outputs["core"]["songs"][0]["tracks"] if t["part_id"]==result["part_id"])
        phrases=result["analysis"]["phrases"]
        ids={p["start_measure"]:f"r:extended/pattern_hypotheses:/phrases/{ti}/analysis/phrases/{pi}" for pi,p in enumerate(phrases)}
        for phrase in phrases:
            ident=ids[phrase["start_measure"]]
            population=[r for r in track["rows"]+track["grace_rows"] if r["voice"]==0 and r["midi"] is not None and phrase["start_measure"]<=r["bar"]<=phrase["end_measure"]]
            expected={f"event:{package['scope']['song_id']}:{r['occurrence']}" for r in population}
            assert {e["to_id"] for e in forward[ident] if e["type"]=="primary_voice_comparison_population"}==expected,"Phrase comparison population differs"
            low={f"event:{package['scope']['song_id']}:{r['occurrence']}" for r in population if r["midi"]==min(x["midi"] for x in population if (x["bar"],x["beat"])==(r["bar"],r["beat"]))}
            assert {e["to_id"] for e in forward[ident] if e["type"]=="lowest_pitch_outline_input"}==low,"Phrase outline input differs"
            previous={ids[phrase["develops_phrase_at"]]} if "develops_phrase_at" in phrase else set()
            assert {e["to_id"] for e in forward[ident] if e["type"]=="develops_previous_phrase"}==previous,"Phrase predecessor link differs"
            checks["verified_phrase_comparison_inputs"]+=1
        hist=Counter()
        summary=f"r:extended/pattern_hypotheses:/phrases/{ti}/analysis"
        assert len([e for e in forward[summary] if e["type"]=="transition_histogram_unit"])==max(0,len(phrases)-1),"Phrase transition histogram units differ"
        for pi,(a,b) in enumerate(zip(phrases,phrases[1:])):
            ident=f"phrase-transition:{ti}:{pi}"
            assert {e["to_id"] for e in forward[ident] if e["type"]=="transition_previous"}=={ids[a["start_measure"]]},"Transition origin differs"
            assert {e["to_id"] for e in forward[ident] if e["type"]=="transition_next"}=={ids[b["start_measure"]]},"Transition destination differs"
            hist[a["relationship"]+" → "+b["relationship"]]+=1
        assert dict(hist)==result["analysis"]["development_transitions"],"Phrase transition counts differ"
    for record in records:
        for target in embedded_refs(record["values"]):
            assert target in nodes,"Dangling embedded reference"
            assert nodes[target]["tier"]<=record["tier"],"Embedded lower-tier reference points upward"
        checks["lower_state_closed_records"]+=1
    expected={};beats=0;raw_note_slots=0;rest_slots=0
    for doc in docs.values():
        if not doc["filename"].startswith("track-"):continue
        part=doc["payload"]
        for mi,measure in enumerate(part.get("measures",[]),1):
            for vi,voice in enumerate(measure.get("voices",[])):
                for bi,beat in enumerate(voice.get("beats",[])):
                    beats+=1
                    for ni,note in enumerate(beat.get("notes",[])):
                        raw_note_slots+=1;rest_slots+=bool(note.get("rest"))
                        if not note.get("rest"):expected[f"event:{package['scope']['song_id']}:{part['partId']}:{mi}:{vi}:{bi}:{ni}"]=note
    events={r["id"]:r for r in records if r.get("event_id")}
    assert set(events)==set(expected),"Entire source note population not preserved"
    assert beats==sum(r["kind"]=="written_beat" for r in records),"Missing source beats"
    for ident,node in events.items():
        ref=node["source"]
        assert pointer(docs[ref["document"]]["payload"],ref["pointer"])==expected[ident]
        assert any(e["type"]=="event_in_beat" for e in forward[ident]),"Unlocated event"
        span=node["time"]["spans"][0];start=F(node["values"]["onset_q"])
        assert F(span["start"])==start,"Canonical event clock changed"
        duration=F(0) if node["kind"]=="grace_note" else F(node["values"]["duration_q"])
        assert F(span["end"])==start+duration,"Canonical event duration changed"
        checks["canonical_note_occurrences"]+=1
    for node in records:
        if node["time"]:
            for span in node["time"]["spans"]:
                assert F(span["end"])>=F(span["start"]),"Negative temporal interval"
                checks["exact_written_spans"]+=1
    for key,ident in package["output_roots"].items():
        document,path=key.split("#",1)
        assert materialize(package,ident,nodes=nodes,docs={k:d["payload"] for k,d in docs.items()})==pointer(outputs["extended"][document.split("/",1)[1]] if document.startswith("extended/") else outputs[document],path),"Existing output lost/changed: "+key
        checks["exact_output_roots"]+=1
    metric_observations=[r["values"] for r in records if r["kind"]=="individual_note_metric_observation"]
    for summary in outputs["individual_notes"]["songs"]:
        for feature,views in summary["metrics"].items():
            for view in ("written_regular_segments","fresh_note_attacks"):
                population=[r for r in metric_observations if view=="written_regular_segments" or r["attack"]]
                assert len(population)==views[view]["candidates"],"Metric denominator population changed"
                assert sum(r["features"][feature]["state"] is not None for r in population)==views[view]["known"],"Known marker denominator changed"
                assert sum(r["features"][feature]["state"] is True for r in population)==views[view]["positive"],"Positive marker count changed"
            mass=views["written_note_duration_mass"]
            assert sum((F(r["written_duration_q"]) for r in metric_observations if r["features"][feature]["state"] is not None),F(0))==F(mass["known_q"]),"Written duration mass changed"
            assert sum((F(r["written_duration_q"]) for r in metric_observations if r["features"][feature]["state"] is True),F(0))==F(mass["positive_q"]),"Positive duration mass changed"
            checks["verified_note_metric_features"]+=1
    support=outputs["profile_support"]
    verify_contexts(package,outputs,nodes,forward,checks)
    for record in records:
        if record["kind"]!="counted_observation_witness":continue
        unit=record["values"]["support"]
        members=set(unit.get("members",[])+unit.get("call_members",[])+unit.get("response_members",[]))
        if "occurrence" in unit:members.add(unit["occurrence"])
        expected_members={f"event:{package['scope']['song_id']}:{m}" for m in members}
        actual_members={e["to_id"] for e in forward[record["id"]] if e["type"]=="observed_unit_member"}
        assert actual_members==expected_members,"Count witness contains scope notes or omits exact units"
        checks["exact_count_witness_memberships"]+=1
    assert all(x["support"] is not None for x in support),"Counted unit without evidence"
    for i,table in enumerate(outputs["relationship_profile"]["tables"]):
        assert sum(x["count"] for x in table["outcomes"])==table["eligible_count"]
        for j,outcome in enumerate(table["outcomes"]):
            ident=f"r:relationship_profile:/tables/{i}/outcomes/{j}"
            links=[e for e in forward[ident] if e["type"]=="derived_from_complete_units"]
            assert len(links)==outcome["count"],"Truncated conditional evidence"
            for link in links:
                assert any(e["type"]=="observed_unit_member" for e in forward[link["to_id"]]),"Support unit not grounded in source events"
            checks["complete_count_unit_cells"]+=1
    # Verify a path FROM every profiled event UP to the corresponding cells.
    grounded={e["to_id"] for state in states.values() for e in state.get("links",[]) if e["type"]=="observed_unit_member"}
    for event in grounded:
        assert any(any(e["type"]=="derived_from_complete_units" for e in reverse[parent["from_id"]]) for parent in reverse[event] if parent["type"]=="observed_unit_member"),"Event cannot walk up to counted result"
    checks["profiled_events_with_upward_path"]=len(grounded)
    checks["source_beats"]=beats
    checks["raw_note_object_slots"]=raw_note_slots
    checks["rest_placeholder_slots"]=rest_slots
    checks["tracks"]=sum(d["filename"].startswith("track-") for d in docs.values())
    checks["records"]=len(records)
    return dict(status="pass",checks=dict(checks),limitations=["Source-preserving mapping and traversal verification, not musical judgment or a GP inverse.","Single song cannot validate artist generalization."])


def main():
    p=argparse.ArgumentParser();p.add_argument("bundle",type=Path);p.add_argument("source",type=Path);a=p.parse_args()
    result=verify(read(a.bundle/"song.tiered.json"),read(a.bundle/"existing-outputs.json"),a.source)
    (a.bundle/"qa.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))

if __name__=="__main__":main()
