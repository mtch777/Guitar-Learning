"""Private source-fitted rhythm experiment with all pitch dimensions locked."""
import argparse,hashlib,json
from pathlib import Path
from rhythm_controls import apply
from gp_author import write_gp

def run(baselines,model_path,out):
    out.mkdir(parents=True,exist_ok=False);model=json.loads(model_path.read_text(encoding='utf-8'));records=[]
    files=[Path(__file__),Path(__file__).with_name('rhythm_controls.py'),Path(__file__).with_name('gp_author.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    for src in sorted(baselines.glob('*.expected.json')):
        reference=json.loads(src.read_text(encoding='utf-8'));roles=[t['name'] for t in reference['tracks']]
        for strength in (0,25,50,75,100):
            score,audit=apply(reference,model,roles,strength)
            dst=out/f'{src.name.removesuffix(".expected.json")}-rhythm-{strength:03d}.gp'
            if strength==0:
                import shutil
                shutil.copyfile(src.with_name(src.name.removesuffix('.expected.json')+'.gp'),dst)
            else:write_gp(score,dst,title='Source-fitted rhythm freedom experiment')
            dst.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
            dst.with_suffix('.control.json').write_text(json.dumps(audit),encoding='utf-8')
            records.append(dict(file=dst.name,strength=strength,changed_units=sum(d['changed'] for d in audit.get('units',[])),
                released_units=sum(d['released'] for d in audit.get('units',[])),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
            print(json.dumps(records[-1]),flush=True)
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during export')
    (out/'batch.json').write_text(json.dumps(dict(outputs=records,code_sha256=hashes,musical_acceptance=False),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('baselines','model','out'):p.add_argument(n,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private artifacts only')
    run(a.baselines,a.model,a.out)
