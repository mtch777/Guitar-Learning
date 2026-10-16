"""Batch constraint, copying and control audits; no musical quality verdicts."""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib,json,random
from pathlib import Path
from engine_controls import vary,distance


def streams(score):
    for t in score['tracks']:
        count=max(len(m['voices']) for m in t['measures'])
        for vi in range(count):
            yield [(str(F(e['duration_q'])),tuple(n['midi'] for n in e['notes'] if n['midi'] is not None)) for m in t['measures'] if vi<len(m['voices']) for e in m['voices'][vi]]


def fingerprint(window,coarse=False):
    pitches=[p for d,ps in window for p in ps]
    if not pitches:return None
    anchor=pitches[0]
    if coarse:
        roots=[min(ps) if ps else None for d,ps in window];prior=next(p for p in roots if p is not None)
        code=[]
        for (d,ps),p in zip(window,roots):
            code.append((round(float(F(d))*2),None if p is None else (p>prior)-(p<prior)))
            if p is not None:prior=p
    else:code=[(d,tuple(p-anchor for p in ps)) for d,ps in window]
    return hashlib.sha256(repr(code).encode()).digest()[:16]


def constraints(score):
    notes=0;violations=[];duration=None
    for t in score['tracks']:
        tuning=t['tunings'][0]
        for mi,m in enumerate(t['measures']):
            for voice in m['voices']:
                cursor=F(0)
                for e in voice:
                    if F(e['local_onset_q'])!=cursor:violations.append('noncontiguous voice')
                    cursor+=F(e['duration_q']);frets=[];strings=[]
                    for n in e['notes']:
                        notes+=1;f=n['fret'];s=n['string'];frets.append(f);strings.append(s)
                        if not 0<=f<=24 or tuning[s]+f!=n['midi']:violations.append('range/tuning')
                    if len(strings)!=len(set(strings)):violations.append('duplicate string')
                    stopped=[f for f in frets if f>0]
                    if stopped and max(stopped)-min(stopped)>5:violations.append('fret span')
                if cursor!=4:violations.append('meter')
        duration=4*len(t['measures'])
    return dict(notes=notes,bars=duration//4,seconds_at_120=duration/2,violations=dict(Counter(violations)),
        human_playability=None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--report-name',default='validation-report.json');args=p.parse_args();root=args.workspace
    corpus=json.loads((root/'corpus/corpus.json').read_text());refs={n:set() for n in (8,16,32)};coarse=set()
    for family in ('cloud','sweet'):
        source=json.loads((root/(family+'.canonical.json')).read_text())
        for stream in streams(source):
            for length,index in refs.items():
                for i in range(len(stream)-length+1):
                    h=fingerprint(stream[i:i+length])
                    if h:index.add(h)
            for i in range(len(stream)-7):
                h=fingerprint(stream[i:i+8],True)
                if h:coarse.add(h)
    for record in corpus:
        notes=[n for phrase in record['melody']['phrases'].values() for n in phrase[0]]
        stream=[(str(F(str(n[4])).limit_denominator(24)),(n[3],)) for n in notes]
        for length,index in refs.items():
            for i in range(len(stream)-length+1):
                h=fingerprint(stream[i:i+length])
                if h:index.add(h)
        for i in range(len(stream)-7):
            h=fingerprint(stream[i:i+8],True)
            if h:coarse.add(h)
    report=dict(reference_pieces=len(corpus)+2,outputs=[],controls=[])
    pool=json.loads((root/'neural-pool.json').read_text())['pool']
    for fi,path in enumerate(sorted((root/'compositions').glob('*.expected.json'))):
        score=json.loads(path.read_text());audit=constraints(score);matches={n:0 for n in refs};denoms={n:0 for n in refs};near=0;near_total=0
        for stream in streams(score):
            for length,index in refs.items():
                for i in range(len(stream)-length+1):
                    h=fingerprint(stream[i:i+length])
                    if h:denoms[length]+=1;matches[length]+=h in index
            for i in range(len(stream)-7):
                h=fingerprint(stream[i:i+8],True)
                if h:near_total+=1;near+=h in coarse
        report['outputs'].append(dict(file=path.name,**audit,exact_relative_matches=matches,eligible_windows=denoms,
            coarse_contour_rhythm_matches=near,coarse_windows=near_total,originality_verdict=None))
        if fi<20:
            excerpt=json.loads(json.dumps(score))
            for t in excerpt['tracks']:t['measures']=t['measures'][:4]
            for seed in (17,29,41,53,67):
                for dimension in ('harmony','melody','rhythm','structure'):
                    for target in (0,25,50,75,100):
                        try:
                            changed,evidence=vary(excerpt,{dimension:target},pool,seed)
                            if constraints(changed)['violations']:raise AssertionError('Invalid control output')
                            report['controls'].append(dict(piece=fi,seed=seed,dimension=dimension,target=target,**evidence))
                        except ValueError as e:report['controls'].append(dict(piece=fi,seed=seed,dimension=dimension,target=target,infeasible=str(e)))
        if fi%20==19:print('validated',fi+1,flush=True)
    report['summary']=dict(pieces=len(report['outputs']),constraint_failures=sum(bool(o['violations']) for o in report['outputs']),
        controls=len(report['controls']),infeasible_controls=sum('infeasible' in r for r in report['controls']),
        extended_match_pieces=sum(o['exact_relative_matches'][16]>0 for o in report['outputs']),
        scope='Exact transposition-relative and coarse contour/rhythm windows; generic repetitions can match; neither proof nor legal determination of originality')
    target=root/args.report_name
    if target.exists():raise FileExistsError('Choose a new report name')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report['summary']))


if __name__=='__main__':main()
