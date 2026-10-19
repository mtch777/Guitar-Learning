"""Preserve explicit generated theme returns while keeping literal data locks.

No theme discovery: the supplied plan is a structural constraint. Material is
copied from the current proposal's first occurrence, never an original pitch bank.
Intermediate pitch/rhythm masks are unsupported when the plan contains returns.
"""
from copy import deepcopy
from fractions import Fraction as F
from generation_freedom import validate,facets

DIMENSIONS=('harmony','melody','bass','rhythm')


def plan_returns(score,sections):
    validate(score)
    if not isinstance(sections,list) or not sections:raise ValueError('Explicit nonempty section plan required')
    total=len(score['tracks'][0]['measures']);cursor=0;bank={};returns=[]
    for index,s in enumerate(sections):
        if not isinstance(s,dict) or set(s)-{'start','length','identity','return_lag'}:raise ValueError('Unsupported section plan fields')
        for name in ('start','length','identity'):
            if isinstance(s.get(name),bool) or not isinstance(s.get(name),int):raise ValueError('Integer plan coordinates required')
        start,length,identity=s['start'],s['length'],s['identity']
        if start!=cursor or length<=0 or identity<0 or start+length>total:raise ValueError('Contiguous positive bounded section plan required')
        if 'return_lag' in s:
            lag=s['return_lag']
            if isinstance(lag,bool) or not isinstance(lag,int) or lag<0 or lag>index:
                raise ValueError('Return lag conflicts with identity history')
            if (lag==0 and identity in bank) or (lag>0 and (sections[index-lag]['identity']!=identity or sections[index-lag]['length']<length)):
                raise ValueError('Return lag conflicts with identity history')
        if identity in bank:
            origin,available=bank[identity]
            if length>available:raise ValueError('Return exceeds established material')
            for track in score['tracks']:
                for offset in range(length):
                    a,b=(track['measures'][i+offset] for i in (origin,start))
                    if a.get('section') is None or a.get('section')!=b.get('section'):raise ValueError('Plan conflicts with section labels')
                    def topology(m):return [[len(e['notes']) for e in v] for v in m['voices']]
                    if a['time_signature']!=b['time_signature'] or topology(a)!=topology(b):
                        raise ValueError('Return conflicts with locked meter/event/rest topology')
            returns.append(dict(identity=identity,origin=origin,start=start,length=length))
        else:bank[identity]=(start,length)
        cursor+=length
    if cursor!=total:raise ValueError('Section plan must cover every bar')
    return returns


def apply(score,sections,roles,controls):
    returns=plan_returns(score,sections);before=facets(score,roles)
    amounts={d:controls.get(d,0) for d in DIMENSIONS}
    if any(isinstance(v,bool) or not isinstance(v,int) or not 0<=v<=100 for v in amounts.values()):raise ValueError('Integer freedom0–100 required')
    if returns and any(v not in (0,100) for v in amounts.values()):
        raise ValueError('Explicit return preservation requires pitch/rhythm controls at0or100')
    out=deepcopy(score);changed=0
    for r in returns:
        for ti,track in enumerate(out['tracks']):
            for offset in range(r['length']):
                target=track['measures'][r['start']+offset]
                voices=deepcopy(score['tracks'][ti]['measures'][r['origin']+offset]['voices'])
                for vi,voice in enumerate(voices):
                    for ei,e in enumerate(voice):
                        previous=target['voices'][vi][ei]
                        for field in ('local_onset_q','duration_q'):
                            if F(previous[field])==F(e[field]):e[field]=previous[field]
                        for ni,n in enumerate(e['notes']):
                            old_note=previous['notes'][ni]
                            # Canonical validation guarantees absent/None ties
                            # and absent/empty technique lists are equivalent.
                            if all(n[k]==old_note[k] for k in ('midi','string','fret')):
                                e['notes'][ni]=deepcopy(old_note)
                        q=F(target['onset_q'])+F(e['local_onset_q'])
                        old=previous['onset_q']
                        e['onset_q']=old if F(old)==q else str(q)
                changed+=int(target['voices']!=voices);target['voices']=voices
    validate(out);after=facets(out,roles)
    for d in DIMENSIONS:
        if amounts[d]==0 and before[d]!=after[d]:raise ValueError('Return conflicts with literal '+d+' lock')
    for d in ('form','instrumentation','performance'):
        if before[d]!=after[d]:raise ValueError('Return conflicts with fixed '+d+' data')
    return out,dict(returns=returns,changed_track_bars=changed,locked_facets_exact=True,
        limitations=['Explicit plan, not discovered thematic identity or musical function.',
            'First-occurrence proposed material reused exactly; expression is applied separately afterward.',
            'Pitch/rhythm intermediate settings rejected when returns exist.'])
