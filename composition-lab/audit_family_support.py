"""Preregistered support accounting only; this never releases a constraint.

Counts are order-dependent set intersections, not a causal or musical verdict.
Inputs are the complete independently checked catalogs from the fixed trial.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from family_policy import admissible

STAGES=(('same_family',('part_id','instrument','member_pitch_classes')),
        ('same_duration',('duration_q',)),
        ('same_meter_position',('meter','metrical_offset_q')),
        ('same_overlap_uncertainty',('overlaps','execution_uncertainty')),
        ('same_neighbors',()))


def audit(trial,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private audit folder required')
    files=[trial/name/'catalog.json' for name in ('under-pressure','over-the-hills','satisfaction')]
    paths=files+[Path(__file__),Path(__file__).with_name('family_policy.py')]
    frozen={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    output.mkdir(parents=True)
    (output/'plan-before-counting.json').write_text(json.dumps(dict(inputs=frozen,stages=STAGES,
        restriction='Distinct source spacing vectors only; all source units; no new candidates, no changed policy, no target/seed selection',
        interpretation='Cumulative support intersections; pre-context physical checks do not authorize transfers'),indent=2),encoding='utf-8')
    reports=[]
    for path in files:
        catalog=json.loads(path.read_text(encoding='utf-8'));rows=[r for r in catalog['units'] if not r['refusal_reasons']]
        contexts={r['id']:json.loads(r['family_context_key']) for r in rows}
        neighbors={r['id']:json.loads(r['family_full_context_key'])[1] for r in rows}
        counts=Counter();targets={name:set() for name,_ in STAGES};physical=Counter();physical_targets=set();final_feasible=0
        for target in rows:
            a=contexts[target['id']]
            for donor in rows:
                if donor['id']==target['id'] or donor['realization']['intervals']==target['realization']['intervals']:continue
                b=contexts[donor['id']]
                if any(a[k]!=b[k] for k in STAGES[0][1]):continue
                value,reason=admissible(target,donor)
                physical[reason or 'ADMISSIBLE_WITHOUT_CONTEXT']+=1
                if reason is None:physical_targets.add(target['id'])
                accepted=True
                for name,fields in STAGES:
                    if name=='same_neighbors':accepted=accepted and neighbors[target['id']]==neighbors[donor['id']]
                    else:accepted=accepted and all(a[k]==b[k] for k in fields)
                    if not accepted:break
                    counts[name]+=1;targets[name].add(target['id'])
                    if name=='same_overlap_uncertainty' and reason is None:final_feasible+=1
        reports.append(dict(case=path.parent.name,eligible_units=len(rows),stages=[dict(stage=name,directed_distinct_spacing_links=counts[name],target_units=len(targets[name])) for name,_ in STAGES],
            pre_context_physical_reasons=dict(physical),pre_context_physically_admissible_targets=len(physical_targets),
            local_context_and_physical_links=final_feasible))
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in frozen.items())
    result=dict(status='PASS_SUPPORT_ACCOUNTING' if unchanged else 'FAIL_INPUT_CHANGED',unchanged=unchanged,cases=reports,
        scope='Diagnostic counts only; no additional option is approved or generated')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    print(json.dumps(audit(args.trial,args.output)))
