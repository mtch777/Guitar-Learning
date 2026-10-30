"""Complete explicit source brackets and conservative repeated-note contexts.

These are notation groups, not inferred phrases or emotional intentions.
Only the preceding complete Tier1 is read. All excluded groups stay visible.
"""
from collections import defaultdict
from fractions import Fraction as F
from source_fact_tier1 import project_documents

NOTE_EXPR=('hp','ghost','dead','tie','slide','bend','harmonic','harmonicFret','staccato','tremolo','vibrato','wideVibrato','leftHandVibrato','pickScrape','trill')
BEAT_EXPR=('palmMute','tapping','letRing','brushStroke','arpeggio','downStroke','downArpeggio','upStroke','pickStroke','fadeIn','tremoloBar','vibrato','wideVibrato','leftHandVibrato','vibratoWithTremoloBar','tremolo','harmonic','gradualVelocity','wahwah','golpe','sustainPedal','slapping')
SPECIAL=('graceNote','dots','dotted','tuplet','tupletStart','tupletStop')
SAFE_BEAT={'notes','type','duration','beamStart','beamStop','beam','beamMode','velocity','chord','rest',*BEAT_EXPR,*SPECIAL}
SAFE_NOTE={'string','fret','rest','velocity','accentuated',*NOTE_EXPR}
TYPES=(1,2,4,8,16,32,64,128)
PROGRAMS=(*range(24,32),33,34,36,37)

# These constrain changing a rhythm, not representing its written clock.
# Unknown/new reasons remain failures: only named non-clock conditions differ.
_NONCLOCK_REASONS=frozenset(('ACTIVE_BEAT_EXECUTION','ACTIVE_NOTE_EXECUTION',
    'ACCENT_DECLARATION','NOTE_DYNAMIC_OVERRIDE','DYNAMIC_BOUNDARY','CHORD_BOUNDARY',
    'NOT_IDENTICAL_PITCH','NOT_IDENTICAL_STRING_FRET','UNKNOWN_OR_CHANGING_DYNAMIC',
    'BOUNDARY_EXECUTION'))


def timing_owner_reasons(row):
    """Versioned written-time admission; does NOT authorize a rhythm change."""
    return [reason for reason in row['reasons']if reason not in _NONCLOCK_REASONS]


def duration(beat):
    d=beat.get('duration')
    return F(*d)*4 if type(d)is list and len(d)==2 and all(type(x)is int for x in d) and d[0]>0 and d[1]>0 else None


def expressions(beat):
    reasons=[]
    if any(beat.get(k) for k in SPECIAL):reasons.append('GRACE_DOTS_OR_TUPLET')
    if any(beat.get(k) for k in BEAT_EXPR):reasons.append('ACTIVE_BEAT_EXECUTION')
    if set(beat)-SAFE_BEAT:reasons.append('OTHER_BEAT_DECLARATION')
    for note in beat.get('notes',[]):
        if any(note.get(k) for k in NOTE_EXPR):reasons.append('ACTIVE_NOTE_EXECUTION')
        if 'accentuated' in note:reasons.append('ACCENT_DECLARATION')
        if note.get('velocity') is not None:reasons.append('NOTE_DYNAMIC_OVERRIDE')
        if set(note)-SAFE_NOTE:reasons.append('OTHER_NOTE_DECLARATION')
    return sorted(set(reasons))


