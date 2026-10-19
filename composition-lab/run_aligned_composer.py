"""Private aligned-role-pattern experiment from an already fitted source model.

Preserve the independent-role baseline. This changes sampled rhythmic/voicing
configurations and downstream pitches together; it is not a pitch-locked ablation.
"""
import argparse,hashlib,json
from pathlib import Path
from corpus_composer import generate
from gp_author import write_gp


def run(model_path,out,count=12,bars=32):
    if isinstance(count,bool) or not isinstance(count,int) or count<1:raise ValueError('Positive count required')
    out.mkdir(parents=True,exist_ok=False)
    model=json.loads(model_path.read_text(encoding='utf-8'))
    if model.get('schema')!='empirical-corpus-composer-v1':raise ValueError('Fitted corpus composer required')
    code=[Path(__file__),Path(__file__).with_name('corpus_composer.py'),Path(__file__).with_name('gp_author.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code}
    records=[];failures=[]
    for i in range(count):
        for retry in range(40):
            seed=10000+i*100+retry
            try:score,plan=generate(model,bars,seed,aligned_patterns=True)
            except ValueError as exc:
                failures.append(dict(piece=i+1,seed=seed,reason=str(exc)));continue
            # Every newly synthesized recurrence cell must use one observed
            # source bar jointly across all three roles, with no cross-song mix.
            cells={}
            for row in plan['sources']:
                cells.setdefault(row['bar'],set()).add((row['training_song'],row['training_bar']))
            if any(len(v)!=1 for v in cells.values()):raise AssertionError('Cross-role source mismatch')
            dst=out/f'piece-{i+1:03d}-aligned.gp';write_gp(score,dst,title=f'Aligned role-pattern experiment {i+1}')
            dst.with_suffix('.expected.json').write_text(json.dumps(score),encoding='utf-8')
            dst.with_suffix('.plan.json').write_text(json.dumps(plan),encoding='utf-8')
            records.append(dict(file=dst.name,seed=seed,sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),bars=bars,
                aligned_new_cells=len(cells)))
            break
        else:raise ValueError('Explicit retry budget exhausted')
    if hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code}:raise AssertionError('Code changed during run')
    result=dict(schema='aligned-role-pattern-experiment-v1',outputs=records,rejected_proposals=failures,
        model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),code_sha256=hashes,
        limitations=['Same source bar for three role rhythms/voicing intervals; generated pitches remain statistical proposals.',
            'Not a pitch-locked ablation; aligned patterns can change subsequent random draws and fingering opportunities.',
            'Main voice, fixed meter, clean-bar support restrictions remain.',
            'Technical validity and annotation matching do not establish musical quality.'],musical_acceptance=False)
    (out/'batch.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('model',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--count',type=int,default=12);p.add_argument('--bars',type=int,default=32);a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private output only')
    print(json.dumps(run(a.model,a.out,a.count,a.bars),indent=2))
