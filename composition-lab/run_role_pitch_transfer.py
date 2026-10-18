"""Private controlled melody/bass experiment using selected role-pitch models."""
import argparse,hashlib,json,shutil
from pathlib import Path
from role_pitch_transfer import apply
from gp_author import write_gp

def run(baselines,composer_path,model_path,out):
    out.mkdir(parents=True,exist_ok=False);composer=json.loads(composer_path.read_text(encoding='utf-8'));model=json.loads(model_path.read_text(encoding='utf-8'))
    files=[Path(__file__),Path(__file__).with_name('role_pitch_transfer.py'),Path(__file__).with_name('role_pitch_model.py'),Path(__file__).with_name('gp_author.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files};records=[]
    for path in sorted(baselines.glob('*.expected.json')):
        ref=json.loads(path.read_text(encoding='utf-8'));roles=[t['name'] for t in ref['tracks']]
        for strength in (0,50,100):
            score,audit=apply(ref,roles,composer,model,strength)
            dst=out/f'{path.name.removesuffix(".expected.json")}-roles-{strength:03d}.gp'
            if strength==0:shutil.copyfile(path.with_name(path.name.removesuffix('.expected.json')+'.gp'),dst)
            else:write_gp(score,dst,title='Development-selected role-pitch experiment')
            dst.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8');dst.with_suffix('.control.json').write_text(json.dumps(audit),encoding='utf-8')
            records.append(dict(file=dst.name,strength=strength,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
                changed_melody=audit.get('units',{}).get('melody',{}).get('changed',0),changed_bass=audit.get('units',{}).get('bass',{}).get('changed',0)))
            print(json.dumps(records[-1]),flush=True)
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during generation')
    (out/'batch.json').write_text(json.dumps(dict(outputs=records,code_sha256=hashes,model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),musical_acceptance=False),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baselines','composer','model','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.baselines,a.composer,a.model,a.out)
