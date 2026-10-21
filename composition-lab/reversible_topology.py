"""Bounded beat-owned timing and note membership; no musical inference."""
from fractions import Fraction as F
import sys
from pathlib import Path
from reversible_relationships import factor_numeric,realize_numeric,ConstraintError

BEAT_CHANNELS={"onset_q":{"translated":True,"scale":"unit"},"duration_q":{"translated":False,"scale":"unit"},"written_duration_q":{"translated":False,"scale":"unit"}}
PITCH_CHANNELS={"base_pitch":{"translated":True,"scale":"identity"}}
BEAT_SYMBOLS={"rest_flag","grace_kind","notation_type","whole_measure_rest","slots"}


def extract(capture):
    from run_reversible_tier_qa import extract as extract_notes,read
    api=Path(__file__).parent/"songsterr_automation/songsterr_api";sys.path.insert(0,str(api))
    from source_semantics import layout,whole_measure_rest
    facts=extract_notes(capture);meta=read(capture/"metadata.json")
    parts=[read(p) for p in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1]))]
    headers,warnings=layout(parts)
    if warnings:raise ConstraintError("Conflicting source layout: "+str(warnings))
    pitches={e["id"]:e["pitch"] for e in facts["events"]};beats=[];notes=[];voices=[];measures=[]
    for part in parts:
        pid=part["partId"]
        for mi,m in enumerate(part.get("measures",[])):
            mid=f"measure:{meta['songId']}:{pid}:{mi+1}";vids=[]
            for vi,v in enumerate(m.get("voices",[])):
                vid=f"voice:{meta['songId']}:{pid}:{mi+1}:{vi}";vids.append(vid);bids=[];cursor=F(headers[mi]["start_q"])
                sourcebeats=v.get("beats",[])
                for bi,b in enumerate(sourcebeats):
                    bid=f"beat:{meta['songId']}:{pid}:{mi+1}:{vi}:{bi}";bids.append(bid)
                    if not b.get("duration"):raise ConstraintError("Missing source beat duration")
                    written=4*F(*b["duration"])
                    if written<=0:raise ConstraintError("Nonpositive written duration")
                    grace=b.get("graceNote");sentinel=whole_measure_rest(m,v)
                    duration=F(0) if grace else F(headers[mi]["span_q"]) if sentinel else written
                    slots=[]
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):slots.append("rest_placeholder");continue
                        ident=f"event:{meta['songId']}:{pid}:{mi+1}:{vi}:{bi}:{ni}"
                        slots.append("note");notes.append(dict(id=ident,beat_ref=bid,slot=ni,base_pitch=pitches[ident]))
                    target=next((f"beat:{meta['songId']}:{pid}:{mi+1}:{vi}:{j}" for j in range(bi+1,len(sourcebeats)) if not sourcebeats[j].get("graceNote")),None) if grace else None
                    beats.append(dict(id=bid,onset_q=str(cursor),duration_q=str(duration),written_duration_q=str(written),symbols=dict(rest_flag=b.get("rest"),grace_kind=grace,notation_type=b.get("type"),whole_measure_rest=sentinel,slots=slots),next_regular_beat_ref=target))
                    cursor+=duration
                voices.append(dict(id=vid,rest_flag=v.get("rest"),beats=bids))
            measures.append(dict(id=mid,rest_flag=m.get("rest"),voices=vids))
    return dict(schema="beat-owned-topology/1",measures=measures,voices=voices,beats=beats,notes=notes)


