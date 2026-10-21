"""Explicit captured-API projections for existing model-free score analyzers.

No source GP is read; source IDs and exact times remain authoritative. Legacy
phrase/harmony algorithms receive a declared rounded pitch-center projection.
"""
from collections import defaultdict
from fractions import Fraction as F
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/"songsterr_automation/songsterr_api"))
from source_semantics import whole_measure_rest
import harmonic_inference
import relational_graph
import sounding_graph
import phrase_development
import phrase_analysis
import harmony_boundaries
import validate_structure
import analyze_motifs
import content_form
import performance_opportunities
import palm_mute_method
import corpus_copy_audit


def project(song,documents):
    headers=song["shared_layout"]
    sections=[(h["bar"],h.get("section")) for h in headers if h.get("section")]
    # Shared layout carries marker text in a separate field in some revisions.
    if not sections:
        first=song["tracks"][0]
        sections=[(s["id"],s["label"]) for s in first["sections"] if s.get("label")]
    tracks=[];legacy=[];aliases={};limitations=[]
    for ti,track in enumerate(song["tracks"]):
        part=next(d["payload"] for d in documents if d["filename"]==f"track-{track['part_id']}.json")
        lookup={r["occurrence"]:r for r in track["rows"]+track["grace_rows"]}
        tie_origins={a for c in track["sustain_relationships"]["chains"] for a in c.get("members",c.get("segment_occurrences",[]))[:-1]}
        # Current chain representation explicitly names its origin.
        tie_origins.update(c["origin"] for c in track["sustain_relationships"]["chains"] if len(c.get("members",c.get("segment_occurrences",[])))>1)
        measures=[];legacy_bars=[]
        for mi,measure in enumerate(part["measures"]):
            h=headers[mi];base=F(h["start_q"]);span=F(h["span_q"]);voices=[];events=[]
            for vi,voice in enumerate(measure.get("voices",[])):
                cursor=F(0);beats=[]
                for bi,beat in enumerate(voice.get("beats",[])):
                    if not beat.get("duration"):raise ValueError("Legacy projection cannot invent missing rhythm")
                    written=span if whole_measure_rest(measure,voice) else F(*beat["duration"])*4
                    grace=beat.get("graceNote");duration=F(0) if grace else written;notes=[]
                    for ni,note in enumerate(beat.get("notes",[])):
                        if note.get("rest"):continue
                        oid=f"{track['part_id']}:{mi+1}:{vi}:{bi}:{ni}";row=lookup[oid]
                        nid=f"t{ti}:m{mi}:v{vi}:b{bi}:n{len(notes)}"
                        aliases[nid]=oid
                        notes.append(dict(note_id=oid,midi=row["midi"],string=row["string"],fret=row["fret"],
                            tie=dict(origin="true" if oid in tie_origins else "false",destination="true" if row["tie_destination"] else "false"),technique_tags=row["effects"]))
                    bid=f"t{ti}:m{mi}:v{vi}:b{bi}";aliases[bid]=dict(part_id=track["part_id"],bar=mi+1,voice=vi,beat=bi)
                    beats.append(dict(onset_q=str(base+cursor),local_onset_q=str(cursor),duration_q=str(duration),notated_duration_q=str(written),grace_type=str(grace) if grace else None,notes=notes,source_beat=dict(part_id=track["part_id"],bar=mi+1,voice=vi,beat=bi)))
                    pitches=tuple(sorted(n["midi"] for n in notes if n["midi"] is not None))
                    if pitches:events.append((vi,round(float(cursor),5),round(float(duration),5),pitches))
                    cursor+=duration
                voices.append(beats)
            measures.append(dict(onset_q=str(base),time_signature=h["signature"],section=next((label for bar,label in sections if bar==mi+1),None),voices=voices))
            legacy_bars.append(events)
        tracks.append(dict(index=ti,name=track["name"],part_id=track["part_id"],measures=measures))
        legacy.append(dict(name=track["name"],measures=legacy_bars))
    score=dict(source_format="captured_songsterr_projection",song=song["title"],measures=len(headers),sections=sections,tracks=tracks)
    compact=dict(song=song["title"],file=song["title"],measures=len(headers),sections=sections,tracks=legacy)
    return score,compact,aliases


