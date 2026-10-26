"""Preregister two fresh cases, then capture without analysis or substitutions."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import secrets


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(output,client_root,policy='incident_dependencies'):
    if policy not in ('incident_dependencies','joint_source_fingering','transposed_voicing_family'):raise ValueError('Declared frozen policy required')
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private folder required')
    root=Path(__file__).parent;excluded=set();origins=[]
    for path in (root/'local-artifacts').rglob('metadata.json'):
        try:
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            if type(data.get('songId'))is int:excluded.add(data['songId']);origins.append(str(path.resolve()))
        except (ValueError,UnicodeError):continue
    # Selected-but-failed captures must not become replacement candidates.
    for path in (root/'local-artifacts').rglob('selection.json'):
        try:
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            if type(data)is dict and type(data.get('selected_song_id'))is int:excluded.add(data['selected_song_id']);origins.append(str(path.resolve()))
        except (ValueError,UnicodeError):continue
    files=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list((client_root/'songsterr_dl').rglob('*.py'))
    manifest=dict(version=2,started_utc=datetime.now(timezone.utc).isoformat(),policy=policy,case_count=2,
        seeds=[secrets.randbits(64),secrets.randbits(64)],excluded_song_ids=sorted(excluded),exclusion_evidence_files=sorted(origins),
        sampling='Existing seed-selected letter search first100 IDs, uniform choice among previously uncaptured results; NOT uniform catalog. Two preregistered slots, never replacement after failure.',
        code_hashes={str(p.resolve()):sha(p) for p in sorted(files)},client_root=str(client_root.resolve()),
        selection='All units audited. First source-order supported alternative is demonstration, not quality selection; else first eligible target. All refusal/coincidence outcomes retained.',
        controls=dict(physical='Explicit 0/50/100 and separate locks for joint policy only',seeds=list(range(9427,9447)),strengths=[0,50,100],register_locked_zero=policy=='transposed_voicing_family',separate=[[100,0,0],[0,0,100]] if policy=='transposed_voicing_family' else [[100,0,0],[0,100,0],[0,0,100],[100,100,0]] if policy=='joint_source_fingering' else [[100,0],[0,100]]),
        gates='Complete source + detector parity; unconditional stripped exact-zero; independent full policy denominator/context/shape audit. Nonzero GP/audio only if supported change.')
    output.mkdir(parents=True);(output/'freeze.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');return manifest


def capture(output):
    from sample_reversible_qa_song import sample
    manifest=json.loads((output/'freeze.json').read_text(encoding='utf-8'))
    if any(sha(Path(p))!=h for p,h in manifest['code_hashes'].items()):raise ValueError('Logic changed after freeze')
    excluded=set(manifest['excluded_song_ids']);results=[]
    for i,seed in enumerate(manifest['seeds'],1):
        case=output/f'case-{i}'
        if case.exists():raise ValueError('No replay/overwrite of frozen case slots')
        try:
            result=sample(case,Path(manifest['client_root']),seed=seed,extra_excluded_ids=excluded)
        except Exception as error:
            result=json.loads((case/'selection.json').read_text(encoding='utf-8'));result['capture_error']=str(error)
        if result.get('selected_song_id'):excluded.add(result['selected_song_id'])
        results.append(result)
        print(json.dumps({k:result.get(k) for k in ('seed','query','status','selected_song_id','artist','title','tracks','capture_error')}),flush=True)
    (output/'capture-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    if any(sha(Path(p))!=h for p,h in manifest['code_hashes'].items()):raise ValueError('Logic changed during capture')
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','capture']);p.add_argument('output',type=Path);p.add_argument('--client-root',type=Path,default=Path('.local/songsterr-dl'));p.add_argument('--policy',choices=['incident_dependencies','joint_source_fingering','transposed_voicing_family'],default='incident_dependencies');args=p.parse_args()
    if args.action=='freeze':
        result=freeze(args.output,args.client_root,args.policy);print(json.dumps({k:result[k] for k in ('policy','case_count','seeds')}))
    else:capture(args.output)
