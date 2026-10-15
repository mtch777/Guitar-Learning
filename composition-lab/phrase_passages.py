"""Audible, authored rhythm/contour tests; not learned phrase intelligence."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
from source_ablations import fit_pitches
from phrase_experiments import attacks,harmony_pcs,nearest
from gp_author import write_gp

# Explicit 4/4 demonstration: pickups, unequal attacks, held endings and breath.
PATTERNS=[[(0,'1/2'),('1/2',1),('3/2','1/2'),('5/2','1/2')],
          [('1/2','1/2'),(1,'1/2'),('3/2',1),('5/2',1)],
          [(0,1),(1,'1/2'),(2,'1/2'),('5/2','1/2')],
          [('1/2','1/2'),(1,1),(2,'3/2')]]


def transform(base,contour=False):
    out=deepcopy(base);lead=out['tracks'][1];tuning=lead['tunings'][0]
    seed=[e['notes'][0]['midi'] for e in attacks(base['tracks'][1]['measures'][:2])][:4]
    if len(seed)<2:raise ValueError('Insufficient generated motif')
    motif=[p-seed[0] for p in seed];previous=();last=seed[0]
    for mi,m in enumerate(lead['measures']):
        if F(m['time_signature'].split('/')[0])*4/F(m['time_signature'].split('/')[1])!=4:raise ValueError('This authored test requires 4/4')
        source=attacks([base['tracks'][1]['measures'][mi]])
        if not source:source=attacks(base['tracks'][1]['measures'][:2])
        pattern=PATTERNS[mi%4];events=[];cursor=F(0)
        pcs=harmony_pcs(base,mi)
        anchor=nearest(last,pcs,min(tuning),max(tuning)+24)
        def event(start,duration,pitches):
            nonlocal previous
            positions=fit_pitches(pitches,tuning,previous) if pitches else []
            if positions:previous=[(s,f) for p,s,f in positions]
            return dict(onset_q=str(F(m['onset_q'])+start),local_onset_q=str(start),duration_q=str(duration),
                notes=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in positions])
        for i,(start,duration) in enumerate(pattern):
            start,duration=F(start),F(duration)
            if start>cursor:events.append(event(cursor,start-cursor,[]))
            pitches=[n['midi'] for n in source[i%len(source)]['notes']]
            if contour:
                offset=motif[i%len(motif)]
                if mi//4==1:offset=-offset
                elif mi//4==2:offset=round(offset/2)
                pitch=anchor+offset
                candidates=[pitch+12*k for k in range(-5,6) if min(tuning)<=pitch+12*k<=max(tuning)+24]
                pitch=min(candidates,key=lambda p:abs(p-last))
                # A held answer, or a stepwise approach to its target.
                if mi%4==3 and i==len(pattern)-1:pitch=nearest(last,pcs,min(tuning),max(tuning)+24)
                pitches=[pitch];last=pitch
            events.append(event(start,duration,pitches));cursor=start+duration
        if cursor<4:events.append(event(cursor,4-cursor,[]))
        m['voices']=[events]
    assert out['tracks'][0]==base['tracks'][0] and out['tracks'][2:]==base['tracks'][2:]
    return out


def main():
    root=Path(__file__).resolve().parent
    for family in ('cloud','sweet'):
        parent=root/f'local-artifacts/{family}-native-ablations'
        base=json.loads((parent/'roles-phrases.expected.json').read_text(encoding='utf-8'))
        folder=root/f'local-artifacts/{family}-audible-phrases';folder.mkdir(exist_ok=False)
        for name,score in [('baseline',base),('rhythm',transform(base)),('developed',transform(base,True))]:
            for solo in (False,True):
                candidate=deepcopy(score)
                if solo:candidate['tracks']=[candidate['tracks'][1]];candidate['tracks'][0]['index']=0
                ident=name+('-solo' if solo else '')
                write_gp(candidate,folder/(ident+'.gp'),title=ident)
                (folder/(ident+'.expected.json')).write_text(json.dumps(candidate),encoding='utf-8')
        print(family,'6 GP files: baseline/rhythm/developed x full/solo')


if __name__=='__main__':main()
