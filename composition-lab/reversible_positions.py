"""Source-position slice: reversible equations, explicit categorical witnesses.

position_pitch is an arithmetic written-position coordinate, NOT acoustic pitch.
Songsterr instrument1024 is its explicit percussion pseudo-instrument convention.
Absent/null capo uses the existing parser's declared zero-offset interpretation;
the original presence/null state is retained, never presented as an explicit0.
"""
from fractions import Fraction as F
from collections import Counter
from reversible_relationships import solve,factor_numeric,realize_numeric,ConstraintError
import reversible_topology as topology

CHANNELS={"position_pitch":{"translated":True,"scale":"identity"},"percussion_code":{"translated":False,"scale":"identity"},"unresolved_fret":{"translated":False,"scale":"identity"}}


def numeric_state(obj,key):
    value=obj.get(key)
    if value is not None and type(value) not in (int,float):raise ConstraintError("Non-numeric source position/settings: "+key)
    return dict(present=key in obj,value=str(F(str(value))) if value is not None else None,number_type=type(value).__name__ if value is not None else None)


def boolean_state(obj,key):
    value=obj.get(key)
    if type(value) not in (bool,type(None)):raise ConstraintError("Non-boolean source field: "+key)
    return dict(present=key in obj,value=value)


def validate_state(state,numeric=True):
    keys={"present","value","number_type"} if numeric else {"present","value"}
    if not isinstance(state,dict) or set(state)!=keys or type(state["present"]) is not bool:raise ConstraintError("Invalid typed source field")
    if not state["present"] and state["value"] is not None:raise ConstraintError("Absent field has a value")
    if numeric:
        if state["value"] is None:
            if state["number_type"] is not None:raise ConstraintError("Null numeric field has type")
        elif state["number_type"] not in ("int","float") or not isinstance(state["value"],str):raise ConstraintError("Invalid numeric field type")
        else:
            value=F(state["value"])
            if state["number_type"]=="int" and value.denominator!=1:raise ConstraintError("Nonintegral integer field")
    elif type(state["value"]) not in (bool,type(None)):raise ConstraintError("Invalid boolean field")


def validate_settings(settings):
    seen=set()
    for s in settings:
        if set(s)!={"id","instrument_id","capo","tuning"} or not isinstance(s["id"],str) or s["id"] in seen:raise ConstraintError("Invalid settings ownership")
        seen.add(s["id"]);validate_state(s["instrument_id"]);validate_state(s["capo"])
        tuning=s["tuning"]
        if set(tuning)!={"present","value"} or type(tuning["present"]) is not bool or not tuning["present"] and tuning["value"] is not None:raise ConstraintError("Invalid tuning field")
        if tuning["value"] is not None:
            if not isinstance(tuning["value"],list) or any(not isinstance(x,str) for x in tuning["value"]):raise ConstraintError("Invalid tuning values")
            for value in tuning["value"]:F(value)


def position_equation():
    # SAME declaration solves position_pitch forward and fret backward.
    return [{"position_pitch":F(1),"open_string":F(-1),"capo":F(-1),"fret":F(-1)}]


def mode(settings,string,fret):
    if settings["instrument_id"]["value"]=="1024":return "percussion"
    tuning=settings["tuning"]["value"]
    if string["number_type"]=="int" and string["value"] is not None and tuning is not None:
        index=F(string["value"])
        if 0<=index<len(tuning) and fret["value"] is not None:return "pitched_position"
    return "unmapped_position"


def residual_reason(settings,string,fret):
    if settings["instrument_id"]["value"]=="1024":return None
    if fret["value"] is None:return "missing_or_null_fret"
    if settings["tuning"]["value"] is None:return "missing_or_null_tuning"
    if string["number_type"]!="int" or string["value"] is None:return "missing_null_or_noninteger_string"
    if not 0<=F(string["value"])<len(settings["tuning"]["value"]):return "string_outside_tuning"
    return None


def constants(settings,string):
    return dict(open_string=settings["tuning"]["value"][int(F(string["value"]))],capo=settings["capo"]["value"] or "0")


