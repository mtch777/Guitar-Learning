"""Isolated meter/tempo observation prototype; not integrated into the song engine.

No playback expansion, default tempo, source repair or musical interpretation.
Only explicit source declarations enter; exact unit equations run both ways.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from reversible_annotations import scalar,validate_scalar,pack,unpack
from reversible_relationships import ConstraintError,solve

# Only type4 is source-contract verified in the current captured corpus.
TEMPO_UNITS={4}
COORDINATES={"meter":{"numerator":"nominal_span_q"},"beat_tempo":{"bpm":"quarter_bpm"},"automation_tempo":{"bpm":"quarter_bpm","position":"position_q"}}


def extract(capture):
    documents={path.name:json.loads(path.read_text(encoding="utf-8-sig")) for path in capture.glob("track-*.json")}
    documents["metadata.json"]=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"))
    return extract_documents(documents)


def extract_documents(documents):
    """Same extraction from the preceding packet's reconstructed documents only."""
    meta=documents["metadata.json"]
    records=[];unsupported=[]
    def fields(obj,owner):
        result={}
        for key,value in obj.items():
            if type(value) in (int,float,bool,str,type(None)):result[key]=scalar(value)
            else:unsupported.append(dict(owner=owner,field=key,source_type=type(value).__name__))
        return result
    for name in sorted(name for name in documents if name.startswith("track-") and name.endswith(".json")):
        part=documents[name];pid=part["partId"]
        part_ref=f"part:{meta['songId']}:{pid}"
        for mi,m in enumerate(part.get("measures",[])):
            mid=f"measure:{meta['songId']}:{pid}:{mi+1}"
            if "signature" in m:
                sig=m["signature"]
                if isinstance(sig,list) and len(sig)==2 and all(type(x) in (int,float) for x in sig):
                    records.append(dict(id=f"meter:{mid}",owner=mid,kind="meter",fields=dict(numerator=scalar(sig[0]),denominator=scalar(sig[1]))))
                else:unsupported.append(dict(owner=mid,field="signature",source_type=type(sig).__name__))
            for vi,v in enumerate(m.get("voices",[])):
                for bi,b in enumerate(v.get("beats",[])):
                    if "tempo" not in b:continue
                    bid=f"beat:{meta['songId']}:{pid}:{mi+1}:{vi}:{bi}"
                    if isinstance(b["tempo"],dict):records.append(dict(id=f"tempo:{bid}",owner=bid,kind="beat_tempo",fields=fields(b["tempo"],bid)))
                    else:unsupported.append(dict(owner=bid,field="tempo",source_type=type(b["tempo"]).__name__))
        for ai,a in enumerate((part.get("automations") or {}).get("tempo",[])):
            ident=f"tempo:{part_ref}:{ai}"
            if isinstance(a,dict):records.append(dict(id=ident,owner=part_ref,kind="automation_tempo",fields=fields(a,ident)))
            else:unsupported.append(dict(owner=part_ref,field="tempo",source_type=type(a).__name__,ordinal=ai))
    return dict(schema="temporal-source-observations/1",records=records,unsupported=unsupported)


def numeric(state):
    return state is not None and state["type"] in {"int","float"}


def relation(kind,field,fields):
    """Return SAME affine relationship for either source or normalized unknown."""
    if kind=="meter" and field=="numerator":
        d=fields.get("denominator")
        if not numeric(d) or F(d["value"])<=0 or not numeric(fields.get("numerator")) or F(fields["numerator"]["value"])<=0:return None
        return [{"source":F(4),"normalized":-F(d["value"])}]
    if kind in {"beat_tempo","automation_tempo"} and field=="bpm":
        unit=fields.get("type")
        if not numeric(unit) or F(unit["value"]) not in TEMPO_UNITS or not numeric(fields.get("bpm")) or F(fields["bpm"]["value"])<=0:return None
        return [{"source":F(4),"normalized":-F(unit["value"])}]
    if kind=="automation_tempo" and field=="position":
        return [{"source":F(4),"normalized":F(-1)}]
    return None


