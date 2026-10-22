"""Faithful T1 measure-key declaration facts; no tonal interpretation here."""
import json
from fractions import Fraction as F
from run_reversible_tier_qa import extract as extract_written


def extract(capture):
    lower=extract_written(capture)
    from source_semantics import layout
    files=sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
    parts=[json.loads(p.read_text(encoding='utf-8-sig')) for p in files]
    headers,_=layout(parts)
    declarations=[];inventory=[]
    for part in parts:
        pid=part['partId']; measures=part.get('measures',[])
        end = F(headers[len(measures)-1]['start_q'])+F(headers[len(measures)-1]['span_q']) if measures else F(0)
        inventory.append(dict(part_id=pid,measure_count=len(measures),end_q=str(end)))
        for index,measure in enumerate(measures):
            if 'keySignature' not in measure: continue
            declarations.append(dict(id=f'key:{pid}:{index+1}',part_id=pid,bar=index+1,onset_q=headers[index]['start_q'],
                                     source_pointer=f'track-{pid}.json#/measures/{index}/keySignature',value=measure['keySignature']))
    lower.update(schema='normalized-written-and-declared-keys/2',scope='base_pitch_metric_time_and_source_key_declarations',source_key_declarations=declarations,source_key_inventory=inventory)
    return lower
