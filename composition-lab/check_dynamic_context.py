"""Independent raw source-local dynamic-context/provenance oracle.

No production dynamic_context imports. Ancestors are found from ordered raw
marking declarations; metrical offsets are independently summed from raw prefixes.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math,random
from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents
from musical_tier2 import geometry_relation
from check_local_dynamics import Oracle as BroadOracle,MARKINGS,encoded

POLICY='source_local_dynamic_transition'
SCHEMA='source-local-dynamic-context/1'
def _known(v):return type(v)is str and v in MARKINGS
def _duration(b):
    d=b.get('duration');return F(*d)*4 if type(d)is list and len(d)==2 and all(type(x)is int for x in d)and d[0]>=0 and d[1]>0 else None

def _meter_provenance(docs):
    """Raw declaration timeline; no parser default or conflict choice is known."""
    parts=[(n,p)for n,p in sorted(docs.items())if n.startswith('track-')];result={};signature=None;refs=[]
    for bar in range(1,max((len(p.get('measures',[]))for _,p in parts),default=0)+1):
        explicit=[];invalid=False
        for name,p in parts:
            if bar>len(p.get('measures',[])):continue
            m=p['measures'][bar-1]
            if not m.get('signature'):continue
            value=m['signature'];ref=f'{name}#/measures/{bar-1}/signature';valid=type(value)is list and len(value)==2 and all(type(x)is int and x>0 for x in value)
            explicit.append((ref,tuple(value)if valid else None));invalid|=not valid
        if explicit:
            distinct={v for _,v in explicit if v is not None};refs=sorted(r for r,_ in explicit);signature=next(iter(distinct))if not invalid and len(distinct)==1 else None
        result[bar]=dict(signature=signature,refs=refs[:])
    return result

def _inventory(tier1,broad):
    docs=project_documents(tier1);lower=extract_documents(docs);events={e['id']for e in lower['events']};g=geometry_relation(source=lower['measure_geometry'])['parameters'];frames={f['ordinal']:f for f in g['frames']};membership={p['part_id']:set(p['frame_refs'])for p in g['parts']}
    warnings=lower['source_coverage']['layout_warnings']+lower['source_coverage']['timing_warnings'];marks=defaultdict(list);meters=_meter_provenance(docs)
    for name,p in docs.items():
        if not name.startswith('track-'):continue
        for mi,m in enumerate(p.get('measures',[]),1):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    if b.get('velocity')is not None:marks[p['partId'],vi].append(((mi,bi),b['velocity'],f'{name}#/measures/{mi-1}/voices/{vi}/beats/{bi}/velocity'))
    contexts=[]
    for d in broad['declarations']:
        p=docs[f"track-{d['part_id']}.json"];m=p['measures'][d['bar']-1];v=m['voices'][d['voice']];beat=v['beats'][d['beat']];frame=frames.get(d['bar']);reasons=list(d['reasons']);prefix=v['beats'][:d['beat']]
        keypoint=(d['bar'],d['beat']);prior=[x for x in marks[d['part_id'],d['voice']]if x[0]<keypoint or d['scope']=='note'and x[0]==keypoint];incoming=prior[-1]if prior else None
        following=[x for x in marks[d['part_id'],d['voice']]if x[0]>keypoint];boundary=following[0][2]if following and d['scope']=='beat'else None
        if incoming is None:reasons.append('MISSING_INCOMING_DYNAMIC')
        elif not _known(incoming[1]):reasons.append('UNKNOWN_INCOMING_DYNAMIC')
        if frame is None or frame['id']not in membership.get(d['part_id'],set()):reasons.append('MISSING_SOURCE_FRAME')
        meterproof=meters.get(d['bar'],dict(signature=None,refs=[]))
        if frame is not None and F(frame['duration_q'])!=F(frame['meter']['beats'])*F(frame['meter']['beat_unit_q']):reasons.append('NONNOMINAL_FRAME_METRICAL_SCOPE')
        if any(w.get('bar')==d['bar']and(w.get('part_id')is None or w['part_id']==d['part_id'])for w in warnings):reasons.append('UNCERTAIN_SOURCE_CLOCK')
        if beat.get('graceNote'):reasons.append('GRACE_SOURCE_CONTEXT')
        if _duration(beat)is None:reasons.append('UNKNOWN_BEAT_DURATION')
        valid_prefix=all(_duration(b)is not None for b in prefix);valid_clock=valid_prefix and _duration(beat)is not None
        if not valid_clock:reasons.append('UNKNOWN_BAR_OFFSET')
        position=sum((_duration(b)for b in prefix if not b.get('graceNote')and _duration(b)is not None),F(0))
        if frame is not None and valid_clock and not F(0)<=position<F(frame['duration_q']):reasons.append('OUTSIDE_SOURCE_FRAME')
        if any(r not in events for r in d['influence_refs']):reasons.append('UNLOCATED_INFLUENCED_NOTE')
        meter=deepcopy(frame['meter'])if frame is not None else None;value=incoming[1]if incoming else None;origin=incoming[2]if incoming else None
        deps={d['fact_ref'],*d['influence_refs']}
        if origin:deps.add(origin)
        if boundary:deps.add(boundary)
        context_key=None if reasons else[d['part_id'],d['voice'],d['scope'],value,meter['beats'],str(F(meter['beat_unit_q'])),str(position)]
        contexts.append(dict(fact_ref=d['fact_ref'],part_id=d['part_id'],voice=d['voice'],scope=d['scope'],outcome_marking=deepcopy(d['marking']),incoming_marking=deepcopy(value),incoming_fact_ref=origin,following_boundary_fact_ref=boundary,source_meter=meter,meter_source_refs=meterproof['refs'],position_q=str(position),context_key=context_key,reasons=sorted(set(reasons)),dependency_refs=sorted(deps),influence_refs=d['influence_refs']))
    return dict(schema=SCHEMA,declarations=deepcopy(broad['declarations']),states=deepcopy(broad['states']),contexts=sorted(contexts,key=lambda r:r['fact_ref']))

def _options(view,ref):
    target=next((d for d in view['declarations']if d['fact_ref']==ref),None);context=next((d for d in view['contexts']if d['fact_ref']==ref),None)
    if target is None or context is None:raise ValueError('Original dynamic declaration required')
    observed=[];excluded=[];pair=None
    if not context['reasons']:
        deps=set(context['dependency_refs']);donors=[]
        for d in view['contexts']:
            if d['context_key']!=context['context_key']:continue
            if d['fact_ref']==ref:excluded.append(dict(fact_ref=ref,reason='SELF_DECLARATION'));continue
            common=sorted(deps&set(d['dependency_refs']))
            if common:excluded.append(dict(fact_ref=d['fact_ref'],reason='REUSED_TARGET_DEPENDENCY',shared_refs=common));continue
            donors.append(d)
        levels=sorted({d['outcome_marking']for d in donors})
        observed=[dict(marking=m,donor_refs=sorted(d['fact_ref']for d in donors if d['outcome_marking']==m),changed=m!=target['marking'])for m in levels]
        for i,a in enumerate(donors):
            for b in donors[i+1:]:
                if a['outcome_marking']!=b['outcome_marking']and not set(a['dependency_refs'])&set(b['dependency_refs']):pair=[a['fact_ref'],b['fact_ref']];break
            if pair:break
    status='NO_SUPPORTED_DYNAMIC_CONTEXT'if context['reasons']else'CONTEXT_SUPPORTED_DYNAMIC_CHOICES'if pair else'NO_INDEPENDENT_CONTEXTUAL_MULTI_CHOICE'
    return dict(target_ref=ref,target=deepcopy(target),context=deepcopy(context),observed_options=deepcopy(observed),options=deepcopy(observed)if pair else[],witness_pair=pair,excluded=excluded,status=status)

def inventory(tier1):return Oracle(tier1).inventory()
def options(tier1,target_ref):return Oracle(tier1).options(target_ref)

class Oracle:
    def __init__(self,tier1):
        self._broad=BroadOracle(tier1);self._before=self._broad._before;self._view=_inventory(self._before,self._broad.inventory())
    def inventory(self):return deepcopy(self._view)
    def options(self,target_ref):return _options(self._view,target_ref)
    def choices(self,target_ref):return self.options(target_ref)
    def check_options(self,target_ref,reported):
        expected=self.options(target_ref);issues=[]if encoded(expected)==encoded(reported)else['Complete raw context/options/provenance differs']
        return dict(status='PASS_INDEPENDENT_DYNAMIC_CONTEXT_OPTIONS'if not issues else'FAIL',issues=issues)
    def check_sample(self,target_ref,controls,chosen,decision):
        issues=[]
        try:
            if type(controls)is not dict or set(controls)!={'context_policy','dynamics','target_ref','seed'}or controls['context_policy']!=POLICY or controls['target_ref']!=target_ref or type(controls['seed'])is not int or type(controls['dynamics'])not in(int,float)or not math.isfinite(controls['dynamics'])or not 0<=controls['dynamics']<=100:raise ValueError('Strict contextual dynamic release controls required')
            evidence=self.options(target_ref);rng=random.Random(controls['seed']);released=rng.random()<controls['dynamics']/100;population=[o for o in evidence['options']for _ in o['donor_refs']];wanted=rng.choice(population)if released and population else None
            if type(decision.get('released'))is not bool or type(decision.get('changed'))is not bool or decision['released']!=released or decision['changed']!=bool(wanted and wanted['changed'])or encoded(chosen)!=encoded(wanted)or encoded(decision.get('chosen'))!=encoded(wanted):raise ValueError('Actual draw differs from deduplicated contextual source votes')
        except Exception as exc:issues.append(str(exc))
        return dict(status='PASS_INDEPENDENT_DYNAMIC_CONTEXT_SAMPLE'if not issues else'FAIL',issues=issues)
    def check(self,after,target_ref,donor_refs,decision=None):
        issues=[];raw=None;expected=None
        try:
            expected=self.options(target_ref)
            beforefacts={f['id']:f for f in self._before['facts']};afterfacts={f['id']:f for f in after['facts']};changed=encoded(beforefacts[target_ref]['value'])!=encoded(afterfacts[target_ref]['value']);new=afterfacts[target_ref]['value']
            if type(donor_refs)is not list or any(type(r)is not str for r in donor_refs)or donor_refs!=sorted(set(donor_refs)):raise ValueError('Unique canonical contextual source donors required')
            released=changed if decision is None else decision.get('released')
            if decision is not None:
                if type(released)is not bool or type(decision.get('changed'))is not bool or decision['changed']!=changed:raise ValueError('Decision disagrees with actual dynamic output')
                if 'evidence'in decision and encoded(decision['evidence'])!=encoded(expected):raise ValueError('Reported contextual source evidence differs')
            if changed and not released:raise ValueError('Unreleased contextual operation changed source')
            broadchoice=None
            if changed or released:
                if not expected['options']:
                    if changed or donor_refs or decision is None or decision.get('chosen')is not None or decision.get('status')!='NO_ADMITTED_CHOICE':raise ValueError('No contextual opportunity must retain exact source')
                else:
                    choice=next((o for o in expected['options']if o['marking']==new),None)
                    if choice is None or choice['donor_refs']!=donor_refs or decision is not None and encoded(decision.get('chosen'))!=encoded(choice):raise ValueError('Selected marking/donors not in complete contextual population')
                    broadchoice=next(o for o in self._broad.choices(target_ref)['options']if o['marking']==new)
            elif donor_refs or decision is not None and decision.get('chosen')is not None:raise ValueError('Unreleased operation invents contextual donors')
            # The broad checker remains unchanged. Supply its independent full
            # source witness list only as a proof adapter for raw/effective locks;
            # actual contextual provenance was checked above, never broadened.
            proof=dict(released=bool(broadchoice),changed=changed)
            if broadchoice:proof['chosen']=broadchoice
            raw=self._broad.check(after,target_ref,broadchoice['donor_refs']if broadchoice else[],proof)
            if raw['status']!='PASS_INDEPENDENT_LOCAL_DYNAMICS':issues.extend(raw['issues'])
        except Exception as exc:issues.append(str(exc))
        return dict(status='PASS_INDEPENDENT_LOCAL_DYNAMICS'if not issues else'FAIL',issues=issues,context_policy=POLICY,affected_refs=raw.get('affected_refs',[])if raw else[],raw_output_check=raw,scope='Conditional dependency-disjoint written source transition and exact effect locks; no aesthetic or predictive accuracy claim')

def check(before,after,target_ref,donor_refs,decision=None):return Oracle(before).check(after,target_ref,donor_refs,decision)
