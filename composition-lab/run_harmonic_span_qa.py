"""Private bounded harmonic-span study: source, SAME isolated relations, labels."""
import argparse
from fractions import Fraction as F
import hashlib
import json
import sys
import importlib
from pathlib import Path
from musical_tier2 import analyze, strip_lower, harmonic_span_evidence, candidates
from check_harmonic_span_source import check as check_harmonic
from qa_isolation_harness import execute


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')


def annotated_labels(annotation,upper,evidence,alignment):
    from music21 import converter
    score=converter.parse(str(annotation));offset=alignment['annotation_to_source_pc_offset']
    end=F(evidence['request']['end_q']);start=F(evidence['request']['start_q'])
    roman=list(score.recurse().getElementsByClass('RomanNumeral'))
    forms={kind:tuple(pattern) for kind,pattern in __import__('musical_tier2').THEORY_FORMS if kind in ('major','dominant-seventh','minor','diminished-seventh','half-diminished-seventh','diminished')}
    totals={name:dict(strict=F(0),fractional=F(0),total=F(0),covered=F(0),unknown=F(0)) for name in ('segmented','instantaneous_exact','all_optimal_consensus')};rows=[]
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']}
    from musical_tier2 import member_pitch
    for i,r in enumerate(roman):
        a=max(start,F(r.getOffsetInHierarchy(score)));b=min(end,F(roman[i+1].getOffsetInHierarchy(score)) if i+1<len(roman) else end)
        if b<=a:continue
        root=(r.root().pitchClass+offset)%12;formula=tuple(sorted({(p.pitchClass-r.root().pitchClass)%12 for p in r.pitches}));kind=next((k for k,v in forms.items() if v==formula),None)
        gold=(root,kind);rows.append(dict(start_q=str(a),end_q=str(b),reference_root_pc=root,reference_kind=kind,reference_formula=formula,outside_published_vocabulary=kind is None))
        segments=[(F(e['start_q']),F(e['end_q']),[(c['root_pc'],c['kind']) for c in e['candidates']]) for e in evidence['canonical_display_path']]
        baseline=[]
        for cell in evidence['minimal_cells']:
            pitches=[p for ref in cell['occurrence_refs'] if (p:=member_pitch(*index[ref])) is not None]
            baseline.append((F(cell['start_q']),F(cell['end_q']),[(c['root_pc'],c['kind']) for c in candidates(pitches) if c['kind'] in forms]))
        consensus=[(F(c['start_q']),F(c['end_q']),[(x['root_pc'],x['kind']) for x in c['candidate_labels']]+([None] if c['no_pitched_evidence_possibility'] else [])) for c in evidence['all_optimal_path_cell_consensus']]
        for name,spans in (('segmented',segments),('instantaneous_exact',baseline),('all_optimal_consensus',consensus)):
            for c,d,labels in spans:
                length=min(b,d)-max(a,c)
                if length<=0:continue
                total=totals[name];total['total']+=length
                if kind is not None:total['covered']+=length
                if not labels or None in labels:total['unknown']+=length
                if gold in labels:
                    total['fractional']+=length/F(len(labels))
                    if len(labels)==1:total['strict']+=length
    metrics={name:{**{k+'_q':str(v) for k,v in row.items()},'strict_all_duration_agreement':float(row['strict']/row['total']),'fractional_all_duration_agreement':float(row['fractional']/row['total'])} for name,row in totals.items()}
    return dict(metrics=metrics,reference_spans=rows,claim='Segmented is canonical display-path diagnostic only. Consensus unions labels from ALL globally optimal covering edges plus no-evidence option; strict credit only for one correct alternative, fractional credit1/alternative_count is not probability. No path selected by gold')


def isolated(code,upper,lower,request,evidence,directory):
    # Adapter changes ONLY the QA return envelope. Actual analysis and inverse
    # functions remain the same code; no source or expected output is staged.
    wrapper="""
_exact_reconstruct = reconstruct
def reconstruct(package, controls):
    if set(package)!={'musical_tier2','harmonic_request'}:raise ValueError('Declared musical input plus query metadata required')
    upper=package['musical_tier2']
    return {'tier1':_exact_reconstruct(upper,controls),
            'harmonic':harmonic_span_evidence(upper,**package['harmonic_request'])}
"""
    package=dict(musical_tier2=strip_lower(upper),harmonic_request=request)
    return execute(code+wrapper,package,dict(variation=0),dict(tier1=lower,harmonic=evidence),directory,timeout=120)


