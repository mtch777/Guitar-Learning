"""Independent raw/native oracle for optional written membership contracts.

No context_membership or nominal_harmony producer imports. Existing independent
interval partitioning and accepted source clocks are reused explicitly.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from check_nominal_harmony import expected as raw_context,_fits
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents

VERSION='conditional-chord-membership-lock/1'
SCOPES=('ensemble_minus_edited','focal_part_minus_edited')
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)

def _request(request):
    if type(request)is not dict or set(request)!={'edited_refs','scope'}:raise ValueError('Exact membership request required')
    refs=request['edited_refs']
    if type(refs)is not list or not refs or any(type(r)is not str for r in refs)or refs!=sorted(set(refs)):raise ValueError('Sorted unique nonempty source refs required')
    if type(request['scope'])is not str or request['scope']not in SCOPES:raise ValueError('Unknown membership scope')
    return refs

def expected(tier1,request):
    refs=_request(request);view=raw_context(tier1);docs=project_documents(tier1);lower=extract_documents(docs);events={e['id']:e for e in lower['events']};inventory={r['occurrence_ref']:r for r in view['occurrence_inventory']}
    if not set(refs)<=set(events):return dict(status='MISSING',packet=None,reasons=['UNLOCATED_REQUESTED_OCCURRENCE'])
    reasons=set();coverage={r:F(0)for r in refs};contexts=[];parts=sorted(p['partId']for name,p in docs.items()if name.startswith('track-'))
    if view['geometry_status']!='AVAILABLE':reasons.add('UNAVAILABLE_SOURCE_GEOMETRY')
    if set(refs)&set(view['crossing_occurrence_refs']):reasons.add('CROSSING_EDITED_OCCURRENCE')
    for ref in refs:
        row=inventory[ref]
        if row['domain']!='pitched'or row['qualifications']or row['written_pitch_qualifications']:reasons.add('UNQUALIFIED_EDITED_OCCURRENCE')
    for cell in view['cells']:
        active=sorted(set(refs)&set(cell['active_refs']))
        if not active:continue
        for r in active:coverage[r]+=F(cell['end_q'])-F(cell['start_q'])
        bad={x['part_id']:x['reasons']for x in cell['part_refusals']}
        for part in sorted({events[r]['part_id']for r in active}):
            scopeparts=parts if request['scope']=='ensemble_minus_edited'else[part]
            support=sorted(r for r in cell['active_refs']if r not in refs and events[r]['part_id']in scopeparts)
            included=[r for r in support if inventory[r]['domain']!='nonpitched']
            if any(bad.get(p)for p in scopeparts)or bad.get(part):reasons.add('UNQUALIFIED_SOURCE_SCOPE')
            if any(inventory[r]['qualifications']or inventory[r]['written_pitch_qualifications']for r in included):reasons.add('UNQUALIFIED_CONTEXT_SUPPORT')
            values=[F(events[r]['pitch'])for r in included if events[r]['pitch']is not None]
            pcs={p%12 for p in values};hypotheses=[]
            if len(pcs)>=2 and all(p.denominator==1 for p in values):hypotheses=deepcopy(_fits(tuple(sorted(pcs))))
            if not hypotheses:reasons.add('NO_USABLE_HARMONIC_CONTEXT')
            memberships=[]
            for r in active:
                if events[r]['part_id']!=part:continue
                p=events[r]['pitch'];known=p is not None and F(p).denominator==1
                memberships.append(dict(occurrence_ref=r,values=[bool(F(p)%12 in{(h['root_pc']+x)%12 for x in h['formula']})for h in hypotheses]if known else[]))
            contexts.append(dict(cell_ref=cell['id'],start_q=cell['start_q'],end_q=cell['end_q'],part_ids=scopeparts,support_refs=support,included_refs=included,hypotheses=hypotheses,memberships=memberships))
    for ref in refs:
        if F(events[ref]['duration_q'])<=0 or coverage[ref]!=F(events[ref]['duration_q']):reasons.add('INCOMPLETE_EDITED_COVERAGE')
    packet=None if reasons else dict(version=VERSION,request=deepcopy(request),contexts=contexts)
    return dict(status='MISSING'if reasons else'SUPPORTED',packet=packet,reasons=sorted(reasons))

def _validate_packet(packet):
    if type(packet)is not dict or set(packet)!={'version','request','contexts'}or packet['version']!=VERSION:raise ValueError('Exact membership packet required')
    _request(packet['request'])
    if type(packet['contexts'])is not list or not packet['contexts']:raise ValueError('Nonempty context denominator required')
    for c in packet['contexts']:
        if type(c)is not dict or set(c)!={'cell_ref','start_q','end_q','part_ids','support_refs','included_refs','hypotheses','memberships'}:raise ValueError('Exact context fields required')
        for k in ('cell_ref','start_q','end_q'):
            if type(c[k])is not str:raise ValueError('Typed context address/clock required')
        if str(F(c['start_q']))!=c['start_q']or str(F(c['end_q']))!=c['end_q']or F(c['start_q'])>=F(c['end_q']):raise ValueError('Canonical positive rational cell required')
        for k,typ in [('part_ids',int),('support_refs',str),('included_refs',str)]:
            a=c[k]
            if type(a)is not list or any(type(x)is not typ for x in a)or a!=sorted(set(a)):raise ValueError('Canonical context reference inventory required')
        if type(c['hypotheses'])is not list or not c['hypotheses']:raise ValueError('Nonempty full hypothesis denominator required')
        for h in c['hypotheses']:
            if type(h)is not dict or set(h)!={'root_pc','kind','formula'}or type(h['root_pc'])is not int or not 0<=h['root_pc']<12 or type(h['kind'])is not str or type(h['formula'])is not list or any(type(x)is not int for x in h['formula']):raise ValueError('Typed native hypothesis required')
        if type(c['memberships'])is not list or not c['memberships']:raise ValueError('Membership inventory required')
        for m in c['memberships']:
            if type(m)is not dict or set(m)!={'occurrence_ref','values'}or type(m['occurrence_ref'])is not str or type(m['values'])is not list or len(m['values'])!=len(c['hypotheses'])or any(type(x)is not bool for x in m['values']):raise ValueError('Strict per-hypothesis membership booleans required')

def _identity(packet):
    x=deepcopy(packet)
    for c in x['contexts']:
        for m in c['memberships']:m.pop('values')
    return x

def assess(tier1,packet):
    _validate_packet(packet);current=expected(tier1,packet['request'])
    if current['status']=='MISSING':return dict(status='MISSING',reasons=current['reasons'],preserved=0,comparisons=0)
    if enc(_identity(current['packet']))!=enc(_identity(packet)):return dict(status='MISSING',reasons=['CONTEXT_CHANGED'],preserved=0,comparisons=0)
    comparisons=[a==b for c,d in zip(packet['contexts'],current['packet']['contexts'])for m,n in zip(c['memberships'],d['memberships'])for a,b in zip(m['values'],n['values'])]
    yes=sum(comparisons);status='SUPPORTED'if yes==len(comparisons)else'CONTRADICTED'if yes==0 else'AMBIGUOUS'
    return dict(status=status,reasons=[],preserved=yes,comparisons=len(comparisons))

def check(before_tier1,after_tier1,packet,reported=None):
    issues=[];result=None
    try:
        _validate_packet(packet);baseline=expected(before_tier1,packet['request'])
        if baseline['status']!='SUPPORTED'or enc(baseline['packet'])!=enc(packet):raise ValueError('Packet differs from complete original raw/native contract')
        result=assess(after_tier1,packet)
        if reported is not None and reported.get('status')!=result['status']:raise ValueError('Reported semantic outcome differs')
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_CONTEXT_MEMBERSHIP'if not issues else'FAIL',issues=issues,assessment=result,scope='Independent written membership constraint; no true-root, voice, acoustic or aesthetic judgment')
