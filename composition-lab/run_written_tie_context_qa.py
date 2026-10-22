"""Private written-tie context QA against raw source and stripped shared inverse."""
import argparse
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import sys
from musical_tier2 import analyze,strip_lower,written_tie_chains
from qa_isolation_harness import execute


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')


def exact_fields(a,b):
    """Independent recursive presence/type/value comparison, including bool/int."""
    if type(a) is not type(b):return False
    if type(a) is dict:return set(a)==set(b) and all(exact_fields(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact_fields(x,y) for x,y in zip(a,b))
    return a==b


def raw_declarations(capture):
    """Literal source ownership check independent of Tier1 adapter/solver."""
    meta=json.loads((capture/'metadata.json').read_text(encoding='utf-8-sig'));parts=[];rows=[]
    for path in sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1])):
        part=json.loads(path.read_text(encoding='utf-8-sig'));pid=part['partId']
        parts.append({'part_id':pid,'fields':{k:v for k,v in part.items() if k in {'instrumentId','tuning','capo'}}})
        for bar,measure in enumerate(part.get('measures',[]),1):
            for voice,v in enumerate(measure.get('voices',[])):
                for beat,b in enumerate(v.get('beats',[])):
                    for note,n in enumerate(b.get('notes',[])):
                        if n.get('rest'):continue
                        rows.append({'occurrence_ref':f"event:{meta['songId']}:{pid}:{bar}:{voice}:{beat}:{note}",'fields':{k:value for k,value in n.items() if k in {'string','fret','dead','tie'}}})
    return {'parts':parts,'occurrences':rows}


def run(fresh,regressions,output):
    from source_tie_tier1 import extract
    from check_reversible_source import check,check_tie_relations,source_expectation
    from three_gate_qa import portability
    root=Path(__file__).resolve().parent
    sys.path.insert(0,str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics');importlib.import_module('analyze_relationships')
    captures=[fresh/'capture']+regressions;selection=fresh/'selection.json'
    output.mkdir(parents=True,exist_ok=False)
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    sources=[selection]+[p for capture in captures for p in capture.glob('*.json')]
    frozen={str(p):sha(p) for p in modules+sources};write(output/'freeze.json',frozen)
    for module in modules:
        path=output/'frozen-code'/module.relative_to(root);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(module.read_bytes())
    code=(root/'musical_tier2.py').read_text(encoding='utf-8');results=[]
    for ordinal,capture in enumerate(captures):
        directory=output/str(ordinal);directory.mkdir();row=dict(capture=str(capture),new_random=ordinal==0)
        try:
            if ordinal==0:row['fresh_selection']=portability(capture,selection)
            lower=extract(capture);upper=analyze(lower);chains=written_tie_chains(upper)
            row['source_fields']=check(capture,[{k:e[k] for k in ('id','pitch','onset_q','duration_q')} for e in lower['events']])
            row['source_declarations']=dict(status='PASS' if exact_fields(raw_declarations(capture),lower['tie_notation']) else 'FAIL',scope='Every added source field presence/type/value; independent literal source reader and comparator')
            row['source_tie_relations']=check_tie_relations(capture,upper['written_ties']['links'],upper['written_ties']['unresolved'])
            raw,_=source_expectation(capture);errors=[]
            for chain in chains['chains']:
                from fractions import Fraction as F
                notes=[raw[i] for i in chain['occurrence_refs']]
                if chain['onset_q']!=notes[0]['onset_q'] or F(chain['written_end_q'])!=F(notes[-1]['onset_q'])+F(notes[-1]['duration_q']) or F(chain['nominal_span_q'])!=sum((F(n['duration_q']) for n in notes),F(0)):errors.append('Raw chain endpoint/extent mismatch')
            row['source_chain_endpoints']=dict(status='PASS' if not errors else 'FAIL',errors=errors,chains=len(chains['chains']))
            wrapper='''
_exact_reconstruct=reconstruct
def reconstruct(upper,controls):
    return dict(tier1=_exact_reconstruct(upper,controls),chains=written_tie_chains(upper))
'''
            row['isolated_same_relations']=execute(code+wrapper,strip_lower(upper),dict(variation=0),dict(tier1=lower,chains=chains),directory/'isolated',timeout=180)
            if ordinal==0:
                row['actual_denial_challenges']={}
                for challenge in ('open','os_open','network','process','repo_import'):
                    forbidden=root/'musical_tier2.py' if challenge=='repo_import' else capture/'metadata.json'
                    row['actual_denial_challenges'][challenge]=execute(code,strip_lower(upper),dict(variation=0),lower,directory/('denial-'+challenge),timeout=30,challenge=challenge,forbidden=forbidden)['status']
            write(directory/'chains.json',chains)
            states=Counter('missing' if 'tie' not in r['fields'] else type(r['fields']['tie']).__name__+':'+str(r['fields']['tie']) for r in lower['tie_notation']['occurrences'])
            row['declaration_inventory']=dict(states)
            row['status']='PASS' if row['source_fields']['status']=='pass_declared_raw_source_fields' and row['source_tie_relations']['status']=='pass_declared_written_tie_relations' and all(row[k]['status']=='PASS' for k in ('source_declarations','source_chain_endpoints','isolated_same_relations')) and (ordinal!=0 or row['fresh_selection']['status']=='PASS' and set(row['actual_denial_challenges'].values())=={'PASS'}) else 'FAIL'
        except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
        write(directory/'result.json',row);results.append(row)
    unchanged=all(sha(Path(p))==digest for p,digest in frozen.items())
    result=dict(technical_status='PASS' if unchanged and all(r['status']=='PASS' for r in results) else 'FAIL',code_and_source_unchanged=unchanged,results=results,musical_acceptance='PENDING_PROJECTPLANNER_REVIEW; written continuity only, no acoustic sustain/attack, no full GP claim')
    write(output/'result.json',result);print(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('fresh',type=Path);p.add_argument('output',type=Path);p.add_argument('--regression',type=Path,action='append',default=[]);args=p.parse_args()
    raise SystemExit(0 if run(args.fresh,args.regression,args.output)['technical_status']=='PASS' else 1)
