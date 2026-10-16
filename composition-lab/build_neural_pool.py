"""Cache sampled phrase content for reproducible full-length engine experiments."""
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from benchmarks.learned_organization import load_model,generate
from learned_phrase_adapter import decode
from benchmarks.yinyang_official_test import tokenize
from structural_learning import phrase_features


def main():
    import torch
    p=argparse.ArgumentParser();p.add_argument('--models',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--count',type=int,default=128)
    args=p.parse_args()
    if args.out.exists():raise FileExistsError('Preserve old pool')
    torch.set_num_threads(2);vocab=json.loads((args.models/'tokenizer.json').read_text());model=load_model(args.models/'phrase_generation')
    records=[r for r in json.loads(args.corpus.read_text(encoding='utf-8')) if r['split']=='train' and r['melody']['metadata']['time_signature']=='TimeSig_4/4']
    track=dict(tunings=[[64,59,55,50,45,40]],program=30);pool=[];rejected=[]
    for i in range(args.count):
        record=records[i%len(records)]
        try:
            context=tokenize(record['melody']['phrases']['0'][0],'TimeSig_4/4',vocab)
            raw,score=generate(model,context,vocab,track,1700+i)
            notes=decode(raw)
            phrase=[[[n['bar'],float(n['position']),0,n['pitch'],float(n['duration']),91] for n in notes]]
            pool.append(dict(id=i,conditioning_group=record['group'],seed=1700+i,tokens=raw,
                notes=[{**n,'position':str(n['position']),'duration':str(n['duration'])} for n in notes],features=phrase_features(phrase)))
        except ValueError as e:rejected.append(dict(id=i,error=str(e)))
        if i%16==15:print('pool',i+1,'accepted',len(pool),flush=True)
    args.out.write_text(json.dumps(dict(pool=pool,rejected=rejected,source='official pretrained Yin-Yang; only grouped-training contexts; no source notes in sampled output',
        limitations=['two-bar 4/4 constrained phrases','folk-domain pretraining','cached vocabulary can limit diversity']),indent=2),encoding='utf-8')


if __name__=='__main__':main()
