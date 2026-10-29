"""Independent source dynamics/influence oracle; no producer state or choices.

Written marking ordinals and MIDI loudness are deliberately not inferred here.
"""
from collections import defaultdict
from copy import deepcopy
import json
from source_fact_tier1 import validate,project_documents

MARKINGS=('ppp','pp','p','mp','mf','f','ff','fff')
SCHEMA='source-local-dynamics/1'
def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def _known(v):return type(v)is str and v in MARKINGS

def inventory(tier1):
    validate(tier1);docs=project_documents(tier1);declarations=[];states=[]
    for name,part in sorted(docs.items()):
        if not name.startswith('track-'):continue
        pid=part['partId'];song=part['songId'];current={};guard_origin={};byref={}
        def declare(scope,value,mi,vi,bi,ni):
            ptr=f'{name}#/measures/{mi-1}/voices/{vi}/beats/{bi}'
            if ni is not None:ptr+=f'/notes/{ni}'
            ref=ptr+'/velocity';row=dict(fact_ref=ref,scope=scope,part_id=pid,voice=vi,bar=mi,beat=bi,note=ni,marking=deepcopy(value),known=_known(value),influence_refs=[],reasons=[]if _known(value)else['UNKNOWN_MARKING'])
            declarations.append(row);byref[ref]=row;return ref
        for mi,m in enumerate(part.get('measures',[]),1):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    beatref=declare('beat',b['velocity'],mi,vi,bi,None)if'velocity'in b else None
                    explicit=b.get('velocity')is not None
                    if explicit:
                        prior=guard_origin.get(vi)
                        if _known(b['velocity']):guard_origin[vi]=beatref
                        elif prior is not None:byref[prior]['reasons'].append('UNKNOWN_BEAT_BOUNDARY')
                        current[vi]=beatref
                    for ni,n in enumerate(b.get('notes',[])):
                        noteref=declare('note',n['velocity'],mi,vi,bi,ni)if'velocity'in n else None
                        if n.get('rest'):continue
                        ref=f'event:{song}:{pid}:{mi}:{vi}:{bi}:{ni}'
                        if n.get('velocity')is not None:
                            origin=noteref;provenance='note_explicit'
                            if not _known(n['velocity'])and vi in guard_origin:byref[guard_origin[vi]]['reasons'].append('UNKNOWN_NOTE_OVERRIDE')
                        elif vi in current:origin=current[vi];provenance='beat_explicit'if explicit else'inherited_explicit'
                        else:origin=None;provenance='unspecified'
                        raw=byref[origin]['marking']if origin else None;known=_known(raw)
                        states.append(dict(occurrence_ref=ref,marking=raw if known else None,known=known,provenance=provenance,origin_fact_ref=origin))
                        if origin:byref[origin]['influence_refs'].append(ref)
    for d in declarations:
        d['influence_refs']=sorted(d['influence_refs'])
        if not d['influence_refs']:d['reasons'].append('NO_INFLUENCED_NOTES')
        d['reasons']=sorted(set(d['reasons']))
    return dict(schema=SCHEMA,declarations=sorted(declarations,key=lambda d:d['fact_ref']),states=sorted(states,key=lambda s:s['occurrence_ref']))

def choices(tier1,target_ref):
    return _choices(inventory(tier1),target_ref)

def _choices(inv,target_ref):
    target=next((d for d in inv['declarations']if d['fact_ref']==target_ref),None)
    if target is None:raise ValueError('Original source velocity declaration required')
    grouped=defaultdict(list)
    if target['known']and not target['reasons']:
        for d in inv['declarations']:
            if d['fact_ref']==target_ref or not d['known']or d['reasons']:continue
            if(d['part_id'],d['voice'],d['scope'])==(target['part_id'],target['voice'],target['scope']):grouped[d['marking']].append(d['fact_ref'])
    options=[dict(marking=m,donor_refs=sorted(grouped[m]),changed=m!=target['marking'])for m in sorted(grouped)]
    return dict(target_ref=target_ref,options=options)

