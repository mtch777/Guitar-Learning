"""Freeze the three previously declared development inputs before counting."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import zipfile

CASES=((17042,8385538,'execution-dependency-fresh-v1/case-1/capture'),
       (11714,9188861,'execution-dependency-fresh-v1/case-2/capture'),
       (16453,7421771,'audible-tier2-fresh-v1/capture'))


def freeze(output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private experiment folder required')
    root=Path(__file__).resolve().parent;cases=[]
    for sid,revision,relative in CASES:
        path=root/'local-artifacts'/relative;meta=json.loads((path/'metadata.json').read_text(encoding='utf-8-sig'))
        if (meta['songId'],meta['revisionId'])!=(sid,revision):raise ValueError('Preregistered capture identity conflict')
        files=sorted(path.glob('*.json'))
        cases.append(dict(song_id=sid,revision=revision,capture=str(path.resolve()),files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    files=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))+list((root.parent/'.local/songsterr-dl/songsterr_dl').rglob('*.py'))
    manifest=dict(version=1,started_utc=datetime.now(timezone.utc).isoformat(),study_kind='DEVELOPMENT_PREDECLARED_FAMILIES',policy='transposed_voicing_family',
        cases=cases,code_hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
        source_snapshot='frozen-code.zip is archived checker/replay code, NEVER an inverse data source',
        controls=dict(seeds=list(range(9427,9447)),joint=[[0,0,0],[50,0,50],[100,0,100]],separate=[[100,0,0],[0,0,100]]),
        selection='ALL units/options/refusals audited; first source-order supported alternative; fixed draws; no adaptive source/seed/context replacement',
        constraints='Same whole translated source shape, all active PC-context normalized, bass0, original member identities/PCs/timing/expression/dependency locks; preserve source open status')
    output.mkdir(parents=True)
    with zipfile.ZipFile(output/'frozen-code.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for i,p in enumerate(sorted(files)):archive.writestr(f'{i:04d}-{p.name}',p.read_bytes())
    (output/'freeze.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args();r=freeze(args.output)
    print(json.dumps(dict(cases=[c['song_id'] for c in r['cases']],code_files=len(r['code_hashes']))))
