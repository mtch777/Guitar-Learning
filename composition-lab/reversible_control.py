"""Isolated source repeat-region relations; no performed-pass or playback policy."""
from copy import deepcopy
from fractions import Fraction as F
import json
from reversible_annotations import scalar,validate_scalar,pack,unpack
from reversible_relationships import ConstraintError,solve,factor_numeric,realize_numeric

FIELDS={"repeatStart","repeat"}
CHANNELS={"measure_span":{"translated":False,"scale":"identity"},"source_repeat_count":{"translated":False,"scale":"identity"}}


def equation():return [{"end":F(1),"start":F(-1),"span":F(-1),"one":F(1)}]


def extract(capture):
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"));parts=[];records=[];endings=[];unsupported=[]
    for path in sorted(capture.glob("track-*.json")):
        part=json.loads(path.read_text(encoding="utf-8-sig"));pid=f"part:{meta['songId']}:{part['partId']}";refs=[]
        pickup=dict(kind="absent")
        if "anacrusis" in part:
            value=part["anacrusis"]
            if type(value) in (int,float,bool,str,type(None)):pickup=dict(kind="scalar",value=scalar(value))
            else:
                pickup=dict(kind="unsupported");unsupported.append(dict(owner=pid,field="anacrusis",source_type=type(value).__name__))
        for i,m in enumerate(part.get("measures",[])):
            owner=f"measure:{meta['songId']}:{part['partId']}:{i+1}";refs.append(owner);fields={}
            for key in FIELDS:
                if key not in m:continue
                value=m[key]
                if type(value) in (int,float,bool,str,type(None)):fields[key]=scalar(value)
                else:unsupported.append(dict(owner=owner,field=key,source_type=type(value).__name__))
            if fields:records.append(dict(id=owner,fields=fields))
            if "alternateEnding" in m:
                value=m["alternateEnding"]
                if isinstance(value,list) and all(type(x) in (int,float,bool,str,type(None)) for x in value):endings.append(dict(owner=owner,kind="array",items=[scalar(x) for x in value]))
                elif type(value) in (int,float,bool,str,type(None)):endings.append(dict(owner=owner,kind="scalar",items=[scalar(value)]))
                else:unsupported.append(dict(owner=owner,field="alternateEnding",source_type=type(value).__name__))
        parts.append(dict(id=pid,measure_refs=refs,anacrusis=pickup))
    return dict(schema="control-source-observations/1",parts=parts,records=sorted(records,key=lambda r:r["id"]),endings=sorted(endings,key=lambda r:r["owner"]),unsupported=sorted(unsupported,key=lambda r:(r["owner"],r["field"])))


