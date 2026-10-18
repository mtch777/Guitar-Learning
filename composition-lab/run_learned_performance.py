"""Apply privately trained performance methods to NEW generated GP baselines."""
import argparse,hashlib,json,shutil
from pathlib import Path
from learned_performance import apply,FAMILIES
from exact_score import extract_score
from technique_analysis import analyze
from bend_analysis import bend_shape


def run(baselines,training,out,artist='Invent Animate'):
    out.mkdir(parents=True,exist_ok=False)
    model=json.loads((training/'model.json').read_text(encoding='utf-8'))
    shapes=json.loads((training/'shapes.json').read_text(encoding='utf-8'))
    files=[Path(__file__),Path(__file__).with_name('learned_performance.py'),Path(__file__).with_name('performance_opportunities.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files};records=[]
    for src in sorted(baselines.glob('*.gp')):
        for strength in (0,50,100):
            dst=out/f'{src.stem}-performance-{strength:03d}.gp'
            audit=apply(src,dst,model,shapes,artist,{f:strength for f in FAMILIES},seed=17)
            score=extract_score(dst);report=analyze(score)
            if any(t['hopo_warnings'] for t in report['tracks']):raise AssertionError('Malformed exported HOPO links')
            dst.with_suffix('.techniques.json').write_text(json.dumps(report),encoding='utf-8')
            curves=dict(tracks=[[[[ [bend_shape(n['note_xml']) for n in e['notes']] for e in v] for v in m['voices']] for m in t['measures']] for t in score['tracks']])
            dst.with_suffix('.curves.json').write_text(json.dumps(curves),encoding='utf-8')
            shutil.copyfile(src.with_suffix('.expected.json'),dst.with_suffix('.expected.json'))
            decisions=audit.get('decisions',[])
            summary={f:dict(opportunities=sum(d['family']==f and d['eligible'] for d in decisions),
                released=sum(d['family']==f and d['released'] for d in decisions),
                selected=sum(d['family']==f and d['released'] and d['proposed_selected'] for d in decisions)) for f in FAMILIES}
            dst.with_suffix('.performance.json').write_text(json.dumps(audit),encoding='utf-8')
            records.append(dict(file=dst.name,strength=strength,sha256=audit['sha256'],summary=summary,
                zero_identity=audit.get('byte_identity'),locked_xml_verified=audit['locked_xml_verified']))
            print(json.dumps(records[-1]),flush=True)
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during generation')
    result=dict(schema='learned-performance-batch-v1',outputs=records,code_sha256=hashes,
        model_sha256=hashlib.sha256((training/'model.json').read_bytes()).hexdigest(),musical_acceptance=False)
    (out/'batch.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baselines','training','out'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.baselines,a.training,a.out)
