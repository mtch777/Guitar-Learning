"""Optional written chord-membership lock over unchanged surrounding notes.

No root selection or pitch backup. Exact-fit aliases share a pitch-class set;
this predicate preserves inclusion in that set over the entire note duration.
The same source projection and membership equations check either direction.
"""
from copy import deepcopy
from fractions import Fraction as F
import nominal_harmony as nominal

VERSION='conditional-chord-membership-lock/1'
SCOPES=('ensemble_minus_edited','focal_part_minus_edited')
MEMBERSHIP={'TEMPLATE_CHORD_TONE':True,'TEMPLATE_NONMEMBER':False}


def validate_request(request):
    if type(request)is not dict or set(request)!={'edited_refs','scope'} or request['scope']not in SCOPES:
        raise ValueError('Explicit edited set and context scope required')
    refs=request['edited_refs']
    if type(refs)is not list or not refs or any(type(r)is not str or not r for r in refs) or refs!=sorted(set(refs)):
        raise ValueError('Unique sorted occurrence refs required')


def compile_lock(tier1,request):
    """Derive semantic parameters from complete preceding-tier facts only."""
    validate_request(request)
    c=nominal.prepare_tier1(tier1);view=nominal.build(c)
    return from_context(c,view,request)


def from_context(c,view,request):
    """Internal reuse for several scopes on the same immutable source view."""
    validate_request(request)
    refs=request['edited_refs'];reasons=[];events=c['events']
    if not set(refs)<=set(events):
        return dict(status='MISSING',packet=None,reasons=['UNLOCATED_REQUESTED_OCCURRENCE'])
    edited=nominal.edited_set_context(c,view,events,refs)
    paths={ref:[] for ref in refs};contexts=[]
    rows={r['occurrence_ref']:r for r in view['occurrence_inventory']}
    for ref in refs:
        reasons.extend(rows[ref]['qualifications'])
        reasons.extend(rows[ref]['written_pitch_qualifications'])
        if rows[ref]['domain']!='pitched':reasons.append('FOCAL_NOT_KNOWN_PITCHED')
    for cell in edited['cells']:
        if cell['scope']!=request['scope']:continue
        pop=cell['population'];hypotheses=pop['hypotheses']
        reasons.extend(cell['scope_refusals']+cell['focal_refusals']+pop['refusals'])
        if not hypotheses:reasons.append('NO_SUPPORTED_CHORD_POPULATION')
        for ref in pop['included_refs']:
            reasons.extend(rows[ref]['written_pitch_qualifications'])
        memberships=[]
        for q in cell['queries']:
            ref=q['occurrence_ref'];paths[ref].append((F(cell['start_q']),F(cell['end_q'])))
            values=[MEMBERSHIP.get(r['before']['status']) for r in q['role_changes']]
            if len(values)!=len(hypotheses) or not values or any(v is None for v in values):
                reasons.append('UNKNOWN_FOCAL_MEMBERSHIP')
            memberships.append(dict(occurrence_ref=ref,values=values))
        contexts.append(dict(cell_ref=cell['cell_ref'],start_q=cell['start_q'],end_q=cell['end_q'],
            part_ids=deepcopy(cell['part_ids']),support_refs=deepcopy(pop['support_refs']),
            included_refs=deepcopy(pop['included_refs']),hypotheses=deepcopy(hypotheses),memberships=memberships))
    for ref,path in paths.items():
        start=F(events[ref]['onset_q']);end=start+F(events[ref]['duration_q']);cursor=start
        if end<=start:reasons.append('NONPOSITIVE_FOCAL_DURATION')
        for a,b in sorted(path):
            if a!=cursor or b<=a:reasons.append('INCOMPLETE_FOCAL_TIME_COVERAGE')
            cursor=b
        if not path or cursor!=end:reasons.append('INCOMPLETE_FOCAL_TIME_COVERAGE')
    if reasons:return dict(status='MISSING',packet=None,reasons=sorted(set(reasons)))
    packet=dict(version=VERSION,request=deepcopy(request),contexts=contexts)
    return dict(status='SUPPORTED',packet=packet,reasons=[])


def _split(packet):
    if type(packet)is not dict or set(packet)!={'version','request','contexts'} or packet['version']!=VERSION:
        raise ValueError('Typed membership contract required')
    validate_request(packet['request'])
    if type(packet['contexts'])is not list or not packet['contexts']:raise ValueError('Complete context denominator required')
    descriptor=deepcopy(packet);values=[]
    for row in descriptor['contexts']:
        if type(row)is not dict or set(row)!={'cell_ref','start_q','end_q','part_ids','support_refs','included_refs','hypotheses','memberships'}:
            raise ValueError('Typed context identity required')
        if type(row['memberships'])is not list or not row['memberships']:raise ValueError('Complete membership rows required')
        if type(row['hypotheses'])is not list or not row['hypotheses']:raise ValueError('Complete hypothesis denominator required')
        refs=[m.get('occurrence_ref') if type(m)is dict else None for m in row['memberships']]
        if any(type(r)is not str for r in refs) or refs!=sorted(set(refs)):raise ValueError('Canonical occurrence rows required')
        for member in row['memberships']:
            if type(member)is not dict or set(member)!={'occurrence_ref','values'}:raise ValueError('Typed membership row required')
            v=member.pop('values')
            if type(v)is not list or not v or any(type(x)is not bool for x in v):raise ValueError('Strict Boolean membership required')
            if len(v)!=len(row['hypotheses']):raise ValueError('Per-occurrence hypothesis denominator differs')
            values.extend(v)
    return descriptor,values


def assess(tier1,packet):
    """Check requested semantic equality, not literal pitch equality."""
    wanted,old=_split(packet)
    actual=compile_lock(tier1,packet['request'])
    if actual['status']!='SUPPORTED':return dict(status='MISSING',reasons=actual['reasons'],preserved=0,changed=0)
    current,new=_split(actual['packet'])
    if nominal.encoded(wanted)!=nominal.encoded(current) or len(old)!=len(new):
        return dict(status='MISSING',reasons=['CONTEXT_CHANGED'],preserved=0,changed=0)
    preserved=sum(a==b for a,b in zip(old,new));changed=len(old)-preserved
    status='SUPPORTED' if not changed else 'CONTRADICTED' if not preserved else 'AMBIGUOUS'
    return dict(status=status,reasons=[],preserved=preserved,changed=changed)


def verify(tier1,packet):
    result=assess(tier1,packet)
    if result['status']!='SUPPORTED':raise ValueError('Requested chord-membership lock: '+result['status']+' '+','.join(result['reasons']))
    return result


def attach(upper,request):
    from connected_tier2 import strip_lower,realize
    if 'membership_lock'in upper:raise ValueError('Never silently replace an active membership lock')
    result=compile_lock(realize(strip_lower(upper)),request)
    if result['status']!='SUPPORTED':raise ValueError('Membership lock unavailable: '+','.join(result['reasons']))
    out=deepcopy(upper);out['membership_lock']=result['packet'];return out