def validate(facts):
    if set(facts)!={"schema","parts","records","endings","unsupported"} or facts["schema"]!="control-source-observations/1":raise ConstraintError("Invalid control facts")
    parts=set();measures=set()
    for part in facts["parts"]:
        if set(part)!={"id","measure_refs","anacrusis"} or not isinstance(part["id"],str) or part["id"] in parts:raise ConstraintError("Invalid control part")
        parts.add(part["id"]);refs=part["measure_refs"]
        if not isinstance(refs,list) or any(not isinstance(x,str) for x in refs) or len(set(refs))!=len(refs) or set(refs)&measures:raise ConstraintError("Invalid written measure ownership")
        measures.update(refs);flag=part["anacrusis"]
        if flag.get("kind") in {"absent","unsupported"}:
            if set(flag)!={"kind"}:raise ConstraintError("Invalid pickup witness")
        elif flag.get("kind")=="scalar" and set(flag)=={"kind","value"}:validate_scalar(flag["value"])
        else:raise ConstraintError("Invalid pickup witness")
    owners=set()
    for row in facts["records"]:
        if set(row)!={"id","fields"} or row["id"] not in measures or row["id"] in owners or not row["fields"] or not set(row["fields"])<=FIELDS:raise ConstraintError("Invalid control declaration")
        owners.add(row["id"])
        for state in row["fields"].values():validate_scalar(state)
    ending_owners=set()
    for row in facts["endings"]:
        if set(row)!={"owner","kind","items"} or row["owner"] not in measures or row["owner"] in ending_owners or row["kind"] not in {"array","scalar"} or not isinstance(row["items"],list) or row["kind"]=="scalar" and len(row["items"])!=1:raise ConstraintError("Invalid ending declaration")
        ending_owners.add(row["owner"])
        for state in row["items"]:validate_scalar(state)
    known={(r["id"],key) for r in facts["records"] for key in r["fields"]}|{(r["owner"],"alternateEnding") for r in facts["endings"]}|{(p["id"],"anacrusis") for p in facts["parts"] if p["anacrusis"]["kind"]=="scalar"}
    seen=set()
    for item in facts["unsupported"]:
        if set(item)!={"owner","field","source_type"} or not all(isinstance(x,str) for x in item.values()) or item["field"] not in FIELDS|{"alternateEnding","anacrusis"}:raise ConstraintError("Invalid unsupported control inventory")
        allowed=parts if item["field"]=="anacrusis" else measures
        key=(item["owner"],item["field"])
        if item["owner"] not in allowed or key in seen or key in known or item["source_type"] not in {"dict","list"}:raise ConstraintError("Invalid or contradictory unsupported control owner")
        seen.add(key)
    for part in facts["parts"]:
        if (part["anacrusis"]["kind"]=="unsupported")!=((part["id"],"anacrusis") in seen):raise ConstraintError("Pickup unsupported ownership contradicts its field state")
    if facts["records"]!=sorted(facts["records"],key=lambda r:r["id"]) or facts["endings"]!=sorted(facts["endings"],key=lambda r:r["owner"]):raise ConstraintError("Noncanonical declaration order")


def plan(facts):
    validate(facts);rows={r["id"]:r["fields"] for r in facts["records"]};regions=[];unresolved=[]
    for part in facts["parts"]:
        stack=[]
        for index,owner in enumerate(part["measure_refs"]):
            fields=rows.get(owner,{})
            if "repeatStart" in fields:
                state=fields["repeatStart"]
                if state==scalar(True):stack.append((index,owner))
                elif state!=scalar(False):unresolved.append(dict(owner=owner,field="repeatStart",reason="non_boolean_start"))
            if "repeat" in fields:
                state=fields["repeat"];value=F(state["value"]) if state["type"] in {"int","float"} else None
                if value==0:continue
                if value is None or value<0 or value.denominator!=1:unresolved.append(dict(owner=owner,field="repeat",reason="invalid_repeat_count"));continue
                if not stack:unresolved.append(dict(owner=owner,field="repeat",reason="no_explicit_start"));continue
                start,start_ref=stack.pop();span=solve(equation(),dict(start=start,end=index,one=1),["span"])["span"]
                regions.append(dict(part_ref=part["id"],start_ref=start_ref,end_ref=owner,measure_span=str(span),source_repeat_count=str(value),count_type=state["type"]))
        unresolved.extend(dict(owner=owner,field="repeatStart",reason="unmatched_start") for _,owner in stack)
    unresolved.extend(dict(owner=r["owner"],field=r["field"],reason="unsupported_source_shape") for r in facts["unsupported"] if r["field"] in FIELDS)
    return regions,sorted(unresolved,key=lambda r:(r["owner"],r["field"],r["reason"]))


def encode(facts):
    regions,unresolved=plan(facts);remaining=deepcopy({r["id"]:r["fields"] for r in facts["records"]});rows=[];bindings=[]
    for i,region in enumerate(regions):
        ident=f"region:{i}";bindings.append(dict(id=ident,part_ref=region["part_ref"],start_ref=region["start_ref"],count_type=region["count_type"]))
        rows.append(dict(id=ident,unit="1",rows=[dict(id=ident,values={k:region[k] for k in CHANNELS},symbols={})]))
        del remaining[region["start_ref"]]["repeatStart"];del remaining[region["end_ref"]]["repeat"]
    markers=[dict(id=k,fields=v) for k,v in sorted(remaining.items()) if v]
    ending_records=[dict(id=r["owner"],fields={str(i):state for i,state in enumerate(r["items"])}) for r in facts["endings"]]
    return dict(schema="repeat-region-constraints/1",parts=deepcopy(facts["parts"]),regions=factor_numeric(rows,CHANNELS),bindings=bindings,remaining=pack(markers,{}),ending_values=pack(ending_records,{}),ending_bindings=[dict(owner=r["owner"],kind=r["kind"],count=len(r["items"])) for r in facts["endings"]],unsupported=deepcopy(facts["unsupported"]),unresolved=unresolved)