def validate(facts):
    if set(facts)!={"schema","measures","voices","beats","notes"} or facts["schema"]!="beat-owned-topology/1":raise ConstraintError("Unexpected topology fields")
    indices={}
    for kind in ("measures","voices","beats","notes"):
        indices[kind]={r["id"]:r for r in facts[kind]}
        if len(indices[kind])!=len(facts[kind]):raise ConstraintError("Duplicate topology identity")
    for m in facts["measures"]:
        if set(m)!={"id","rest_flag","voices"} or type(m["rest_flag"]) not in (bool,type(None)):raise ConstraintError("Unexpected measure fields")
    for v in facts["voices"]:
        if set(v)!={"id","rest_flag","beats"} or type(v["rest_flag"]) not in (bool,type(None)):raise ConstraintError("Unexpected voice fields")
    if sorted(x for m in facts["measures"] for x in m["voices"])!=sorted(indices["voices"]):raise ConstraintError("Voice ownership mismatch")
    if sorted(x for v in facts["voices"] for x in v["beats"])!=sorted(indices["beats"]):raise ConstraintError("Beat ownership mismatch")
    occupied=set();expected_next={}
    for v in facts["voices"]:
        for i,bid in enumerate(v["beats"]):
            b=indices["beats"][bid]
            expected_next[bid]=next((other for other in v["beats"][i+1:] if not indices["beats"][other]["symbols"]["grace_kind"]),None) if b["symbols"]["grace_kind"] else None
    for b in facts["beats"]:
        if set(b)!={"id","onset_q","duration_q","written_duration_q","symbols","next_regular_beat_ref"} or set(b["symbols"])!=BEAT_SYMBOLS:raise ConstraintError("Unexpected beat fields")
        if F(b["duration_q"])<0 or F(b["written_duration_q"])<=0:raise ConstraintError("Invalid beat duration")
        if b["next_regular_beat_ref"]!=expected_next[b["id"]]:raise ConstraintError("Invalid next regular beat reference")
        symbols=b["symbols"]
        if any(type(symbols[k]) not in (str,int,float,bool,type(None)) for k in ("rest_flag","grace_kind","notation_type","whole_measure_rest")):raise ConstraintError("Non-scalar beat symbol")
        if type(symbols["rest_flag"]) not in (bool,type(None)) or type(symbols["notation_type"]) not in (int,type(None)) or type(symbols["grace_kind"]) not in (bool,str,type(None)):raise ConstraintError("Invalid typed beat symbols")
        if type(symbols["whole_measure_rest"]) is not bool or not isinstance(symbols["slots"],list):raise ConstraintError("Invalid beat symbols")
        if any(x not in {"note","rest_placeholder"} for x in b["symbols"]["slots"]):raise ConstraintError("Unknown slot type")
    for n in facts["notes"]:
        if set(n)!={"id","beat_ref","slot","base_pitch"}:raise ConstraintError("Unexpected note fields/duplicated timing")
        b=indices["beats"].get(n["beat_ref"]);key=(n["beat_ref"],n["slot"])
        if not b or type(n["slot"]) is not int or not 0<=n["slot"]<len(b["symbols"]["slots"]) or b["symbols"]["slots"][n["slot"]]!="note" or key in occupied:raise ConstraintError("Invalid note ownership")
        occupied.add(key)
    if occupied!={(b["id"],i) for b in facts["beats"] for i,s in enumerate(b["symbols"]["slots"]) if s=="note"}:raise ConstraintError("Missing note slot")


def encode(facts):
    validate(facts);beats={b["id"]:b for b in facts["beats"]};notes={n["id"]:n for n in facts["notes"]};bybeat={}
    for n in notes.values():bybeat.setdefault(n["beat_ref"],[]).append(n)
    beat_regions=[];pitch_regions=[]
    for v in facts["voices"]:
        rows=[beats[x] for x in v["beats"]]
        if not rows:continue
        positive=[F(b["duration_q"]) for b in rows if F(b["duration_q"])>0];unit=min(positive) if positive else F(1)
        beat_regions.append(dict(id=v["id"],unit=str(unit),rows=[dict(id=b["id"],values={k:b[k] for k in BEAT_CHANNELS},symbols=b["symbols"]) for b in rows]))
        ns=[n for b in rows for n in sorted(bybeat.get(b["id"],[]),key=lambda n:n["slot"])]
        if ns:pitch_regions.append(dict(id=v["id"],unit="1",rows=[dict(id=n["id"],values={"base_pitch":n["base_pitch"]},symbols=None) for n in ns]))
    return dict(schema="relative-beat-topology/1",measures=facts["measures"],voices=facts["voices"],beat_patterns=factor_numeric(beat_regions,BEAT_CHANNELS),pitch_patterns=factor_numeric(pitch_regions,PITCH_CHANNELS),memberships=[{k:n[k] for k in ("id","beat_ref","slot")} for n in facts["notes"]],next_regular_beat_refs={b["id"]:b["next_regular_beat_ref"] for b in facts["beats"] if b["next_regular_beat_ref"] is not None})


def decode(model):
    if set(model)!={"schema","measures","voices","beat_patterns","pitch_patterns","memberships","next_regular_beat_refs"} or model["schema"]!="relative-beat-topology/1":raise ConstraintError("Unexpected higher-tier fields")
    if model["beat_patterns"]["channels"]!=BEAT_CHANNELS or model["pitch_patterns"]["channels"]!=PITCH_CHANNELS:raise ConstraintError("Unexpected channel declarations")
    beats=[dict(id=r["id"],**r["values"],symbols=r["symbols"],next_regular_beat_ref=model["next_regular_beat_refs"].get(r["id"])) for r in realize_numeric(model["beat_patterns"])]
    if set(model["next_regular_beat_refs"])-{b["id"] for b in beats}:raise ConstraintError("Unknown next regular beat reference owner")
    pitches={r["id"]:r for r in realize_numeric(model["pitch_patterns"])}
    if any(r["symbols"] is not None for r in pitches.values()):raise ConstraintError("Unexpected pitch symbols")
    if {n["id"] for n in model["memberships"]}!=set(pitches):raise ConstraintError("Pitch membership mismatch")
    notes=[dict(**n,base_pitch=pitches[n["id"]]["values"]["base_pitch"]) for n in model["memberships"]]
    result=dict(schema="beat-owned-topology/1",measures=model["measures"],voices=model["voices"],beats=beats,notes=notes);validate(result)
    return result


def event_view(facts):
    validate(facts);beats={b["id"]:b for b in facts["beats"]}
    return sorted([dict(id=n["id"],pitch=n["base_pitch"],onset_q=beats[n["beat_ref"]]["onset_q"],duration_q=beats[n["beat_ref"]]["duration_q"]) for n in facts["notes"]],key=lambda r:r["id"])
