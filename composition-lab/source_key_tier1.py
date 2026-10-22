"""Faithful T1 measure-key declaration facts; no tonal interpretation here."""
import json
from fractions import Fraction as F
from run_reversible_tier_qa import extract as extract_written


def extract(capture):
    lower=extract_written(capture)
    from source_semantics import layout, filled
    files=sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
    parts=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
    headers,warnings=layout(parts)
    if any(w["reason"]=="conflicting_track_meter" for w in warnings): raise ValueError("Conflicting source meter; no forced shared geometry")
    frames=[];last_explicit=0
    for index,header in enumerate(headers):
        explicit=any(index<len(p.get("measures",[])) and p["measures"][index].get("signature") for p in parts)
        if explicit:last_explicit=index+1
        if not last_explicit:raise ValueError("Missing source meter; no invented 4/4 geometry")
        frames.append(dict(id=f"measure:{index+1}",ordinal=index+1,label=str(index+1),start_q=header["start_q"],span_q=header["span_q"],signature=header["signature"],meter_source="explicit" if explicit else "inherited",meter_source_frame=last_explicit))
    declarations=[];inventory=[]
    for part in parts:
        pid=part['partId']; measures=part.get('measures',[])
        end = F(headers[len(measures)-1]['start_q'])+F(headers[len(measures)-1]['span_q']) if measures else F(0)
        inventory.append(dict(part_id=pid,measure_count=len(measures),end_q=str(end)))
        for index,measure in enumerate(measures):
            if 'keySignature' not in measure: continue
            declarations.append(dict(id=f'key:{pid}:{index+1}',part_id=pid,bar=index+1,onset_q=headers[index]['start_q'],
                                     source_pointer=f'track-{pid}.json#/measures/{index}/keySignature',value=measure['keySignature']))
    geometry_parts=[]
    for part in parts:
        pickup=part.get("anacrusis")
        if pickup is not None and type(pickup) is not bool:raise ValueError("Unsupported source pickup encoding")
        geometry_parts.append(dict(part_id=part["partId"],frame_refs=[f"measure:{i+1}" for i in range(len(part.get("measures",[])))],source_pickup_declared=pickup))
    meta=json.loads((capture/"metadata.json").read_text(encoding="utf-8-sig"))
    geometry=dict(source_format="songsterr_json",source_id=f"songsterr:{meta['songId']}:{meta['revisionId']}",frames=frames,parts=geometry_parts,first_notated_span_q=str(max((filled(p['measures'][0]) for p in parts if p.get('measures')),default=F(0))) if frames else None)
    lower.update(schema='normalized-written-context-facts/3',scope='written_context_facts_geometry_and_optional_source_keys',measure_geometry=geometry,source_key_declarations=declarations,source_key_inventory=inventory)
    return lower
