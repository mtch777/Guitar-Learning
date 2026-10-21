"""Exact written-tie relation lift; no source lookup or acoustic sustain claim."""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from reversible_relationships import ConstraintError,solve,realize_numeric,factor_numeric
import reversible_annotations as annotations
import reversible_topology as topology
from reversible_positions import constants,position_equation

TRUE_TIE={"type":"bool","value":True}
KINDS={"written_pitched_tie","written_dead_tie"}
REASONS={"zero_metric_duration","invalid_string_lane","ambiguous_lane_onset","no_predecessor","noncontiguous","unmapped_position","different_written_position","dead_transition","invalid_written_position"}


def context(physical_upper):
    structural=topology.decode_structure(physical_upper["topology"],{n["id"]:None for n in physical_upper["topology"]["memberships"]})
    rows={r["id"]:r for r in realize_numeric(physical_upper["position_patterns"])}
    settings={s["id"]:s for s in physical_upper["settings"]}
    lanes={}
    for m in structural["measures"]:
        for vi,vid in enumerate(m["voices"]):lanes[vid]=(physical_upper["region_settings"][vid],vi)
    bybeat={bid:lanes[v["id"]] for v in structural["voices"] for bid in v["beats"]}
    beats={b["id"]:b for b in structural["beats"]};result={}
    for note in structural["notes"]:
        ident=note["id"];r=rows[ident];string=r["symbols"]["string"];b=beats[note["beat_ref"]]
        lane=(*bybeat[b["id"]],string["value"]) if string["number_type"]=="int" and string["value"] is not None and F(string["value"])>=0 else None
        nominal=r["values"]["position_pitch"];valid_position=None
        if nominal is not None and r["symbols"]["kind"]=="pitched_position":
            known=dict(**constants(settings[bybeat[b["id"]][0]],string),position_pitch=nominal)
            valid_position=solve(position_equation(),known,["fret"])["fret"]>=0
        result[ident]=dict(valid_position=valid_position,id=ident,lane=lane,onset=F(b["onset_q"]),duration=F(b["duration_q"]),position=r["values"]["position_pitch"],kind=r["symbols"]["kind"],dead=r["symbols"]["dead"]["value"] is True)
    return result


def tie_equations(links,context):
    # SAME declarations validate forward coordinates and infer removed ones.
    eq=[]
    for link in links:
        a,b=link["origin"],link["destination"]
        eq.extend([{f"position:{a}":F(1),f"position:{b}":F(-1)},
                   {f"onset:{a}":F(1),f"duration:{a}":F(1),f"onset:{b}":F(-1)}])
    return eq


def solve_links(links,ctx,required):
    known={f"{field}:{ident}":row[field] for ident,row in ctx.items() for field in ("onset","duration","position") if row[field] is not None}
    return solve(tie_equations(links,ctx),known,[f"position:{ident}" for ident in required])


def analyze(physical_upper,true_ids):
    ctx=context(physical_upper);lanes=defaultdict(lambda:defaultdict(list));links=[];unresolved=[]
    for ident,row in ctx.items():
        if row["duration"]<=0:
            if ident in true_ids:unresolved.append(dict(destination=ident,reason="zero_metric_duration"))
        elif row["lane"] is None:
            if ident in true_ids:unresolved.append(dict(destination=ident,reason="invalid_string_lane"))
        else:lanes[row["lane"]][row["onset"]].append(row)
    for groups in lanes.values():
        previous=None
        for q,group in sorted(groups.items()):
            if len(group)!=1:
                unresolved.extend(dict(destination=r["id"],reason="ambiguous_lane_onset") for r in group if r["id"] in true_ids)
                previous=None;continue
            row=group[0]
            if row["id"] in true_ids:
                reason=("no_predecessor" if previous is None else
                        "noncontiguous" if previous["onset"]+previous["duration"]!=q else
                        "unmapped_position" if previous["kind"]!="pitched_position" or row["kind"]!="pitched_position" or previous["position"] is None or row["position"] is None else
                        "invalid_written_position" if not previous["valid_position"] or not row["valid_position"] else
                        "dead_transition" if previous["dead"]!=row["dead"] else
                        "different_written_position" if previous["position"]!=row["position"] else None)
                if reason:unresolved.append(dict(destination=row["id"],reason=reason))
                else:links.append(dict(origin=previous["id"],destination=row["id"],kind="written_dead_tie" if row["dead"] else "written_pitched_tie"))
            previous=row
    links=sorted(links,key=lambda r:r["destination"]);unresolved=sorted(unresolved,key=lambda r:r["destination"])
    if {x["destination"] for x in links+unresolved}!=set(true_ids):raise ConstraintError("Tie ownership incomplete")
    solve_links(links,ctx,[])
    return links,unresolved


