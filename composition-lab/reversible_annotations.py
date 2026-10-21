"""Sparse source observations and exact registered point-curve relations.

No technique execution, acoustic interpretation, placement or smoothing.
"""
from fractions import Fraction as F
from collections import Counter
from reversible_relationships import ConstraintError,solve,factor_numeric,realize_numeric
import reversible_positions as positions

CURVE_FIELDS={"note":{"bend"},"beat":{"tremoloBar"},"rest_slot":set()}
SOURCE_UNITS={"tone":"50","position":"60","precisePosition":"100"}
EXCLUDED={"note":{"fret","string","dead","rest"},"beat":{"notes","duration","type","rest","graceNote"},"rest_slot":{"rest"}}


def scalar(value):
    kind=type(value).__name__
    if kind not in {"int","float","bool","str","NoneType"}:raise ConstraintError("Nested source payload is not a scalar observation")
    return dict(type=kind,value=str(F(str(value))) if kind in {"int","float"} else value)


def validate_scalar(state):
    if not isinstance(state,dict) or set(state)!={"type","value"}:raise ConstraintError("Invalid scalar observation")
    kind=state["type"];value=state["value"]
    if kind in {"int","float"}:
        if not isinstance(value,str):raise ConstraintError("Rational scalar required")
        if kind=="int" and F(value).denominator!=1:raise ConstraintError("Nonintegral source integer")
        F(value)
    elif kind=="NoneType":
        if value is not None:raise ConstraintError("Invalid null scalar")
    elif kind not in {"bool","str"} or type(value).__name__!=kind:raise ConstraintError("Invalid categorical scalar")


def unit_equation(field,units):
    # SAME relation converts source units forward and backward.
    return [{"source":F(1),"normalized":-F(units.get(field,"1"))}]


def pack(records,units,groups=None):
    fields=sorted({k for r in records for k,v in r["fields"].items() if v["type"] in {"int","float"}})
    channels={k:dict(translated=False,scale="identity") for k in fields};regions=[]
    for record in records:
        if set(record)!={"id","fields"}:raise ConstraintError("Unexpected annotation record")
        values={k:None for k in fields};symbols={}
        for key,state in record["fields"].items():
            validate_scalar(state)
            if state["type"] in {"int","float"}:
                values[key]=str(solve(unit_equation(key,units),{"source":state["value"]},["normalized"])["normalized"])
                symbols[key]=dict(type=state["type"])
            else:symbols[key]=state
        regions.append(dict(id=record["id"],unit="1",rows=[dict(id=record["id"],values=values,symbols=symbols)]))
    if groups is not None:
        rows={r["rows"][0]["id"]:r["rows"][0] for r in regions}
        requested=[ident for ids in groups.values() for ident in ids]
        if len(requested)!=len(set(requested)) or set(requested)!=set(rows):raise ConstraintError("Invalid point grouping")
        regions=[dict(id=ident,unit="1",rows=[rows[x] for x in members]) for ident,members in groups.items() if members]
    return factor_numeric(regions,channels)


def unpack(model,units):
    if any(v!={"translated":False,"scale":"identity"} for v in model["channels"].values()):raise ConstraintError("Invalid observation channel declaration")
    records=[]
    for row in realize_numeric(model):
        if not isinstance(row["symbols"],dict):raise ConstraintError("Invalid observation fields")
        fields={};numeric=set()
        for key,desc in row["symbols"].items():
            if not isinstance(key,str) or not isinstance(desc,dict):raise ConstraintError("Invalid scalar field descriptor")
            if desc.get("type") in {"int","float"}:
                if set(desc)!={"type"} or key not in row["values"] or row["values"][key] is None:raise ConstraintError("Numeric observation missing or duplicated")
                state=dict(type=desc["type"],value=str(solve(unit_equation(key,units),{"normalized":row["values"][key]},["source"])["source"]))
                numeric.add(key)
            else:state=desc
            validate_scalar(state);fields[key]=state
        if numeric!={k for k,v in row["values"].items() if v is not None}:raise ConstraintError("Unexpected numeric observation payload")
        records.append(dict(id=row["id"],fields=fields))
    return records


def extract(capture):
    from run_reversible_tier_qa import read
    physical=positions.extract(capture);meta=read(capture/"metadata.json");markers=[];curves=[];unsupported=[]
    def visit(owner,kind,obj):
        fields={}
        for key,value in obj.items():
            if key in EXCLUDED[kind]:continue
            if key in CURVE_FIELDS[kind] and isinstance(value,dict):
                points=value.get("points")
                if isinstance(points,list) and all(isinstance(p,dict) and all(type(v) in (int,float,bool,str,type(None)) for v in p.values()) for p in points) and all(type(v) in (int,float,bool,str,type(None)) for k,v in value.items() if k!="points"):
                    ident=f"curve:{owner}:{key}"
                    curves.append(dict(id=ident,owner=owner,kind=kind,field=key,header={k:scalar(v) for k,v in value.items() if k!="points"},points_present="points" in value,points=[dict(id=f"{ident}:point:{i}",fields={k:scalar(v) for k,v in p.items()}) for i,p in enumerate(points)]));continue
            if type(value) in (int,float,bool,str,type(None)):fields[key]=scalar(value)
            else:unsupported.append(dict(owner=owner,kind=kind,field=key,source_type=type(value).__name__))
        if fields:markers.append(dict(id=owner,fields=fields))
    for path in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1])):
        part=read(path)
        for mi,m in enumerate(part.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                for bi,b in enumerate(v.get("beats",[])):
                    bid=f"beat:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}";visit(bid,"beat",b)
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):
                            visit(f"rest-slot:{bid}:{ni}","rest_slot",n);continue
                        visit(f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}","note",n)
    return dict(schema="annotated-position-topology/1",physical=physical,markers=sorted(markers,key=lambda r:r["id"]),curves=curves,unsupported=unsupported)


