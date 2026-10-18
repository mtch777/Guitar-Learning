"""Controlled role-pitch experiment: rhythm, harmony and arrangement locked.

Melody/bass proposals receive no original target pitches/frets/strings. Harmony
is intentionally available as a locked accompanying context. New notes follow
the development-selected pitch model, conditioned on generated previous notes.
"""
from copy import deepcopy
from fractions import Fraction as F
import random
from collections import defaultdict
from role_pitch_model import distribution
from corpus_composer import choose_family
from controlled_generation import position_chord
from generation_freedom import validate,mix
from artist_profiles import stable_hash


def locked_context(reference,roles):
    if len(roles)!=len(reference['tracks']) or set(roles)-{'harmony','melody','bass'} or roles.count('harmony')!=1:raise ValueError('Explicit supported roles and exactly one harmony context required')
    tracks=[]
    for ti,t in enumerate(reference['tracks']):
        if any(any(v for v in m['voices'][1:]) for m in t['measures']):raise ValueError('Role-pitch method supports main written voice only')
        track={k:deepcopy(t[k]) for k in ('index','name','program','tunings')}
        track['measures']=[]
        for m in t['measures']:
            measure={k:deepcopy(m[k]) for k in ('number','onset_q','time_signature')}
            if 'section' in m:measure['section']=m['section']
            measure['voices']=[]
            for v in m['voices']:
                voice=[]
                for e in v:
                    event={k:e[k] for k in ('onset_q','local_onset_q','duration_q')}
                    event['notes']=deepcopy(e['notes']) if roles[ti]=='harmony' else [{} for n in e['notes']]
                    voice.append(event)
                measure['voices'].append(voice)
            track['measures'].append(measure)
        tracks.append(track)
    return dict(tracks=tracks,**({'tempo_bpm':reference['tempo_bpm']} if 'tempo_bpm' in reference else {}))


def propose(context,roles,composer,pitch_model,seed=17):
    if pitch_model.get('schema')!='written-role-pitch-mixture-v1' or pitch_model.get('source_composer_sha256')!=stable_hash(composer):raise ValueError('Exact source-composer provenance required')
    if composer['artist']!=pitch_model.get('artist'):raise ValueError('Artist model mismatch')
    if set(composer['training_songs'])!=set(pitch_model['training_songs']):
        # Pitch observations may omit songs with no usable melody/bass role.
        if not set(pitch_model['training_songs'])<=set(composer['training_songs']):raise ValueError('Training provenance mismatch')
    rng=random.Random(seed);out=deepcopy(context);harmony=[];cache={};decisions=[]
    for ti,t in enumerate(context['tracks']):
        if roles[ti]=='harmony':harmony.extend(e for m in t['measures'] for v in m['voices'] for e in v if e['notes'])
    for ti,t in enumerate(out['tracks']):
        role=roles[ti]
        if role=='harmony':continue
        tuning=t['tunings'][0]
        for m in t['measures']:
            for vi,v in enumerate(m['voices']):
                previous_pitch=None;previous_fingering=()
                for ei,e in enumerate(v):
                    count=len(e['notes'])
                    if not count:previous_pitch=None;continue
                    key=(role,count)
                    if key not in cache:
                        cache[key]={f:[p for p in records if any(len(x['intervals'])==count for x in p['events'])]
                            for f,records in composer['parts'][role].items()}
                        cache[key]={f:ps for f,ps in cache[key].items() if ps}
                    if not cache[key]:raise ValueError('No source voicing support for locked cardinality')
                    active=[h for h in harmony if F(h['onset_q'])<=F(e['onset_q'])<F(h['onset_q'])+F(h['duration_q'])]
                    anchor=min(n['midi'] for n in active[-1]['notes']) if active else None
                    probs=distribution(pitch_model,role,previous_pitch,anchor)
                    for retry in range(50):
                        p=choose_family(rng,cache[key]);intervals=rng.choice([x['intervals'] for x in p['events'] if len(x['intervals'])==count])
                        candidates={}
                        for root in range(max(0,min(tuning)),min(127,max(tuning)+24)+1):
                            pitches=[root+d for d in intervals]
                            if max(pitches)>127:continue
                            try:positions=position_chord(pitches,tuning,max_span=4,previous=previous_fingering)
                            except ValueError:continue
                            candidates[root]=[(pitch,s,f) for pitch,(s,f) in zip(pitches,positions)]
                        if candidates:break
                    else:raise ValueError('No playable source-supported voicing after bounded retries')
                    roots=sorted(candidates);root=rng.choices(roots,weights=[probs[p] for p in roots],k=1)[0]
                    e['notes']=[dict(midi=p,string=s,fret=f,tie=None,technique_tags=[]) for p,s,f in candidates[root]]
                    previous_pitch=root;previous_fingering=[(s,f) for p,s,f in candidates[root]]
                    decisions.append(dict(track=ti,bar=m['number'],voice=vi,event=ei,anchor=anchor,root=root,playable_roots=len(roots)))
    validate(out)
    return out,decisions


def apply(reference,roles,composer,pitch_model,freedom=100,seed=17):
    if isinstance(freedom,bool) or not isinstance(freedom,int) or not 0<=freedom<=100:raise ValueError('Integer freedom0–100 required')
    validate(reference)
    if freedom==0:return mix(reference,None,{},roles)
    proposal,decisions=propose(locked_context(reference,roles),roles,composer,pitch_model,seed)
    out,audit=mix(reference,proposal,dict(melody=freedom,bass=freedom),roles)
    audit.update(decisions=decisions,method='development-selected normalized role-pitch mixture; playable target support',
        limitations=['Not functional harmony or musical-feel validation.','Rhythm/form/harmony/instrumentation locked; target voicing pitches may change.',
            'Proposal sampling conditions on its generated previous note; intermediate mixes can retain reference notes and need separate listening.'])
    return out,audit
