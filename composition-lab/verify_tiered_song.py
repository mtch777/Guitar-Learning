"""Independent integrity/coverage checks for the private tiered song artifact."""
import argparse
from collections import Counter,defaultdict,deque
from fractions import Fraction as F
import json
from pathlib import Path
from build_tiered_song import layers,read,digest,pointer,materialize


def verify(package,outputs,source_folder=None):
    states=layers(package)
    assert list(states)==[5,4,3,2,1,0], "Hierarchy must be physically nested 5 through 0"
    records=[r for s in states.values() for r in s["records"]]
    nodes={r["id"]:r for r in records}
    assert len(nodes)==len(records),"Duplicate record identities"
    docs={d["id"]:d for d in states[0]["documents"]}
    checks=Counter()
    for doc in docs.values():
        assert digest(doc["payload"])==doc["payload_sha256"],"Source payload changed"
        if source_folder:assert read(Path(source_folder)/doc["filename"])==doc["payload"],"Captured JSON differs"
        checks["source_documents"]+=1
    forward=defaultdict(list);reverse=defaultdict(list)
    for state in states.values():
        for edge in state.get("links",[]):
            assert edge["from_id"] in nodes,"Dangling edge origin"
            if "to_id" in edge:
                assert edge["to_id"] in nodes,"Dangling edge target"
                assert nodes[edge["to_id"]]["tier"]<=nodes[edge["from_id"]]["tier"],"Lower tier depends on higher tier"
                forward[edge["from_id"]].append(edge)
                reverse[edge["to_id"]].append(edge)
            else:
                ref=edge["to_source"]
                pointer(docs[ref["document"]]["payload"],ref["pointer"])
                checks["source_links"]+=1
            checks["edges"]+=1
    def embedded_refs(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key in ("$record","$count_cell","$count_witness"):yield item
                else:yield from embedded_refs(item)
        elif isinstance(value,list):
            for item in value:yield from embedded_refs(item)
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
    assert all(x["support"] is not None for x in support),"Counted unit without evidence"
    for i,table in enumerate(outputs["relationship_profile"]["tables"]):
        assert sum(x["count"] for x in table["outcomes"])==table["eligible_count"]
        for j,outcome in enumerate(table["outcomes"]):
            ident=f"r:relationship_profile:/tables/{i}/outcomes/{j}"
            links=[e for e in forward[ident] if e["type"]=="derived_from_complete_units"]
            assert len(links)==outcome["count"],"Truncated conditional evidence"
            for link in links:
                assert any(e["type"]=="observed_unit_member" for e in forward[link["to_id"]]),"Support unit not grounded in source events"
            checks["fully_grounded_conditional_cells"]+=1
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