def check(before,after,target_fact_ref,donor_fact_refs,decision=None):
    return _check(before,after,target_fact_ref,donor_fact_refs,decision)

def _check(before,after,target_fact_ref,donor_fact_refs,decision=None,prepared=None):
    issues=[];affected=[];option=None
    try:
        validate(before);validate(after);a=inventory(before)if prepared is None else prepared;b=inventory(after)
        if encoded({k:v for k,v in before.items()if k!='facts'})!=encoded({k:v for k,v in after.items()if k!='facts'}):raise ValueError('Source envelope changed')
        if len(before['facts'])!=len(after['facts']):raise ValueError('Source fact denominator changed')
        index={d['fact_ref']:d for d in a['declarations']};target=index.get(target_fact_ref)
        if target is None:raise ValueError('Original velocity declaration target required')
        changed=False;newmark=target['marking']
        for x,y in zip(before['facts'],after['facts']):
            if encoded(x)==encoded(y):continue
            if x['id']!=target_fact_ref or encoded({k:v for k,v in x.items()if k!='value'})!=encoded({k:v for k,v in y.items()if k!='value'}):raise ValueError('Outside dynamic declaration source fact changed')
            changed=True;newmark=y['value']
        if type(donor_fact_refs)is not list or any(type(r)is not str for r in donor_fact_refs)or donor_fact_refs!=sorted(set(donor_fact_refs)):raise ValueError('Canonical unique source donor refs required')
        released=decision.get('released')if decision is not None else changed
        if decision is not None:
            if type(decision)is not dict or type(decision.get('released'))is not bool or type(decision.get('changed'))is not bool or decision['changed']!=changed:raise ValueError('Decision disagrees with actual source change')
        if changed and not released:raise ValueError('Unreleased operation changed source dynamics')
        if changed or released:
            palette=_choices(a,target_fact_ref)['options']
            if not palette:
                if changed or donor_fact_refs or decision is None or decision.get('chosen')is not None or decision.get('status')!='NO_ADMITTED_CHOICE':raise ValueError('Empty independent palette must retain an exact no-choice output')
            else:
                if not target['known']or target['reasons']:raise ValueError('Target has unavailable dynamic influence')
                matches=[o for o in palette if o['marking']==newmark]
                if len(matches)!=1:raise ValueError('No eligible independent source marking')
                option=matches[0]
                if donor_fact_refs!=option['donor_refs']:raise ValueError('Incomplete/forged source marking donor denominator')
                if decision is not None and decision.get('chosen')!=option:raise ValueError('Chosen source option differs')
        elif donor_fact_refs or decision is not None and decision.get('chosen')is not None:raise ValueError('Unreleased operation claims a donor choice')
        affected=target['influence_refs']if changed else[];affectedset=set(affected)
        oldstates={r['occurrence_ref']:r for r in a['states']};newstates={r['occurrence_ref']:r for r in b['states']}
        if set(oldstates)!=set(newstates):raise ValueError('Source note-state denominator changed')
        for ref,old in oldstates.items():
            new=newstates[ref]
            if ref not in affectedset:
                if encoded(old)!=encoded(new):raise ValueError('Outside effective dynamics changed')
            else:
                if new['marking']!=newmark or new['known']is not True or encoded({k:v for k,v in old.items()if k not in('marking','known')})!=encoded({k:v for k,v in new.items()if k not in('marking','known')}):raise ValueError('Complete inherited influence was not realized')
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_LOCAL_DYNAMICS'if not issues else'FAIL',issues=issues,affected_refs=affected,option=option,scope='Exact written declaration/inheritance/source locks; no loudness linearity, acoustic tails, stylistic fit or human listening claim')


class Oracle:
    """Cache only this oracle's immutable raw source inventory, never producer data."""
    def __init__(self,tier1):
        self._before=deepcopy(tier1);self._view=inventory(self._before)
    def inventory(self):return deepcopy(self._view)
    def choices(self,target_ref):return _choices(self._view,target_ref)
    def check(self,after,target_fact_ref,donor_fact_refs,decision=None):
        return _check(self._before,after,target_fact_ref,donor_fact_refs,decision,self._view)