def run(song,documents):
    score,compact,aliases=project(song,documents)
    relational=relational_graph.build_graph(score)
    sounding=sounding_graph.build_sounding(score)
    sounding_audit=sounding_graph.audit_sounding(score,sounding)
    harmony=harmonic_inference.infer_score(compact)
    phrases=[dict(part_id=t["part_id"],analysis=phrase_development.analyze_track(v,compact["sections"],compact["measures"])) for t,v in zip(song["tracks"],compact["tracks"]) if t["guitar_or_bass"]]
    motifs=[];identities=[]
    for t,v in zip(song["tracks"],compact["tracks"]):
        timed=[analyze_motifs.motif_signature(e) for e in v["measures"]];flex=[analyze_motifs.motif_signature(e,True) for e in v["measures"]]
        pairs=[(a,b) if a is not None and b is not None else None for a,b in zip(timed,timed[1:])]
        motifs.append(dict(part_id=t["part_id"],timed_signatures=timed,flexible_signatures=flex,timed_repeats=analyze_motifs.repeat_groups(timed),flexible_repeats=analyze_motifs.repeat_groups(flex),two_bar_repeats=analyze_motifs.repeat_groups(pairs)))
        for section in t["sections"]:
            start,end=F(section["start_q"]),F(section["end_q"])
            scoped=[h for h in song["shared_layout"] if start<=F(h["start_q"])<end]
            identities.append(dict(part_id=t["part_id"],section_start=section["id"],start_q=str(start),end_q=str(end),signature=content_form.timeline_signature(t,scoped,start,end)))
    ensemble=dict(file=song["title"],tracks=[dict(track=t["name"],measures=t["measures"]) for t in compact["tracks"]],meter=[h["signature"] for h in song["shared_layout"]],sections=compact["sections"])
    candidates=dict(phrases=phrases,motifs=motifs,variant_windows=phrase_analysis.scan_score(dict(compact,sections=[dict(measure=n,label=l) for n,l in compact["sections"]])),source_section_content_identity=identities)
    opportunities,exclusions=performance_opportunities.opportunities(dict(songs=[song]))
    palm_evidence=[]
    palm_observations,palm_inventory=palm_mute_method.observations(dict(songs=[song]),True,evidence_sink=palm_evidence.append)
    if (palm_observations,palm_inventory)!=palm_mute_method.observations(dict(songs=[song]),True):raise AssertionError("Palm evidence recording changed output")
    streams,stream_exclusions=corpus_copy_audit.source_streams(dict(songs=[song]))
    fingerprints=[]
    for index,stream in enumerate(streams):
        windows=[]
        for length in (8,16,32):
            for start in range(len(stream["events"])-length+1):
                fingerprint,constant=corpus_copy_audit.fingerprint(stream["events"][start:start+length])
                windows.append(dict(start_event_index=start,length=length,fingerprint=fingerprint,constant_voicing=constant))
        fingerprints.append(dict(stream_index=index,song_id=song["song_id"],part_id=stream["part_id"],voice=stream["voice"],windows=windows))
    return dict(analysis_inputs=dict(exact_score=score,rounded_score=compact,ensemble_score=ensemble),source_attack_streams=dict(streams=streams,exclusions=stream_exclusions),source_fingerprint_windows=fingerprints,palm_opportunities=dict(events=palm_observations,inventory=palm_inventory,evidence=palm_evidence),relational_graph=relational,sounding_graph=sounding,sounding_audit=sounding_audit,harmony_hypotheses=harmony,pattern_hypotheses=candidates,
        harmony_boundaries=harmony_boundaries.analyze_score(ensemble),structure_hypotheses=validate_structure.analyze_score(ensemble),performance_opportunities=dict(observations=opportunities,exclusions=exclusions),
        projection=dict(aliases=aliases,sections=compact["sections"],limitations=["Legacy phrase/harmony views round exact rational times to five decimals and omit rests/unpitched notes; they are derived inputs, never source authority.","Legacy track-name selectors may omit tracks with personal names; all tracks remain in canonical source/events/graphs.","Explicit tie destinations plus existing resolved chains supply tie-origin hints; inferred lanes and phrase/key/chord outputs remain hypotheses.","Legacy tonal/phrase/harmony hypotheses use written base pitch, not bend/slide/whammy/harmonic sounding trajectories.","Sounding/lane graph models explicit written sustain and tie hints, not physical ringout or recorded audio.","No cross-song artist generalization or listening verification."]))
