"""Frozen all-part chain-to-harmony query; no attack or note-function truth claim."""
import argparse
from fractions import Fraction as F
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
from musical_tier2 import analyze,strip_lower,written_tie_chains,harmonic_span_evidence,tied_harmonic_context
from qa_isolation_harness import execute


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')


def study(upper,max_edges):
    chains=written_tie_chains(upper)['chains'];index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']};rows=[]
    for part in range(upper['source_quality']['tracks']):
        selected=sorted((c for c in chains if index[c['origin_ref']][0]['part_id']==part),key=lambda c:tuple(index[c['origin_ref']][1][k] for k in ('bar','voice','beat','note')))
        unresolved=[r for r in upper['written_ties']['unresolved'] if index[r['destination']][0]['part_id']==part]
        row=dict(part_id=part,candidate_origins=[c['origin_ref'] for c in selected],unresolved_declarations=unresolved,selected_origin=None,context=None,harmonic=None)
        if selected:
            chain=selected[0];row['selected_origin']=chain['origin_ref'];refs=chain['occurrence_refs']
            clocks=[str(F(index[i][0]['onset_q'])+F(index[i][1]['duration_q'])/2) for i in (refs[0],refs[-1])]
            evidence=harmonic_span_evidence(upper,chain['onset_q'],chain['written_end_q'],part_id=None,max_edges=max_edges)
            row.update(harmonic=evidence,context=tied_harmonic_context(upper,evidence,chain['origin_ref'],clocks))
            row['status']=row['context']['status']
        else:row['status']='NO_RESOLVED_CHAIN_IN_PART'
        rows.append(row)
    return dict(parts=rows,selection='First source-address chain per part; all candidates/unresolved retained; no quarantine replacement',scope='First/last constituent midpoint membership only, not all intermediate note functions')


def source_queries(capture,upper,result):
    from check_reversible_source import source_expectation
    from check_harmonic_span_source import check
    raw,_=source_expectation(capture);population=[(int(i.split(':')[2]),int(i.split(':')[3]),n['pitch'],n['onset_q'],n['duration_q']) for i,n in raw.items()]
    links=upper['written_ties']['links'];successor={r['origin']:r['destination'] for r in links};destinations={r['destination'] for r in links};roots=[i for i in successor if i not in destinations]
    errors=[];oracles=[]
    part_ids=[r['part_id'] for r in result['parts']]
    if any(type(i) is not int for i in part_ids) or sorted(part_ids)!=list(range(upper['source_quality']['tracks'])):errors.append('Exact unique source part inventory differs')
    for row in result['parts']:
        expected_unresolved=[r for r in upper['written_ties']['unresolved'] if int(r['destination'].split(':')[2])==row['part_id']]
        if row['unresolved_declarations']!=expected_unresolved:errors.append('Complete unresolved-declaration subset differs')
        expected=sorted((i for i in roots if int(i.split(':')[2])==row['part_id']),key=lambda i:tuple(map(int,i.split(':')[3:])))
        if row['candidate_origins']!=expected or row['selected_origin']!=(expected[0] if expected else None):errors.append('Source chain selection denominator differs')
        if not expected:continue
        refs=[expected[0]]
        while refs[-1] in successor:refs.append(successor[refs[-1]])
        context=row['context'];queries=context['resolved_original_queries']
        clocks=[str(F(raw[i]['onset_q'])+F(raw[i]['duration_q'])/2) for i in (refs[0],refs[-1])]
        if context['requested_clocks_q']!=clocks or queries!=[dict(occurrence_ref=i,at_q=t) for i,t in zip((refs[0],refs[-1]),clocks)] or context['chain']['occurrence_refs']!=refs:errors.append('Raw chain-to-original-constituent mapping differs')
        if context['membership'] is not None and context['membership']['queries']!=queries:errors.append('Membership replaced source queries')
        if context['status']=='CONDITIONAL_CONTINUITY_CONTEXT' and (context['membership'] is None or not context['membership']['feasible_membership_vectors']):errors.append('Eligible chain context omitted joint witnesses')
        if context['status']=='QUARANTINED_CHAIN' and (context['membership'] is not None or not context['quarantine_reasons']):errors.append('Quarantine invented interpretation or lost reasons')
        if row['harmonic']['status']=='SCORED_NOT_MUSICAL_TRUTH' or row['harmonic']['status']=='NOT_RUN_RESOURCE_LIMIT':
            oracles.append(check(population,row['harmonic'],context['membership'],raw))
        elif context['status']!='QUARANTINED_CHAIN':errors.append('Unexplained non-run harmonic context')
    return dict(status='PASS' if not errors and all(r['status']=='PASS' for r in oracles) else 'FAIL',errors=errors,harmonic_source_oracles=oracles,scope='Raw source mapping and independently verified optimal joint witnesses; no annotated musical-role accuracy')


