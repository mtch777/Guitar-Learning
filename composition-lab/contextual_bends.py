"""Scripted bend destinations/spacing/trajectories, without reference bends."""
from collections import defaultdict
from fractions import Fraction as F
from xml.etree import ElementTree as ET
from bend_analysis import analyze, extract_score, tie_chains
from reference_levers import BEND_PROPERTIES, write_property_edits


def sustain_context(report):
    """Return only permitted non-bend observations. No technique annotations."""
    tracks=[]
    for track in report['tracks']:
        chains,unresolved,dangling=tie_chains(track['occurrences'])
        if unresolved or dangling:raise ValueError('Unresolved ties')
        rows=[]
        for chain in chains:
            first=chain[0]
            rows.append(dict(id=first['occurrence'],midi=first['midi'],voice=first['voice'],
                             start=F(first['onset_q']),end=F(chain[-1]['onset_q'])+F(chain[-1]['duration_q']),
                             segments=[dict(id=r['note_id'],start=F(r['onset_q']),duration=F(r['duration_q'])) for r in chain]))
        tracks.append(dict(index=track['index'],program=track['program'],rows=rows))
    return tracks


def target_scores(note, following, support):
    """Observed accompanying pitch support and following-note proximity; no chord labels."""
    duration=note['end']-note['start'];left=note['start']+duration/2
    pcs=defaultdict(float)
    for other in support:
        overlap=max(F(0),min(note['end'],other['end'])-max(left,other['start']))
        if overlap and other['midi'] is not None:pcs[other['midi']%12]+=float(overlap)
    total=sum(pcs.values())
    result={}
    for step in (1,2):
        target=note['midi']+step
        support_score=pcs[target%12]/total if total else 0
        next_score=0 if following is None else max(0,1-abs(target-following['midi'])/5)
        result[step]=round(3*support_score+next_score,8)
    return result


def choose(notes,support,sparse=False):
    candidates=[]
    ordered=sorted(notes,key=lambda n:(n['start'],n['id']))
    for n in ordered:
        duration=n['end']-n['start']
        if n['midi'] is None or duration<F(1,2):continue
        # Avoid bending while another solo sustain sounds, including held notes.
        if any(o['id']!=n['id'] and o['start']<n['end'] and o['end']>n['start'] for o in ordered):continue
        following=next((o for o in ordered if o['start']>=n['end'] and o['midi'] is not None and o['voice']==n['voice']),None)
        scores=target_scores(n,following,support)
        step=max(scores,key=lambda s:(scores[s],-s))
        if scores[step]<=0:continue
        rank=scores[step]+min(float(duration),3)*.25
        candidates.append((rank,n,step,scores))
    selected={}
    # Selection is a transparent engineering budget, not an artist-derived bend rate.
    budget=max(1,round(len(ordered)*(.12 if sparse else .22)))
    for rank,n,step,scores in sorted(candidates,key=lambda x:(-x[0],x[1]['id'])):
        spacing=F(2) if sparse else F(1)
        if any(abs(n['start']-v['note']['start'])<spacing for v in selected.values()):continue
        selected[n['id']]=dict(note=n,step=step,scores=scores,rank=rank)
        if len(selected)>=budget:break
    return selected


def trajectory(peak,duration,varied=False):
    """Whole-sustain curve; later split across tied segments without retriggering."""
    if not varied:return [(F(0),F(0)),(F(1,2),F(peak)),(F(1),F(peak))]
    if duration>=2:return [(F(0),F(0)),(F(13,20),F(peak)),(F(1),F(peak))]
    if duration>=1:return [(F(0),F(0)),(F(1,3),F(peak)),(F(4,5),F(peak)),(F(1),F(0))]
    return [(F(0),F(0)),(F(2,3),F(peak)),(F(1),F(peak))]


def interpolate(points,x):
    for (a,v),(b,w) in zip(points,points[1:]):
        if a<=x<=b:return v+(w-v)*(x-a)/(b-a)
    return points[-1][1]


def segment_properties(points,left,right):
    """GPIF has at most two interior points sharing one value. Reject loss."""
    inside=[(x,y) for x,y in points if left<x<right]
    if len(inside)>2 or len({y for x,y in inside})>1:raise ValueError('Curve not exactly representable in GPIF segment')
    origin=interpolate(points,left);end=interpolate(points,right)
    values={'Bended':None,'BendOriginOffset':0,'BendOriginValue':origin*50,
            'BendDestinationOffset':100,'BendDestinationValue':end*50}
    if inside:
        values.update(BendMiddleOffset1=(inside[0][0]-left)/(right-left)*100,
                      BendMiddleOffset2=(inside[-1][0]-left)/(right-left)*100,
                      BendMiddleValue=inside[0][1]*50)
    out=[]
    for name,value in values.items():
        p=ET.Element('Property',name=name)
        ET.SubElement(p,'Enable' if value is None else 'Float').text=None if value is None else str(float(value))
        out.append(ET.tostring(p,encoding='unicode'))
    return out


def apply(source,destination,track_index,variant):
    if variant not in ('destinations','trajectories','spaced'):raise ValueError('Unknown variant')
    report=analyze(extract_score(source));context=sustain_context(report);lead=context[track_index]['rows']
    support=[n for t in context if t['index']!=track_index and t['program'] is not None
             and (0<=t['program']<=7 or 16<=t['program']<=39) for n in t['rows']]
    selected=choose(lead,support,variant=='spaced')
    edits={};allowed={};decisions=[];fallbacks=0
    counts=defaultdict(int)
    for t in context:
        for n in t['rows']:
            for s in n['segments']:counts[s['id']]+=1
    for n in lead:
        d=n['end']-n['start'];choice=selected.get(n['id'])
        points=trajectory(choice['step'],d,variant!='destinations') if choice else None
        proposed={}
        if points and d:
            try:
                for s in n['segments']:
                    proposed[s['id']]=segment_properties(points,(s['start']-n['start'])/d,(s['start']+s['duration']-n['start'])/d)
            except ValueError:
                # Explicitly fall back to one representable rise/hold; never approximate silently.
                fallbacks+=1;points=trajectory(choice['step'],d,False)
                proposed={s['id']:segment_properties(points,(s['start']-n['start'])/d,(s['start']+s['duration']-n['start'])/d) for s in n['segments']}
        for s in n['segments']:
            if counts[s['id']]!=1:raise ValueError('Shared note definition')
            edits[s['id']]=proposed.get(s['id'],[]);allowed[s['id']]=BEND_PROPERTIES
        if choice:decisions.append(dict(id=n['id'],step=choice['step'],scores=choice['scores']))
    audit=write_property_edits(source,destination,edits,allowed)
    return dict(**audit,variant=variant,selected=len(selected),curve_fallbacks=fallbacks,
                decisions=decisions,reference_bends_used=False,
                limitations=['Observed pitch support is not verified harmony','Engineering priors, not learned artist style','Base pitches and all non-bend data locked'])
