"""Eligibility-conditioned source-annotation probabilities, never listening truth.

Separate denominators per technique. Restrict to untied, known natural pitches;
no interpolation of missing annotations or inferred expressive intent.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
from copy import deepcopy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
from artist_profiles import connected_families,context,fit,stable_hash,FEATURES
from analyze_relationships import hopo

FAMILIES=('bend','finger_vibrato','hammer_on_from_open','pull_off_to_open')


def safe(row):
    return (row.get('midi') is not None and isinstance(row.get('fret'),(int,float))
        and isinstance(row.get('string'),int) and not row.get('tie_destination')
        and not row.get('raw_note',{}).get('dead')
        and not row.get('raw_note',{}).get('harmonic')
        and not row.get('raw_beat_effects',{}).get('harmonic'))


def opportunities(report):
    families=connected_families(report['songs']);out=[];excluded=Counter()
    for song in report['songs']:
        for track in song['tracks']:
            if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):continue
            rows=track['rows'];groups=defaultdict(list);ending=defaultdict(list)
            for n in rows:ending[n['voice'],n['string'],F(n['onset_q'])+F(n['duration_q'])].append(n['occurrence'])
            tied={ident for chain in track.get('sustain_relationships',{}).get('chains',[])
                  if len(chain.get('members',[]))>1 for ident in chain['members']}
            # Some report versions name these segment_occurrences. Explicit tie
            # origins are also found from contiguous destination segments.
            for n in rows:
                if n.get('tie_destination'):
                    tied.add(n['occurrence'])
                    tied.update(ending[n['voice'],n['string'],F(n['onset_q'])])
                if not n.get('tie_destination'):groups[F(n['onset_q'])].append(n)
            pitches=[n['midi'] for n in rows if n['midi'] is not None];register=(min(pitches),max(pitches)) if pitches else (None,None)
            base=dict(song_id=song['song_id'],family=families[song['song_id']],artist=song.get('artist') or '(unknown)',
                partition=song['provisional_partition'],flagged=not(song.get('ai_generated') is False and song.get('is_junk') is False))
            def emit(n,feature,positive):
                ns=groups[F(n['onset_q'])]
                out.append(dict(base,part_id=track['part_id'],members=[n['occurrence']],context=context(n,ns,register),
                    known=[feature],labels=[feature] if positive else []))
            usable=[n for n in rows if safe(n) and n['occurrence'] not in tied]
            for n in usable:
                if len(groups[F(n['onset_q'])])!=1 or n['fret']<=0:continue
                emit(n,'bend',bool(n.get('raw_note',{}).get('bend')))
                emit(n,'finger_vibrato',any(n.get(scope,{}).get(k) for scope in ('raw_note','raw_beat_effects')
                    for k in ('vibrato','wideVibrato','leftHandVibrato')))
            # Query all contiguous pairs with the SAME helper used to interpret
            # actual source hp labels. Annotation flags cannot affect eligibility.
            marked=deepcopy(rows)
            for n in marked:n['effects']=list(set(n['effects'])|{'hp'})
            pairs,_=hopo(marked,track.get('grace_rows',[]));byid={n['occurrence']:n for n in usable}
            actual={(p['origin'],p['destination']) for p in track.get('hopo_transition_candidates',[])}
            for pair in pairs:
                feature=pair['direction']+'_'+pair['context']
                a,b=byid.get(pair['origin']),byid.get(pair['destination'])
                if feature in FAMILIES and a and b:emit(a,feature,(a['occurrence'],b['occurrence']) in actual)
    return out,dict(excluded)


def train(report):
    events,excluded=opportunities(report);tables={};models=[]
    # Fit each feature separately so family/song weighting uses that feature's
    # eligible opportunity denominator, not the total of unrelated opportunities.
    for feature in FAMILIES:
        model=fit([e for e in events if feature in e['known']]);models.append(model)
        for t in model['tables']:
            target=tables.setdefault((t['artist'],t['context']),dict(artist=t['artist'],context=t['context'],total='0',known={},features={}))
            target['known'].update(t['known']);target['features'].update(t['features'])
    return dict(schema='artist-performance-opportunity-v1',weighting='family',alpha='1/2000',
        training_songs=sorted({s for m in models for s in m['training_songs']}),
        training_families=sorted({s for m in models for s in m['training_families']}),
        training_sha256=stable_hash([e for e in events if e['partition']=='development' and not e['flagged']]),
        training_source_sha256=stable_hash([s for s in report['songs'] if s['provisional_partition']=='development' and s.get('ai_generated') is False and s.get('is_junk') is False]),
        training_events=sum(m['training_events'] for m in models),tables=list(tables.values()),excluded=excluded),events
