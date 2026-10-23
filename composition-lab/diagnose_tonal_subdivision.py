"""Research-only representation sensitivity; unchanged models, no retuning.

Subdivision changes emission count, predecessor features AND HMM transitions.
It is not a causal isolation of any one mechanism or a new source-score event.
"""
from copy import deepcopy
from fractions import Fraction as F
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
from ordered_tonal_factor import infer, public_observations

FIELDS={'id','mask','previous_mask','sequence','start_q','end_q'}


def check_rows(rows):
    seen=set();previous=None
    if type(rows) is not list or not rows:raise ValueError('Nonempty observations required')
    for row in rows:
        if set(row)!=FIELDS or type(row['id']) not in (str,int) or row['id'] in seen:raise ValueError('Invalid/duplicate observation identity')
        seen.add(row['id'])
        for k in ('start_q','end_q'):
            if type(row[k]) is not str or str(F(row[k]))!=row[k]:raise ValueError('Canonical rational clock required')
        if F(row['end_q'])<=F(row['start_q']):raise ValueError('Positive observation interval required')
        if type(row['mask']) is not int or not 0<=row['mask']<4096:raise ValueError('Typed PC mask required')
        if previous is not None and row['sequence']==previous['sequence']:
            if row['start_q']!=previous['end_q'] or row['previous_mask']!=previous['mask']:raise ValueError('Broken predecessor/time sequence')
        elif row['previous_mask'] is not None:raise ValueError('Hidden sequence-start predecessor')
        previous=row


def split(rows):
    check_rows(rows);halves=[];mapping=[]
    for i,row in enumerate(rows):
        midpoint=str((F(row['start_q'])+F(row['end_q']))/2)
        left=dict(row,id=f'subdivision:{i}:0',end_q=midpoint)
        right=dict(row,id=f'subdivision:{i}:1',start_q=midpoint,previous_mask=row['mask'])
        halves.extend((left,right));mapping.append(dict(parent_ref=row['id'],half_refs=[left['id'],right['id']]))
    check_rows(halves)
    return halves,mapping


def join(halves,mapping):
    check_rows(halves);index={r['id']:r for r in halves};used=[];rows=[];parents=set()
    for link in mapping:
        if set(link)!={'parent_ref','half_refs'} or type(link['parent_ref']) not in (int,str) or link['parent_ref'] in parents or len(link['half_refs'])!=2:raise ValueError('Invalid parent membership')
        parents.add(link['parent_ref']);a,b=[index[i] for i in link['half_refs']];used.extend(link['half_refs'])
        if a['mask']!=b['mask'] or a['sequence']!=b['sequence'] or a['end_q']!=b['start_q'] or b['previous_mask']!=a['mask']:raise ValueError('Split cells do not share continuous evidence')
        if F(a['end_q'])-F(a['start_q'])!=F(b['end_q'])-F(b['start_q']):raise ValueError('Not exact half subdivision')
        rows.append(dict(a,id=link['parent_ref'],end_q=b['end_q']))
    if used!=[r['id'] for r in halves]:raise ValueError('Missing/duplicate/reordered subdivision membership')
    check_rows(rows);return rows


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(base, subdivided, mapping, targets):
    left={r['observation_ref']:r for r in base};right={r['observation_ref']:r for r in subdivided}
    if len(left)!=len(base) or len(right)!=len(subdivided) or set(left)!={m['parent_ref'] for m in mapping} or set(right)!={i for m in mapping for i in m['half_refs']}:raise ValueError('Prediction denominator differs')
    cells=[];duration=F(0);sums=dict(baseline_nll=0.,average_half_nll=0.,averaged_posterior_nll=0.,tv=0.)
    for m in mapping:
        original=left[m['parent_ref']];a,b=[right[i] for i in m['half_refs']]
        if a['start_q']!=original['start_q'] or a['end_q']!=b['start_q'] or b['end_q']!=original['end_q']:raise ValueError('Prediction clocks differ')
        durations=[F(x['end_q'])-F(x['start_q']) for x in (a,b)];d=sum(durations)
        if durations[0]!=durations[1] or d<=0:raise ValueError('Prediction durations differ')
        probabilities=[x['posterior'] for x in (original,a,b)]
        if any(len(p)!=24 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in p) or abs(sum(p)-1)>1e-10 for p in probabilities):raise ValueError('Invalid model posterior')
        mean=[sum(float(w/d)*p[i] for w,p in zip(durations,probabilities[1:])) for i in range(24)]
        target=targets[m['parent_ref']]['target']['state']
        if type(target) is not int or not 0<=target<24:raise ValueError('Typed evaluation-only target required')
        loss=lambda p:-math.log(max(p[target],1e-300))
        values=dict(baseline_nll=loss(probabilities[0]),average_half_nll=sum(float(w/d)*loss(p) for w,p in zip(durations,probabilities[1:])),averaged_posterior_nll=loss(mean),tv=sum(abs(x-y) for x,y in zip(mean,probabilities[0]))/2)
        for k,v in values.items():sums[k]+=float(d)*v
        duration+=d
        maps=[max(range(24),key=lambda i:p[i]) for p in probabilities]
        average_map=max(range(24),key=lambda i:mean[i])
        cells.append(dict(parent_ref=m['parent_ref'],start_q=original['start_q'],end_q=original['end_q'],duration_q=str(d),baseline_posterior=probabilities[0],half_posteriors=probabilities[1:],averaged_posterior=mean,baseline_map=maps[0],half_maps=maps[1:],averaged_map=average_map,averaged_map_changed=average_map!=maps[0],either_half_map_changed=any(i!=maps[0] for i in maps[1:]),**values))
    return dict(duration_q=str(duration),parent_cells=len(cells),half_cells=len(subdivided),duration_weighted={k:v/float(duration) for k,v in sums.items()},averaged_map_changes=sum(r['averaged_map_changed'] for r in cells),either_half_map_changes=sum(r['either_half_map_changed'] for r in cells),maximum_tv=max(r['tv'] for r in cells),cells=cells)