def transform(records,reverse=False):
    output=[];seen=set()
    for record in records:
        if set(record)!={"id","owner","kind","fields"} or record["kind"] not in {"meter","beat_tempo","automation_tempo"}:raise ConstraintError("Invalid temporal record")
        if record["id"] in seen:raise ConstraintError("Duplicate temporal occurrence")
        if not isinstance(record["id"],str) or not isinstance(record["owner"],str) or not isinstance(record["fields"],dict):raise ConstraintError("Invalid temporal ownership")
        seen.add(record["id"]);fields=deepcopy(record["fields"])
        for state in fields.values():validate_scalar(state)
        aliases=COORDINATES[record["kind"]]
        renamed=set()
        if not reverse and set(fields)&set(aliases.values()):raise ConstraintError("Reserved normalized coordinate in source fields")
        if reverse:
            for source,target in aliases.items():
                if target in fields:
                    if source in fields:raise ConstraintError("Duplicated temporal coordinate")
                    fields[source]=fields.pop(target);renamed.add(source)
        converted={}
        for key,state in fields.items():
            if not numeric(state):
                if key in renamed:raise ConstraintError("Normalized temporal coordinate must be numeric")
                continue
            eq=relation(record["kind"],key,fields)
            if eq is None:
                if key in renamed:raise ConstraintError("Normalized temporal coordinate has no valid source equation")
                continue
            if reverse and key not in renamed:raise ConstraintError("Convertible temporal value must use its normalized coordinate")
            known="normalized" if reverse else "source";unknown="source" if reverse else "normalized"
            state["value"]=str(solve(eq,{known:state["value"]},[unknown])[unknown])
            if not reverse:converted[key]=aliases[key]
        if not reverse:
            for source,target in converted.items():
                if target in fields:raise ConstraintError("Temporal source field collides with derived coordinate")
                fields[target]=fields.pop(source)
            for state in fields.values():
                if numeric(state):state["type"]="float"
        output.append({**record,"fields":fields})
    return output


def validate_inventory(items):
    if not isinstance(items,list):raise ConstraintError("Invalid temporal unsupported inventory")
    for item in items:
        if not isinstance(item,dict) or set(item) not in ({"owner","field","source_type"},{"owner","field","source_type","ordinal"}) or not all(isinstance(item[k],str) for k in ("owner","field","source_type")):raise ConstraintError("Temporal inventory cannot carry source payloads")
        if "ordinal" in item and (item["field"]!="tempo" or type(item["ordinal"]) is not int or item["ordinal"]<0):raise ConstraintError("Invalid temporal source slot")


def encode(facts):
    if set(facts)!={"schema","records","unsupported"} or facts["schema"]!="temporal-source-observations/1":raise ConstraintError("Invalid temporal facts")
    validate_inventory(facts["unsupported"])
    records=transform(facts["records"])
    return dict(schema="relative-temporal-observations/1",bindings=[{**{k:r[k] for k in ("id","owner","kind")},"source_numeric_types":{k:v["type"] for k,v in original["fields"].items() if numeric(v)}} for r,original in zip(records,facts["records"])],parameters=pack([dict(id=r["id"],fields=r["fields"]) for r in records],{}),unsupported=deepcopy(facts["unsupported"]))


def decode(model):
    if set(model)!={"schema","bindings","parameters","unsupported"} or model["schema"]!="relative-temporal-observations/1":raise ConstraintError("Invalid temporal representation")
    validate_inventory(model["unsupported"])
    rows={r["id"]:r["fields"] for r in unpack(model["parameters"],{})};bindings=model["bindings"]
    if len(bindings)!=len(rows) or {b["id"] for b in bindings}!=set(rows):raise ConstraintError("Invalid temporal membership")
    records=[]
    for binding in bindings:
        if set(binding)!={"id","owner","kind","source_numeric_types"}:raise ConstraintError("Invalid temporal binding")
        records.append({**{k:binding[k] for k in ("id","owner","kind")},"fields":rows[binding["id"]]})
    restored=transform(records,True)
    for record,binding in zip(restored,bindings):
        kinds=binding["source_numeric_types"]
        if set(kinds)!={k for k,v in record["fields"].items() if numeric(v)}:raise ConstraintError("Invalid temporal numeric type ownership")
        for key,kind in kinds.items():
            if kind not in {"int","float"}:raise ConstraintError("Invalid temporal source number type")
            record["fields"][key]["type"]=kind;validate_scalar(record["fields"][key])
    return dict(schema="temporal-source-observations/1",records=restored,unsupported=deepcopy(model["unsupported"]))


def interpretation_status(model):
    """Derived support view; no chosen tempo, repaired source or playback clock."""
    result=[]
    for record in decode(model)["records"]:
        fields=record["fields"];kind=record["kind"];reasons=[]
        if kind=="meter":
            if relation(kind,"numerator",fields) is None:reasons.append("missing_or_nonpositive_meter")
        else:
            unit=fields.get("type");bpm=fields.get("bpm")
            if not numeric(unit) or F(unit["value"]) not in TEMPO_UNITS:reasons.append("unverified_or_missing_tempo_unit")
            if not numeric(bpm) or F(bpm["value"])<=0:reasons.append("missing_or_nonpositive_bpm")
            if fields.get("linear")==scalar(True):reasons.append("ramp_execution_unresolved")
        result.append(dict(id=record["id"],unit_conversion="supported" if relation(kind,"numerator" if kind=="meter" else "bpm",fields) is not None else "unsupported",playback="not_implemented",reasons=reasons))
    return result
