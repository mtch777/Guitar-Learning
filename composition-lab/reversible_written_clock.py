"""Written clock lift: replace voice origins with shared meter relationships.

No performed-repeat expansion, seconds, default meter, source repair or note cache.
The lower envelope retains duration parameters; only redundant onset anchors leave.
"""
from copy import deepcopy
from fractions import Fraction as F
import reversible_song as song
import reversible_temporal as temporal
import reversible_control as control
from reversible_numeric_view import project
from reversible_relationships import ConstraintError,realize_numeric,solve


def advance():return [{"next":F(1),"start":F(-1),"span":F(-1)}]
def origin():return [{"anchor":F(1),"frame":F(-1)}]


def topology(envelope):
    if envelope.get("schema")!="owned-song-stages/2" or envelope.get("stage")!="control":raise ConstraintError("Written clock requires complete owned control stage")
    return envelope["music"]["lower"]["lower"]["physical"]["topology"]


def context(envelope):
    """Pure derived dependencies; intentionally works before origins are restored."""
    top=topology(envelope);registry=envelope["registry"]
    measures={m["id"]:m for m in top["measures"]};voices={v["id"]:v for v in top["voices"]}
    patterns=top["beat_patterns"]
    durations={r["id"]:r for r in realize_numeric(project(patterns,["duration_q","written_duration_q"]))}
    facts=temporal.decode(envelope["temporal"])
    normalized=temporal.transform(facts["records"])
    declarations={r["owner"]:r for r in normalized if r["kind"]=="meter"}
    unsupported={r["owner"] for r in facts["unsupported"] if r["field"]=="signature"}
    controls=control.decode(envelope["control"])
    if [(p["id"],p["measure_refs"]) for p in controls["parts"]]!=[(p["id"],p["measure_refs"]) for p in registry]:raise ConstraintError("Clock control ownership differs")
    for part in controls["parts"]:
        flag=part["anacrusis"]
        if flag["kind"]=="unsupported" or flag["kind"]=="scalar" and flag["value"]["type"] not in {"bool","NoneType"}:raise ConstraintError("Unverified pickup flag interpretation")
    pickup=any(p["anacrusis"]==dict(kind="scalar",value=dict(type="bool",value=True)) for p in controls["parts"])
    total=max((len(p["measure_refs"]) for p in registry),default=0)
    frames=[];voice_frames={};current=None;start=F(0)
    for index in range(total):
        refs=[p["measure_refs"][index] for p in registry if index<len(p["measure_refs"])]
        if set(refs)&unsupported:raise ConstraintError("Unsupported meter declaration at written frame")
        evidence=[declarations[mid] for mid in refs if mid in declarations]
        signatures=set()
        for record in evidence:
            fields=record["fields"]
            if "nominal_span_q" not in fields:raise ConstraintError("Unusable meter declaration")
            span=F(fields["nominal_span_q"]["value"]);denominator=F(fields["denominator"]["value"])
            signatures.add((span,denominator))
        if len(signatures)>1:raise ConstraintError("Conflicting written meter declarations")
        if signatures:current=next(iter(signatures))
        if current is None:raise ConstraintError("No explicit initial meter; no guessed default")
        nominal=current[0];span=nominal;occupancies=[];contributors=[]
        for mid in refs:
            if mid not in measures:raise ConstraintError("Missing written measure owner")
            for vid in measures[mid]["voices"]:
                if vid in voice_frames or vid not in voices:raise ConstraintError("Clock voice ownership mismatch")
                voice_frames[vid]=index
                # Whole-measure-rest metric duration depends on the frame itself.
                # It cannot independently justify a shortened pickup.
                rows=[durations[bid] for bid in voices[vid]["beats"]]
                if any(r["symbols"]["whole_measure_rest"] for r in rows):continue
                occupied=sum((F(r["values"]["written_duration_q"]) for r in rows if not r["symbols"]["grace_kind"]),F(0))
                occupancies.append(occupied);contributors.append(vid)
        occupied=max(occupancies,default=F(0))
        status="nominal"
        if index==0 and pickup:
            if 0<occupied<nominal:span=occupied;status="observed_short_pickup"
            elif occupied==0:status="pickup_flag_without_independent_occupancy"
            else:status="pickup_flag_without_short_occupancy"
        frames.append(dict(index=index,start_q=str(start),span_q=str(span),nominal_span_q=str(nominal),meter_evidence=[r["id"] for r in evidence],status=status,pickup_contributors=contributors if index==0 and pickup else []))
        start=solve(advance(),dict(start=start,span=span),["next"])["next"]
    if set(voice_frames)!=set(voices):raise ConstraintError("Incomplete clock voice ownership")
    occurrences=patterns["occurrences"]
    nonempty={vid for vid,v in voices.items() if v["beats"]}
    if {o["region_id"] for o in occurrences}!=nonempty or len(occurrences)!=len(nonempty):raise ConstraintError("Clock numeric voice membership mismatch")
    return frames,voice_frames


