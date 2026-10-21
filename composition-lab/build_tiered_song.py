"""Map a complete captured Songsterr song and existing analysis into nested JSON.

Private output only. This is a provenance-preserving adapter, not a GP inverse,
new musical detector or cross-song artist validation.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
import re
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).parent
API = ROOT / "songsterr_automation/songsterr_api"
sys.path.insert(0, str(API))
import analyze_relationships as core
import analyze_pattern_robustness as robustness
from pedal_evidence import analyze_evidence
from evaluate_pedal_expansion import evaluate as expand
from pedal_dialogue import analyze_dialogue
import artist_profiles
import artist_relationship_profiles as profiles
import artist_note_summaries
import relationship_profile_summary
import audit_api_coverage
import validate_technique_analysis
import build_analysis_evidence
import analyze_remaining_gaps
import api_analysis_views
from connect_tiered_patterns import connect_patterns


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError("Duplicate JSON key: "+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError("Invalid nonfinite JSON number: "+value)
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),object_pairs_hook=pairs,parse_constant=invalid)


def escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def pointer(value, path):
    if path and not path.startswith("/"):raise ValueError("JSON pointer must be absolute")
    for key in path[1:].split("/") if path else []:
        if re.search(r"~(?![01])",key):raise ValueError("Invalid JSON pointer escape")
        key = key.replace("~1", "/").replace("~0", "~")
        if isinstance(value,list):
            if not key.isdigit() or (len(key)>1 and key.startswith("0")) or int(key)>=len(value):raise ValueError("Invalid JSON array pointer")
            value=value[int(key)]
        else:value=value[key]
    return value


def layer(tier, lower=None):
    result = dict(tier=tier, name=["captured_source", "events", "relationships", "patterns", "song", "artist"][tier], records=[], coverage={}, lower_tier=lower)
    return result


def layers(package):
    result = {}
    node = package["representation"]
    while node is not None:
        result[node["tier"]] = node
        node = node["lower_tier"]
    return result


def source_capture(folder):
    files = [folder / "metadata.json", *sorted(folder.glob("track-*.json"), key=lambda p:int(p.stem.split("-")[-1]))]
    documents = []
    for path in files:
        payload = read(path)
        documents.append(dict(id="source:"+path.name, filename=path.name, byte_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), payload_sha256=digest(payload), payload=payload))
    return documents


def analyze_capture(documents):
    # Existing composite analyzer accepts folders. Materialize ONLY supplied JSON.
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp) / "song"
        folder.mkdir()
        for doc in documents:
            (folder / doc["filename"]).write_text(json.dumps(doc["payload"]), encoding="utf-8")
        return core.analyze(Path(temp))


def existing_outputs(report, documents):
    song = report["songs"][0]
    seeds = []
    for track in song["tracks"]:
        if not track["guitar_or_bass"] or not track["temporal_relationships_eligible"]:
            continue
        for section in sorted({r["section_start"] for r in track["rows"]}):
            rows = [r for r in track["rows"] if r["section_start"] == section]
            result = analyze_evidence(rows)
            seeds.append(dict(song_id=song["song_id"], part_id=track["part_id"], section_start=section, **{k:result[k] for k in ("accepted", "anchor_pitches", "roles", "cycles", "reason")}))
    accepted = expand(report, seeds)
    dialogues = []
    for pedal in accepted["tracks"]:
        track = next(t for t in song["tracks"] if t["part_id"] == pedal["part_id"])
        # The existing dialogue analyzer is explicitly a source region measurement,
        # not a replacement for approved phrase membership.
        for phrase in pedal["phrases"]:
            region = dict(phrase, anchor_pitches=sorted({r["midi"] for r in track["rows"] if phrase["roles"].get(r["occurrence"]) == "call"}), section_start=next(r["section_start"] for r in track["rows"] if r["occurrence"] in phrase["members"]), scope_end_q=phrase["end_q"])
            dialogues.append(dict(part_id=track["part_id"], measurement=analyze_dialogue(track, region)))
    public_robustness, private_robustness = robustness.analyze(report)
    support = []
    partition = song["provisional_partition"]
    programs = {(song["song_id"], t["partId"]):t.get("instrumentId") for t in (d["payload"] for d in documents if d["filename"].startswith("track-")) if isinstance(t.get("instrumentId"),int) and 0<=t["instrumentId"]<=127}
    model = profiles.build_relationship_profile(report, accepted, song["artist"], programs, partition=partition, support_sink=support.append)
    baseline = profiles.build_relationship_profile(report, accepted, song["artist"], programs, partition=partition)
    if model != baseline:
        raise AssertionError("Support recording changed existing profile output")
    notes = artist_note_summaries.summarize_notes(report, song["artist"], partition=partition)
    event_observations, observation_exclusions = artist_profiles.observations(report, {(p["song_id"],p["part_id"]):{i:role for phrase in p["phrases"] for i,role in phrase["roles"].items()} for p in accepted["tracks"]}, [(p["song_id"],p["part_id"]) for p in accepted["tracks"]])
    summary = relationship_profile_summary.summarize(model) if model["scope"] == "development_fit" else {"unavailable":"Requires development partition; preserved original partition"}
    coverage,private_coverage=audit_api_coverage.scan_documents(("metadata" if d["filename"]=="metadata.json" else "track",d["payload"],str(song["song_id"]),None if d["filename"]=="metadata.json" else d["filename"]) for d in documents)
    with tempfile.TemporaryDirectory() as temp:
        source_root=Path(temp);source_song=source_root/str(song["song_id"]);source_song.mkdir()
        for doc in documents:(source_song/doc["filename"]).write_text(json.dumps(doc["payload"]),encoding="utf-8")
        verification=validate_technique_analysis.audit(report,source_root)
        examples=build_analysis_evidence.build(report,source_root)
        # This legacy helper constructs a GP filename even when none was supplied.
        # It is not captured song data and must not become a phantom resource.
        for example in examples["examples"]:
            example["source_gp"]=None
            example["source_gp_status"]="not_supplied_in_API_only_analysis; legacy constructed filename is not a real asset"
        remaining=analyze_remaining_gaps.analyze(source_root)
    extended=api_analysis_views.run(song,documents)
    return dict(extended=extended,api_coverage=coverage,private_api_coverage=private_coverage,verification=verification,evidence_examples=examples,remaining_gaps=remaining,core=report, pedal_seeds=seeds, approved_pedals=accepted, dialogue=dialogues, pattern_robustness=dict(summary=public_robustness, tracks=private_robustness), profile_observations=dict(events=event_observations, exclusions=observation_exclusions,descriptive_inventory=artist_profiles.describe(event_observations)), relationship_profile=model, profile_support=support, individual_notes=notes, profile_summary=summary)


# Explicit root-field allocation: unrecognized fields fail instead of disappearing.
TRACK_TIERS = {
  1: {"part_id","name","program_guitar_or_bass","catalog_flags","identity_warnings","rest_spans","rows","grace_rows","timing_warnings","physical_notation_flags","temporal_relationships_eligible","guitar_or_bass"},
  2: {"technique_values","technique_value_histograms","sustain_relationships","relationship_details","coattack_groups","hopo_transition_candidates","unresolved_hp","examples","counterexamples"},
  3: {"pedal_candidates"}, 4: {"summary","sections"}}
SONG_TIERS = {1:{"shared_layout","layout_warnings","playback","timeline"},4:{"song_id","revision_id","artist","title","ai_generated","is_junk","candidate_work_family","provisional_partition","notation_hash","summary"}}


def contains_entities(value):
    if isinstance(value,list):return any(isinstance(x,dict) for x in value)
    return isinstance(value,dict) and any(contains_entities(x) for x in value.values())


class Mapper:
    def __init__(self, documents, song):
        self.song = song
        self.documents = {d["id"]:d for d in documents}
        self.tiers = {0:layer(0)}
        self.tiers[0]["documents"] = documents
        for tier in range(1,6):
            self.tiers[tier] = layer(tier,self.tiers[tier-1])
        self.nodes = {}
        self.event_ids = {}
        self.roots = {}
        self.links = []
        self.pending = []
        self.mapping = []
        self.output_projections = {}

    def source_ref(self, part_id, row):
        base = f"/measures/{row['bar']-1}/voices/{row['voice']}/beats/{row['beat']}"
        return dict(document="source:track-"+str(part_id)+".json", pointer=base+"/notes/"+str(row["note"]))

    def emit(self, value, document, path, tier, part=None, context=None):
        # Dicts/lists are encoded as connected records; scalar arrays remain exact.
        ident = "r:"+document+":"+path
        if tier==1 and isinstance(value,dict) and "occurrence" in value and "raw_note" in value:
            ident="event:"+str(self.song["song_id"])+":"+value["occurrence"]
        inherited = dict(context or {})
        if isinstance(value, dict):
            inherited.update({k:value[k] for k in ("part_id","section_start","bar","measure","start_measure","end_measure") if k in value})
            if "/sections/" in path and path.rsplit("/",1)[-1].isdigit() and "id" in value:inherited["section_start"]=value["id"]
        if document in ("extended/relational_graph","extended/sounding_graph") and isinstance(value,dict) and isinstance(value.get("measure"),int):
            inherited["measure"]=value["measure"]+1  # Legacy graph indices are zero-based.
        scope = dict(song_id=self.song["song_id"], **inherited)
        if part is not None: scope["part_id"] = part
        kind=path.rsplit("/",1)[-1] or document
        if kind.isdigit():kind=path.rsplit("/",2)[-2]+"_item"
        if document=="extended/relational_graph" and path.startswith("/nodes/") and path.count("/")==2:
            kind="relational_"+value["kind"]
        elif document=="extended/sounding_graph" and path.count("/")==2:
            if path.startswith("/occurrences/"):kind="sounding_written_occurrence"
            elif path.startswith("/sustains/"):kind="sounding_sustain"
            elif path.startswith("/lanes/"):kind="inferred_lane"
        node = dict(id=ident,tier=tier,kind=kind,scope=scope,values=None,time=None,origin=dict(document=document,pointer=path),status="existing_logic_output")
        if document in ("extended/harmony_hypotheses","extended/pattern_hypotheses","extended/harmony_boundaries","extended/structure_hypotheses"):
            node["status"]="heuristic_hypothesis_not_source_fact"
        elif document=="extended/sounding_graph":node["status"]="explicit_tie_resolution_and_inferred_lane_view"
        elif document in ("relationship_profile","profile_summary","individual_notes"):node["status"]="single_song_descriptive_result_not_artist_generalization"
        elif document=="approved_pedals":node["status"]="accepted_detector_output_not_individual_human_label"
        elif document=="pedal_seeds" or "pedal_candidates" in path:node["status"]="candidate_detection_output"
        self.nodes[ident]=node
        self.tiers[tier]["records"].append(node)
        self.mapping.append(dict(document=document,pointer=path,record=ident,tier=tier))
        if isinstance(value, dict) and "occurrence" in value and "raw_note" in value and tier == 1:
            ref = self.source_ref(part,value)
            raw = pointer(self.documents[ref["document"]]["payload"],ref["pointer"])
            if raw != value["raw_note"]:raise AssertionError("Source occurrence mismatch")
            event = "event:"+str(self.song["song_id"])+":"+value["occurrence"]
            if value["occurrence"] in self.event_ids:raise AssertionError("Duplicate canonical occurrence")
            self.event_ids[value["occurrence"]]=ident
            node.update(event_id=event,kind="grace_note" if "/grace_rows/" in path else "note",source=ref)
            self.links.append(dict(type="resolved_from",from_id=ident,to_source=ref))
            part_doc=self.documents[ref["document"]]["payload"]
            midi=value.get("midi")
            for setting in ("tuning","capo"):
                if setting not in part_doc:continue
                location="/"+setting
                if setting=="tuning" and midi is not None:location+="/"+str(value["string"])
                self.links.append(dict(type="pitch_setting_input" if midi is not None else "track_setting_context",from_id=ident,to_source=dict(document=ref["document"],pointer=location)))
            if midi is not None:
                names=("C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B")
                node["resolved_display"]=dict(letter_octave=names[int(midi)%12]+"_"+str(int(midi)//12-1) if float(midi).is_integer() else None,basis="calculated base MIDI pitch; display spelling convention, not literal source spelling")
        if isinstance(value, dict):
            values={}
            for key,child in value.items():
                if key in ("next_monophonic_interval","next_attack_gap_q") and node.get("event_id"):
                    child_id=self.emit(child,document,path+"/"+escape(key),2,part,inherited)
                    self.nodes[child_id]["kind"]=key
                    self.nodes[child_id]["origin_occurrence"]=value["occurrence"]
                    self.output_projections.setdefault(ident,{})[key]={"$record":child_id}
                    self.links.append(dict(type="describes_origin_event",from_id=child_id,to_id=ident))
                elif key == "raw_note" and node.get("source"):
                    values[key]={"$source":node["source"]}
                elif key == "raw_beat_effects" and node.get("source"):
                    values[key]={"$source":dict(document=node["source"]["document"],pointer=node["source"]["pointer"].rsplit("/notes/",1)[0],exclude_keys=["notes"])}
                elif contains_entities(child) or document=="extended/sounding_graph" and path=="" and key in {"occurrences","sustains"} or document in ("extended/relational_graph","extended/sounding_graph") and path in ("/nodes","/occurrences","/sustains") and isinstance(child,dict):
                    child_tier=4 if document=="individual_notes" and path=="" and key in ("songs","track_sections") else 2 if document=="profile_observations" and path=="" and key=="events" else tier
                    child_id=self.emit(child,document,path+"/"+escape(key),child_tier,part,inherited)
                    values[key]={"$record":child_id}
                    self.links.append(dict(type="contains",from_id=ident,to_id=child_id))
                else: values[key]=child
            node["values"]=values
        elif isinstance(value,list):
            values=[]
            for i,child in enumerate(value):
                if isinstance(child,(dict,list)):
                    child_id=self.emit(child,document,path+"/"+str(i),tier,part,inherited)
                    values.append({"$record":child_id});self.links.append(dict(type="contains",from_id=ident,to_id=child_id))
                else:values.append(child)
            node["values"]=values
        else:node["values"]=value
        self.pending.append((ident,value,part))
        return ident

    def add(self,value,document,path,tier,part=None):
        self.roots[document+"#"+path]=self.emit(value,document,path,tier,part)

    def finish(self):
        rows={r["occurrence"]:r for t in self.song["tracks"] for r in t["rows"]+t["grace_rows"]}
        aliases=getattr(self,"aliases",{})
        def alias_target(alias):
            locator=aliases.get(alias)
            if isinstance(locator,str):return self.event_ids[locator]
            if isinstance(locator,dict):return f"beat:{self.song['song_id']}:{locator['part_id']}:{locator['bar']}:{locator['voice']}:{locator['beat']}"
        graph_members=defaultdict(set)
        for edge in getattr(self,"graph_edges",[]):
            if edge["relation"] in {"SAME_TRACK","IN_VOICE","SAME_MEASURE","IN_SECTION"}:
                member=alias_target(edge["source"])
                if member:graph_members[edge["target"]].add(member)
        def graph_context(node):
            origin=node.get("origin",{});path=origin.get("pointer","")
            if origin.get("document")!="extended/relational_graph" or not path.startswith("/nodes/"):return False
            key=path.split("/")[2].replace("~1","/").replace("~0","~")
            target=alias_target(key)
            members={target} if target else graph_members.get(key,set())
            if not members:return False
            scopes=[self.nodes[m]["scope"] for m in sorted(members)]
            scope=dict(song_id=self.song["song_id"])
            for field in ("part_id","bar","voice","beat"):
                values={s.get(field) for s in scopes}
                if len(values)==1 and None not in values:scope[field]=values.pop()
            node["scope"]=scope
            spans={ (s["start"],s["end"]) for m in members for s in (self.nodes[m].get("time") or {}).get("spans",[]) }
            if spans:
                node["time"]=dict(basis="written_quarter_notes",spans=[dict(start=a,end=b) for a,b in sorted(spans,key=lambda s:(F(s[0]),F(s[1])))],status="exact_canonical_event_clock" if target else "exact_member_spans_not_continuous_extent")
            if path.count("/")==2:
                for member in sorted(members):self.links.append(dict(type="graph_source_occurrence" if target else "graph_group_member",from_id=node["id"],to_id=member))
            return True
        def sounding_context(node):
            origin=node.get("origin",{});path=origin.get("pointer","")
            if origin.get("document")!="extended/sounding_graph":return False
            fields=path.split("/")
            if len(fields)<3 or fields[1] not in {"occurrences","sustains","lanes"}:return False
            key=fields[2].replace("~1","/").replace("~0","~")
            source=self.sounding[fields[1]][int(key) if fields[1]=="lanes" else key]
            node["scope"]=dict(song_id=self.song["song_id"],part_id=self.song["tracks"][source["track"]]["part_id"],voice=source.get("voice",source.get("source_voice")))
            if fields[1]=="occurrences":
                target=self.nodes[alias_target(key)]
                node["scope"]=dict(target["scope"])
                spans=target["time"]["spans"]
            elif fields[1]=="sustains":spans=[dict(start=source["onset_q"],end=source["end_q"])]
            else:spans=[dict(start=self.sounding["sustains"][s]["onset_q"],end=self.sounding["sustains"][s]["end_q"]) for s in source["members"]]
            node["time"]=dict(basis="written_quarter_notes",spans=spans,status="existing_written_sustain_or_inferred_lane_members_not_acoustic_sound")
            return True
        def refs(v, beat_refs):
            if isinstance(v,str):
                if v in rows:return {v}
                alias=aliases.get(v)
                if isinstance(alias,dict) and set(alias)=={"part_id","bar","voice","beat"}:
                    beat_id=f"beat:{self.song['song_id']}:{alias['part_id']}:{alias['bar']}:{alias['voice']}:{alias['beat']}"
                    if beat_id not in self.nodes:raise AssertionError("Graph alias lacks canonical source beat")
                    beat_refs.add(beat_id)
                return {alias} if isinstance(alias,str) and alias in rows else set()
            if isinstance(v,list):return set().union(*(refs(x,beat_refs) for x in v)) if v else set()
            if isinstance(v,dict):
                if set(v)=={"part_id","bar","voice","beat"}:
                    beat_id=f"beat:{self.song['song_id']}:{v['part_id']}:{v['bar']}:{v['voice']}:{v['beat']}"
                    if beat_id not in self.nodes:raise AssertionError("Source locator lacks canonical written beat")
                    beat_refs.add(beat_id)
                return set().union(*(refs(k,beat_refs)|refs(x,beat_refs) for k,x in v.items())) if v else set()
            return set()
        for ident,value,part in self.pending:
            node=self.nodes[ident]
            beat_refs=set()
            ids=refs(value,beat_refs)
            origin=node.get("origin",{})
            graph_path=origin.get("pointer","")
            if origin.get("document")=="extended/relational_graph" and graph_path.startswith("/nodes/") and graph_path.count("/")==2:
                ids.update(refs(graph_path.rsplit("/",1)[1].replace("~1","/").replace("~0","~"),beat_refs))
            for beat_id in sorted(beat_refs):
                self.links.append(dict(type="mentions_written_beat",from_id=ident,to_id=beat_id))
            if node.get("origin_occurrence"):
                origin=rows[node["origin_occurrence"]];ids.add(node["origin_occurrence"])
                target_q=F(origin["onset_q"])+F(origin["next_attack_gap_q"])
                destinations=[i for i,r in rows.items() if i.split(":")[0]==origin["occurrence"].split(":")[0] and r["voice"]==origin["voice"] and r["section_start"]==origin["section_start"] and not r["tie_destination"] and F(r["onset_q"])==target_q]
                if len(destinations)!=1:raise AssertionError("Legacy next-note annotation lacks a unique destination")
                destination=destinations[0];ids.add(destination)
                node["endpoints"]=dict(origin=self.event_ids[origin["occurrence"]],destination=self.event_ids[destination])
                node["units"]="signed_semitones" if node["kind"]=="next_monophonic_interval" else "quarter_notes"
                for endpoint,event_id in node["endpoints"].items():self.links.append(dict(type="relationship_"+endpoint,from_id=ident,to_id=event_id))
            # Explicit population links are different from source membership.
            population=set()
            if node["kind"]=="summary" and part is not None:
                population={r["occurrence"] for t in self.song["tracks"] if t["part_id"]==part for r in t["rows"] if node["scope"].get("section_start") in (None,r["section_start"])}
            for occurrence in sorted(population):
                self.links.append(dict(type="summarizes_population",from_id=ident,to_id=self.event_ids[occurrence]))
            for occurrence in sorted(ids):
                event=self.event_ids[occurrence]
                relation="observed_unit_member" if node["origin"]["document"]=="count_witnesses" else "calculation_input_member" if node["origin"]["document"]=="count_calculation_inputs" else "mentions_event"
                if event!=ident:self.links.append(dict(type=relation,from_id=ident,to_id=event))
            time=value if isinstance(value,dict) else {}
            start=next((time[k] for k in ("onset_q","start_q","scope_start_q","call_start_q") if time.get(k) is not None),None)
            end=next((time[k] for k in ("end_q","scope_end_q") if time.get(k) is not None),None)
            if graph_context(node) or sounding_context(node):
                pass
            elif start is not None:
                end=end if end is not None else str(F(start)+F(time["duration_q"])) if time.get("duration_q") is not None else start
                if node["kind"]=="grace_note":end=start
                node["time"]=dict(basis="written_quarter_notes",spans=[dict(start=str(F(start)),end=str(F(end)))],status="grace_attached_not_metric_duration" if node["kind"]=="grace_note" else "point_no_duration_claimed" if F(start)==F(end) else "explicit_existing_output")
            elif node["scope"].get("measure") is not None or node["scope"].get("start_measure") is not None:
                first=node["scope"].get("start_measure",node["scope"].get("measure"));last=node["scope"].get("end_measure",first)
                headers={h["bar"]:h for h in self.song["shared_layout"]}
                if first in headers and last in headers:
                    node["time"]=dict(basis="written_quarter_notes",spans=[dict(start=headers[first]["start_q"],end=str(F(headers[last]["start_q"])+F(headers[last]["span_q"])))],status="source_measure_scope_not_precise_attack")
                    eligible={r["occurrence"] for t in self.song["tracks"] if node["scope"].get("part_id") in (None,t["part_id"]) for r in t["rows"] if first<=r["bar"]<=last}
                    self.links.extend(dict(type="scope_contains_event",from_id=ident,to_id=self.event_ids[i]) for i in sorted(eligible))
            elif ids:
                node["temporal_support"]={"via":"outgoing_event_links","meaning":"disjoint underlying event spans; no invented continuous range"}
        # Structural child links and evidence edges have a single canonical store.
        for edge in self.links:
            tier=self.nodes[edge["from_id"]]["tier"]
            self.tiers[tier].setdefault("links",[]).append(edge)
        reverse=defaultdict(list)
        for edge in self.links:
            if "to_id" in edge:reverse[edge["to_id"]].append(dict(type=edge["type"],from_id=edge["from_id"]))
        for tier,state in self.tiers.items():
            state["coverage"]=dict(records=len(state["records"]),timed_records=sum(r["time"] is not None for r in state["records"]),interpretation="mapping existing outputs; not a new detector or proof of musical correctness")
        return dict(schema="composition-tiered-song/1",package_id="songsterr:"+str(self.song["song_id"])+":"+str(self.song["revision_id"]),id_contract="Record IDs are local to this immutable song/revision package. Cross-package references must include package_id and record_id.",scope=dict(song_id=self.song["song_id"],revision_id=self.song["revision_id"],artist=self.song["artist"],title=self.song["title"],whole_song=True,artist_generalization="unavailable_single_song"),representation=self.tiers[5],output_roots=self.roots,legacy_output_projections=self.output_projections,field_mapping=dict(derive_from="record.origin",mapped_record_count=len(self.mapping)),indexes=dict(reverse_links=dict(derive_from="canonical layer links",stored_separately=False),written_time=[dict(record=r["id"],**r["time"]) for r in self.nodes.values() if r["time"] and r["time"]["basis"]=="written_quarter_notes"],playback_time=[dict(record=r["id"],**r["time"]) for r in self.nodes.values() if r["time"] and r["time"]["basis"]=="playback_quarter_notes"]),limitations=["Existing composite analyzers are mapped by meaning; this adapter does not yet enforce isolated per-tier execution.","Source markers are not inferred phrase functions. Old candidate windows and approved pedal phrases remain distinct.","Written time is separate from repeat playback visits. Unknown musical interpretation is not invented."])


def add_beat_inventory(mapper):
    """Account for every written beat, including silent and grace beats."""
    header=mapper.song["shared_layout"]
    canonical={n["event_id"].split(":",2)[-1]:n for n in mapper.nodes.values() if n.get("event_id")}
    for doc in mapper.documents.values():
        if not doc["filename"].startswith("track-"):continue
        part=doc["payload"];pid=part["partId"]
        for mi,measure in enumerate(part.get("measures",[])):
            h=header[mi];start=F(h["start_q"]);span=F(h["span_q"])
            for vi,voice in enumerate(measure.get("voices",[])):
                cursor=F(0)
                for bi,beat in enumerate(voice.get("beats",[])):
                    grace=bool(beat.get("graceNote"))
                    raw=beat.get("duration")
                    duration=span if core.whole_measure_rest(measure,voice) else F(*raw)*4 if raw else None
                    q=None if cursor is None else start+cursor
                    ident=f"beat:{mapper.song['song_id']}:{pid}:{mi+1}:{vi}:{bi}"
                    ref=dict(document=doc["id"],pointer=f"/measures/{mi}/voices/{vi}/beats/{bi}")
                    node=dict(id=ident,tier=1,kind="written_beat",scope=dict(song_id=mapper.song["song_id"],part_id=pid,bar=mi+1,voice=vi,beat=bi),
                        values=dict(grace=grace,written_duration_q=str(duration) if duration is not None else None,source_note_slots=len(beat.get("notes",[]))),
                        time=None if q is None else dict(basis="written_quarter_notes",spans=[dict(start=str(q),end=str(q if grace or duration is None else q+duration))],status="grace_attachment" if grace else "unknown_duration" if duration is None else "resolved_source_rhythm"),
                        source=ref,status="calculated_from_captured_rhythm")
                    mapper.nodes[ident]=node;mapper.tiers[1]["records"].append(node)
                    mapper.links.append(dict(type="resolved_from",from_id=ident,to_source=ref))
                    for ni,note in enumerate(beat.get("notes",[])):
                        occurrence=f"{pid}:{mi+1}:{vi}:{bi}:{ni}"
                        if not note.get("rest"):
                            if occurrence not in mapper.event_ids:raise AssertionError("Unaccounted source note "+occurrence)
                            mapper.links.append(dict(type="event_in_beat",from_id=mapper.event_ids[occurrence],to_id=ident))
                    if not grace:cursor=None if duration is None or cursor is None else cursor+duration
    for track in mapper.song["tracks"]:
        pid=track["part_id"]
        for index,rest in enumerate(track["rest_spans"]):
            rid=f"r:core:/songs/0/tracks/{mapper.song['tracks'].index(track)}/rest_spans/{index}"
            candidates=[n for n in mapper.tiers[1]["records"] if n["kind"]=="written_beat" and n["scope"]["part_id"]==pid and n["scope"]["bar"]==rest["bar"] and n["scope"]["voice"]==rest["voice"] and n["time"] and n["time"]["spans"][0]["start"]==str(F(rest["onset_q"]))]
            for node in candidates:mapper.links.append(dict(type="rest_resolved_from_beat",from_id=rid,to_id=node["id"]))


def connect_summaries(mapper,outputs):
    """Give descriptive metrics their actual denominator observations."""
    song=mapper.song;eligible={}
    note_summary=outputs["individual_notes"]
    source_songs=set(note_summary["source_songs"])
    for track in song["tracks"]:
        if song["song_id"] not in source_songs or not track["guitar_or_bass"] or not track["temporal_relationships_eligible"]:continue
        for row in track["rows"]:
            ident=mapper.emit(dict(occurrence=row["occurrence"],attack=not row["tie_destination"],written_duration_q=row["duration_q"],features={f:dict(state=artist_note_summaries.marker_state(row,f)[0],reason=artist_note_summaries.marker_state(row,f)[1]) for f in artist_note_summaries.MARKERS}),"note_metric_observations","/"+row["occurrence"],2,track["part_id"],dict(section_start=row["section_start"]))
            mapper.nodes[ident]["kind"]="individual_note_metric_observation"
            eligible[row["occurrence"]]=(ident,track["part_id"],row["section_start"])
    for i,scope in enumerate(note_summary["track_sections"]):
        ident=f"r:individual_notes:/track_sections/{i}"
        mapper.links.extend(dict(type="metric_denominator_observation",from_id=ident,to_id=entry[0]) for occurrence,entry in eligible.items() if entry[1]==scope["part_id"] and entry[2]==scope["source_section_instance"])
    for i,scope in enumerate(note_summary["songs"]):
        ident=f"r:individual_notes:/songs/{i}"
        mapper.links.extend(dict(type="metric_denominator_observation",from_id=ident,to_id=entry[0]) for entry in eligible.values())
    # The artist-labelled aggregate is explicitly descriptive of this ONE song.
    agg="r:individual_notes:/artist_aggregate"
    if agg not in mapper.nodes:
        parent=mapper.nodes["r:individual_notes:"]
        value=note_summary["artist_aggregate"]
        agg=mapper.emit(value,"individual_notes","/artist_aggregate",5)
        parent["values"]["artist_aggregate"]={"$record":agg}
        mapper.links.append(dict(type="contains",from_id=parent["id"],to_id=agg))
    for i in range(len(note_summary["songs"])):mapper.links.append(dict(type="aggregate_of_song_metrics",from_id=agg,to_id=f"r:individual_notes:/songs/{i}"))
    # Equal-score/family/group summaries are derived from the original count rows.
    summary_root="r:profile_summary:"
    model=outputs["relationship_profile"]
    for i in range(len(model["technique_song_summaries"])):
        ident=f"r:relationship_profile:/technique_song_summaries/{i}"
        mapper.links.append(dict(type="summary_count_input",from_id=summary_root,to_id=ident))
        feature=model["technique_song_summaries"][i]["feature"]
        for ti,table in enumerate(model["tables"]):
            if table["kind"]=="technique_given_context" and table["condition"]["feature"]==feature:
                for oi in range(len(table["outcomes"])):mapper.links.append(dict(type="count_partition",from_id=ident,to_id=f"r:relationship_profile:/tables/{ti}/outcomes/{oi}"))


def add_playback_inventory(mapper):
    cursor=F(0);headers={h["bar"]:h for h in mapper.song["shared_layout"]}
    for index,visit in enumerate(mapper.song["playback"]["order"]):
        header=headers[visit["bar"]];duration=F(header["span_q"])
        ident=f"playback:{mapper.song['song_id']}:{index}"
        node=dict(id=ident,tier=1,kind="playback_bar_visit",scope=dict(song_id=mapper.song["song_id"],bar=visit["bar"]),
            values=dict(visit_index=index,pass_number=visit["pass_number"],source_bar=visit["bar"],source_written_start_q=header["start_q"],source_written_duration_q=str(duration)),
            time=dict(basis="playback_quarter_notes",spans=[dict(start=str(cursor),end=str(cursor+duration))],status="existing_repeat_order"),status="calculated_from_existing_playback_order")
        mapper.nodes[ident]=node;mapper.tiers[1]["records"].append(node)
        source_record=f"r:core:/playback/order/{index}"
        # The core document's source order remains separate and recoverable.
        actual=f"r:core:/songs/0/playback/order/{index}"
        mapper.links.append(dict(type="playback_order_input",from_id=ident,to_id=actual))
        for event in list(mapper.nodes.values()):
            if event.get("event_id") and event["scope"].get("bar")==visit["bar"]:
                mapper.links.append(dict(type="visits_written_event",from_id=ident,to_id=event["id"]))
        cursor+=duration


def connect_count_contexts(mapper,outputs,identities):
    """Connect recorded calculation scopes without relabeling them as count units."""
    tracks={t["part_id"]:(i,t) for i,t in enumerate(mapper.song["tracks"])}
    pedals={t["part_id"]:(i,t) for i,t in enumerate(outputs["approved_pedals"]["tracks"])}
    for ident in identities:
        descriptor=mapper.nodes[ident]["values"]
        # Local descriptor dictionaries contain no entity objects, so are inline.
        scope=descriptor["source_scope"];pid=descriptor.get("part_id")
        def link(target,relation="calculation_scope_input"):
            if target not in mapper.nodes:raise AssertionError("Missing calculation input "+target)
            mapper.links.append(dict(type=relation,from_id=ident,to_id=target))
        for part in ([pid] if pid is not None else descriptor.get("parts",[])):
            ti,_=tracks[part]
            for field in ("guitar_or_bass","temporal_relationships_eligible"):
                link(f"r:core:/songs/0/tracks/{ti}/{field}","track_eligibility_input")
        if scope in {"core_track_rows","eligible_attack_groups"}:
            ti,track=tracks[pid]
            link(f"r:core:/songs/0/tracks/{ti}/rows")
            population=[r for r in track["rows"] if r["midi"] is not None] if scope=="core_track_rows" else [r for r in track["rows"] if not r["tie_destination"] and F(r["duration_q"])>0]
            for row in population:link(mapper.event_ids[row["occurrence"]],"calculation_search_population")
            mapper.nodes[ident]["query"]=dict(selector=descriptor.get("selector","untied_positive_duration_regular_rows"),population_size=len(population),result_members=[])
            if descriptor.get("predicate")=="no_eligible_attack_at":
                matches=[r["occurrence"] for r in population if F(r["onset_q"])==F(descriptor["onset_q"])]
                if matches:raise AssertionError("False no-attack absence")
                mapper.nodes[ident]["query"]["result_members"]=matches
            elif descriptor.get("predicate")=="no_next_attack_in_same_section":
                origins={r["occurrence"]:r for r in track["rows"]}
                origin_rows=[origins[m] for m in descriptor["after_members"]]
                q=F(origin_rows[0]["onset_q"]);sections={r["section_start"] for r in origin_rows}
                section=next(iter(sections)) if len(sections)==1 else None
                later=[r for r in population if F(r["onset_q"])>q]
                next_q=min((F(r["onset_q"]) for r in later),default=None)
                next_rows=[r for r in later if F(r["onset_q"])==next_q]
                next_sections={r["section_start"] for r in next_rows}
                matches=[r["occurrence"] for r in next_rows] if section is not None and next_sections=={section} else []
                if matches:raise AssertionError("False no-next-in-section absence")
                mapper.nodes[ident]["query"].update(origin_q=str(q),section_start=section,result_members=matches)
        elif scope=="core_track_events":
            if not descriptor.get("members"):raise AssertionError("Empty local calculation inputs")
        elif scope=="accepted_pedal_track":
            if pid not in pedals:
                if descriptor.get("coverage")!="not_supplied":raise AssertionError("Accepted context track missing")
                link("r:approved_pedals:","accepted_coverage_search_scope")
                continue
            pi,track=pedals[pid]
            link(f"r:approved_pedals:/tracks/{pi}","accepted_role_coverage_input")
            for phrase in descriptor.get("phrase_indices",[]):link(f"r:approved_pedals:/tracks/{pi}/phrases/{phrase}","accepted_role_phrase_input")
        elif scope=="accepted_pedal_cycle":
            pi,track=pedals[pid]
            link(f"r:approved_pedals:/tracks/{pi}/phrases/{descriptor['phrase_index']}/cycles/{descriptor['cycle_index']}","accepted_cycle_input")
        elif scope=="core_shared_layout":
            for bar in descriptor["bars"]:link(f"r:core:/songs/0/shared_layout/{bar-1}","bar_layout_input")
        elif scope in {"core_hopo_candidates","core_technique_values","core_coattack_groups"}:
            ti,track=tracks[pid]
            field={"core_hopo_candidates":"hopo_transition_candidates","core_technique_values":"technique_values","core_coattack_groups":"coattack_groups"}[scope]
            if scope=="core_hopo_candidates":
                indices=[descriptor["pair_index"]] if "pair_index" in descriptor else [i for i,p in enumerate(track[field]) if p["origin"] in descriptor["origin_members"]]
            elif scope=="core_technique_values":indices=[descriptor["detail_index"]]
            else:
                onsets={F(q) for q in descriptor.get("onsets_q",[descriptor.get("onset_q")]) if q is not None}
                indices=[i for i,g in enumerate(track[field]) if F(g["onset_q"]) in onsets]
            for index in indices:link(f"r:core:/songs/0/tracks/{ti}/{field}/{index}","existing_classifier_or_mechanic_input")
            link(f"r:core:/songs/0/tracks/{ti}/{field}","classifier_lookup_scope")
        elif scope in {"captured_track_programs","supplied_track_programs"}:
            for part in descriptor["parts"]:
                doc=mapper.documents[f"source:track-{part}.json"]
                if "instrumentId" in doc["payload"]:mapper.links.append(dict(type="source_program_input",from_id=ident,to_source=dict(document=doc["id"],pointer="/instrumentId")))
        elif scope=="core_song_selection":
            for field in ("artist","provisional_partition","ai_generated","is_junk","candidate_work_family"):
                link(f"r:core:/songs/0/{field}","eligibility_or_weighting_input")
        elif scope=="accepted_pedal_tracks":link("r:approved_pedals:","accepted_coverage_search_scope")
        elif scope=="prior_eligible_bar_patterns":
            ti,track=tracks[pid]
            population=[r for r in track["rows"] if r["bar"]<descriptor["before_bar"] and not r["tie_destination"] and F(r["duration_q"])>0]
            for row in population:link(mapper.event_ids[row["occurrence"]],"prior_pattern_search_population")
            for bar in sorted({r["bar"] for r in population}):link(f"r:core:/songs/0/shared_layout/{bar-1}","prior_pattern_layout_input")
            mapper.nodes[ident]["query"]=dict(selector="untied_positive_duration_regular_attacks_in_prior_bars",before_bar_exclusive=descriptor["before_bar"],population_size=len(population),matched_members=descriptor.get("matched_members",[]))
        else:raise AssertionError("Unmapped count calculation scope "+scope)


def connect_selection_provenance(mapper):
    """Original metadata and actual eligibility inputs, not inferred musical roles."""
    meta=mapper.documents["source:metadata.json"]
    for field,key in {"song_id":"songId","revision_id":"revisionId","artist":"artist","title":"title","ai_generated":"aiGenerated","is_junk":"isJunk"}.items():
        if key in meta["payload"]:mapper.links.append(dict(type="captured_metadata_field",from_id=f"r:core:/songs/0/{field}",to_source=dict(document=meta["id"],pointer="/"+key)))
    for field,input_fields in {"candidate_work_family":("artist","title"),"provisional_partition":("song_id","candidate_work_family","notation_hash")}.items():
        for input_field in input_fields:
            mapper.links.append(dict(type="family_partition_method_input",from_id=f"r:core:/songs/0/{field}",to_id=f"r:core:/songs/0/{input_field}"))
    for doc in mapper.documents.values():
        if not doc["filename"].startswith("track-"):continue
        for key in ("measures","tuning","capo","instrumentId","automations","sounds","trackAutomations"):
            if key in doc["payload"]:mapper.links.append(dict(type="notation_hash_input",from_id="r:core:/songs/0/notation_hash",to_source=dict(document=doc["id"],pointer="/"+key)))
    for ti,track in enumerate(mapper.song["tracks"]):
        prefix=f"r:core:/songs/0/tracks/{ti}"
        doc=mapper.documents[f"source:track-{track['part_id']}.json"]
        if "instrumentId" in doc["payload"]:mapper.links.append(dict(type="program_classification_input",from_id=prefix+"/program_guitar_or_bass",to_source=dict(document=doc["id"],pointer="/instrumentId")))
        if "tracks" in meta["payload"]:mapper.links.append(dict(type="catalog_flag_lookup_input",from_id=prefix+"/catalog_flags",to_source=dict(document=meta["id"],pointer=f"/tracks/{ti}" if ti<len(meta["payload"]["tracks"]) else "/tracks")))
        for field in ("program_guitar_or_bass","catalog_flags"):
            mapper.links.append(dict(type="track_classification_input",from_id=prefix+"/guitar_or_bass",to_id=prefix+"/"+field))
        for field in ("timing_warnings","identity_warnings"):
            mapper.links.append(dict(type="temporal_eligibility_input",from_id=prefix+"/temporal_relationships_eligible",to_id=prefix+"/"+field))
        mapper.links.append(dict(type="temporal_eligibility_input",from_id=prefix+"/temporal_relationships_eligible",to_id="r:core:/songs/0/layout_warnings"))


INCLUDED_MODULES = {
    "build_tiered_song.py":"Current source capture, canonical mapping, evidence joins and lossless legacy-view normalization",
    "connect_tiered_patterns.py":"Exact occurrence/spans for existing fingerprint/repeat/variant/content outputs; no new detections",
    "walk_tiered_song.py":"Private traversal/time/source inspection; no new musical findings",
    "api_analysis_views.py":"Explicit API-to-existing-model-free-input projections with source aliases",
    "harmonic_inference.py":"Existing deterministic tonal/chord hypotheses, not musical ground truth",
    "relational_graph.py":"Existing exact event relationships from explicit API projection",
    "sounding_graph.py":"Existing tie/sounding/lane graph with original algorithm limitations",
    "phrase_development.py":"Existing candidate phrase and return heuristics from declared rounded view",
    "phrase_analysis.py":"Existing candidate motif-window scan; parsed-input entrypoint extracted unchanged",
    "analyze_motifs.py":"Existing timed/flexible/two-bar motif signatures and capped repeat groups",
    "harmony_boundaries.py":"Existing multi-track novelty from declared legacy input view",
    "validate_structure.py":"Existing label-blind boundary and chord candidates; not human validation",
    "palm_mute_method.py":"Existing source eligibility observations and mixed-group exclusions; optional complete evidence sink, no fitting or edits",
    "corpus_copy_audit.py":"Existing source streams/fingerprint helper for complete8/16/32-event windows; no generated comparison or originality claim",
    "pedal_register.py":"uniform_arpeggio guard included through approved detector; older analyze_register not substituted",
    "infer_tonality.py":"Compatibility wrapper for included harmonic_inference, not independently rerun",
    "performance_opportunities.py":"Existing positive/negative source technique opportunities; no fitting",
    "content_form.py":"Existing full source-section timeline identity; composer-dependent wrappers not invoked",
    "analyze_relationships.py":"Fresh complete source analysis; all output roots mapped",
    "source_semantics.py":"Included through core: layout, rhythm, playback, tempo, mechanics and sustain",
    "source_dynamics.py":"Included through core: explicit/inherited dynamics",
    "source_relationship_details.py":"Included through core: local timing, slides and unpitched ties",
    "source_slides.py":"Included through relationship_details: typed source endpoints",
    "source_timing_regions.py":"Included through relationship_details: explicit eligible regions",
    "technique_analysis.py":"Existing group classifier invoked by core; GP-only report entrypoint is separate",
    "pedal_patterns.py":"Legacy candidate windows retained distinctly, not approved phrases",
    "pedal_evidence.py":"Accepted identification logic rerun unchanged",
    "pedal_expansion.py":"Accepted additive continuation logic rerun unchanged",
    "pedal_dialogue.py":"Existing full-region measurements, separate from accepted roles",
    "analyze_pattern_robustness.py":"Existing recurrence and sustained-group analysis",
    "artist_profiles.py":"Existing observation features; no new model fitting/generalization",
    "artist_relationship_profiles.py":"Existing conditional tables; new optional complete-support recording",
    "artist_note_summaries.py":"Existing individual-note summaries in all three units",
    "relationship_profile_summary.py":"Existing weighted/pooled descriptive summary",
    "audit_api_coverage.py":"Verification: every observed API path reviewed by existing registry",
    "validate_technique_analysis.py":"Verification: independent source notation checks",
    "build_analysis_evidence.py":"Verification: source-readback examples; not full support substitute",
    "analyze_remaining_gaps.py":"Verification: known timing/slide/tie/dynamic gaps",
    "evaluate_pedal_expansion.py":"Existing unchanged additive-pass evaluator",
}


def implementation_registry():
    entries=[]
    for directory in (ROOT,API):
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("test_"):status="regression_test";reason="Test infrastructure, no song analysis output"
            elif path.name in INCLUDED_MODULES:status="included";reason=INCLUDED_MODULES[path.name]
            elif path.name=="joint_motion_contract.py":status="requires_explicit_role_schema";reason="observe is model-free but requires exactly named harmony/melody/bass tracks, one voice and declared role assignment; these are not supplied or invented for the capture."
            elif path.name=="aligned_relationship_audit.py":status="requires_declared_paired_streams";reason="interval_stream/changes are model-free on two declared nonoverlapping root streams; compare requires a candidate pair. No declared pair or overlap policy is supplied."
            elif path.name=="structural_learning.py":status="mixed_model_and_schema_dependencies";reason="phrase_features is model-free on its specific legacy phrase schema; form_sequence requires a fitted clusterer. No matching phrase schema or fitted clusterer is supplied."
            elif path.name=="relationship_hypotheses.py":status="composite_model_dependency";reason="interpret requires a boundary model and threshold; deterministic motif/harmony loops inside are not themselves trained models. Composite entrypoint not invoked without those inputs."
            elif path.name in {"artist_form.py","corpus_composer.py","source_harmony_transitions.py","joint_register_profile.py","harmony_feasibility.py","historical_harmony_replay.py"}:status="requires_prior_generator_model";reason="Existing model-specific analysis requires selected composer/role/harmony-bank artifacts; not a direct raw-song analysis. No new generation model fitted."
            elif path.name in {"structural_learning.py","relationship_hypotheses.py","external_score_export.py","model_benchmark.py"}:status="requires_external_model_or_corpus";reason="External trained model/corpus or separate benchmark dependency; not fabricated from this single capture."
            elif path.name.startswith(("compose","generate","run_","train_","learned_","role_","sequence_","pair_","open_pair","rhythm_control","profile_control","metadata_control")) or path.name in {"artist_form.py","structure_model.py","generation_freedom.py","generation_validation.py","form_returns.py"}:status="generation_or_model_workflow";reason="Separate generation/training/control workflow, not extraction of existing captured song facts."
            elif path.name.startswith(("build_","serve_","render_","review_","verify_","test_","evaluate_")):status="review_or_verification_entrypoint";reason="Presentation/render/evaluation orchestration; musical computations are included through named algorithms where applicable."
            elif path.name in {"analyze_corpus_sources.py","inspect_metadata.py","inspect_notation.py"}:status="legacy_or_capture_inventory";reason="Earlier overlapping source inventory; current core and API field audit retain source facts with repaired semantics. Not merged into duplicate counts."
            elif path.name in {"extract.py","analyze_style.py","technique_report.py","bend_analysis.py","bend_catalog.py","gp_io.py","edit_gp.py","technique_edits.py","contextual_bends.py","bend_timing.py","bend_levers.py","technique_strength.py","technique_effects.py"}:status="gp_or_edit_specific";reason="GP-format extraction/edit/report wrapper. Captured source authority stays API; related technique facts use source core. No GP-only fields falsely asserted as API facts."
            elif path.name in {"annotation_context_gap.py","joint_register_harmony_audit.py","joint_role_evaluation.py","joint_roles.py","barline_continuity.py","conditional_harmony_steps.py","conditional_harmony_pilot.py","performance_sampling_audit.py","style_diagnostics.py","validate_artist_annotations.py","relationship_profile_evaluation.py"}:status="requires_comparison_model_or_role_inputs";reason="Comparative/generated/model-role analysis requires additional experiment/model inputs. Not raw single-song extraction; no invented roles, fits or held-out outcomes."
            elif path.name in {"pedal_regions.py"}:status="superseded_detector";reason="Older detector is not substituted for approved evidence+expansion logic."
            elif path.name in {"research_corpus.py"}:status="requires_external_corpus";reason="MTC corpus preparation, not Invent Animate capture analysis."
            elif path.name in {"exact_score.py","gp_author.py","musicxml_bridge.py"}:status="format_adapter";reason="GP reader/writer or MusicXML bridge; not invoked to redefine captured JSON authority."
            elif path.name in {"download_csv.py","download_configurable.py","catalog_csv_corpus.py","validate_conversion.py","validate_corpus.py","validate_source.py"}:status="capture_conversion_or_external_validation";reason="Acquisition/export/reimport workflow; existing captures used without network downloads or invented GP fidelity."
            elif path.name in {"analyze_pedal_dialogue.py"}:status="measurement_wrapper";reason="Underlying analyze_dialogue is included on approved regions; older region selection/corpus summary not used as new identification truth."
            else:status="experiment_or_review_orchestration";reason="Existing method entrypoint/experiment or review infrastructure, not an additional raw-song musical analyzer. Exact module description/functions retained for audit."
            import ast
            module=ast.parse(path.read_text(encoding="utf-8-sig"))
            entries.append(dict(module=path.relative_to(ROOT).as_posix(),status=status,reason=reason,description=ast.get_docstring(module),functions=[n.name for n in module.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))],sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return entries


def materialize(package,ident,*,nodes=None,docs=None):
    states=layers(package)
    if nodes is None:nodes={r["id"]:r for s in states.values() for r in s["records"]}
    if docs is None:docs={d["id"]:d["payload"] for d in states[0]["documents"]}
    def resolve_node(record_id):
        value=resolve(nodes[record_id]["values"])
        overlay=package.get("legacy_output_projections",{}).get(record_id,{})
        return dict(value,**{k:resolve(x) for k,x in overlay.items()}) if overlay else value
    def resolve(v):
        if isinstance(v,dict) and {"$count_cell","$count_witness"}<=set(v):
            cell=nodes[v["$count_cell"]];witness=resolve(nodes[v["$count_witness"]]["values"])
            context=resolve_node(v["$count_context"]) if "$count_context" in v else {}
            return dict(song_id=witness["song_id"],kind=cell["count_context"]["kind"],condition=cell["count_context"]["condition"],outcome=resolve(cell["values"])["outcome"],section=witness["section"],support=witness["support"],**context)
        if isinstance(v,dict) and set(v)=={"$record"}:return resolve_node(v["$record"])
        if isinstance(v,dict) and set(v)=={"$source"}:
            ref=v["$source"];result=pointer(docs[ref["document"]],ref["pointer"])
            return {k:x for k,x in result.items() if k not in ref["exclude_keys"]} if ref.get("exclude_keys") else result
        if isinstance(v,dict):return {k:resolve(x) for k,x in v.items()}
        if isinstance(v,list):return [resolve(x) for x in v]
        return v
    return resolve_node(ident)


def build(folder):
    documents=source_capture(folder)
    sealed={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*ROOT.glob("*.py"),*API.glob("*.py")]}
    report=analyze_capture(documents);song=report["songs"][0]
    outputs=json.loads(json.dumps(existing_outputs(report, documents),ensure_ascii=False,allow_nan=False))
    report=outputs["core"];song=report["songs"][0]
    mapper=Mapper(documents,song)
    for key,value in song.items():
        if key=="tracks":continue
        tier=next((t for t,keys in SONG_TIERS.items() if key in keys),None)
        if tier is None:raise ValueError("Unmapped song field "+key)
        mapper.add(value,"core","/songs/0/"+key,tier)
    for i,track in enumerate(song["tracks"]):
        for key,value in track.items():
            tier=next((t for t,keys in TRACK_TIERS.items() if key in keys),None)
            if tier is None:raise ValueError("Unmapped track field "+key)
            mapper.add(value,"core",f"/songs/0/tracks/{i}/"+key,tier,track["part_id"])
    for key,value in report.items():
        if key!="songs":mapper.add(value,"core","/"+key,5 if key in ("artists","cohorts") else 4)
    allocation={"pedal_seeds":3,"approved_pedals":3,"dialogue":3,"pattern_robustness":3,"profile_observations":5,"relationship_profile":5,"profile_support":5,"individual_notes":5,"profile_summary":5,"api_coverage":4,"private_api_coverage":4,"verification":4,"evidence_examples":2,"remaining_gaps":2}
    for key,tier in allocation.items():
        if key!="profile_support":mapper.add(outputs[key],key,"",tier)
    extended_tiers={"source_attack_streams":2,"source_fingerprint_windows":3,"palm_opportunities":2,"relational_graph":2,"sounding_graph":2,"sounding_audit":4,"harmony_hypotheses":2,"pattern_hypotheses":3,"harmony_boundaries":4,"structure_hypotheses":4,"performance_opportunities":2,"projection":1}
    extended_tiers["analysis_inputs"]=1
    mapper.aliases=outputs["extended"]["projection"]["aliases"]
    mapper.graph_edges=outputs["extended"]["relational_graph"]["edges"]
    mapper.sounding=outputs["extended"]["sounding_graph"]
    for key,value in outputs["extended"].items():
        mapper.add(value,"extended/"+key,"",extended_tiers[key])
    for name,input_name in {"relational_graph":"exact_score","sounding_graph":"exact_score","harmony_hypotheses":"rounded_score","pattern_hypotheses":"rounded_score","harmony_boundaries":"ensemble_score","structure_hypotheses":"ensemble_score"}.items():
        mapper.links.append(dict(type="declared_full_method_input_not_unit_membership",from_id=f"r:extended/{name}:",to_id=f"r:extended/analysis_inputs:/{input_name}"))
    sounding=outputs["extended"]["sounding_graph"]
    for lane_i,lane in enumerate(sounding["lanes"]):
        lane_id=f"r:extended/sounding_graph:/lanes/{lane_i}"
        for sustain_id in lane["members"]:
            mapper.links.append(dict(type="inferred_lane_member",from_id=lane_id,to_id="r:extended/sounding_graph:/sustains/"+escape(sustain_id)))
    for row in outputs["extended"]["palm_opportunities"]["evidence"]:
        mapper.links.append(dict(type="eligible_palm_group_evidence",from_id=f"r:extended/palm_opportunities:/events/{row['event_index']}",to_id=f"r:extended/palm_opportunities:/evidence/{row['event_index']}"))
    for index,stream in enumerate(outputs["extended"]["source_fingerprint_windows"]):
        mapper.links.append(dict(type="fingerprinted_stream",from_id=f"r:extended/source_fingerprint_windows:/{index}",to_id=f"r:extended/source_attack_streams:/streams/{stream['stream_index']}"))
    # Map each pre-existing graph edge to its graph endpoints as well as source aliases.
    for i,edge in enumerate(outputs["extended"]["relational_graph"]["edges"]):
        rid=f"r:extended/relational_graph:/edges/{i}"
        for endpoint in ("source","target"):
            target="r:extended/relational_graph:/nodes/"+escape(edge[endpoint])
            if target not in mapper.nodes:raise AssertionError("Unmapped legacy graph endpoint")
            mapper.links.append(dict(type="graph_"+endpoint,from_id=rid,to_id=target))
    # Counts refer to shared observation witnesses, not 153k repeated copies of
    # the same groups. The ordered stream remains exactly materializable.
    cell_ids={}
    for i,table in enumerate(outputs["relationship_profile"]["tables"]):
        for j,outcome in enumerate(table["outcomes"]):
            cid=f"r:relationship_profile:/tables/{i}/outcomes/{j}"
            mapper.nodes[cid]["count_context"]=dict(kind=table["kind"],condition=table["condition"])
            cell_ids[digest([table["kind"],table["condition"],outcome["outcome"]])]=cid
    witnesses={};contexts={};context_inputs={};stream=[];cell_counts=Counter()
    for unit in outputs["profile_support"]:
        witness={k:unit[k] for k in ("song_id","section","support")}
        signature=digest(witness)
        if signature not in witnesses:
            wid=mapper.emit(witness,"count_witnesses","/"+signature,2,part=(unit["support"] or {}).get("part_id"))
            mapper.nodes[wid]["kind"]="counted_observation_witness"
            witnesses[signature]=wid
        wid=witnesses[signature]
        cid=cell_ids[digest([unit["kind"],unit["condition"],unit["outcome"]])]
        contribution={"$count_cell":cid,"$count_witness":wid}
        context={}
        for field in ("calculation_inputs","absence_checks"):
            if field not in unit:continue
            refs=[]
            for descriptor in unit[field]:
                key=digest(descriptor)
                if key not in context_inputs:
                    descriptor_tier=5 if descriptor.get("source_scope")=="core_song_selection" else 3
                    record=mapper.emit(descriptor,"count_calculation_inputs","/"+key,descriptor_tier,part=descriptor.get("part_id"))
                    mapper.nodes[record]["kind"]="conditional_absence_check" if field=="absence_checks" else "conditional_calculation_input"
                    context_inputs[key]=record
                refs.append({"$record":context_inputs[key]})
            context[field]=refs
        if context:
            key=digest(context)
            if key not in contexts:
                record="count-context:"+key
                context_tier=max((mapper.nodes[r["$record"]]["tier"] for refs in context.values() for r in refs),default=3)
                mapper.nodes[record]=dict(id=record,tier=context_tier,kind="conditional_calculation_context",scope=dict(song_id=song["song_id"]),values=context,time=None,origin=dict(document="normalized_count_contexts",pointer="/"+key),status="recorded_existing_calculation_inputs_not_counted_units")
                mapper.tiers[context_tier]["records"].append(mapper.nodes[record])
                for refs in context.values():
                    for ref in refs:mapper.links.append(dict(type="calculation_input",from_id=record,to_id=ref["$record"]))
                contexts[key]=record
            contribution["$count_context"]=contexts[key]
            mapper.links.append(dict(type="conditional_calculation_context",from_id=cid,to_id=contexts[key]))
        stream.append(contribution)
        mapper.links.append(dict(type="derived_from_complete_units",from_id=cid,to_id=wid))
        cell_counts[cid]+=1
    connect_count_contexts(mapper,outputs,context_inputs.values())
    connect_selection_provenance(mapper)
    sid="r:profile_support:"
    stream_node=dict(id=sid,tier=5,kind="ordered_count_contributions",scope=dict(song_id=song["song_id"]),values=stream,time=None,origin=dict(document="profile_support",pointer=""),status="lossless_normalized_existing_support_log")
    mapper.nodes[sid]=stream_node;mapper.tiers[5]["records"].append(stream_node);mapper.roots["profile_support#"]=sid
    for i,table in enumerate(outputs["relationship_profile"]["tables"]):
        for j,outcome in enumerate(table["outcomes"]):
            if cell_counts[f"r:relationship_profile:/tables/{i}/outcomes/{j}"]!=outcome["count"]:raise AssertionError("Incomplete normalized support")
    connect_patterns(mapper,outputs)
    connect_summaries(mapper,outputs)
    add_beat_inventory(mapper)
    add_playback_inventory(mapper)
    package=mapper.finish()
    package["implementation_registry"]=implementation_registry()
    package["document_producers"]={
        "core":dict(module="songsterr_automation/songsterr_api/analyze_relationships.py",function="analyze",input_scope="all captured metadata/track JSON"),
        "relationship_profile":dict(module="artist_relationship_profiles.py",function="build_relationship_profile",input_scope="core + accepted_pedals; computed single-capture provisional partition and captured flags; not a corpus holdout split"),
        "profile_summary":dict(module="relationship_profile_summary.py",function="summarize",input_scope="relationship_profile"),
        "individual_notes":dict(module="artist_note_summaries.py",function="summarize_notes",input_scope="core; eligible guitar/bass regular-note population"),
        "count_witnesses":dict(module="artist_relationship_profiles.py",function="Counts.add optional support_sink",input_scope="complete counted unit support; canonical witness normalization is lossless"),
        "extended":dict(module="api_analysis_views.py",function="run",input_scope="explicit source-derived exact graph / rounded legacy views; projection aliases retained")}
    package["provenance"]=dict(capture_payloads=[dict(id=d["id"],sha256=d["payload_sha256"]) for d in documents],producer="build_tiered_song.py",analysis_scope="single-song existing logic; not cross-song evidence",support_log="Complete Counts.add units; no statistical output changes")
    package["source_id"]=package["package_id"]
    package["analysis_revision"]=digest(dict(outputs_sha256=digest(outputs),implementation_registry_sha256=digest(package["implementation_registry"]),source_inputs=[dict(byte_sha256=d["byte_sha256"],payload_sha256=d["payload_sha256"]) for d in documents],schema=package["schema"]))
    package["package_id"]=package["source_id"]+":analysis:"+package["analysis_revision"]
    package["id_contract"]="Record IDs are local to this immutable analysis snapshot. Source identity is source_id; cross-snapshot references require package_id plus record_id."
    package["adapter_corrections"]=[dict(field="evidence_examples.examples[].source_gp",action="explicitly_unavailable",reason="Legacy helper constructs a temporary filename without a supplied GP; no phantom resource retained")]
    nodes={r["id"]:r for state in layers(package).values() for r in state["records"]}
    source_docs={d["id"]:d["payload"] for d in documents}
    for key,ident in package["output_roots"].items():
        doc,path=key.split("#",1)
        if materialize(package,ident,nodes=nodes,docs=source_docs)!=pointer(outputs["extended"][doc.split("/",1)[1]] if doc.startswith("extended/") else outputs[doc],path):raise AssertionError("Output changed: "+key)
    for path,checksum in sealed.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=checksum:raise AssertionError("Implementation changed during run")
    for doc in documents:
        if read(folder/doc["filename"])!=doc["payload"] or hashlib.sha256((folder/doc["filename"]).read_bytes()).hexdigest()!=doc["byte_sha256"]:raise AssertionError("Source changed during run")
    return package,outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path);parser.add_argument("output",type=Path)
    args=parser.parse_args()
    if "local-artifacts" not in args.output.resolve().parts or args.output.exists():parser.error("Fresh private output path required")
    package,outputs=build(args.capture)
    args.output.mkdir(parents=True)
    (args.output/"song.tiered.json").write_text(json.dumps(package,ensure_ascii=False,separators=(",",":"),allow_nan=False),encoding="utf-8")
    (args.output/"existing-outputs.json").write_text(json.dumps(outputs,ensure_ascii=False,separators=(",",":"),allow_nan=False),encoding="utf-8")
    print(json.dumps(dict(song=package["scope"],tiers={t:s["coverage"] for t,s in layers(package).items()})))

if __name__=="__main__":main()