def run(study,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private research output required')
    output.mkdir(parents=True)
    old=json.loads((study/'freeze.json').read_text());manifest_path=Path(next(p for p in old if p.endswith('manifest.json')));manifest=json.loads(manifest_path.read_text())
    selected=min((r for r in manifest['records'] if r['split']=='test'),key=lambda r:r['file'])
    files=list(study.glob('*.json'))+[Path(p) for p in old]+[Path(__file__),Path(__file__).with_name('test_diagnose_tonal_subdivision.py')]
    frozen={str(p.resolve()):sha(p) for p in files}
    for p,h in old.items():
        if sha(Path(p))!=h:raise ValueError('Original study seal differs')
    plan=dict(selected_piece=selected,rule='Lexicographically first fixed test filename, before prediction reads',frozen=frozen,model_kinds=['ordered','marginal'],primary='ordered',control='fixed marginal model',transformation='Every eligible source PC cell split into exact rational halves; no new source notes/attacks; all quarantines and sequence gaps retained',qualification='Changes count, predecessors and HMM transitions together; not isolated causal factor',scope='NC research only, no product deployment or full-source/tier musical gate claim')
    (output/'plan-before-inference.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
    piece=json.loads((manifest_path.parent/selected['file']).read_text());observed=public_observations(piece['rows']);split_rows,mapping=split(observed)
    if join(split_rows,mapping)!=observed:raise ValueError('Split/join source observation mismatch')
    supports={r['id']:r.get('active_note_refs',[]) for r in piece['rows']};support_map=[dict(parent_ref=m['parent_ref'],half_refs=m['half_refs'],unchanged_source_note_refs=supports[m['parent_ref']]) for m in mapping]
    (output/'split-observations.json').write_text(json.dumps(dict(observations=split_rows,mapping=mapping,source_support=support_map)),encoding='utf-8')
    targets={r['id']:r for r in piece['rows'] if not r['quarantine_reasons']};outcomes={}
    for kind in plan['model_kinds']:
        model=json.loads((study/(kind+'-research-model.json')).read_text());saved=json.loads((study/(kind+'-test.json')).read_text());expected=next(r['prediction'] for r in saved['predictions'] if r['piece']==piece['piece'])
        baseline=infer(model,observed)
        if [r['observation_ref'] for r in baseline['rows']]!=[r['observation_ref'] for r in expected['rows']]:raise ValueError('Baseline saved identity mismatch')
        maxerror=max(abs(a-b) for x,y in zip(baseline['rows'],expected['rows']) for a,b in zip(x['posterior'],y['posterior']))
        if maxerror>1e-12:raise ValueError('Saved baseline does not replay')
        divided=infer(model,split_rows);comparison=compare(baseline['rows'],divided['rows'],mapping,targets)
        comparison['baseline_replay_maximum_error']=maxerror
        (output/(kind+'-comparison.json')).write_text(json.dumps(comparison),encoding='utf-8')
        outcomes[kind]={k:v for k,v in comparison.items() if k!='cells'}
    unchanged=all(sha(Path(p))==h for p,h in frozen.items())
    import numpy
    report=dict(status='COMPLETED_FIXED_REPRESENTATION_TEST' if unchanged else 'FAIL_CHANGED',unchanged=unchanged,piece=piece['piece'],work=piece['work'],source_cells=len(piece['rows']),quarantined_cells=len(piece['rows'])-len(observed),exact_split_join=True,unchanged_note_support=True,models=outcomes,runtime=dict(python=platform.python_version(),numpy=numpy.__version__),limitations=['Changed emission count, predecessor features and transition count are not causally separated','Same nominal PC support/time, no new notes/attacks; this is not a changed score','Split/join proof is NOT complete-source musical-tier inversion','Previously inspected held-out-by-work research data; no guitar/mode/center accuracy claim'])
    (output/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=run(a.study,a.output);print(json.dumps(r));raise SystemExit(0 if r['unchanged'] else 1)
