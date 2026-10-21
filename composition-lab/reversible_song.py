"""Owned composition of existing reversible operators; one source boundary.

This is a stage envelope, not another music generator or complete song schema.
"""
from copy import deepcopy
import hashlib,json
import reversible_annotations as annotations
import reversible_temporal as temporal
import reversible_ties as ties
import reversible_voicings as voicings
import reversible_topology as topology
import reversible_control as control
from reversible_relationships import ConstraintError

STAGES={"extracted","music","temporal"}
CONTROL_STAGES=STAGES|{"control"}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def extract(capture,controls=False):
    """ONLY source-reading boundary. No later operator accepts a source path."""
    music=annotations.extract(capture);timing=temporal.extract(capture)
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"));parts=[]
    for path in sorted(capture.glob("track-*.json")):
        part=json.loads(path.read_text(encoding="utf-8-sig"));pid=part["partId"];song=meta["songId"]
        parts.append(dict(id=f"part:{song}:{pid}",settings_ref=f"settings:{song}:{pid}",measure_refs=[f"measure:{song}:{pid}:{i+1}" for i in range(len(part.get("measures",[])))],automation_slots=[f"tempo:part:{song}:{pid}:{i}" for i in range(len((part.get("automations") or {}).get("tempo",[])))]))
    result=dict(schema="owned-song-stages/1",stage="extracted",identity=dict(song_id=meta["songId"],revision_id=meta["revisionId"]),registry=parts,music=music,temporal=timing)
    if controls:result.update(schema="owned-song-stages/2",control=control.extract(capture))
    validate(result);return result


def structure(envelope):
    if envelope["stage"]=="extracted":
        physical=envelope["music"]["physical"];return physical,physical["topology"]
    physical=envelope["music"]["lower"]["lower"]["physical"]
    model=physical["topology"]
    return physical,topology.decode_structure(model,{n["id"]:None for n in model["memberships"]})


