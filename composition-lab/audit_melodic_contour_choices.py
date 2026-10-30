"""Qualify every fixed-source melodic opportunity; retain every rejection."""
from pathlib import Path
import hashlib
import json
import sys
from collections import Counter
from source_fact_tier1 import extract
from connected_tier2 import analyze,strip_lower,realize
import melodic_contour_intervention as change


def run(protocol_path,census,output):
    protocol=json.loads(protocol_path.read_bytes())
    for p,h in protocol['hashes'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:
            raise ValueError('Frozen development census changed: '+p)
    output.mkdir(parents=True,exist_ok=False);summary={}
    for name,capture in protocol['captures'].items():
        source=json.loads((census/(name+'.json')).read_bytes())
        refs=[r['target']['target_ref']for r in source['options']if r['witness_pair']]
        if not refs:
            summary[name]=dict(status='NO_SOURCE_ALTERNATIVES',targets=0,changed_targets=0)
            print(name,json.dumps(summary[name]),flush=True);continue
        before=extract(Path(capture));upper=strip_lower(analyze(before))
        if realize(upper)!=before:raise ValueError('Complete source inverse failed')
        print(name,'prepare',len(refs),'source targets',flush=True)
        prepared=change.prepare(upper);rows=[]
        for ref in refs:
            result=change.options(upper,ref,prepared);rows.append(result)
            print(name,ref,result['status'],flush=True)
        counts=dict(targets=len(refs),changed_targets=sum(any(o['changed']for o in row['options'])for row in rows),
            statuses=dict(Counter(r['status']for r in rows)),
            rejections=dict(Counter(r['reason']for row in rows for r in row['rejected'])))
        (output/(name+'.json')).write_text(json.dumps(dict(counts=counts,results=rows),indent=2),encoding='utf-8')
        summary[name]=counts
    result=dict(status='DEVELOPMENT_FULL_CONTEXT_OPTIONS',summary=summary,
        scope='Every preliminary source choice checked against unchanged accompanying notes for its entire duration; not fresh-song or audio acceptance')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
