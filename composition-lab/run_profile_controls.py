"""Export real GP pitch-freedom ablations with exact remaining-dimension locks."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
from generation_freedom import mix,validate,facets
from profile_controls import locked_context,propose
from gp_author import write_gp


def run(model,reference_path,out):
    out.mkdir(parents=True,exist_ok=False)
    reference=json.loads(reference_path.with_suffix('.expected.json').read_text(encoding='utf-8'))
    roles=['harmony','melody','bass'];context=locked_context(reference)
    failures=[]
    for seed in range(700,800):
        try:candidate=propose(model,context,roles,seed);break
        except ValueError as exc:failures.append(dict(seed=seed,reason=str(exc)))
    else:raise ValueError('No valid independent control proposal after explicit retries')
    perturbed=copy.deepcopy(reference);changed=False
    for t in perturbed['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:
                    if len(e['notes'])==1 and not changed:
                        n=e['notes'][0];step=1 if n['fret']<24 else -1;n['midi']+=step;n['fret']+=step;changed=True
    if not changed:raise ValueError('No isolated note available for independent reference perturbation test')
    validate(perturbed);assert locked_context(perturbed)==context
    assert propose(model,locked_context(perturbed),roles,seed)==candidate
    full=dict(harmony=100,melody=100,bass=100)
    assert mix(reference,candidate,full,roles)[0]==mix(perturbed,candidate,full,roles)[0]
    records=[]
    zero=out/'all-locked-000.gp';shutil.copyfile(reference_path,zero)
    zero.with_suffix('.expected.json').write_text(json.dumps(reference,separators=(',',':')),encoding='utf-8')
    assert zero.read_bytes()==reference_path.read_bytes()
    records.append(dict(file=zero.name,literal_byte_identity=True))
    for dimension in ('harmony','melody','bass'):
        for strength in (25,50,75,100):
            result,audit=mix(reference,candidate,{dimension:strength},roles)
            path=out/f'{dimension}-{strength:03d}.gp';write_gp(result,path,title=f'{dimension} freedom {strength}')
            path.with_suffix('.expected.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
            records.append(dict(file=path.name,audit=audit,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report=dict(schema='profile-freedom-batch-v1',proposal_seed=seed,outputs=records,rejected_proposals=failures,
        hidden_reference_pitch_invariance=True,zero_byte_identity=True,
        limitations=['Generated-core pitch controls only; general rhythm/form/instrumentation controls remain coupled and fail closed.',
            'All performance edits remain a separate layer; no authentic legato or musical-quality claim.'])
    (out/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(outputs=len(records),rejected_proposals=len(failures),zero_byte_identity=True,hidden_reference_pitch_invariance=True)))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('model','reference','out'):p.add_argument(n,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(json.loads(a.model.read_text(encoding='utf-8')),a.reference,a.out)