def validate(envelope):
    if not isinstance(envelope,dict):raise ConstraintError("Invalid owned song envelope")
    version=envelope.get("schema");extended=version=="owned-song-stages/2"
    fields={"schema","stage","identity","registry","music","temporal"}|({"control"} if extended else set())
    if version not in {"owned-song-stages/1","owned-song-stages/2"} or set(envelope)!=fields or envelope["stage"] not in (CONTROL_STAGES if extended else STAGES):raise ConstraintError("Invalid owned song envelope")
    identity=envelope["identity"]
    if not isinstance(identity,dict) or set(identity)!={"song_id","revision_id"} or any(type(x) is not int for x in identity.values()):raise ConstraintError("Invalid source identity")
    expected_music="annotated-position-topology/1" if envelope["stage"]=="extracted" else "voicing-constrained-song/1"
    if envelope["music"].get("schema")!=expected_music:raise ConstraintError("Music slot schema does not match stage")
    physical,structural=structure(envelope);settings={r["id"] for r in physical["settings"]};measures={r["id"]:r for r in structural["measures"]}
    voices={r["id"]:r for r in structural["voices"]};beats={r["id"] for r in structural["beats"]}
    parts=set();owned_measures=set();owned_settings=set();slots={};all_slots=set()
    for part in envelope["registry"]:
        if not isinstance(part,dict) or set(part)!={"id","settings_ref","measure_refs","automation_slots"} or not isinstance(part["id"],str) or part["id"] in parts:raise ConstraintError("Invalid part ownership")
        parts.add(part["id"]);setting=part["settings_ref"]
        entries=part["automation_slots"]
        if not isinstance(entries,list) or any(not isinstance(x,str) for x in entries) or len(set(entries))!=len(entries) or all_slots&set(entries):raise ConstraintError("Invalid automation slot ownership")
        slots[part["id"]]=entries;all_slots.update(entries)
        if setting not in settings or setting in owned_settings:raise ConstraintError("Invalid settings ownership")
        owned_settings.add(setting)
        for mid in part["measure_refs"]:
            if mid not in measures or mid in owned_measures:raise ConstraintError("Invalid measure ownership")
            owned_measures.add(mid)
            for vid in measures[mid]["voices"]:
                if vid not in voices or physical["region_settings"].get(vid)!=setting:raise ConstraintError("Structural voice/part ownership conflict")
    if owned_measures!=set(measures) or owned_settings!=settings:raise ConstraintError("Incomplete source ownership")
    timing=temporal.decode(envelope["temporal"]) if envelope["stage"] in {"temporal","control"} else envelope["temporal"]
    # Strict declaration validation, even before its lift; no arbitrary side slot.
    temporal.encode(timing)
    record_ids={r["id"] for r in timing["records"]}
    for record in timing["records"]:
        owners=set(measures) if record["kind"]=="meter" else beats if record["kind"]=="beat_tempo" else parts
        if record["owner"] not in owners:raise ConstraintError("Temporal owner does not exist in this song")
        if record["kind"]=="automation_tempo" and record["id"] not in slots[record["owner"]]:raise ConstraintError("Automation occurrence does not belong to source part")
    accounted={r["id"] for r in timing["records"] if r["kind"]=="automation_tempo"}
    for item in timing["unsupported"]:
        if "ordinal" in item:
            entries=slots.get(item["owner"],[])
            if item["ordinal"]>=len(entries):raise ConstraintError("Unsupported automation slot does not exist")
            ident=entries[item["ordinal"]]
            if ident in accounted:raise ConstraintError("Automation slot counted twice")
            accounted.add(ident)
        if item["owner"] not in parts|set(measures)|beats|record_ids:raise ConstraintError("Unsupported declaration owner does not exist")
    if accounted!=all_slots:raise ConstraintError("Automation source slots not fully accounted")
    if extended:
        controls=control.decode(envelope["control"]) if envelope["stage"]=="control" else envelope["control"]
        control.encode(controls)
        expected=[dict(id=p["id"],measure_refs=p["measure_refs"]) for p in envelope["registry"]]
        actual=[dict(id=p["id"],measure_refs=p["measure_refs"]) for p in controls["parts"]]
        if actual!=expected:raise ConstraintError("Control source ownership differs from song registry")
    return envelope


def replace(envelope,slot,operation,prior_stage,next_stage):
    validate(envelope)
    if envelope["stage"]!=prior_stage:raise ConstraintError("Invalid tier transition")
    protected={k:digest(v) for k,v in envelope.items() if k not in {slot,"stage"}}
    original=digest(envelope);result=deepcopy(envelope)
    result[slot]=operation(deepcopy(envelope[slot]));result["stage"]=next_stage
    if digest(envelope)!=original or any(digest(result[k])!=h for k,h in protected.items()):raise ConstraintError("Protected tier slot was changed")
    validate(result);return result


def lift_music(envelope):return replace(envelope,"music",lambda facts:voicings.encode(ties.encode(facts)),"extracted","music")
def lift_temporal(envelope):return replace(envelope,"temporal",temporal.encode,"music","temporal")
def lower_temporal(envelope):return replace(envelope,"temporal",temporal.decode,"temporal","music")
def lower_music(envelope):return replace(envelope,"music",voicings.decode,"music","extracted")
def lift_control(envelope):
    if envelope.get("schema")!="owned-song-stages/2":raise ConstraintError("Control stage requires version2")
    return replace(envelope,"control",control.encode,"temporal","control")
def lower_control(envelope):return replace(envelope,"control",control.decode,"control","temporal")
def encode(facts):
    model=lift_temporal(lift_music(facts))
    return lift_control(model) if model["schema"]=="owned-song-stages/2" else model

def decode(model):
    if model.get("schema")=="owned-song-stages/2":model=lower_control(model)
    return lower_music(lower_temporal(model))
