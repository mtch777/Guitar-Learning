"""Private empirical generation batch, deterministic retries and manifests."""
import argparse,hashlib,json
from pathlib import Path
from corpus_composer import learn,generate
from gp_author import write_gp


def run(report,corpus,out,artist,count=12,bars=32):
    out.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),Path(__file__).with_name('corpus_composer.py'),Path(__file__).with_name('gp_author.py')]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    model=learn(report,corpus,artist)
    (out/'model.json').write_text(json.dumps(model,separators=(',',':')),encoding='utf-8')
    records=[];failed=[]
    for index in range(count):
        for retry in range(40):
            seed=10000+index*100+retry
            try:score,plan=generate(model,bars,seed)
            except ValueError as exc:
                failed.append(dict(piece=index+1,seed=seed,reason=str(exc)));continue
            path=out/f'piece-{index+1:03d}.gp'
            write_gp(score,path,title=f'Empirical corpus experiment {index+1}')
            path.with_suffix('.expected.json').write_text(json.dumps(score,separators=(',',':')),encoding='utf-8')
            path.with_suffix('.plan.json').write_text(json.dumps(plan,separators=(',',':')),encoding='utf-8')
            records.append(dict(file=path.name,seed=seed,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bars=bars))
            print('Generated',path.name,'seed',seed,flush=True);break
        else:raise ValueError('No valid output after explicit retry budget; inspect failed proposals')
    result=dict(schema='empirical-composer-batch-v1',artist=artist,outputs=records,rejected_proposals=failed,
        code_sha256=hashes,
        training_songs=model['training_songs'],excluded_training_bars=model['excluded'],limitations=model['limitations'],
        musical_acceptance=False)
    assert hashes=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'Code changed during batch; unsealed'
    (out/'batch.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('report','corpus','out'):p.add_argument(n,type=Path)
    p.add_argument('--artist',default='Invent Animate');p.add_argument('--count',type=int,default=12);p.add_argument('--bars',type=int,default=32)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private artifacts only')
    run(json.loads(a.report.read_text(encoding='utf-8')),a.corpus,a.out,a.artist,a.count,a.bars)