def extract(capture):
    from run_reversible_tier_qa import read
    structural=topology.extract(capture);positions=[];settings=[];regions={}
    meta=read(capture/"metadata.json")
    for path in sorted(capture.glob("track-*.json"),key=lambda p:int(p.stem.split("-")[-1])):
        part=read(path);sid=f"settings:{meta['songId']}:{part['partId']}"
        tuning=part.get("tuning")
        if tuning is not None and (not isinstance(tuning,list) or any(type(x) not in (int,float) for x in tuning)):raise ConstraintError("Invalid source tuning")
        settings.append(dict(id=sid,instrument_id=numeric_state(part,"instrumentId"),capo=numeric_state(part,"capo"),tuning=dict(present="tuning" in part,value=[str(F(str(x))) for x in tuning] if tuning is not None else None)))
        for mi,m in enumerate(part.get("measures",[])):
            for vi,v in enumerate(m.get("voices",[])):
                region=f"voice:{meta['songId']}:{part['partId']}:{mi+1}:{vi}";regions[region]=sid
                for bi,b in enumerate(v.get("beats",[])):
                    for ni,n in enumerate(b.get("notes",[])):
                        if n.get("rest"):continue
                        ident=f"event:{meta['songId']}:{part['partId']}:{mi+1}:{vi}:{bi}:{ni}"
                        positions.append(dict(id=ident,string=numeric_state(n,"string"),fret=numeric_state(n,"fret"),dead=boolean_state(n,"dead")))
    for n in structural["notes"]:n.pop("base_pitch")
    return dict(schema="position-owned-topology/1",topology=structural,settings=settings,region_settings=regions,positions=positions)


def encode(facts):
    if set(facts)!={"schema","topology","settings","region_settings","positions"} or facts["schema"]!="position-owned-topology/1":raise ConstraintError("Invalid position facts")
    validate_settings(facts["settings"]);settings={s["id"]:s for s in facts["settings"]}
    positions={p["id"]:p for p in facts["positions"]}
    if len(positions)!=len(facts["positions"]):raise ConstraintError("Duplicate position identity")
    bybeat={};byid={};pitches={};regions=[];counts=Counter()
    for n in facts["topology"]["notes"]:
        if set(n)!={"id","beat_ref","slot"}:raise ConstraintError("Duplicate note timing/pitch payload")
        bybeat.setdefault(n["beat_ref"],[]).append(n["id"]);byid[n["id"]]=n
    if set(positions)!=set(byid):raise ConstraintError("Position ownership differs")
    if set(facts["region_settings"])!={v["id"] for v in facts["topology"]["voices"]}:raise ConstraintError("Region settings ownership differs")
    for voice in facts["topology"]["voices"]:
        setting_id=facts["region_settings"][voice["id"]]
        if setting_id not in settings:raise ConstraintError("Missing setting reference")
        setting=settings[setting_id];rows=[]
        for bid in voice["beats"]:
            for ident in sorted(bybeat.get(bid,[]),key=lambda ident:byid[ident]["slot"]):
                p=positions[ident]
                if set(p)!={"id","string","fret","dead"}:raise ConstraintError("Unexpected position fields")
                validate_state(p["string"]);validate_state(p["fret"]);validate_state(p["dead"],False)
                kind=mode(setting,p["string"],p["fret"]);counts[kind]+=1
                reason=residual_reason(setting,p["string"],p["fret"])
                if reason:counts["reason:"+reason]+=1
                if p["fret"]["value"] is not None and F(p["fret"]["value"])<0:counts["negative_source_fret_unrepaired"]+=1
                values=dict(position_pitch=None,percussion_code=None,unresolved_fret=None)
                if kind=="pitched_position":values["position_pitch"]=str(solve(position_equation(),dict(**constants(setting,p["string"]),fret=p["fret"]["value"]),["position_pitch"])["position_pitch"])
                elif kind=="percussion":values["percussion_code"]=p["fret"]["value"]
                else:values["unresolved_fret"]=p["fret"]["value"]
                counts["retained_unresolved_fret_values"]+=values["unresolved_fret"] is not None
                pitches[ident]=values["position_pitch"] if not p["dead"]["value"] else None
                rows.append(dict(id=ident,values=values,symbols=dict(string=p["string"],fret_presence=p["fret"]["present"],fret_number_type=p["fret"]["number_type"],dead=p["dead"],kind=kind,unresolved_reason=reason)))
        if rows:regions.append(dict(id=voice["id"],unit="1",rows=rows))
    lower=dict(facts["topology"],notes=[dict(n,base_pitch=pitches[n["id"]]) for n in facts["topology"]["notes"]])
    upper=topology.encode(lower);upper.pop("pitch_patterns")
    return dict(schema="positioned-relative-topology/1",topology=upper,settings=facts["settings"],region_settings=facts["region_settings"],position_patterns=factor_numeric(regions,CHANNELS),coverage=dict(counts))