def owners(physical):
    structural=physical["topology"]
    return {**{r["id"]:"note" for r in structural["notes"]},**{r["id"]:"beat" for r in structural["beats"]},**{f"rest-slot:{b['id']}:{i}":"rest_slot" for b in structural["beats"] for i,slot in enumerate(b["symbols"]["slots"]) if slot=="rest_placeholder"}}


def validate_witnesses(markers,curves,unsupported,owner_kinds):
    used=set();seen=set()
    for marker in markers:
        if marker["id"] not in owner_kinds or marker["id"] in seen or not marker["fields"]:raise ConstraintError("Invalid sparse marker ownership")
        seen.add(marker["id"])
        for field,state in marker["fields"].items():
            if field in EXCLUDED[owner_kinds[marker["id"]]]:raise ConstraintError("Duplicated lower-owned source field")
            validate_scalar(state);used.add((marker["id"],field))
    for curve in curves:
        if set(curve)!={"id","owner","kind","field","header","points_present","points"}:raise ConstraintError("Invalid curve fields")
        if curve["owner"] not in owner_kinds or curve["kind"]!=owner_kinds[curve["owner"]] or curve["field"] not in CURVE_FIELDS[curve["kind"]]:raise ConstraintError("Unregistered curve ownership/units")
        if curve["id"]!=f"curve:{curve['owner']}:{curve['field']}" or (curve["owner"],curve["field"]) in used:raise ConstraintError("Duplicate curve identity")
        used.add((curve["owner"],curve["field"]))
        if type(curve["points_present"]) is not bool or not curve["points_present"]:raise ConstraintError("Missing source point list")
        if "points" in curve["header"]:raise ConstraintError("Nested points header")
        for state in curve["header"].values():validate_scalar(state)
        for i,p in enumerate(curve["points"]):
            if set(p)!={"id","fields"} or p["id"]!=f"{curve['id']}:point:{i}":raise ConstraintError("Invalid point order/identity")
            for state in p["fields"].values():validate_scalar(state)
    for item in unsupported:
        if set(item)!={"owner","kind","field","source_type"} or item["owner"] not in owner_kinds or owner_kinds[item["owner"]]!=item["kind"] or not isinstance(item["field"],str) or item["source_type"] not in {"dict","list"}:raise ConstraintError("Invalid unsupported-field inventory")
        if item["field"] in EXCLUDED[item["kind"]] or (item["owner"],item["field"]) in used:raise ConstraintError("Duplicate unsupported field")
        used.add((item["owner"],item["field"]))


def encode(facts):
    if set(facts)!={"schema","physical","markers","curves","unsupported"} or facts["schema"]!="annotated-position-topology/1":raise ConstraintError("Unexpected annotated facts")
    validate_witnesses(facts["markers"],facts["curves"],facts["unsupported"],owners(facts["physical"]))
    headers=[dict(id=c["id"],fields=c["header"]) for c in facts["curves"]]
    points=[p for c in facts["curves"] for p in c["points"]]
    return dict(schema="relative-annotated-topology/1",physical=positions.encode(facts["physical"]),markers=pack(facts["markers"],{}),curve_headers=pack(headers,SOURCE_UNITS),curve_points=pack(points,SOURCE_UNITS,{c["id"]:[p["id"] for p in c["points"]] for c in facts["curves"]}),curve_memberships=[dict(id=c["id"],owner=c["owner"],kind=c["kind"],field=c["field"],points_present=c["points_present"],points=[p["id"] for p in c["points"]]) for c in facts["curves"]],unsupported=facts["unsupported"])


def decode(model,inferred_positions=None):
    if set(model)!={"schema","physical","markers","curve_headers","curve_points","curve_memberships","unsupported"} or model["schema"]!="relative-annotated-topology/1":raise ConstraintError("Unexpected annotated upper fields")
    physical=positions.decode(model["physical"],inferred_positions);markers=unpack(model["markers"],{});headers={r["id"]:r["fields"] for r in unpack(model["curve_headers"],SOURCE_UNITS)};points={r["id"]:r for r in unpack(model["curve_points"],SOURCE_UNITS)}
    expected_groups={c["id"]:c["points"] for c in model["curve_memberships"] if c["points"]}
    actual_groups={o["region_id"]:o["members"] for o in model["curve_points"]["occurrences"]}
    if expected_groups!=actual_groups:raise ConstraintError("Curve pattern membership differs")
    curves=[];seen=[]
    for c in model["curve_memberships"]:
        if set(c)!={"id","owner","kind","field","points_present","points"} or c["id"] not in headers:raise ConstraintError("Invalid curve membership")
        if any(p not in points for p in c["points"]):raise ConstraintError("Missing curve point")
        curves.append(dict(c,header=headers[c["id"]],points=[points[p] for p in c["points"]]));seen.extend(c["points"])
    if len(seen)!=len(set(seen)) or set(seen)!=set(points) or len(curves)!=len(headers):raise ConstraintError("Curve point/header ownership mismatch")
    validate_witnesses(markers,curves,model["unsupported"],owners(physical))
    return dict(schema="annotated-position-topology/1",physical=physical,markers=markers,curves=curves,unsupported=model["unsupported"])