def decode(model):
    if set(model)!={"schema","parts","regions","bindings","remaining","ending_values","ending_bindings","unsupported","unresolved"} or model["schema"]!="repeat-region-constraints/1":raise ConstraintError("Invalid repeat-region model")
    if model["regions"]["channels"]!=CHANNELS:raise ConstraintError("Invalid repeat-region channels")
    records={r["id"]:r["fields"] for r in unpack(model["remaining"],{})};parts={p["id"]:p for p in model["parts"]};values={r["id"]:r for r in realize_numeric(model["regions"])};seen=set()
    for binding in model["bindings"]:
        if set(binding)!={"id","part_ref","start_ref","count_type"} or binding["id"] in seen or binding["id"] not in values or binding["part_ref"] not in parts or binding["count_type"] not in {"int","float"}:raise ConstraintError("Invalid repeat-region binding")
        seen.add(binding["id"]);row=values[binding["id"]]
        if row["symbols"] or set(row["values"])!=set(CHANNELS) or any(x is None for x in row["values"].values()):raise ConstraintError("Invalid region parameters")
        refs=parts[binding["part_ref"]]["measure_refs"]
        if binding["start_ref"] not in refs:raise ConstraintError("Missing repeat start owner")
        start=refs.index(binding["start_ref"]);span=F(row["values"]["measure_span"]);count=F(row["values"]["source_repeat_count"])
        end=solve(equation(),dict(start=start,span=span,one=1),["end"])["end"]
        if span<1 or span.denominator!=1 or count<=0 or count.denominator!=1 or end.denominator!=1 or not 0<=end<len(refs):raise ConstraintError("Invalid repeat region extent/count")
        end_ref=refs[int(end)]
        for owner,key,state in [(binding["start_ref"],"repeatStart",scalar(True)),(end_ref,"repeat",dict(type=binding["count_type"],value=str(count)))]:
            fields=records.setdefault(owner,{})
            if key in fields:raise ConstraintError("Lifted endpoint duplicated in lower observations")
            fields[key]=state
    if seen!=set(values):raise ConstraintError("Unused region payload")
    ending_rows={r["id"]:r["fields"] for r in unpack(model["ending_values"],{})};endings=[];used=set()
    for binding in model["ending_bindings"]:
        if set(binding)!={"owner","kind","count"} or binding["owner"] in used or binding["owner"] not in ending_rows or type(binding["count"]) is not int or binding["count"]<0:raise ConstraintError("Invalid ending membership")
        used.add(binding["owner"]);fields=ending_rows[binding["owner"]]
        if set(fields)!={str(i) for i in range(binding["count"])}:raise ConstraintError("Invalid ending label ownership")
        endings.append(dict(owner=binding["owner"],kind=binding["kind"],items=[fields[str(i)] for i in range(binding["count"])]))
    if used!=set(ending_rows):raise ConstraintError("Unused ending observations")
    facts=dict(schema="control-source-observations/1",parts=deepcopy(model["parts"]),records=[dict(id=k,fields=v) for k,v in sorted(records.items()) if v],endings=endings,unsupported=deepcopy(model["unsupported"]))
    if encode(facts)!=model:raise ConstraintError("Region set, observations or unresolved reasons are noncanonical")
    return facts


def ending_geometry(model):
    facts=decode(model);regions,_=plan(facts);positions={mid:(p["id"],i) for p in facts["parts"] for i,mid in enumerate(p["measure_refs"])}
    return [dict(owner=e["owner"],containing_regions=[i for i,r in enumerate(regions) if positions[e["owner"]][0]==r["part_ref"] and positions[r["start_ref"]][1]<=positions[e["owner"]][1]<=positions[r["end_ref"]][1]],musical_attachment="unknown") for e in facts["endings"]]
