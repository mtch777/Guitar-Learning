"""Reproducible private fit/evaluation of source-eligible performance methods."""
import argparse,hashlib,json
from pathlib import Path
from performance_opportunities import train
from learned_performance import learn_shapes
from artist_profiles import evaluate

def run(report_path,out,artist):
    out.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__),Path(__file__).with_name('performance_opportunities.py'),Path(__file__).with_name('learned_performance.py'),Path(__file__).with_name('artist_profiles.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    report=json.loads(report_path.read_text(encoding='utf-8'));model,events=train(report);shapes=learn_shapes(report,artist)
    evaluation=evaluate(model,events)
    for name,value in [('model',model),('shapes',shapes),('evaluation',evaluation)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Training code changed during run')
    manifest=dict(schema='performance-profile-fit-v1',code_sha256=hashes,source_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(),
        training_events=model['training_events'],training_songs=model['training_songs'],
        compatible_raw_templates=sum(len(v) for f in shapes['families'].values() for v in f.values()),excluded_shapes=shapes['excluded'],
        interpretation='Annotation prediction, not expressive intent or musical quality. No held-out tuning/promotion.')
    (out/'fit.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps(manifest))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('report','out'):p.add_argument(name,type=Path)
    p.add_argument('--artist',default='Invent Animate');a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    run(a.report,a.out,a.artist)
