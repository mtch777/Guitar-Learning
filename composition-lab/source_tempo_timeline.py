"""Opt-in declared score clock. No recording synchronization or role decisions.

Measure-index base is explicit because capture revisions use different schemes.
Repeat/navigation playback must be supplied, never guessed. Returned times are
score-derived hypotheses and cannot be used as verified recording attestations.
"""
from fractions import Fraction
from math import isfinite


def _fraction(v):
    if isinstance(v,bool):raise ValueError('boolean time')
    try:f=Fraction(str(v))
    except (ValueError,ZeroDivisionError,TypeError) as e:raise ValueError('invalid rational time') from e
    if not isfinite(float(f)):raise ValueError('nonfinite time')
    return f


def source_tempo_timeline(bars, tempo_events, *, measure_index_base,
                          playback_order=None, navigation_present=False):
    if type(navigation_present)is not bool:raise ValueError('navigation flag must be boolean')
    if type(measure_index_base)is not int or measure_index_base not in(0,1):raise ValueError('explicit measure index base0 or1 required')
    if not bars:raise ValueError('bars required')
    normalized=[];ids=set();last=Fraction(0)
    for b in bars:
        bid=b['bar'];q=_fraction(b['start_q']);span=_fraction(b['span_q'])
        if type(bid)is not int or bid<1 or bid in ids or q!=last or span<=0:raise ValueError('bars must be unique, contiguous from zero and positive')
        ids.add(bid);normalized.append((bid,q,span));last=q+span
    requires_order=navigation_present or any(b.get('repeat_start') or b.get('repeat_count') or b.get('endings') for b in bars)
    if playback_order is None:
        if requires_order:raise ValueError('explicit playback order required for repeats/navigation')
        order=[b[0]for b in normalized]
    else:
        order=list(playback_order)
        if not order or any(type(b)is not int or b not in ids for b in order):raise ValueError('invalid playback order')
    changes={}
    for e in tempo_events:
        m=e.get('measure');bpm=e.get('bpm')
        if type(m)is not int or not 0<=m-measure_index_base<len(bars):raise ValueError('tempo measure outside score')
        if isinstance(e.get('position',0),bool) or type(e.get('linear',False))is not bool or type(e.get('type',4))is not int or e.get('position',0)!=0 or e.get('linear',False) or e.get('type',4)!=4:raise ValueError('unsupported intra-bar, ramped or nonquarter tempo')
        if isinstance(bpm,bool) or not isinstance(bpm,(int,float)) or not isfinite(bpm) or bpm<=0:raise ValueError('invalid BPM')
        i=m-measure_index_base
        if i in changes and changes[i]!=bpm:raise ValueError('conflicting tempos')
        changes[i]=bpm
    if 0 not in changes:raise ValueError('initial tempo missing; no default assumed')
    by_bar={};bpm=None
    for i,(bid,q,span)in enumerate(normalized):
        bpm=changes.get(i,bpm);by_bar[bid]=(q,span,bpm)
    t=0.;visits=[];previous_index=None;current_bpm=None
    written_indices={v[0]:i for i,v in enumerate(normalized)}
    for index,bid in enumerate(order):
        q,span,bpm=by_bar[bid];written_index=written_indices[bid]
        sequential=previous_index is not None and written_index==previous_index+1
        if not sequential and written_index not in changes and (current_bpm is None or current_bpm!=bpm):
            raise ValueError('ambiguous tempo across playback jump; explicit destination tempo required')
        end=t+float(span)*60/bpm
        previous_index=written_index;current_bpm=bpm
        visits.append({'visit':index+1,'bar':bid,'start_q':str(q),'span_q':str(span),'bpm':bpm,'score_start_seconds':t,'score_end_seconds':end,'validation_status':'unverified_score_clock'})
        t=end
    return {'schema':'source-tempo-timeline/1','measure_index_base':measure_index_base,'explicit_playback_order':playback_order is not None,'visits':visits,'score_duration_seconds':t,'limitations':['Declared score tempo is not verified recording time.','Repeated bar visits are distinct; never collapse them by bar number.','Omissions, version differences and expressive timing need independent alignment.']}


