"""Limited melodic copying screen, excluding only the supplied initial motif.

References are two GP attack projections and 2,000 locally held MTC pieces.
Matches are flags, not an originality/legal verdict. Expected later returns of
the supplied motif are still counted rather than silently removed.
"""
import argparse,json,sys,hashlib
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def key(rows):
    first,pitch=rows[0][0],rows[0][2]
    return tuple((str(a-first),str(d),p-pitch) for a,d,p in rows)


def index(streams,n):
    return {key(rows[i:i+n]) for rows in streams for i in range(len(rows)-n+1)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.workspace;prior=root.parent/'autonomous-v1'
    gp=[]
    for family,ti in [('cloud',0),('sweet',3)]:
        score=json.loads((prior/(family+'.canonical.json')).read_text());rows=[]
        for m in score['tracks'][ti]['measures']:
            for e in m['voices'][0]:
                notes=[n for n in e['notes'] if n['midi'] is not None and (n.get('tie') or {}).get('destination')!='true']
                if notes and not e.get('grace_type'):rows.append((F(e['onset_q']),F(e['duration_q']),max(n['midi'] for n in notes)))
        gp.append(rows)
    corpus=json.loads((prior/'corpus/corpus.json').read_text());folk=[]
    for r in corpus:
        meter=r['melody']['metadata']['time_signature'].split('_')[1];num,den=map(int,meter.split('/'));barq=F(num*4,den)
        for phrase in r['melody']['phrases'].values():
            folk.append([(F(str(n[0]))*barq+F(str(n[1])).limit_denominator(24),F(str(n[4])).limit_denominator(24),n[3]) for n in phrase[0]])
    refs={n:{'gp':index(gp,n),'folk':index(folk,n)} for n in (8,16)};results=[]
    for path in sorted(root.glob('*selector*/raw-notes.json')):
        raw=json.loads(path.read_text())['notes']
        if any(n[4]<=0 or n[0]*4+n[1]<0 for n in raw):continue
        rows=[(F(str(n[0]*4+n[1])).limit_denominator(24),F(str(n[4])).limit_denominator(24),n[3]) for n in raw if n[0]*4+n[1]>=8]
        result=dict(run=path.parent.name,post_seed_attacks=len(rows),matches={})
        for n in refs:
            windows=[key(rows[i:i+n]) for i in range(len(rows)-n+1)]
            result['matches'][str(n)]=dict(windows=len(windows),**{name:sum(w in values for w in windows) for name,values in refs[n].items()})
        results.append(result)
    report=dict(scope='transposition-relative timed melody attack windows; supplied first two bars excluded, later motif returns counted; GP highest-note voice0 attack projection; processed MTC phrase timings rationalized to denominator<=24; neither proof nor legal certification of originality',gp_sources=2,folk_pieces=len(corpus),runs=results,quality_judgment=None)
    if a.out.exists():raise FileExistsError('Preserve prior audit')
    a.out.write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
