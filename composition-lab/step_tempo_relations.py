"""One global step-speed coordinate, with exact source BPM alias bindings.

seconds_per_quarter * quarter_BPM = 60. Written notes and time coordinates
belong to their existing owners. No source files, original BPM backup, default
tempo, ramp interpretation, or performed-repeat clock is used here.
"""
from copy import deepcopy
from fractions import Fraction as F
import re
from source_fact_tier1 import project_documents

SCHEMA='source-global-step-tempo/1'
OWNER='global_step_tempo'
BPM_REF=re.compile(r'track-\d+\.json#/automations/tempo/\d+/bpm')


def speed_relation(*,bpm=None,quarter_seconds=None):
    if (bpm is None)==(quarter_seconds is None):
        raise ValueError('Exactly one speed coordinate required')
    value=bpm if bpm is not None else quarter_seconds
    if type(value)not in(int,str):raise ValueError('Exact rational speed required')
    value=F(value)
    if value<=0:raise ValueError('Positive speed required')
    return str(F(60)/value)


def lift(tier1):
    from tempo_source_census import global_inventory_documents
    clock=global_inventory_documents(project_documents(tier1));groups=[]
    # Other declarations retain their existing literal owner. They must not
    # quietly become a fully understood global step clock.
    if not(clock['geometry_error']or clock['unlocated']or clock['unsupported_temporal_records']or clock['extra_tempo_fields']or clock['initial_gap_q']):
        for event in clock['global_events']:
            if event['native_reasons']:continue
            groups.append(dict(id=event['id'],onset_q=event['onset_q'],end_q=event['end_q'],quarter_seconds=speed_relation(bpm=event['quarter_bpm']),
                               bpm_refs=sorted(a['source_ref']+'/bpm'for a in event['aliases'])))
    result=dict(schema=SCHEMA,groups=groups)
    expand(result)
    return result


def expand(model):
    if type(model)is not dict or set(model)!={'schema','groups'}or model['schema']!=SCHEMA or type(model['groups'])is not list:
        raise ValueError('Unsupported global step-tempo owner')
    values={};seen=set();previous_end=F(0)
    for group in model['groups']:
        if type(group)is not dict or set(group)!={'id','onset_q','end_q','quarter_seconds','bpm_refs'}:
            raise ValueError('Unknown tempo payload or copied source backup')
        ident=group['id'];seconds=group['quarter_seconds'];refs=group['bpm_refs']
        if type(ident)is not str or ident in seen or not ident.startswith('global-tempo:'):
            raise ValueError('Unique global tempo identity required')
        seen.add(ident)
        if any(type(group[k])is not str or str(F(group[k]))!=group[k]for k in('onset_q','end_q'))or not 0<=F(group['onset_q'])<F(group['end_q']):
            raise ValueError('Exact ordered source influence interval required')
        if F(group['onset_q'])<previous_end:raise ValueError('Overlapping or reordered tempo influence intervals')
        previous_end=F(group['end_q'])
        if type(seconds)is not str or str(F(seconds))!=seconds:
            raise ValueError('Canonical exact quarter duration required')
        bpm=F(speed_relation(quarter_seconds=seconds))
        if bpm.denominator!=1:raise ValueError('Native step scope requires integer BPM')
        if type(refs)is not list or not refs or any(type(r)is not str or not BPM_REF.fullmatch(r)for r in refs)or refs!=sorted(set(refs)):
            raise ValueError('Unique ordered source BPM aliases required')
        for ref in refs:
            if ref in values:raise ValueError('Duplicate BPM alias ownership')
            values[ref]=int(bpm)
    return values


def validate_source(model,tier1):
    expand(model)
    if model!=lift(tier1):raise ValueError('Global tempo aliases or source positions disagree')


def set_bpm(model,event_ref,bpm):
    expand(model)
    updated=deepcopy(model);matches=[g for g in updated['groups']if g['id']==event_ref]
    if len(matches)!=1:raise ValueError('Unknown owned tempo event')
    matches[0]['quarter_seconds']=speed_relation(bpm=bpm)
    expand(updated)
    return updated


def seconds_for_span(span_q,*,quarter_seconds):
    speed_relation(quarter_seconds=quarter_seconds)
    if type(span_q)not in(int,str)or F(span_q)<0:raise ValueError('Nonnegative exact written span required')
    return str(F(span_q)*F(quarter_seconds))


def written_pass_seconds_at(model,position_q):
    """Integrate one written traversal; performed repeats need their own ledger.

    Refuse unknown initial tempo and gaps rather than fill them with defaults.
    The same group speed equation drives this view and source BPM reconstruction.
    """
    expand(model)
    if type(position_q)not in(int,str)or F(position_q)<0:raise ValueError('Nonnegative exact written position required')
    target=F(position_q);cursor=F(0);seconds=F(0)
    for group in model['groups']:
        start,end=F(group['onset_q']),F(group['end_q'])
        if start!=cursor:raise ValueError('Incomplete or unordered step clock')
        if target<=end:return str(seconds+F(seconds_for_span(str(target-start),quarter_seconds=group['quarter_seconds'])))
        seconds+=F(seconds_for_span(str(end-start),quarter_seconds=group['quarter_seconds']));cursor=end
    raise ValueError('Position outside the qualified written step clock')