def encode(envelope):
    song.validate(envelope);frames,owners=context(envelope);lower=deepcopy(envelope)
    for occurrence in topology(lower)["beat_patterns"]["occurrences"]:
        anchor=occurrence["anchors"].get("onset_q")
        if anchor is None:raise ConstraintError("Missing forward onset anchor")
        frame=frames[owners[occurrence["region_id"]]]["start_q"]
        solve(origin(),dict(anchor=anchor,frame=frame),[])
        del occurrence["anchors"]["onset_q"]
    return dict(schema="shared-written-clock/1",lower=lower)


def decode(model):
    if not isinstance(model,dict) or set(model)!={"schema","lower"} or model["schema"]!="shared-written-clock/1":raise ConstraintError("Invalid written clock representation")
    lower=deepcopy(model["lower"]);frames,owners=context(lower)
    for occurrence in topology(lower)["beat_patterns"]["occurrences"]:
        if "onset_q" in occurrence["anchors"]:raise ConstraintError("Duplicated written onset origin")
        frame=frames[owners[occurrence["region_id"]]]["start_q"]
        occurrence["anchors"]["onset_q"]=str(solve(origin(),dict(frame=frame),["anchor"])["anchor"])
    # A successful duration projection does NOT validate the full parent.
    song.validate(lower)
    song.decode(lower)
    return lower


def timing_view(model):
    """Derived links, never an authoritative duplicate clock or playback timeline."""
    restored=decode(model);frames,_=context(restored)
    rows={r["id"]:r for r in realize_numeric(topology(restored)["beat_patterns"])}
    parts={p["id"]:p for p in restored["registry"]};addresses=[]
    normalized=temporal.transform(temporal.decode(restored["temporal"])["records"])
    for record in normalized:
        if record["kind"]=="meter":continue
        fields=record["fields"];address=dict(id=record["id"],owner=record["owner"],kind=record["kind"])
        if record["kind"]=="beat_tempo":
            row=rows.get(record["owner"])
            if row is None:raise ConstraintError("Beat tempo has no written beat")
            address.update(status="linked",event_q=row["values"]["onset_q"])
        else:
            index=fields.get("measure");position=fields.get("position_q",fields.get("position"))
            if index is None or position is None:address["status"]="missing_source_address"
            elif not temporal.numeric(index) or not temporal.numeric(position):address["status"]="unsupported_source_address"
            else:
                i=F(index["value"]);p=parts.get(record["owner"])
                if p is None:raise ConstraintError("Tempo part owner does not exist")
                if i.denominator!=1 or not 0<=i<len(p["measure_refs"]):address["status"]="source_measure_out_of_range"
                else:
                    # SAME affine addition, normalized position is already quarter units.
                    q=solve(advance(),dict(start=frames[int(i)]["start_q"],span=position["value"]),["next"])["next"]
                    address.update(status="linked",measure_ref=p["measure_refs"][int(i)],event_q=str(q))
        addresses.append(address)
    return dict(frames=frames,tempo_addresses=addresses,performed_visits="NOT_IMPLEMENTED",seconds="NOT_IMPLEMENTED")