def decode(model):
    if set(model)!={"schema","topology","settings","region_settings","position_patterns","coverage"} or model["schema"]!="positioned-relative-topology/1":raise ConstraintError("Unexpected position representation")
    validate_settings(model["settings"]);settings={s["id"]:s for s in model["settings"]}
    if model["position_patterns"]["channels"]!=CHANNELS:raise ConstraintError("Unexpected physical channels")
    region_settings=model["region_settings"]
    if set(region_settings)!={v["id"] for v in model["topology"]["voices"]}:raise ConstraintError("Region ownership differs")
    bybeat={}
    for n in model["topology"]["memberships"]:bybeat.setdefault(n["beat_ref"],[]).append(n)
    ownership={v["id"]:[n["id"] for bid in v["beats"] for n in sorted(bybeat.get(bid,[]),key=lambda n:n["slot"])] for v in model["topology"]["voices"]}
    nonempty={k:v for k,v in ownership.items() if v}
    if len(model["position_patterns"]["occurrences"])!=len(nonempty):raise ConstraintError("Missing/duplicate position region")
    members={}
    for occurrence in model["position_patterns"]["occurrences"]:
        if occurrence["region_id"] not in region_settings or occurrence["members"]!=nonempty.get(occurrence["region_id"]):raise ConstraintError("Position region membership/order mismatch")
        for ident in occurrence["members"]:members[ident]=region_settings[occurrence["region_id"]]
    positions=[];pitches={}
    for row in realize_numeric(model["position_patterns"]):
        ident=row["id"];s=row["symbols"];values=row["values"]
        if not isinstance(s,dict) or set(s)!={"string","fret_presence","fret_number_type","dead","kind","unresolved_reason"}:raise ConstraintError("Unexpected physical symbols")
        validate_state(s["string"]);validate_state(s["dead"],False)
        if type(s["fret_presence"]) is not bool or s["fret_number_type"] not in (None,"int","float"):raise ConstraintError("Invalid fret witness")
        if members.get(ident) not in settings:raise ConstraintError("Missing position settings")
        setting=settings[members[ident]];kind=s["kind"]
        if kind=="pitched_position":
            if values["position_pitch"] is None or values["percussion_code"] is not None or values["unresolved_fret"] is not None:raise ConstraintError("Invalid position channel mask")
            fret=str(solve(position_equation(),dict(**constants(setting,s["string"]),position_pitch=values["position_pitch"]),["fret"])["fret"])
        elif kind in ("percussion","unmapped_position"):
            key="percussion_code" if kind=="percussion" else "unresolved_fret"
            if any(v is not None for k,v in values.items() if k!=key):raise ConstraintError("Invalid nonpitched channels")
            fret=values[key]
        else:raise ConstraintError("Unknown position kind")
        fret_state=dict(present=s["fret_presence"],value=fret,number_type=s["fret_number_type"]);validate_state(fret_state)
        if residual_reason(setting,s["string"],fret_state)!=s["unresolved_reason"]:raise ConstraintError("Invalid residual reason")
        if mode(setting,s["string"],fret_state)!=kind:raise ConstraintError("Physical classification contradicts settings")
        positions.append(dict(id=ident,string=s["string"],fret=fret_state,dead=s["dead"]))
        pitches[ident]=values["position_pitch"] if not s["dead"]["value"] else None
    structural=topology.decode_structure(model["topology"],pitches)
    for n in structural["notes"]:n.pop("base_pitch")
    result=dict(schema="position-owned-topology/1",topology=structural,settings=model["settings"],region_settings=region_settings,positions=positions)
    expected_coverage=encode(result)["coverage"]
    if model["coverage"]!=expected_coverage or any(type(n) is not int for n in model["coverage"].values()):raise ConstraintError("Invalid derived physical coverage")
    return result


def event_view(facts):
    # Derive the declared base-pitch view using the same equation, not a second recipe.
    upper=encode(facts);pitches={r["id"]:(r["values"]["position_pitch"] if not r["symbols"]["dead"]["value"] else None) for r in realize_numeric(upper["position_patterns"])}
    return topology.event_view(topology.decode_structure(upper["topology"],pitches))
