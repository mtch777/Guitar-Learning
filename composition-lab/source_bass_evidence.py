"""Target-independent lowest ACTIVE written pitch; not a structural bass role.

Source IDs/ties remain literal evidence. No key/root/attack/function is inferred.
"""
from fractions import Fraction as F
from bisect import bisect_right

OBSERVATION_FIELDS={'id','mask','previous_mask','sequence','start_q','end_q'}
EVENT_FIELDS={'id','mc','mc_onset','onset_q','duration_q','pitch','source_tpc','source_name','source_staff','source_voice','source_tied','source_gracenote'}


def extract_bass_features(piece,observations,source_events):
    if type(piece)is not str or not piece:raise ValueError('Explicit piece identity required')
    if type(observations)is not list or type(source_events)is not list:raise ValueError('Observation/event lists required')
    changes={};seen=set()
    for event in source_events:
        if not {'id','onset_q','duration_q','pitch'}<=set(event)<=EVENT_FIELDS:raise ValueError('Only source observation event fields accepted')
        ident=event['id'];pitch=event['pitch']
        if type(ident)is not str or not ident or ident in seen:raise ValueError('Unique source note IDs required')
        seen.add(ident)
        if pitch is not None and (type(pitch)is not int or not 0<=pitch<=127):raise ValueError('Typed source MIDI or explicit unknown required')
        a=F(event['onset_q']);duration=F(event['duration_q'])
        if duration<0:raise ValueError('Negative source duration')
        if duration==0:continue
        changes.setdefault(a,[]).append((1,ident,pitch));changes.setdefault(a+duration,[]).append((-1,ident,pitch))
    clocks=sorted(changes);cursor=0;active={};rows=[];ids=set();last_end=None
    for row in observations:
        if set(row)!=OBSERVATION_FIELDS or type(row['id'])not in (int,str) or row['id']in ids:raise ValueError('Unique typed label-free observation required')
        ids.add(row['id'])
        if type(row['mask'])is not int or not 0<=row['mask']<4096:raise ValueError('Typed observed PC mask required')
        for k in ('start_q','end_q'):
            if type(row[k])is not str or str(F(row[k]))!=row[k]:raise ValueError('Canonical rational observation clock required')
        a,b=F(row['start_q']),F(row['end_q'])
        if b<=a or last_end is not None and a<last_end:raise ValueError('Positive ordered nonoverlapping observations required')
        last_end=b
        while cursor<len(clocks)and clocks[cursor]<=a:
            for direction,ident,pitch in sorted(changes[clocks[cursor]]):
                if direction<0:active.pop(ident,None)
                else:active[ident]=pitch
            cursor+=1
        if cursor<len(clocks)and clocks[cursor]<b:raise ValueError('Source note change inside observation cell')
        refs=sorted(active);unknown=sorted(i for i,p in active.items()if p is None);known=[p for p in active.values()if p is not None]
        expected=sum(1<<p for p in {p%12 for p in known})
        if expected!=row['mask']:raise ValueError('Source-derived PC mask disagrees with fixed observation')
        status='UNRESOLVED'if unknown else'EMPTY'if not refs else'KNOWN'
        lowest=min(known)if status=='KNOWN'else None
        rows.append(dict(piece=piece,observation_ref=row['id'],start_q=row['start_q'],end_q=row['end_q'],status=status,
            lowest_midi=lowest,lowest_pc=None if lowest is None else lowest%12,
            lowest_note_refs=[]if lowest is None else sorted(i for i,p in active.items()if p==lowest),
            active_note_refs=refs,unknown_note_refs=unknown))
    return rows