def run(fresh,regressions,output):
    from source_tie_tier1 import extract
    from check_reversible_source import check,check_tie_relations
    from run_written_tie_context_qa import raw_declarations,exact_fields
    from three_gate_qa import portability
    root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics');importlib.import_module('analyze_relationships');importlib.import_module('check_harmonic_span_source')
    plan_path=fresh/'chaincontext-plan.json';plan=json.loads(plan_path.read_text(encoding='utf-8'));selection=fresh/'selection.json'
    if sha(selection)!=plan['selection_sha256']:raise ValueError('Selection changed after frozen chain plan')
    captures=[fresh/'capture']+regressions;output.mkdir(parents=True,exist_ok=False)
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    sources=[selection,plan_path]+[p for capture in captures for p in capture.glob('*.json')];frozen={str(p):sha(p) for p in modules+sources};write(output/'freeze.json',frozen)
    for module in modules:
        path=output/'frozen-code'/module.relative_to(root);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(module.read_bytes())
    code=(root/'musical_tier2.py').read_text(encoding='utf-8');wrapper='\n'+inspect.getsource(study)+'''
_exact_reconstruct=reconstruct
def reconstruct(package,controls):
    if set(package)!={'upper','max_edges'}:raise ValueError('Declared source-independent query cap only')
    return dict(tier1=_exact_reconstruct(package['upper'],controls),study=study(package['upper'],package['max_edges']))
'''
    results=[]
    for ordinal,capture in enumerate(captures):
        directory=output/str(ordinal);directory.mkdir();row=dict(capture=str(capture),new_random=ordinal==0)
        try:
            if ordinal==0:row['fresh_selection']=portability(capture,selection)
            lower=extract(capture);upper=analyze(lower)
            # The analysis query needs T2 only, exactly as in the isolated worker.
            # Public validators remain enabled; do not repeatedly validate a
            # redundant nested T1 copy for every constituent/context query.
            result=study(strip_lower(upper),plan['max_edges']);write(directory/'study.json',result)
            row['source_fields']=check(capture,[{k:e[k] for k in ('id','pitch','onset_q','duration_q')} for e in lower['events']])
            row['source_ties']=check_tie_relations(capture,upper['written_ties']['links'],upper['written_ties']['unresolved'])
            row['source_declarations']=dict(status='PASS' if exact_fields(raw_declarations(capture),lower['tie_notation']) else 'FAIL')
            row['source_context']=source_queries(capture,upper,result)
            row['isolated_same_relations']=execute(code+wrapper,dict(upper=strip_lower(upper),max_edges=plan['max_edges']),dict(variation=0),dict(tier1=lower,study=result),directory/'isolated',timeout=240)
            row['part_outcomes']=[dict(part_id=r['part_id'],status=r['status'],candidates=len(r['candidate_origins']),unresolved=len(r['unresolved_declarations']),vectors=len(r['context']['membership']['feasible_membership_vectors']) if r['context'] and r['context']['membership'] else 0) for r in result['parts']]
            row['status']='PASS' if row['source_fields']['status']=='pass_declared_raw_source_fields' and row['source_ties']['status']=='pass_declared_written_tie_relations' and all(row[k]['status']=='PASS' for k in ('source_declarations','source_context','isolated_same_relations')) and (ordinal!=0 or row['fresh_selection']['status']=='PASS') else 'FAIL'
        except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
        write(directory/'result.json',row);results.append(row)
    unchanged=all(sha(Path(p))==digest for p,digest in frozen.items());report=dict(technical_status='PASS' if unchanged and all(r['status']=='PASS' for r in results) else 'FAIL',code_and_source_unchanged=unchanged,results=results,musical_acceptance='PENDING_PROJECTPLANNER_REVIEW; declared continuity/context only, not key or suspension truth')
    write(output/'result.json',report);print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('fresh',type=Path);p.add_argument('output',type=Path);p.add_argument('--regression',type=Path,action='append',default=[]);a=p.parse_args()
    raise SystemExit(0 if run(a.fresh,a.regression,a.output)['technical_status']=='PASS' else 1)
