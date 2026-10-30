"""Independent literal-source oracle for the bounded middle-note operation."""
from copy import deepcopy
from fractions import Fraction as F
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents
from check_context_membership import check as check_membership


def expected(before,target_ref,donor_ref):
    """Parent-only raw fact answer from an actual donor; never stage in worker."""
    refs=[]
    for ref in (target_ref,donor_ref):
        _,_,pid,bar,voice,beat,note=ref.split(':')
        refs.append(f'track-{pid}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}/notes/{note}')
    rows={r['id']:r for r in before['facts']}
    if rows[refs[0]+'/string']['value']!=rows[refs[1]+'/string']['value']:raise ValueError('Physical string changed')
    value=rows[refs[1]+'/fret']['value'];out=deepcopy(before)
    next(r for r in out['facts']if r['id']==refs[0]+'/fret')['value']=value
    return out


def check(before,after,target,chosen,contract):
    issues=[];harmonic=None
    try:
        if not chosen['donor_refs']:raise ValueError('Missing observed donor')
        if after!=expected(before,target['target_ref'],chosen['donor_refs'][0]):raise ValueError('Output differs from the one allowed observed physical note')
        original={r['id']:r for r in extract_documents(project_documents(before))['events']}
        actual={r['id']:r for r in extract_documents(project_documents(after))['events']}
        refs=target['occurrence_refs']
        if len(refs)!=3 or refs[1]!=target['target_ref']:raise ValueError('Complete ordered triple required')
        old=[F(original[r]['pitch'])for r in refs];new=[F(actual[r]['pitch'])for r in refs]
        if old[0]!=new[0]or old[2]!=new[2]:raise ValueError('Outside pitches changed')
        directions=lambda v:[(v[i+1]>v[i])-(v[i+1]<v[i])for i in(0,1)]
        if directions(old)!=directions(new):raise ValueError('Signed contour changed')
        harmonic=check_membership(before,after,contract)
        if harmonic['status']!='PASS_INDEPENDENT_CONTEXT_MEMBERSHIP':raise ValueError(harmonic)
        if harmonic['assessment']['status']!='SUPPORTED':raise ValueError('Conditional harmonic membership changed')
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_MIDDLE_NOTE_CHANGE'if not issues else'FAIL',issues=issues,
        harmonic=harmonic,scope='Complete raw fields except one observed same-string fret, both contour directions, entire-duration conditional harmonic membership; no listening judgment')
