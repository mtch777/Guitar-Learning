"""Development-only, family-balanced source-notation models.

Conditional Bernoulli baselines, not a neural model or inferred musical intent.
All event provenance/learned distributions are private artifacts. Holdout
predictions never update the fitted vocabulary, weights, contexts or counts.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib,json,math

FEATURES=('bend','slide','finger_vibrato','palm_mute','tapping','dead',
          'hammer_on_from_open','pull_off_to_open','close_interval_texture',
          'power_chord','extended_power_chord','double_stop','pedal_call','pedal_response')


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def connected_families(songs):
    """Verify supplied partitions against title AND exact-notation components."""
    parents={s['song_id']:s['song_id'] for s in songs};seen={}
    def find(x):
        while parents[x]!=x:
            parents[x]=parents[parents[x]];x=parents[x]
        return x
    for s in songs:
        for field in ('candidate_work_family','notation_hash'):
            value=s.get(field)
            if not value:continue
            key=(field,value)
            if key in seen:parents[find(s['song_id'])]=find(seen[key])
            else:seen[key]=s['song_id']
    components=defaultdict(list)
    for s in songs:components[find(s['song_id'])].append(s)
    result={}
    for group in components.values():
        partitions={s['provisional_partition'] for s in group}
        if len(partitions)!=1:raise ValueError('Connected work family crosses train/held-out split')
        identity='family-'+stable_hash(sorted(s['song_id'] for s in group))[:16]
        result.update({s['song_id']:identity for s in group})
    return result


def context(row,notes,register):
    # Attack-group context is invariant to the source voice/note iteration order.
    duration=max(F(n['duration_q']) for n in notes)
    offsets={F(n.get('bar_offset_q','0')) for n in notes}
    position='bar_start' if offsets=={F(0)} else 'inside_bar' if len(offsets)==1 else 'ambiguous_bar_position'
    known=[n['midi'] for n in notes if n['midi'] is not None]
    lo,hi=register
    relative='unknown' if not known or lo==hi else 'low' if 3*(min(known)-lo)<hi-lo else 'high' if 3*(min(known)-lo)>2*(hi-lo) else 'middle'
    # Keep section names out: labels such as "Verse" have inconsistent coverage.
    return '|'.join(('single' if len(notes)==1 else 'dyad' if len(notes)==2 else 'chord',
        'short' if duration<F(1,2) else 'medium' if duration<2 else 'long',
        position,relative,
        'open' if any(n.get('fret')==0 for n in notes) else 'fretted'))


def observations(report,pedals=None,pedal_coverage=()):
    families=connected_families(report['songs']);pedals=pedals or {};events=[];excluded=Counter()
    coverage=set(pedal_coverage)
    for song in report['songs']:
        for track in song['tracks']:
            if not track.get('guitar_or_bass'):continue
            if not track.get('temporal_relationships_eligible'):
                excluded['temporal_ineligible_tracks']+=1;continue
            rows=track['rows'];pitches=[n['midi'] for n in rows if n['midi'] is not None]
            register=(min(pitches),max(pitches)) if pitches else (None,None)
            byid={n['occurrence']:n for n in rows}
            groups=defaultdict(list)
            for n in rows:
                if not n['tie_destination'] and F(n['duration_q'])>0:groups[F(n['onset_q'])].append(n)
            extra=defaultdict(set)
            for g in track.get('coattack_groups',[]):extra[F(g['onset_q'])].update(g['labels'])
            for pair in track.get('hopo_transition_candidates',[]):
                feature=pair['direction']+'_'+pair['context']
                if feature not in FEATURES:continue
                origin=byid.get(pair['origin'])
                if origin:extra[F(origin['onset_q'])].add(feature)
            pedal_roles=pedals.get((song['song_id'],track['part_id']),{})
            for q,notes in sorted(groups.items()):
                labels=set(extra[q]);effects=set(e for n in notes for e in n['effects'])
                for old,new in [('bend','bend'),('slide','slide'),('palmMute','palm_mute'),('tapping','tapping'),('dead','dead')]:
                    if old in effects:labels.add(new)
                if any(any(n.get(scope,{}).get(k) for scope in ('raw_note','raw_beat_effects')
                           for k in ('vibrato','wideVibrato','leftHandVibrato')) for n in notes):labels.add('finger_vibrato')
                for n in notes:
                    role=pedal_roles.get(n['occurrence'])
                    if role in ('call','response'):labels.add('pedal_'+role)
                pedal_known=(song['song_id'],track['part_id']) in coverage
                known=[f for f in FEATURES if pedal_known or not f.startswith('pedal_')]
                if any(n['midi'] is None or not isinstance(n.get('string'),int) for n in notes):
                    unresolved={'close_interval_texture','power_chord','extended_power_chord','double_stop'}
                    known=[f for f in known if f not in unresolved]
                    labels-=unresolved
                if not pedal_known:labels-={'pedal_call','pedal_response'}
                events.append(dict(song_id=song['song_id'],part_id=track['part_id'],onset_q=str(q),
                    members=[n['occurrence'] for n in notes],family=families[song['song_id']],artist=song.get('artist') or '(unknown)',
                    partition=song['provisional_partition'],flagged=not(song.get('ai_generated') is False and song.get('is_junk') is False),
                    context=context(notes[0],notes,register),labels=sorted(set(FEATURES)&labels),known=known))
    return events,dict(excluded)


def fit(events, *, weighting='family',alpha=None):
    if weighting not in ('family','song','pooled'):raise ValueError('Unknown weighting')
    # A fixed prior in the chosen weight units preserves revision-duplication
    # invariance. Do not derive smoothing from the number of duplicate events.
    alpha=F(alpha) if alpha is not None else F(1,2) if weighting=='pooled' else F(1,2000)
    if alpha<=0:raise ValueError('Positive smoothing required')
    train=[e for e in events if e['partition']=='development' and not e['flagged']]
    song_counts=Counter((e['artist'],e['song_id']) for e in train)
    family_songs=defaultdict(set)
    for e in train:family_songs[e['artist'],e['family']].add(e['song_id'])
    # Weights sum to one per song or connected family, not per transcription.
    tables=defaultdict(lambda:dict(total=F(0),features=Counter(),known=Counter()))
    for e in train:
        weight=F(1) if weighting=='pooled' else F(1,song_counts[e['artist'],e['song_id']])
        if weighting=='family':weight/=len(family_songs[e['artist'],e['family']])
        for key in ((e['artist'],'*'),(e['artist'],e['context'])):
            table=tables[key];table['total']+=weight
            for feature in e.get('known',FEATURES):table['known'][feature]+=weight
            for feature in e['labels']:table['features'][feature]+=weight
    return dict(schema='artist-conditional-notation-v1',weighting=weighting,alpha=str(alpha),
        training_songs=sorted({e['song_id'] for e in train}),training_families=sorted({e['family'] for e in train}),
        training_events=len(train),training_sha256=stable_hash(train),
        tables=[dict(artist=a,context=c,total=str(v['total']),features={k:str(n) for k,n in sorted(v['features'].items())},
                     known={k:str(n) for k,n in sorted(v['known'].items())}) for (a,c),v in sorted(tables.items())])


def predict(model,event,*,conditional=True,tables=None,details=False):
    if tables is None:tables={(t['artist'],t['context']):t for t in model['tables']}
    table=tables.get((event['artist'],event['context'])) if conditional else None
    fallback=conditional and table is None
    table=table or tables.get((event['artist'],'*'))
    if table is None:return (None,dict(unknown_artist=True,context=False,features=[])) if details else (None,True)
    alpha=F(model['alpha']);result={}
    feature_backoff=[]
    for f in FEATURES:
        selected=table
        if not F(selected['known'].get(f,'0')):
            selected=tables.get((event['artist'],'*'))
            if conditional and not fallback:feature_backoff.append(f)
        total=F(selected['known'].get(f,'0')) if selected else F(0)
        result[f]=float((F(selected['features'].get(f,'0'))+alpha)/(total+2*alpha)) if total else None
    return (result,dict(unknown_artist=False,context=fallback,features=feature_backoff)) if details else (result,fallback or bool(feature_backoff))


def evaluate(model,events):
    held=[e for e in events if e['partition']=='held_out' and not e['flagged']]
    train_families=set(model['training_families'])
    if any(e['family'] in train_families for e in held):raise ValueError('Work-family leakage')
    by_song=defaultdict(lambda:defaultdict(lambda:[0.,0.,0]));unknown=0
    by_feature=defaultdict(lambda:defaultdict(lambda:[0.,0.,0,0]));fallbacks=Counter();unknown_features=Counter();feature_backoff=Counter()
    tables={(t['artist'],t['context']):t for t in model['tables']}
    for e in held:
        for method in ('conditional','unconditional'):
            probs,backoff=predict(model,e,conditional=method=='conditional',tables=tables,details=True)
            if probs is None:
                if method=='conditional':unknown+=1
                continue
            if backoff['context']:fallbacks[method]+=1
            for f in backoff['features']:feature_backoff[f]+=1
            for feature,p in probs.items():
                if feature not in e.get('known',FEATURES) or p is None:
                    unknown_features[method+':'+feature]+=1;continue
                y=int(feature in e['labels']);p=max(1e-12,min(1-1e-12,p))
                nll=-math.log(p if y else 1-p);brier=(p-y)**2
                v=by_song[e['song_id']][method];v[0]+=nll;v[1]+=brier;v[2]+=1
                v=by_feature[feature][method];v[0]+=nll;v[1]+=brier;v[2]+=1;v[3]+=y
    output={}
    for method in ('conditional','unconditional'):
        values=[v[method] for v in by_song.values() if v[method][2]]
        output[method]=dict(songs=len(values),nll_equal_song=sum(v[0]/v[2] for v in values)/len(values) if values else None,
            brier_equal_song=sum(v[1]/v[2] for v in values)/len(values) if values else None)
    return dict(held_out_events=len(held),unknown_artist_events=unknown,metrics=output,
        context_backoff_events=dict(fallbacks),unknown_feature_events=dict(unknown_features),
        feature_backoff_events=dict(feature_backoff),
        per_feature={f:{m:dict(nll=v[0]/v[2],brier=v[1]/v[2],events=v[2],positive_annotations=v[3]) for m,v in ms.items()} for f,ms in by_feature.items()},
        interpretation='Annotation prediction only; source family split, no inferred technique truth or musical-feel score.')


def describe(events):
    """Descriptive (not fitted) rates; held-out data is clearly labelled here."""
    songs=defaultdict(list)
    for e in events:songs[e['artist'],e['song_id']].append(e)
    output=[]
    for artist in sorted({e['artist'] for e in events}):
        groups=[es for (a,s),es in songs.items() if a==artist]
        features={}
        for f in FEATURES:
            eligible=[[e for e in es if f in e.get('known',FEATURES)] for es in groups]
            eligible=[es for es in eligible if es]
            rates=[sum(f in e['labels'] for e in es)/len(es) for es in eligible]
            features[f]=dict(pooled=sum(sum(f in e['labels'] for e in es) for es in eligible)/sum(map(len,eligible)) if eligible else None,
                equal_song=sum(rates)/len(rates) if rates else None,songs_with_annotation=sum(v>0 for v in rates),songs=len(eligible),
                unknown_songs=len(groups)-len(eligible),minimum_song_rate=min(rates) if rates else None,maximum_song_rate=max(rates) if rates else None)
        output.append(dict(artist=artist,features=features))
    return dict(scope='All partitions for descriptive inventory ONLY; never used to fit the predictive model.',artists=output)
