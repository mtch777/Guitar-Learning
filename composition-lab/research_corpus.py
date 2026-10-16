"""Local noncommercial MTC corpus, family/content-grouped splits and features.

No corpus notes or labels are committed. Public summaries contain counts only.
MTC rights/provenance: https://www.liederenbank.nl/mtc/ (CC BY-NC-SA 3.0).
The five-style target is NOT satisfied by calling folk subcollections genres.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json,zipfile
from pathlib import Path


def content_signature(phrases):
    notes=[n for p in phrases.values() for n in p[0]]
    anchor=notes[0][3] if notes else 0
    return hashlib.sha256(json.dumps([(n[3]-anchor,str(F(str(n[4])))) for n in notes]).encode()).hexdigest()


def boundary_rows(features):
    pitches=features['midipitch'];dur=[float(F(str(x))) for x in features['duration_frac']]
    gaps=[float(F(str(x))) if x is not None else 0 for x in features['restduration_frac']]
    n=len(pitches);rows=[]
    for i in range(n-1):
        # No phrase position, song position, end/cadence annotation or other
        # label-derived feature enters this offline local-boundary detector.
        prev=abs(pitches[i]-pitches[i-1]) if i else 0
        following=abs(pitches[i+1]-pitches[i])
        strength=features.get('beatstrength',[0]*n)[i]
        try:strength=float(strength or 0)
        except (ValueError,TypeError):strength=0
        rows.append(dict(x=[dur[i],gaps[i],prev,following,dur[i]/max(.01,dur[i+1]),strength],
                         y=int(bool(features['phrase_end'][i]))))
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--limit',type=int,default=2000)
    args=p.parse_args();args.out.mkdir(exist_ok=False,parents=True)
    records={};eligible=set()
    with zipfile.ZipFile(args.archive) as z:
        paths={Path(n).stem:n for n in z.namelist() if n.startswith('data/extracted_phrases/NLB') and n.endswith('.json')}
        # Hash-order selection fixed independently of labels, metrics and split.
        selected=set(sorted(paths,key=lambda s:hashlib.sha256(s.encode()).hexdigest())[:args.limit])
        name='data/annotations/MTC-FS-INST-2.0_sequences-1.1.jsonl/mtcfsinst_sequences.jsonl'
        with z.open(name) as stream:
            for line in stream:
                d=json.loads(line)
                if d['id'] not in selected:continue
                melody=json.loads(z.read(paths[d['id']]))
                family=str(d.get('tunefamily') or '')
                if family in ('','0','None'):family='unknown:'+d['id'].split('_')[0]
                try:boundaries=boundary_rows(d['features'])
                except (ValueError,TypeError,KeyError):boundaries=[]
                records[d['id']]=dict(id=d['id'],family=family,type=d.get('type','unknown'),melody=melody,
                    boundary_rows=boundaries,signature=content_signature(melody['phrases']))
    # Union shared families and exact transposition-relative melodic content.
    parent={k:k for k in records}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    seen={}
    for ident,r in records.items():
        for key in [('family',r['family']),('content',r['signature'])]:
            if key in seen:
                a,b=find(ident),find(seen[key]);parent[max(a,b)]=min(a,b)
            else:seen[key]=ident
    for ident,r in records.items():
        group=find(ident);bucket=int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%100
        r['group']=group;r['split']='train' if bucket<70 else 'development' if bucket<85 else 'test'
    for field in ('family','signature','group'):
        split_for={}
        for r in records.values():
            prior=split_for.setdefault(r[field],r['split'])
            if prior!=r['split']:raise AssertionError('Split leakage')
    (args.out/'corpus.json').write_text(json.dumps(list(records.values())),encoding='utf-8')
    summary=dict(pieces=len(records),groups=len({r['group'] for r in records.values()}),
        splits=dict(Counter(r['split'] for r in records.values())),types=dict(Counter(r['type'] for r in records.values())),
        boundary_examples=dict(Counter({s:sum(len(r['boundary_rows']) for r in records.values() if r['split']==s) for s in ['train','development','test']})),
        rights='MTC CC BY-NC-SA 3.0; local noncommercial research; no corpus redistribution',
        provenance='Official Yin-Yang derived MTC JSON plus MTC feature annotations; attributed Meertens Institute',
        style_target='NOT MET: one folk tradition, vocal/instrumental are not five genres',
        family_content_leakage=False,pretraining_overlap='external Yin-Yang may have seen these songs; scratch-trained models use grouped split')
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))


if __name__=='__main__':main()
