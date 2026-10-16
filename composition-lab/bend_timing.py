"""Research-informed, scripted bend arrival scheduling. No reference bends/model calls."""
from collections import defaultdict
from fractions import Fraction as F
from bend_analysis import analyze,extract_score
from contextual_bends import sustain_context,choose,segment_properties
from reference_levers import BEND_PROPERTIES,write_property_edits


def pitch_support(target,time,support):
    """Normalize by active track, avoiding domination by dense chord notation."""
    groups=defaultdict(list)
    for n in support:
        if n['start']<=time<n['end'] and n['midi'] is not None:groups[n['track']].append(n['midi']%12)
    return sum(values.count(target%12)/len(values) for values in groups.values())/len(groups) if groups else 0.


def schedule(note,step,support,measures,mode):
    if mode not in ('pulse','delayed','response'):raise ValueError('Unknown timing mode')
    start,end=note['start'],note['end'];duration=end-start
    # Complete the rise within one written segment: no fractional pitch at a tie seam.
    segment=next((s for s in note['segments'] if s['duration']>=F(1,4)),None)
    if segment is None:raise ValueError('No representable rise window')
    left=segment['start'];right=left+segment['duration']
    latest=min(right,end-F(1,8));earliest=left+F(1,8)
    candidates={earliest,latest}
    for m in measures:
        n,d=map(int,m['time_signature'].split('/'));bar=F(m['onset_q'])
        beat=F(4,d)*(3 if n>3 and n%3==0 and d==8 else 1)
        for i in range(2*n+1):
            q=bar+i*beat/2
            if earliest<=q<=latest:candidates.add(q)
    for s in support:
        if earliest<=s['start']<=latest:candidates.add(s['start'])
    target=note['midi']+step
    def rank(q):
        m=next(m for m in reversed(measures) if F(m['onset_q'])<=q)
        n,d=map(int,m['time_signature'].split('/'));beat=F(4,d)*(3 if n>3 and n%3==0 and d==8 else 1)
        phase=(q-F(m['onset_q']))/beat
        accent=1. if phase.denominator==1 else .45 if (phase*2).denominator==1 else 0.
        harmonic=pitch_support(target,q,support)
        # Mode shifts preference within valid arrival windows, not note placement or pitch.
        progress=float((q-left)/(right-left))
        return 2*harmonic+accent+(progress if mode=='delayed' else -progress*.35)
    arrival=max(sorted(candidates),key=rank)
    if mode=='pulse':rise=min(F(1,4),(arrival-left))
    elif mode=='delayed':rise=min(F(3,4),arrival-left)
    else:rise=min(F(1,2),arrival-left)
    begin=arrival-rise
    points=[(start,F(0))]
    if begin>start:points.append((begin,F(0)))
    points.append((arrival,F(step)))
    release=None
    # Release only within the final written segment; cadence/end quality is not scored.
    last=note['segments'][-1]
    if mode=='response' and last['duration']>=F(1,2) and end-arrival>=F(1,2):
        release=max(arrival,last['start'],end-F(1,2))
        if release>arrival:points.append((release,F(step)))
        points.append((end,F(0)))
    else:points.append((end,F(step)))
    points=sorted(set(((q-start)/duration,v) for q,v in points))
    return points,dict(begin_q=str(begin),arrival_q=str(arrival),release_q=str(release) if release is not None else None,
                       target_support_at_arrival=pitch_support(target,arrival,support))


def apply(source,destination,track_index,mode):
    score=extract_score(source);report=analyze(score);tracks=sustain_context(report)
    lead=tracks[track_index]['rows'];support=[]
    for t in tracks:
        if t['index']!=track_index and t['program'] is not None and (0<=t['program']<=7 or 16<=t['program']<=39):
            support.extend(dict(n,track=t['index']) for n in t['rows'])
    selected=choose(lead,support) # Fixed across all timing modes; preserves v2 selections/targets.
    counts=defaultdict(int)
    for t in tracks:
        for n in t['rows']:
            for s in n['segments']:counts[s['id']]+=1
    edits={};allowed={};decisions=[]
    for n in lead:
        choice=selected.get(n['id']);d=n['end']-n['start'];points=None
        if choice:
            points,detail=schedule(n,choice['step'],support,score['tracks'][track_index]['measures'],mode)
            decisions.append(dict(id=n['id'],step=choice['step'],**detail))
        for s in n['segments']:
            if counts[s['id']]!=1:raise ValueError('Shared note definition')
            edits[s['id']]=segment_properties(points,(s['start']-n['start'])/d,(s['start']+s['duration']-n['start'])/d) if points else []
            allowed[s['id']]=BEND_PROPERTIES
    audit=write_property_edits(source,destination,edits,allowed)
    return dict(**audit,method=mode,selected=len(selected),decisions=decisions,reference_bends_used=False,
                scope='Fixed v2 selections and displacement; only bend start/arrival/hold/release vary',
                limitations=['Scripted timing preferences, not learned artist style','Observed pitch support is not verified harmony','No phrase-end quality objective','No base-pitch or fingering changes'])
