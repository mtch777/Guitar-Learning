"""Private MIDI-program/global-tempo control exports with pitch/time locks."""
import argparse,hashlib,json,shutil
from pathlib import Path
from metadata_controls import apply
from gp_author import write_gp

def run(baselines,model_path,out):
    out.mkdir(parents=True,exist_ok=False);model=json.loads(model_path.read_text(encoding='utf-8'));records=[]
    files=[Path(__file__),Path(__file__).with_name('metadata_controls.py'),Path(__file__).with_name('gp_author.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    cases=[('locked',{}),('programs-050',dict(programs=50)),('programs-100',dict(programs=100)),
           ('tempo-050',dict(tempo=50)),('tempo-100',dict(tempo=100)),('both-100',dict(programs=100,tempo=100))]
    for src in sorted(baselines.glob('*.expected.json')):
        reference=json.loads(src.read_text(encoding='utf-8'));roles=[t['name'] for t in reference['tracks']]
        for label,freedom in cases:
            score,audit=apply(reference,roles,model,freedom);dst=out/f'{src.name.removesuffix(".expected.json")}-{label}.gp'
            if not freedom:shutil.copyfile(src.with_name(src.name.removesuffix('.expected.json')+'.gp'),dst)
            else:write_gp(score,dst,title='Empirical program/tempo control')
            dst.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8');dst.with_suffix('.control.json').write_text(json.dumps(audit),encoding='utf-8')
            records.append(dict(file=dst.name,case=label,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),
                changed=sum(d['changed'] for d in audit.get('decisions',[]))))
            print(json.dumps(records[-1]),flush=True)
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during export')
    (out/'batch.json').write_text(json.dumps(dict(outputs=records,code_sha256=hashes,musical_acceptance=False),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baselines','model','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.baselines,a.model,a.out)
