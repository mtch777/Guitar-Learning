"""Private nested-family model selection and outer held-out diagnostics."""
import argparse,hashlib,json
from copy import deepcopy
from pathlib import Path
from artist_profiles import connected_families,stable_hash
from corpus_composer import learn
from role_pitch_model import observations,select,evaluate

def run(composer_path,report_path,corpus,out):
    out.mkdir(parents=True,exist_ok=False)
    files=[Path(__file__),Path(__file__).with_name('role_pitch_model.py'),Path(__file__).with_name('corpus_composer.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    composer=json.loads(composer_path.read_text(encoding='utf-8'));train=observations(composer);model=select(train);model['artist']=composer['artist']
    model['source_composer_sha256']=stable_hash(composer)
    report=json.loads(report_path.read_text(encoding='utf-8'));connected_families(report['songs'])
    report['songs']=[s for s in report['songs'] if s['provisional_partition']=='held_out']
    for song in report['songs']:song['provisional_partition']='development'
    held=observations(learn(report,corpus,composer['artist']));results=evaluate(model,held)
    for name,value in [('model',model),('evaluation',results)]:
        (out/(name+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}:raise AssertionError('Code changed during fit')
    (out/'fit.json').write_text(json.dumps(dict(code_sha256=hashes,training_events=len(train),outer_heldout_events=len(held),
        limitations=['Heuristic track roles and minimum written pitches, not intended harmonic roots.',
            'Previous pitch is teacher-forced within a bar; generated rollout quality is not measured.',
            'Outer set has already served prior method diagnostics; no claim of pristine confirmatory testing.']),indent=2),encoding='utf-8')
    print(json.dumps(dict(weights=model['weights'],evaluation=results)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('composer','report','corpus','out'):p.add_argument(n,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private model only')
    run(a.composer,a.report,a.corpus,a.out)
