"""Exact descriptive decomposition on shared known notation contexts.

This is an accounting identity, not a causal attribution or a style score.
Unsupported context mass is reported separately, never assigned an invented rate.
"""
from fractions import Fraction as F
from collections import defaultdict
from pathlib import Path
import argparse,json
from exact_score import extract_score
from validate_artist_annotations import generated,FEATURES


def decompose(source,target):
    # context -> (known weight, positive weight). Zero-positive is observed zero.
    for table in (source,target):
        if any(F(n)<0 or F(y)<0 or F(y)>F(n) for n,y in table.values()):
            raise ValueError('Invalid known/positive mass')
    shared=sorted(c for c in source.keys()&target.keys() if F(source[c][0])>0 and F(target[c][0])>0)
    sn=sum((F(n) for n,y in source.values()),F(0));tn=sum((F(n) for n,y in target.values()),F(0))
    a=sum((F(source[c][0]) for c in shared),F(0));b=sum((F(target[c][0]) for c in shared),F(0))
    result=dict(shared_contexts=len(shared),source_shared_known_mass=str(a/sn) if sn else None,
        generated_shared_known_mass=str(b/tn) if tn else None)
    if not a or not b:return dict(result,components=None)
    context=conditional=old=new=F(0)
    for c in shared:
        ns,ys=map(F,source[c]);nt,yt=map(F,target[c]);p=ns/a;q=nt/b;r=ys/ns;s=yt/nt
        old+=p*r;new+=q*s;context+=(q-p)*r;conditional+=q*(s-r)
    assert new-old==context+conditional
    return dict(result,components={k:str(v) for k,v in dict(source_rate=old,generated_rate=new,
        signed_gap=new-old,context_mix_component=context,within_context_component=conditional).items()})


def run(model,paths,artist):
    if model.get('schema')!='artist-conditional-notation-v1' or model.get('weighting')!='family':
        raise ValueError('Family-weighted notation model required')
    tables=[t for t in model['tables'] if t['artist']==artist and t['context']!='*']
    if not tables or not paths:raise ValueError('Artist model and generated pieces required')
    target={f:defaultdict(lambda:[F(0),F(0)]) for f in FEATURES}
    for path in paths:
        events=generated(extract_score(path),artist)
        if not events:raise ValueError('Empty generated piece')
        for f in FEATURES:
            known=[e for e in events if f in e['known']]
            if not known:continue
            weight=F(1,len(paths)*len(known))
            for e in known:
                row=target[f][e['context']];row[0]+=weight;row[1]+=weight*int(f in e['labels'])
    results={}
    for f in FEATURES:
        source={t['context']:(t['known'].get(f,'0'),t['features'].get(f,'0')) for t in tables}
        results[f]=decompose(source,target[f])
    return dict(schema='shared-notation-context-gap-v1',pieces=len(paths),features=results,
        limitations=['Exact accounting on shared known contexts only; inspect coverage before reading components.',
            'Source family-weighted and generated equal-piece weights; track mixtures differ.',
            'Components are order-dependent descriptive terms, not causal effects or quality judgments.',
            'Contexts capture only coarse cardinality, duration, bar position, register and open/fretted state.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','directory','out'):p.add_argument(name,type=Path)
    p.add_argument('--artist',default='Invent Animate');p.add_argument('--pattern',default='*-palm-100.gp');a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts or a.out.exists():p.error('Fresh private report required')
    result=run(json.loads(a.model.read_text(encoding='utf-8')),sorted(a.directory.glob(a.pattern)),a.artist)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