def strip_coordinates(model,removed):
    rows={r["id"]:r for r in realize_numeric(model)}
    for ident in removed:
        if ident not in rows or rows[ident]["values"]["position_pitch"] is None:raise ConstraintError("Missing removable coordinate")
        rows[ident]["values"]["position_pitch"]=None
    regions=[dict(id=o["region_id"],unit=o["unit"],rows=[rows[x] for x in o["members"]]) for o in model["occurrences"]]
    return factor_numeric(regions,model["channels"])


def encode(facts):
    lower=annotations.encode(facts)
    note_ids={n["id"] for n in facts["physical"]["topology"]["notes"]}
    true_ids={m["id"] for m in facts["markers"] if m["id"] in note_ids and m["fields"].get("tie")==TRUE_TIE}
    links,unresolved=analyze(lower["physical"],true_ids)
    clean=deepcopy(facts);markers=[]
    for m in clean["markers"]:
        if m["id"] in true_ids:m["fields"].pop("tie")
        if m["fields"]:markers.append(m)
    clean["markers"]=markers;lower=annotations.encode(clean)
    lower["physical"]["position_patterns"]=strip_coordinates(lower["physical"]["position_patterns"],{r["destination"] for r in links})
    return dict(schema="tie-constrained-song/1",lower=lower,links=links,unresolved=unresolved)


def decode(model):
    if set(model)!={"schema","lower","links","unresolved"} or model["schema"]!="tie-constrained-song/1":raise ConstraintError("Unexpected tie upper fields")
    links=model["links"];unresolved=model["unresolved"];ctx=context(model["lower"]["physical"]);destinations=set()
    for link in links:
        if set(link)!={"origin","destination","kind"} or link["kind"] not in KINDS or link["origin"] not in ctx or link["destination"] not in ctx or link["destination"] in destinations or link["origin"]==link["destination"]:raise ConstraintError("Invalid tie link")
        a,b=ctx[link["origin"]],ctx[link["destination"]]
        if a["lane"] is None or a["lane"]!=b["lane"] or a["duration"]<=0 or b["duration"]<=0 or a["kind"]!="pitched_position" or b["kind"]!="pitched_position" or b["position"] is not None:raise ConstraintError("Invalid tie lane/coordinate ownership")
        destinations.add(link["destination"])
    for item in unresolved:
        if set(item)!={"destination","reason"} or item["reason"] not in REASONS or item["destination"] not in ctx or item["destination"] in destinations:raise ConstraintError("Invalid unresolved tie witness")
        destinations.add(item["destination"])
    solved=solve_links(links,ctx,[r["destination"] for r in links])
    inferred={r["destination"]:str(solved[f"position:{r['destination']}"]) for r in links}
    facts=annotations.decode(model["lower"],inferred);markers={m["id"]:m for m in facts["markers"]}
    for ident in destinations:
        marker=markers.setdefault(ident,dict(id=ident,fields={}))
        if "tie" in marker["fields"]:raise ConstraintError("Duplicate source tie ownership")
        marker["fields"]["tie"]=dict(TRUE_TIE)
    facts["markers"]=[markers[k] for k in sorted(markers)]
    expected_links,expected_unresolved=analyze(annotations.encode(facts)["physical"],destinations)
    if links!=expected_links or unresolved!=expected_unresolved:raise ConstraintError("Tie relations do not match reconstructed observations")
    return facts
