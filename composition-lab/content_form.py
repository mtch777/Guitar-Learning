"""Conservative section recurrence from complete written content, not names.

Exact transposition-relative bar sequences, reduced only by exact repetition.
Incomplete source coverage or static-root textures abstain from recurrence. This
is a content identity baseline, not validated thematic/functional similarity.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
from artist_profiles import connected_families,stable_hash


def signature(records):
    if not records:return None
    roots=[e['root'] for p in records for e in p['root_events']]
    if len(roots)<4 or len(set(roots))<2:return None
    anchor=roots[0];tokens=[]
    for p in records:
        attacks=iter(p['root_events']);events=[]
        for e in p['events']:
            if e['intervals']:
                root=next(attacks)['root'];pitches=[str(F(str(root))-F(str(anchor))+F(str(i))) for i in e['intervals']]
            else:pitches=[]
            events.append((e['duration_q'],pitches))
        tokens.append(stable_hash(dict(meter=p['meter'],events=events)))
    # Exact repeated whole-bar periods only; do not guess phase or near-matches.
    for period in range(1,len(tokens)+1):
        if len(tokens)%period==0 and all(t==tokens[i%period] for i,t in enumerate(tokens)):
            return stable_hash(tokens[:period])
    raise AssertionError('Full sequence is always an exact period')


def timeline_signature(track,headers,start,end):
    """Analyze original occurrences, not the generator's restricted bar bank.

    Generator exclusions (ties/dead notes) are not missing source observations.
    Resolved ties retain full length, including held notes crossing a marker.
    Grace events remain zero-time, distinct written ornament symbols.
    """
    if not headers:return None
    chains=track.get('sustain_relationships',{}).get('chains',[])
    if any(c.get('orphan_tie') for c in chains):return None
    tails={c['origin']:F(c['end_q']) for c in chains}
    rows=[dict(n,grace_identity=False) for n in track['rows']]+[dict(n,grace_identity=True) for n in track.get('grace_rows',[])]
    attacks=[]
    for n in rows:
        if n['voice']!=0 or n['tie_destination']:continue
        q=F(n['onset_q']);duration=F(0) if n['grace_identity'] else F(n['duration_q']);finish=q if n['grace_identity'] else tails.get(n['occurrence'],q+duration)
        if start<=q<end or q<start<finish:
            if n['midi'] is None and not n.get('raw_note',{}).get('dead'):return None
            attacks.append((q,n,finish-q))
    grouped=defaultdict(list)
    for q,n,d in attacks:grouped[q].append(n)
    pitch_sets=[tuple(sorted(n['midi'] for n in ns if n['midi'] is not None)) for q,ns in sorted(grouped.items()) if any(n['midi'] is not None for n in ns)]
    if len(pitch_sets)<4 or len(set(pitch_sets))<2:return None
    anchor=min(pitch_sets[0]);tokens=[]
    for i,h in enumerate(headers):
        q=F(h['start_q']);right=q+F(h['span_q']);events=[]
        for onset,n,duration in attacks:
            if q<=onset<right or i==0 and onset<start:
                pitch='unknown-written-pitch' if n['midi'] is None else str(F(str(n['midi']))-F(str(anchor)))
                events.append((str(onset-q),pitch,str(duration),n['grace_identity'],str(F(n['duration_q'])) if n['grace_identity'] else None))
        tokens.append(stable_hash(dict(meter=h['signature'],span_q=str(F(h['span_q'])),events=sorted(events))))
    for period in range(1,len(tokens)+1):
        if len(tokens)%period==0 and all(t==tokens[i%period] for i,t in enumerate(tokens)):return stable_hash(tokens[:period])
    raise AssertionError('Full timeline is always an exact period')


def observations(report,composer):
    families=connected_families(report['songs']);parts=defaultdict(lambda:defaultdict(dict));out=[];excluded=Counter()
    for records in composer['parts']['harmony'].values():
        for p in records:parts[p['song_id']][p['part_id']][p['bar']]=p
    for song in report['songs']:
        if song['song_id'] not in parts:continue
        part=min(parts[song['song_id']],key=lambda p:(-len(parts[song['song_id']][p]),p));bars=parts[song['song_id']][part]
        track=next(t for t in song['tracks'] if t['part_id']==part)
        if len(track.get('sections',[]))<2:excluded['fewer_than_two_source_marked_sections']+=1;continue
        sequence=[];last={}
        for section in track['sections']:
            headers=[h for h in song['shared_layout'] if F(section['start_q'])<=F(h['start_q'])<F(section['end_q'])]
            if not headers:continue
            identity=timeline_signature(track,headers,F(section['start_q']),F(section['end_q']))
            if identity is None:excluded['sections_with_insufficient_nonstatic_content']+=1
            lag=len(sequence)-last[identity] if identity is not None and identity in last else 0
            if identity is not None:last[identity]=len(sequence)
            sequence.append(dict(length=len(headers),return_lag=lag,known_label=False,content_identity_supported=identity is not None))
        if len(sequence)>=2:
            out.append(dict(song_id=song['song_id'],family=families[song['song_id']],artist=song.get('artist'),
                partition=song['provisional_partition'],flagged=not(song.get('ai_generated') is False and song.get('is_junk') is False),sections=sequence))
    return out,dict(excluded)
