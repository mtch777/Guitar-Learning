"""Frozen conditional collection-coordinate QA; no selected true-key claim."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import sys
from musical_tier2 import analyze,strip_lower,collection_motion_context,collection_degree_relation
from qa_isolation_harness import execute


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')


def study(upper,tolerance):
    import math
    scope=next(s for s in upper['tonal_evidence']['scopes'] if s['id']=='song-pooled')
    candidates=[c for c in scope['candidates'] if c['family']=='KrumhanslSchmuckler' and c['score'] is not None and math.isfinite(c['score'])]
    maximum=max((c['score'] for c in candidates),default=None)
    winners=[c for c in candidates if maximum-c['score']<=tolerance]
    index={m['id']:(g,m) for g in upper['coattacks'] for m in g['members']};sequences=[]
    for part in range(upper['source_quality']['tracks']):
        voices=sorted({m['voice'] for g in upper['coattacks'] if g['part_id']==part for m in g['members']})
        if not voices:sequences.append(dict(part_id=part,voice=None,owned_occurrences=0,occurrence_refs=[],contexts=[],status='NO_OWNED_NOTE_OCCURRENCES_IN_PART'));continue
        for voice in voices:
            refs=sorted((i for i,(g,m) in index.items() if g['part_id']==part and m['voice']==voice),key=lambda i:tuple(index[i][1][k] for k in ('bar','beat','note')))
            sequences.append(dict(part_id=part,voice=voice,owned_occurrences=len(refs),occurrence_refs=refs[:3],contexts=[],status='FEWER_THAN_THREE_RETAINED' if len(refs)<3 else 'NO_UNIQUE_MODEL_QUERY_REFERENCE'))
    result=dict(query_reference=None,numerically_tied_maxima=[dict(candidate_ref=c['id'],score=c['score'],tonic_pc=c['tonic_pc'],quality=c['quality']) for c in winners],tolerance=tolerance,sequences=sequences,
                scope='Owned note-bearing voices plus all part inventory; empty raw voice/rest topology outside T1 scope',claim='Highest KS candidate selects query reference ONLY, never established key or mode')
    if len(winners)!=1:return result
    reference=winners[0];parallel=[c for c in candidates if c['tonic_pc']==reference['tonic_pc']]
    result['query_reference']=dict(candidate_ref=reference['id'],score=reference['score'],tonic_pc=reference['tonic_pc'],quality=reference['quality'],parallel_candidates=[dict(candidate_ref=c['id'],score=c['score'],quality=c['quality'],reference_collection=c['reference_collection']) for c in parallel])
    for sequence in sequences:
        if len(sequence['occurrence_refs'])!=3:continue
        for c in parallel:
            context=collection_motion_context(upper,sequence['occurrence_refs'],c['id']);inverses=[]
            for note in context['note_contexts']:
                coordinate=note['interval_of_note_base_key_candidate']
                if coordinate is not None and coordinate['reference_collection_degree'] is not None:
                    pitch=collection_degree_relation(c['tonic_pc'],c['reference_intervals'],degree=coordinate['reference_collection_degree'],relative_octaves=coordinate['relative_octaves'])['pitch']
                    inverses.append(dict(occurrence_ref=note['occurrence_ref'],pitch=pitch))
            sequence['contexts'].append(dict(context=context,mapped_degree_inverses=inverses))
        sequence['status']='CONDITIONAL_REFERENCE_COORDINATES'
    return result


def reference_selection_issues(scope,result,tolerance):
    """Independent ranking/metadata check; not a key-adjudication oracle."""
    import math
    issues=[];pool=[]
    for candidate in scope['candidates']:
        if candidate['family']=='KrumhanslSchmuckler' and candidate['score'] is not None and math.isfinite(candidate['score']):pool.append(candidate)
    highest=max([c['score'] for c in pool],default=None)
    ties=[c for c in pool if abs(c['score']-highest)<=tolerance]
    expected=[dict(candidate_ref=c['id'],score=c['score'],tonic_pc=c['tonic_pc'],quality=c['quality']) for c in ties]
    if result['tolerance']!=tolerance or result['numerically_tied_maxima']!=expected:issues.append('Frozen tolerance or tied model-reference inventory differs')
    if len(ties)!=1:
        if result['query_reference'] is not None:issues.append('Arbitrary model reference selected from tied/undefined scores')
    else:
        c=ties[0];parallel=[p for p in pool if p['tonic_pc']==c['tonic_pc']]
        reference=dict(candidate_ref=c['id'],score=c['score'],tonic_pc=c['tonic_pc'],quality=c['quality'],parallel_candidates=[dict(candidate_ref=p['id'],score=p['score'],quality=p['quality'],reference_collection=p['reference_collection']) for p in parallel])
        if result['query_reference']!=reference:issues.append('Unique model query reference or parallel candidates differ')
    return issues


def source_check(capture,upper,result,tolerance):
    from check_reversible_source import source_expectation
    from check_collection_degrees import check
    raw,_=source_expectation(capture);errors=[];oracles=[]
    expected=[]
    for part in range(upper['source_quality']['tracks']):
        voices=sorted({int(i.split(':')[4]) for i in raw if int(i.split(':')[2])==part})
        if not voices:expected.append((part,None,[],0));continue
        for voice in voices:
            refs=[i for i in raw if int(i.split(':')[2])==part and int(i.split(':')[4])==voice]
            expected.append((part,voice,refs[:3],len(refs)))
    actual=[(r['part_id'],r['voice'],r['occurrence_refs'],r['owned_occurrences']) for r in result['sequences']]
    if actual!=expected:errors.append('Raw owned part/voice/first-three denominator differs')
    scope=next(s for s in upper['tonal_evidence']['scopes'] if s['id']=='song-pooled');byid={c['id']:c for c in scope['candidates']}
    errors.extend(reference_selection_issues(scope,result,tolerance))
    for row in result['sequences']:
        if result['query_reference'] is not None and len(row['occurrence_refs'])==3 and len(row['contexts'])!=2:errors.append('Missing parallel reference context')
        expected_ids={c['candidate_ref'] for c in result['query_reference']['parallel_candidates']} if result['query_reference'] is not None and len(row['occurrence_refs'])==3 else set()
        actual_ids=[r['context']['candidate_ref'] for r in row['contexts']]
        if len(actual_ids)!=len(expected_ids) or set(actual_ids)!=expected_ids:errors.append('Duplicate or missing reference candidate')
        for record in row['contexts']:
            context=record['context']
            if context['source_motion']['occurrence_refs']!=row['occurrence_refs']:errors.append('Source sequence replaced')
            oracles.append(check(raw,context,byid[context['candidate_ref']],record['mapped_degree_inverses']))
    return dict(status='PASS' if not errors and all(o['status']=='PASS' for o in oracles) else 'FAIL',errors=errors,source_reference_oracles=oracles,scope='Independent raw occurrence denominator + native mapped/unmapped degrees and pitch reconstruction; not key or melodic-function accuracy')


def run(fresh,output):
    import music21
    from source_tie_tier1 import extract
    from check_reversible_source import check
    from check_collection_degrees import equations,native_reference
    from check_tonal_profiles import check as tonal_check
    from three_gate_qa import portability
    root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'songsterr_automation/songsterr_api'))
    importlib.import_module('source_semantics');importlib.import_module('analyze_relationships')
    capture=fresh/'capture';selection=fresh/'selection.json';plan_path=fresh/'collection-plan.json';plan=json.loads(plan_path.read_text(encoding='utf-8'))
    if sha(selection)!=plan['selection_sha256']:raise ValueError('Frozen selection changed')
    output.mkdir(parents=True,exist_ok=False)
    modules=sorted({Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).suffix=='.py' and root in Path(m.__file__).resolve().parents and 'local-artifacts' not in Path(m.__file__).parts}|{Path(__file__).resolve()})
    frozen={str(p):sha(p) for p in modules+[selection,plan_path]+list(capture.glob('*.json'))};write(output/'freeze.json',frozen)
    for module in modules:
        target=output/'frozen-code'/module.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(module.read_bytes())
    oracle_version=dict(music21=music21.__version__,native_scale_source_sha256=sha(Path(inspect.getfile(music21.scale))),explicit_minor='music21.scale.MinorScale natural minor',comparison_attribute='pitchClass_no_source_spelling_claim');write(output/'native-oracle.json',oracle_version)
    native=equations();selection_result=portability(capture,selection);lower=extract(capture);upper=analyze(lower);result=study(strip_lower(upper),plan['ks_maximum_tie_tolerance']);write(output/'study.json',result)
    raw=check(capture,[{k:e[k] for k in ('id','pitch','onset_q','duration_q')} for e in lower['events']]);source=source_check(capture,upper,result,plan['ks_maximum_tie_tolerance']);tonal=tonal_check(capture,upper)
    code=(root/'musical_tier2.py').read_text(encoding='utf-8');wrapper='\n'+inspect.getsource(study)+'''
_exact_reconstruct=reconstruct
def reconstruct(package,controls):
    if set(package)!={'upper','tolerance'}:raise ValueError('Declared query tolerance only')
    return dict(tier1=_exact_reconstruct(package['upper'],controls),study=study(package['upper'],package['tolerance']))
'''
    isolated=execute(code+wrapper,dict(upper=strip_lower(upper),tolerance=plan['ks_maximum_tie_tolerance']),dict(variation=0),dict(tier1=lower,study=result),output/'isolated',timeout=240)
    unchanged=all(sha(Path(p))==digest for p,digest in frozen.items())
    report=dict(technical_status='PASS' if unchanged and raw['status']=='pass_declared_raw_source_fields' and all(r['status']=='PASS' for r in (native,selection_result,source,tonal,isolated)) else 'FAIL',code_and_source_unchanged=unchanged,native_equation_oracle=native,fresh_selection=selection_result,raw_source_oracle=raw,tonal_profile_source_oracle=tonal,reference_context_source_oracle=source,isolated_same_relations=isolated,query_reference=result['query_reference'],sequence_outcomes=dict(Counter(r['status'] for r in result['sequences'])),musical_acceptance='PENDING_PROJECTPLANNER_REVIEW; mapped reference coordinate equation exact, unmapped notes retain existing exact realization; no inferred key/style claim')
    write(output/'result.json',report);print(json.dumps(report,indent=2));return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('fresh',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    raise SystemExit(0 if run(a.fresh,a.output)['technical_status']=='PASS' else 1)
