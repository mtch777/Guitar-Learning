"""Fixed-source development census; no edits, new song draw or acceptance claim."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
from melodic_contour_choices import inventory,source_options
from source_fact_tier1 import extract


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(protocol_path,output):
    protocol=json.loads(protocol_path.read_bytes())
    for path,value in protocol['hashes'].items():
        if digest(path)!=value:raise ValueError('Frozen development input changed: '+path)
    output.mkdir(parents=True,exist_ok=False)
    summary={}
    for name,folder in protocol['captures'].items():
        view=inventory(extract(Path(folder)))
        eligible=[r for r in view['neighborhoods'] if not r['reasons']]
        options=[source_options(view,r['target_ref']) for r in eligible]
        opportunities=[r for r in options if r['witness_pair'] is not None]
        counts=dict(all_triples=len(view['neighborhoods']),eligible=len(eligible),
            source_alternative_targets=len(opportunities),
            refusal_counts=dict(Counter(reason for r in view['neighborhoods'] for reason in r['reasons'])))
        (output/(name+'.json')).write_text(json.dumps(dict(inventory=view,options=options,counts=counts),indent=2),encoding='utf-8')
        summary[name]=counts
        print(name,json.dumps(counts),flush=True)
    for path,value in protocol['hashes'].items():
        if digest(path)!=value:raise ValueError('Frozen development input changed during audit: '+path)
    result=dict(status='DEVELOPMENT_SOURCE_CENSUS_ONLY',summary=summary,
        protocol_sha256=digest(protocol_path),
        remaining='Every candidate still requires full-duration independent harmony and complete output locks; no edits or creative acceptance')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    run(Path(sys.argv[1]),Path(sys.argv[2]))