def run(selection,alignment_path,fresh,requests_path,output):
    from music21 import corpus
    from musicxml_context_tier1 import extract as xml_extract
    from check_musicxml_context_source import raw_notes,check as xml_check
    from source_key_tier1 import extract as source_extract
    from check_reversible_source import source_expectation,check as source_check
    from three_gate_qa import portability
    output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent;code=(root/'musical_tier2.py').read_text(encoding='utf-8')
    selected=json.loads(selection.read_text(encoding='utf-8'));alignments=json.loads(alignment_path.read_text(encoding='utf-8'));results=[]
    # Load retained extraction dependencies before sealing any musical operation.
    sys.path.insert(0,str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics');importlib.import_module('analyze_relationships')
    sources=[selection,alignment_path,requests_path,requests_path.parent/'selection.json']+list(fresh.glob('*.json'))
    for item in selected['selected']:sources.extend([Path(item['score']),Path(corpus.getWork('bach/choraleAnalyses/'+item['name']))])
    sources=sorted({p.resolve() for p in sources})
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root.resolve() in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    frozen=dict(code={str(p.relative_to(root.resolve())):sha(p) for p in modules},source={str(p):sha(p) for p in sources},scope='All preloaded transitive local Python modules and complete declared source/plans; not OS/native-package isolation')
    write(output/'freeze.json',frozen)
    for module in modules:
        snapshot=output/'frozen-code'/module.relative_to(root.resolve());snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_bytes(module.read_bytes())
    for item in selected['selected']:
        directory=output/item['name'].split('.')[0];directory.mkdir();row=dict(case=item['name'])
        try:
            source=Path(item['score']);annotation=Path(corpus.getWork('bach/choraleAnalyses/'+item['name']))
            if sha(source)!=item['score_sha256'] or sha(annotation)!=item['sha256']:raise ValueError('Frozen reference/source changed')
            lower=xml_extract(source);row['source_oracle']=xml_check(source,lower);upper=analyze(lower);raw,_=raw_notes(source)
            end=lower['source_key_inventory'][0]['end_q'];request=dict(start_q='0',end_q=end,part_id=None,max_edges=50000)
            evidence=harmonic_span_evidence(upper,**request);write(directory/'harmonic.json',evidence)
            row['source_harmonic_oracle']=check_harmonic(raw,evidence)
            row['isolated_same_relations']=isolated(code,upper,lower,request,evidence,directory/'isolated')
            alignment=next(a for a in alignments['references'] if a['reference']==item['name'])
            row['annotated_evaluation']=annotated_labels(annotation,upper,evidence,alignment)
            row['status']='PASS' if all(row[k]['status']=='PASS' for k in ('source_oracle','source_harmonic_oracle','isolated_same_relations')) else 'FAIL'
        except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
        write(directory/'result.json',row);results.append(row)
    directory=output/'new-random-song';directory.mkdir();row=dict(case='new-random-Songsterr')
    try:
        row['fresh_selection']=portability(fresh,requests_path.parent/'selection.json')
        lower=source_extract(fresh);row['source_oracle']=source_check(fresh,[{k:e[k] for k in ('id','pitch','onset_q','duration_q')} for e in lower['events']]);upper=analyze(lower)
        expected,_=source_expectation(fresh);raw=[(int(i.split(':')[2]),int(i.split(':')[3]),v['pitch'],v['onset_q'],v['duration_q']) for i,v in expected.items()]
        requests=json.loads(requests_path.read_text(encoding='utf-8'))['requests'];row['requests']=[]
        for i,request in enumerate(requests):
            evidence=harmonic_span_evidence(upper,**request);write(directory/f'harmonic-{i}.json',evidence)
            row['requests'].append(dict(request=request,analytical_status=evidence['status'],source_harmonic_oracle=check_harmonic(raw,evidence),isolated_same_relations=isolated(code,upper,lower,request,evidence,directory/f'isolated-{i}')))
        row['status']='PASS' if row['fresh_selection']['status']=='PASS' and row['source_oracle']['status']=='pass_declared_raw_source_fields' and all(r['source_harmonic_oracle']['status']=='PASS' and r['isolated_same_relations']['status']=='PASS' for r in row['requests']) else 'FAIL'
    except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
    write(directory/'result.json',row);results.append(row)
    unchanged=all(sha(p)==frozen['code'][str(p.relative_to(root.resolve()))] for p in modules)
    source_unchanged=all(sha(p)==frozen['source'][str(p)] for p in sources)
    result=dict(technical_status='PASS' if unchanged and source_unchanged and all(r['status']=='PASS' for r in results) else 'FAIL',code_unchanged=unchanged,source_unchanged=source_unchanged,results=results,musical_acceptance='PENDING_PROJECTPLANNER_REVIEW_NOT_INFERRED_FROM_OPTIMAL_SEARCH')
    write(output/'result.json',result)
    print(json.dumps([dict(case=r['case'],status=r['status'],error=r.get('error'),metrics=r.get('annotated_evaluation',{}).get('metrics')) for r in results],indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('selection',type=Path);p.add_argument('alignment',type=Path);p.add_argument('fresh',type=Path);p.add_argument('requests',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    raise SystemExit(0 if run(a.selection,a.alignment,a.fresh,a.requests,a.output)['technical_status']=='PASS' else 1)