def inventory(tier1):
    from source_tie_tier1 import extract_documents
    from local_dynamics import inventory as dynamics
    docs=project_documents(tier1);lower=extract_documents(docs)
    events={e['id']:e for e in lower['events']}
    states={s['occurrence_ref']:s for s in dynamics(tier1)['states']}
    frames={f['ordinal']:f for f in lower['measure_geometry']['frames']}
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings']
    lanes=defaultdict(list);brackets=[];invalid=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        pid=part['partId']
        for bar,m in enumerate(part.get('measures',[]),1):
            for voice,v in enumerate(m.get('voices',[])):
                active=None;bad=False;pos=F(0);known=True
                beats=v.get('beats',[]);total=sum((duration(b)or F(0) for b in beats if not b.get('graceNote')),F(0))
                for bi,b in enumerate(beats):
                    ref=f'{name}#/measures/{bar-1}/voices/{voice}/beats/{bi}'
                    node=dict(ref=ref,part=part,bar=bar,voice=voice,beat=bi,raw=b,pos=pos,duration=duration(b),known=known,total=total,
                              rest=bool(m.get('rest')or v.get('rest')),other_voices=any(j!=voice and vv.get('beats')for j,vv in enumerate(m.get('voices',[]))))
                    lane=lanes[pid,voice];lane.append(node)
                    a=b.get('beamStart',False);z=b.get('beamStop',False)
                    if type(a)is not bool or type(z)is not bool:
                        bad=True;invalid.append(dict(beat_ref=ref,reason='UNKNOWN_BOUNDARY_VALUE'))
                    elif a and z:
                        invalid.append(dict(beat_ref=ref,reason='SIMULTANEOUS_START_STOP'));active=None;bad=False
                    else:
                        if a:
                            if active is not None:bad=True
                            else:active=len(lane)-1;bad=False
                        if z:
                            if active is None:invalid.append(dict(beat_ref=ref,reason='ORPHAN_STOP'))
                            elif bad:invalid.append(dict(beat_ref=ref,reason='AMBIGUOUS_BRACKET'))
                            else:brackets.append((lane,active,len(lane)))
                            active=None;bad=False
                    if node['duration'] is None:known=False
                    elif not b.get('graceNote'):pos+=node['duration']
                if active is not None:invalid.append(dict(beat_ref=lane[active]['ref'],reason='OPEN_OR_CROSS_BAR_BRACKET'))
    rows=[]
    for lane,start,end in brackets:
        members=lane[start:end];first=members[0];part=first['part'];pid=part['partId'];bar=first['bar'];voice=first['voice'];frame=frames.get(bar)
        reasons=[];pitches=[];physical=[];marks=[];refs=[]
        if type(part.get('instrumentId'))is not int or part['instrumentId']not in PROGRAMS:reasons.append('OUTSIDE_GUITAR_BASS')
        if len(members)<2:reasons.append('NOT_REPEATED_GROUP')
        if frame is None or F(frame['span_q'])!=F(frame['signature'][0])*4/F(frame['signature'][1]):reasons.append('NONNOMINAL_FRAME')
        if any(w.get('bar')==bar and(w.get('part_id')is None or w['part_id']==pid)for w in warnings):reasons.append('SOURCE_CLOCK_WARNING')
        for j,n in enumerate(members):
            b=n['raw'];dq=n['duration'];typ=b.get('type');reasons.extend(expressions(b))
            if n['rest']or b.get('rest'):reasons.append('REST_CONTAINER')
            if n['other_voices']:reasons.append('OTHER_SAME_PART_VOICE')
            if frame is not None and n['total']!=F(frame['span_q']):reasons.append('VOICE_TOTAL_NOT_FRAME')
            if not n['known']or dq is None:reasons.append('UNKNOWN_CLOCK')
            if type(typ)is not int or typ not in TYPES or dq!=F(4,typ):reasons.append('NOT_FLAT_NOTATION')
            if j and b.get('velocity') is not None:reasons.append('DYNAMIC_BOUNDARY')
            if j and b.get('chord') is not None:reasons.append('CHORD_BOUNDARY')
            if len(b.get('notes',[]))!=1:reasons.append('NOT_SINGLE_NOTE');continue
            note=b['notes'][0];ref=f"event:{part['songId']}:{pid}:{bar}:{voice}:{n['beat']}:0";refs.append(ref)
            ev=events.get(ref);state=states.get(ref);st=note.get('string');fr=note.get('fret');tuning=part.get('tuning');capo=part.get('capo')
            if note.get('rest'):reasons.append('REST_NOTE')
            if type(st)is not int or type(fr)is not int or fr<0 or type(tuning)is not list or not 0<=st<len(tuning)or type(tuning[st])is not int or(capo is not None and type(capo)is not int):reasons.append('UNKNOWN_PHYSICAL')
            physical.append((st,fr));marks.append(state['marking']if state and state['known']else None)
            if ev is None or ev['pitch']is None or F(ev['pitch']).denominator!=1:reasons.append('UNKNOWN_PITCH')
            else:
                pitches.append(ev['pitch'])
                if frame is None or F(ev['onset_q'])!=F(frame['start_q'])+n['pos']or F(ev['duration_q'])!=dq:reasons.append('CLOCK_EVENT_CONFLICT')
        if len(pitches)!=len(members)or len(set(pitches))!=1:reasons.append('NOT_IDENTICAL_PITCH')
        if len(physical)!=len(members)or len(set(physical))!=1:reasons.append('NOT_IDENTICAL_STRING_FRET')
        if len(marks)!=len(members)or None in marks or len(set(marks))!=1:reasons.append('UNKNOWN_OR_CHANGING_DYNAMIC')
        span=sum((n['duration']or F(0)for n in members),F(0))
        if frame is None or span<=0 or first['pos']+span>F(frame['span_q']):reasons.append('OUTSIDE_FRAME')
        neighbors=lane[max(0,start-1):min(len(lane),end+1)]
        if any(expressions(n['raw'])for n in neighbors if n not in members):reasons.append('BOUNDARY_EXECUTION')
        closure=[n['ref']for n in neighbors]
        rows.append(dict(id='source-beam:'+first['ref']+'|'+members[-1]['ref'],part_id=pid,bar=bar,voice=voice,
            beat_refs=[n['ref']for n in members],occurrence_refs=refs,closure_refs=closure,
            start_q=str(F(frame['start_q'])+first['pos'])if frame else None,span_q=str(span),
            shares=[str(n['duration']/span)for n in members]if span>0 and all(n['duration']for n in members)else None,
            context_key=[pid,voice,len(members),frame['signature']if frame else None,str(first['pos']),str(span),marks[0]if marks else None],
            reasons=sorted(set(reasons))))
    return dict(schema='complete-source-rhythm-groups/1',groups=rows,invalid_boundaries=invalid)
