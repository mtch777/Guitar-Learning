"""Development-selected mixture of written root, motion and role alignment.

Teacher-forced next-written-minimum-pitch likelihood, not harmony or listening
quality. Every component is normalized over MIDI0..127. Family-held-out inner
validation selects mixtures without accessing the outer held-out songs.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
import hashlib,math
from artist_profiles import stable_hash

METHODS=('absolute','motion','alignment')


def observations(composer):
    index={r:defaultdict(list) for r in composer['parts']};families={}
    for role,fs in composer['parts'].items():
        for family,records in fs.items():
            for p in records:index[role][p['song_id'],p['bar']].append(p);families[p['song_id']]=family
    events=[]
    for role in ('melody','bass'):
        for (song,bar),records in sorted(index[role].items()):
            p=min(records,key=lambda r:r['part_id']);h=min(index['harmony'][song,bar],key=lambda r:r['part_id']) if index['harmony'][song,bar] else None
            # Meter changes cannot reconstruct global onset from bar number.
            # Link within a bar only; no fabricated cross-bar/section continuity.
            prev=None;end=None
            for e in p['root_events']:
                q=F(e['local_q']);anchor=None
                if h:
                    active=[a for a in h['root_events'] if F(a['local_q'])<=q<F(a['local_q'])+F(a['duration_q'])]
                    if active:anchor=int(active[-1]['root'])
                target=int(e['root'])
                if not 0<=target<=127:continue
                events.append(dict(role=role,song_id=song,family=families[song],target=target,
                    previous=prev if end==q else None,anchor=anchor))
                prev=target;end=q+F(e['duration_q'])
    return events


def fit(events):
    groups=defaultdict(lambda:defaultdict(lambda:defaultdict(Counter)))
    for e in events:
        for method,key in [('absolute',e['target']),('motion',None if e['previous'] is None else e['target']-e['previous']),
                           ('alignment',None if e['anchor'] is None else e['target']-e['anchor'])]:
            if key is not None:groups[e['role'],method][e['family']][str(e['song_id'])][str(key)]+=1
    tables={}
    for (role,method),fs in groups.items():
        counter=defaultdict(float)
        for songs in fs.values():
            for counts in songs.values():
                total=sum(counts.values())
                for key,count in counts.items():counter[key]+=count/total/len(songs)/len(fs)
        tables.setdefault(role,{})[method]=dict(counter)
    return dict(schema='written-role-pitch-mixture-v1',tables=tables,
        training_songs=sorted({e['song_id'] for e in events}),training_families=sorted({e['family'] for e in events}),
        training_sha256=stable_hash(events))


def components(model,role,previous,anchor):
    tables=model['tables'].get(role)
    if not tables or 'absolute' not in tables:raise ValueError('No trained role-pitch support')
    result={};alpha=1e-4
    for method in METHODS:
        center=0 if method=='absolute' else previous if method=='motion' else anchor
        table=tables.get(method,{}) if center is not None else {}
        if not table:
            table=tables['absolute'];center=0
        counts=[table.get(str(p-center),0) for p in range(128)];total=sum(counts)+128*alpha
        result[method]=[(c+alpha)/total for c in counts]
    return result


def distribution(model,role,previous,anchor,weights=None):
    weights=weights or model['weights'][role]
    if len(weights)!=3 or any(isinstance(w,bool) or not isinstance(w,(int,float)) or not math.isfinite(w) or w<0 for w in weights) or abs(sum(weights)-1)>1e-9:raise ValueError('Normalized finite nonnegative mixture weights required')
    cs=components(model,role,previous,anchor)
    return [sum(w*cs[method][p] for method,w in zip(METHODS,weights)) for p in range(128)]


def select(events,folds=5):
    if isinstance(folds,bool) or not isinstance(folds,int) or folds<2:raise ValueError('At least two integer folds required')
    families=sorted({e['family'] for e in events})
    if len(families)<2:raise ValueError('At least two development work families required for model selection')
    folds=min(folds,len(families));ordered=sorted(families,key=lambda f:hashlib.sha256(f.encode()).hexdigest())
    assignments={f:i%folds for i,f in enumerate(ordered)}
    weights=[(a/4,b/4,(4-a-b)/4) for a in range(5) for b in range(5-a)]
    losses=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for fold in range(folds):
        train=[e for e in events if assignments[e['family']]!=fold];valid=[e for e in events if assignments[e['family']]==fold]
        model=fit(train)
        for e in valid:
            if e['role'] not in model['tables']:continue
            cs=components(model,e['role'],e['previous'],e['anchor'])
            for w in weights:
                p=sum(weight*cs[m][e['target']] for m,weight in zip(METHODS,w))
                losses[e['role'],w][e['family']][e['song_id']].append(-math.log(max(p,1e-300)))
    scores={role:{w:sum(sum(sum(v)/len(v) for v in songs.values())/len(songs) for songs in fs.values())/len(fs)
        for (r,w),fs in losses.items() if r==role} for role in ('melody','bass')}
    if any(not values for values in scores.values()):raise ValueError('No independent fold support for each required role')
    selected={role:list(min(values,key=lambda w:(values[w],-w[0],-w[1]))) for role,values in scores.items()}
    model=fit(events);model.update(weights=selected,selection=dict(folds=folds,assignments=assignments,
        scores={r:[dict(weights=w,nll=v) for w,v in sorted(values.items())] for r,values in scores.items()},
        metric='equal-family, equal-song-within-family teacher-forced written-root NLL; development only'))
    return model


def evaluate(model,events):
    if set(model['training_families'])&{e['family'] for e in events}:raise ValueError('Family leakage')
    if set(model['training_songs'])&{e['song_id'] for e in events}:raise ValueError('Song leakage')
    groups=defaultdict(lambda:defaultdict(list))
    for e in events:
        for name,weights in [('selected',model['weights'][e['role']]),('absolute',[1,0,0]),('motion',[0,1,0]),('alignment',[0,0,1])]:
            probs=distribution(model,e['role'],e['previous'],e['anchor'],weights)
            groups[e['role'],name][e['song_id']].append(-math.log(max(probs[e['target']],1e-300)))
    return {role:{name:dict(equal_song_nll=sum(sum(v)/len(v) for v in gs.values())/len(gs),songs=len(gs),events=sum(map(len,gs.values())))
        for (r,name),gs in groups.items() if r==role} for role in ('melody','bass')}
