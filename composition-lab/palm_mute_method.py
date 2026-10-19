"""Source-eligible palm-mute transfer, separate from pitch and other expression.

One decision per exact coattack, shared by all notes in that attack. Source beat
markers provide annotation labels; this does not infer physical muting depth.
"""
from collections import defaultdict,Counter
from copy import deepcopy
from fractions import Fraction as F
import random,zipfile,math
from pathlib import Path
from xml.etree import ElementTree as ET
from artist_profiles import connected_families,context,fit,predict,stable_hash
from performance_opportunities import safe
from exact_score import extract_score
from technique_edits import transact,enable_property
from technique_strength import released


def eligible(n):
    return (safe(n) and not isinstance(n['string'],bool) and n['string']>=0
        and not isinstance(n['fret'],bool) and math.isfinite(n['fret']) and n['fret']>=0 and int(n['fret'])==n['fret']
        and isinstance(n['midi'],(int,float)) and not isinstance(n['midi'],bool) and math.isfinite(n['midi']) and 0<=n['midi']<=127 and int(n['midi'])==n['midi'])


def observations(report,details=False):
    families=connected_families(report['songs']);out=[];inventory=Counter()
    for song in report['songs']:
        for track in song['tracks']:
            if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):continue
            rows=track['rows'];groups=defaultdict(list);tied=set()
            for chain in track.get('sustain_relationships',{}).get('chains',[]):
                if len(chain['members'])>1:tied.update(chain['members'])
            for row in rows:
                if not row['tie_destination']:groups[F(row['onset_q'])].append(row)
            pitches=[n['midi'] for n in rows if n['midi'] is not None];register=(min(pitches),max(pitches)) if pitches else (None,None)
            for q,notes in sorted(groups.items()):
                if any(not eligible(n) or n['occurrence'] in tied for n in notes):continue
                labels=[bool(n.get('raw_beat_effects',{}).get('palmMute') or n.get('raw_note',{}).get('palmMute')) for n in notes]
                kind='all' if all(labels) else 'mixed' if any(labels) else 'none'
                inventory[song['provisional_partition']+':'+kind]+=1
                if kind=='mixed':continue  # never turn a partial source gesture into whole-group truth
                out.append(dict(song_id=song['song_id'],family=families[song['song_id']],artist=song.get('artist') or '(unknown)',
                    partition=song['provisional_partition'],flagged=not(song.get('ai_generated') is False and song.get('is_junk') is False),
                    context=context(notes[0],notes,register),known=['palm_mute'],
                    labels=['palm_mute'] if kind=='all' else []))
    return (out,dict(inventory)) if details else out


def train(report):
    events,inventory=observations(report,True);model=fit(events);model['schema']='eligible-palm-mute-v1';model['source_group_inventory']=inventory
    model['source_training_sha256']=stable_hash([s for s in report['songs'] if s['provisional_partition']=='development' and s.get('ai_generated') is False and s.get('is_junk') is False])
    return model


def apply(source,destination,model,artist,freedom,seed=17):
    if isinstance(freedom,bool) or not isinstance(freedom,int) or not 0<=freedom<=100:raise ValueError('Integer freedom0–100 required')
    if freedom==0:return dict(**transact(source,destination,{},{}),all_locked=True)
    if model.get('schema')!='eligible-palm-mute-v1' or not model.get('source_training_sha256'):raise ValueError('Verified eligible palm-mute model required')
    score=extract_score(source);permissions={};edits={};decisions=[]
    counts=defaultdict(int)
    for t in score['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:
                    for n in e['notes']:counts[n['note_id']]+=1
    if any(v!=1 for v in counts.values()):raise ValueError('Shared note definitions require occurrence cloning')
    tables=[t for t in model['tables'] if t['artist']==artist and t['context']=='*']
    if not tables:raise ValueError('Unknown artist')
    support=F(tables[0]['features'].get('palm_mute','0'))
    for ti,t in enumerate(score['tracks']):
        if t.get('program') is None or not 24<=t['program']<=39:continue
        groups=defaultdict(list);pitches=[]
        for m in t['measures']:
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    for ni,n in enumerate(e['notes']):
                        if n.get('grace_type') or F(e['duration_q'])<=0:continue
                        if n['midi'] is not None:pitches.append(n['midi'])
                        if (n.get('tie') or {}).get('destination')=='true':continue
                        groups[F(e['onset_q'])].append((n,e,f'{ti}:{m["number"]}:{vi}:{ei}:{ni}'))
        register=(min(pitches),max(pitches)) if pitches else (None,None)
        for q,notes in sorted(groups.items()):
            if any(not eligible(n) or n.get('tie') or any(p in n['property_names'] for p in ('Muted','HarmonicType')) for n,e,o in notes):continue
            basic=[dict(midi=n['midi'],fret=n['fret'],duration_q=e['duration_q'],bar_offset_q=e['local_onset_q']) for n,e,o in notes]
            probs,backoff=predict(model,dict(artist=artist,context=context(basic[0],basic,register)),details=True)
            probability=probs['palm_mute'];rng=random.Random(f'{seed}:palm_mute:{ti}:{q}')
            selected=probability is not None and support>0 and rng.random()<probability
            unlocked=released(('palm_mute',ti,str(q)),freedom)
            for n,e,occurrence in notes:
                key=('note',n['note_id'],'property');permissions[key]={'PalmMuted'}
                if unlocked:edits[key]=[enable_property('PalmMuted')] if selected else []
                else:
                    node=ET.fromstring(n['note_xml']).find('./Properties/Property[@name="PalmMuted"]')
                    edits[key]=[] if node is None else [ET.tostring(node,encoding='unicode')]
            decisions.append(dict(track=ti,onset_q=str(q),members=[o for n,e,o in notes],probability=probability,
                proposed_selected=bool(selected),released=unlocked,context_backoff=backoff['context'] or 'palm_mute' in backoff['features']))
    return dict(**transact(source,destination,edits,permissions),decisions=decisions,freedom=freedom,
        limitations=['Beat-marker source annotations, not performed muting depth or sound-quality truth.',
            'Natural untied regular attack groups only; unsupported source events remain locked.'])
