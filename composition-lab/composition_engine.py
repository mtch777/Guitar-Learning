"""Research engine: neural phrase pool + learned form-state/joint-role baselines.

The current form-state model failed its quality gate. This exports exploratory
full-length material, not a claim of learned coherent global form. No source
phrase is copied into outputs. Role timing remains an explicit quarter grid.
"""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import hashlib,itertools,json,pickle,random
from pathlib import Path
from controlled_generation import position_chord
from source_ablations import fit_pitches
from structural_learning import FormModel
from joint_roles import JointRoleModel,source_rows
from gp_author import write_gp

ROLES={'cloud':dict(harmony=2,melody=0,bass=4),'sweet':dict(harmony=4,melody=3,bass=7)}


def note_event(onset,duration,positions):
    return dict(onset_q=str(onset),duration_q=str(duration),notes=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in positions])


def make_voicing(classes,anchor,tuning,previous=()):
    classes=tuple(sorted(set((anchor+p)%12 for p in classes)))[:3]
    center=min(tuning)+14;options=[]
    for pc in classes:
        pitches=sorted((p for p in range(min(tuning),max(tuning)+25) if p%12==pc),key=lambda p:abs(p-center))[:3]
        options.append(pitches)
    candidates=[]
    for pitches in itertools.product(*options):
        try:
            positions=position_chord(pitches,tuning,previous=previous)
            cost=sum(abs(p-center) for p in pitches)
            candidates.append((cost,[(p,s,f) for p,(s,f) in zip(pitches,positions)]))
        except ValueError:pass
    if not candidates:raise ValueError('No playable learned PC-set voicing')
    return min(candidates,key=lambda c:c[0])[1]


def to_bars(events,info,bars,name):
    track=dict(index=0,name=name,tunings=deepcopy(info['tunings']),program=info['program'],measures=[])
    for bar in range(bars):
        start=F(bar*4);end=start+4;cursor=start;result=[]
        for e in [e for e in events if start<=F(e['onset_q'])<end]:
            pos=F(e['onset_q']);duration=min(F(e['duration_q']),end-pos)
            if pos>cursor:result.append(dict(onset_q=str(cursor),local_onset_q=str(cursor-start),duration_q=str(pos-cursor),notes=[]))
            result.append(dict(e,duration_q=str(duration),local_onset_q=str(pos-start)));cursor=pos+duration
        if cursor<end:result.append(dict(onset_q=str(cursor),local_onset_q=str(cursor-start),duration_q=str(end-cursor),notes=[]))
        track['measures'].append(dict(number=bar+1,onset_q=str(start),time_signature='4/4',voices=[result]))
    return track


def compose(source,joint,models,pool,bars,seed):
    import numpy as np
    rng=random.Random(seed);family=source['family'];roles=ROLES[family];score=source['score'];form=models['form'];clusterer=models['clusters']
    vectors=np.array([p['features'] for p in pool]);centers=clusterer.cluster_centers_
    history=[];plan=[];lead=[];bar=0;last_phrase=None;repairs=Counter();previous=()
    while bar<bars:
        state=form.sample(rng,history,bar/bars);history.append(state);cluster,length=state;length=min(length,bars-bar)
        distances=((vectors-centers[cluster])**2).sum(axis=1);shortlist=np.argsort(distances)[:8]
        choice=pool[int(rng.choice(list(shortlist)))];plan.append(dict(start_bar=bar,bars=length,cluster=cluster,pool_id=choice['id'],learned_state=list(state)))
        for local_bar in range(length):
            for n in [n for n in choice['notes'] if n['bar']==local_bar%2]:
                pitch=n['pitch'];positions=fit_pitches([pitch],score['tracks'][roles['melody']]['tunings'][0],previous)
                repairs['lead_octave_changes']+=int(positions[0][0]!=pitch);previous=[(s,f) for p,s,f in positions]
                lead.append(note_event(F((bar+local_bar)*4)+F(n['position']),F(n['duration']),positions))
        bar+=length
    accompaniment=[];bass=[];last_anchor=60;prev_h=();prev_b=()
    for q in range(bars*4):
        active=[n['midi'] for e in lead if F(e['onset_q'])<=q<F(e['onset_q'])+F(e['duration_q']) for n in e['notes']]
        if active:last_anchor=max(active)
        classes,bass_interval=joint.sample(rng,(last_anchor%12,q%4))
        try:positions=make_voicing(classes,last_anchor,score['tracks'][roles['harmony']]['tunings'][0],prev_h)
        except ValueError:
            repairs['voicing_tone_reductions']+=1;positions=make_voicing(classes[:1],last_anchor,score['tracks'][roles['harmony']]['tunings'][0],prev_h)
        prev_h=[(s,f) for p,s,f in positions];accompaniment.append(note_event(q,1,positions))
        tuning=score['tracks'][roles['bass']]['tunings'][0];pc=(last_anchor+bass_interval)%12
        pitch=min((p for p in range(min(tuning),max(tuning)+25) if p%12==pc),key=lambda p:abs(p-(min(tuning)+10)))
        positions=fit_pitches([pitch],tuning,prev_b);prev_b=[(s,f) for p,s,f in positions];bass.append(note_event(q,1,positions))
    result=dict(source_file='learned-research-composition',tracks=[])
    for i,(role,events) in enumerate([('harmony',accompaniment),('melody',lead),('bass',bass)]):
        track=to_bars(events,score['tracks'][roles[role]],bars,role);track['index']=i;result['tracks'].append(track)
    return result,dict(seed=seed,form=plan,repairs=dict(repairs),
        limitations=['form model failed independent baseline gate','neural pool cached; restricted vocabulary','phrase lengths rounded/capped 1-4 bars; 2-bar content may repeat/truncate','accompaniment timing is fixed quarter grid','joint role model fitted to one private song; no harmonic-function truth','no learned drum/vocal/technique generation'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--count',type=int,default=100);p.add_argument('--bars',type=int,default=64)
    args=p.parse_args();root=args.workspace;out=root/'compositions';out.mkdir(exist_ok=False)
    models=pickle.loads((root/'structure-v2/models.pkl').read_bytes());pool=json.loads((root/'neural-pool.json').read_text())['pool']
    sources={family:dict(family=family,score=json.loads((root/(family+'.canonical.json')).read_text()),graph=json.loads((root/(family+'.sounding.json')).read_text())) for family in ROLES}
    rows={k:source_rows(v['graph'],ROLES[k],v['score']['duration_q']) for k,v in sources.items()}
    joints={k:JointRoleModel().fit(r) for k,r in rows.items()}
    report=dict(role_cross_song={k+'-to-'+other:joints[k].evaluate(rows[other]) for k in sources for other in sources if k!=other},compositions=[])
    for i in range(args.count):
        family=['cloud','sweet'][i%2];score,plan=compose(sources[family],joints[family],models,pool,args.bars,1000+i)
        ident=f'piece-{i+1:03d}-{family}';path=out/(ident+'.gp');write_gp(score,path,title=ident)
        (out/(ident+'.expected.json')).write_text(json.dumps(score),encoding='utf-8')
        (out/(ident+'.plan.json')).write_text(json.dumps(plan),encoding='utf-8')
        report['compositions'].append(dict(id=ident,family=family,bars=args.bars,seed=1000+i,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),repairs=plan['repairs']))
        if i%10==9:print('compositions',i+1,flush=True)
    (root/'engine-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report['role_cross_song']))


if __name__=='__main__':main()
