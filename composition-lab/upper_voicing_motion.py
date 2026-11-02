"""One shared upper-interval pattern, with explicit intentional release.

interval[i] = base + motion * (reference[i] - reference[0]).
The same equation extracts the parameters and realizes them. It describes
movement relative to each retained lower note, not inferred keys or intentions.
"""
from copy import deepcopy
from fractions import Fraction as F
import random

import backing_pitch_ownership as backing
import backing_execution_constraints as execution
import backing_written_tie_constraints as ties
import group_rhythm_relations as rhythm
import musical_tier2 as music
from source_observation_evidence import digest, validate_origin as check_origin, assert_only_parameter_changes

SCHEMA = 'source-upper-voicing-motion/1'
STEP_SCHEMA = 'source-upper-voicing-motion/2'
SCHEMAS = (SCHEMA, STEP_SCHEMA)
REFERENCE_STEP = 'reference_step'
POLICY = 'source_upper_voicing_motion'
INTENTS = ('repeat_upper_interval', 'follow_reference_upper_motion')


def step_relation(*, source_intervals, target_intervals=None, base_interval=None, steps=None):
    """Own the starting vertical interval and its ordered signed movements.

    A reference_step is a live dependency on the corresponding reference
    movement. No original target vector survives when its steps are replaced.
    """
    if type(source_intervals) is not list or len(source_intervals) < 2:
        raise ValueError('At least two reference intervals required')
    source = [music.fraction(v) for v in source_intervals]
    if any(v <= 0 or v.denominator != 1 for v in source):
        raise ValueError('Positive integral source upper intervals required')
    if target_intervals is not None:
        if type(target_intervals) is not list or len(target_intervals) != len(source):
            raise ValueError('One target interval per reference required')
        target = [music.fraction(v) for v in target_intervals]
        if any(v <= 0 or v.denominator != 1 for v in target):
            raise ValueError('Positive integral target upper intervals required')
        if base_interval is not None or steps is not None:
            raise ValueError('Choose extraction or realization, not both')
        base_interval = str(target[0])
        steps = [str(b-a) for a,b in zip(target,target[1:])]
    if type(steps) is not list or len(steps) != len(source)-1:
        raise ValueError('Exactly one step between successive selected attacks required')
    base = music.fraction(base_interval)
    result = [base]
    for i, step in enumerate(steps):
        if step == REFERENCE_STEP:
            change = source[i+1]-source[i]
        else:
            if type(step) is not str:
                raise ValueError('A signed interval string or explicit reference_step required')
            change = music.fraction(step)
            if change.denominator != 1:
                raise ValueError('Integral signed semitone step required')
        result.append(result[-1]+change)
    if any(v <= 0 or v.denominator != 1 for v in result):
        raise ValueError('Upper notes must remain above their retained lower notes')
    return dict(base_interval=str(base), steps=deepcopy(steps), target_intervals=list(map(str,result)))


def relation(*, source_intervals, target_intervals=None, base_interval=None, motion=None):
    if type(source_intervals) is not list or len(source_intervals) < 2:
        raise ValueError('At least two explicit reference intervals required')
    source = [music.fraction(v) for v in source_intervals]
    if any(v <= 0 or v.denominator != 1 for v in source):
        raise ValueError('Original upper intervals must be positive integral semitones')
    delta = [v-source[0] for v in source]
    if not any(delta):
        raise ValueError('Constant reference cannot identify a motion choice')
    if target_intervals is not None:
        if type(target_intervals) is not list or len(target_intervals) != len(source):
            raise ValueError('One target per reference required')
        target = [music.fraction(v) for v in target_intervals]
        base = target[0]
        choices = [m for m in (0, 1) if all(t == base+m*d for t, d in zip(target, delta))]
        if len(choices) != 1:
            raise ValueError('Target is not one identifiable repeat or reference motion')
        if base_interval is not None and music.fraction(base_interval) != base:
            raise ValueError('Conflicting base interval')
        if motion is not None and (type(motion) is not int or motion != choices[0]):
            raise ValueError('Conflicting motion parameter')
        motion = choices[0]
    else:
        base = music.fraction(base_interval)
    if type(motion) is not int or motion not in (0, 1):
        raise ValueError('Explicit binary repeat/follow motion required')
    intervals = [base+motion*d for d in delta]
    if any(v <= 0 or v.denominator != 1 for v in intervals):
        raise ValueError('Integral upper intervals above the retained lower note required')
    return dict(base_interval=str(base), motion=motion, target_intervals=list(map(str, intervals)))


def _body(core):
    if core.get('schema') == backing.MEMBER_SCHEMA:
        return backing._body(core['core'])
    if core.get('schema') == backing.PLAIN:
        return core
    raise ValueError('Plain or explicit voiced-member ownership required; no flattening')


def _bindings(rows):
    if type(rows) is not list or len(rows) < 2:
        raise ValueError('At least two explicit source/target pairs required')
    for row in rows:
        if type(row) is not dict or set(row) != {'source_ref', 'target_ref'}:
            raise ValueError('Exact source/target binding fields required')
        for ref in row.values(): backing.address(ref)
    source = [r['source_ref'] for r in rows]; target = [r['target_ref'] for r in rows]
    if len(set(source)) != len(source) or len(set(target)) != len(target) or set(source) & set(target):
        raise ValueError('Unique disjoint source and target owners required')
    return rows


def _plan(core, rows, *, stored):
    index = backing._index(_body(core)); pairs=[]
    for row in _bindings(rows):
        if any(ref not in index for ref in row.values()): raise ValueError('Missing voice occurrence')
        source, sm = index[row['source_ref']]; target, tm = index[row['target_ref']]
        if source['part_id'] != target['part_id'] or sm['voice'] != tm['voice']:
            raise ValueError('One explicitly selected written voice required')
        for group, member, is_target in ((source, sm, False), (target, tm, True)):
            if group['timing_uncertain'] is not False or 'bass_register_anchor' not in group:
                raise ValueError('Independent retained lower anchor and known clock required')
            if not any(m is not member and m.get('voicing_interval') == '0' for m in group['members']):
                raise ValueError('Known separate lower member required')
            if is_target and stored:
                if 'voicing_interval' in member: raise ValueError('Duplicate focal interval owner')
            elif member.get('voicing_interval') is None or music.fraction(member['voicing_interval']) <= 0:
                raise ValueError('Known independently owned upper interval required')
        pairs.append((source, sm, target, tm))
    if len({(s['part_id'],sm['voice']) for s,sm,_,_ in pairs}) != 1:
        raise ValueError('One written lane required')
    for side in (0, 2):
        starts=[F(p[side]['onset_q']) for p in pairs]
        if starts != sorted(set(starts)): raise ValueError('Chronological distinct coattacks required')
    if {p[0]['id'] for p in pairs} & {p[2]['id'] for p in pairs}:
        raise ValueError('Source and target coattacks must be disjoint')
    return pairs


def _step_frame(pairs):
    """This policy aligns complete attack sequences without time warping."""
    source_start=F(pairs[0][0]['onset_q']);target_start=F(pairs[0][2]['onset_q'])
    for source,sm,target,tm in pairs:
        if (F(source['onset_q'])-source_start != F(target['onset_q'])-target_start
                or F(sm['duration_q']) != F(tm['duration_q'])):
            raise ValueError('Reference and target movement require matching attack clocks')


def lift(shared, tier1, bindings, *, source_origin, encoding='binary_motion'):
    if encoding not in ('binary_motion', 'signed_steps'):
        raise ValueError('Explicit supported upper-motion encoding required')
    check_origin(source_origin)
    if digest(tier1) != source_origin['facts_sha256']:
        raise ValueError('Only original observations may establish this relationship')
    from source_fact_tier1 import project_documents
    from run_reversible_tier_qa import extract_documents
    normal=backing.expand(shared) if shared.get('schema')==backing.MEMBER_SCHEMA else shared
    # Compare the SAME normalized interface consumed by connected_tier2. This
    # read-only check never replaces existing owners or refits edited evidence.
    if music.realize(normal) != extract_documents(project_documents(tier1)):
        raise ValueError('Supplied musical relationships disagree with original source facts')
    rows=deepcopy(_bindings(bindings)); pairs=_plan(shared,rows,stored=False)
    source=[sm['voicing_interval'] for _,sm,_,_ in pairs]
    target=[tm['voicing_interval'] for _,_,_,tm in pairs]
    signed = encoding == 'signed_steps'
    if signed: _step_frame(pairs)
    solved=(step_relation if signed else relation)(source_intervals=source,target_intervals=target)
    refs=[r['target_ref'] for r in rows]
    result=dict(schema=STEP_SCHEMA if signed else SCHEMA,core=deepcopy(shared),bindings=rows,
                observations=dict(origin=deepcopy(source_origin),source_intervals=source),
                parameters={k:solved[k] for k in ('base_interval','steps' if signed else 'motion')},
                written_tie_constraints=ties.from_tier1(normal,tier1,refs),
                execution_constraints=execution.build(tier1,refs))
    body=_body(result['core'])
    if result['core']['schema']==backing.PLAIN:
        for field in rhythm.VIEWS: body.pop(field,None)
        for group in body['coattacks']: group.pop('interpretation',None)
    for _,_,_,member in _plan(result['core'],rows,stored=False):
        del member['voicing_interval']
    expand(result)
    return result


def validate_origin(wrapper, origin):
    if type(wrapper) is not dict or wrapper.get('schema') not in SCHEMAS or set(wrapper) != {
            'schema','core','bindings','observations','parameters','written_tie_constraints','execution_constraints'}:
        raise ValueError('Exact upper-motion ownership fields required')
    obs=wrapper['observations']
    if type(obs) is not dict or set(obs) != {'origin','source_intervals'}:
        raise ValueError('Explicit original observations required')
    check_origin(obs['origin']);check_origin(origin)
    if obs['origin'] != origin: raise ValueError('Original observation identity changed')
    signed=wrapper['schema']==STEP_SCHEMA
    if signed:
        step_relation(source_intervals=obs['source_intervals'],target_intervals=obs['source_intervals'])
    else:
        relation(source_intervals=obs['source_intervals'],base_interval='1',motion=0)
    if len(obs['source_intervals']) != len(_bindings(wrapper['bindings'])):
        raise ValueError('Original observation count differs from bindings')
    if type(wrapper['parameters']) is not dict or set(wrapper['parameters']) != {'base_interval','steps' if signed else 'motion'}:
        raise ValueError('Only shared base and the declared movement parameters allowed')


def expand(wrapper):
    validate_origin(wrapper,wrapper.get('observations',{}).get('origin'))
    pairs=_plan(wrapper['core'],wrapper['bindings'],stored=True)
    if wrapper['schema']==STEP_SCHEMA: _step_frame(pairs)
    solve=step_relation if wrapper['schema']==STEP_SCHEMA else relation
    solved=solve(source_intervals=[sm['voicing_interval'] for _,sm,_,_ in pairs],**wrapper['parameters'])
    refs=[r['target_ref'] for r in wrapper['bindings']]
    ties.shape(wrapper['written_tie_constraints'],refs);execution.shape(wrapper['execution_constraints'],refs)
    result=deepcopy(wrapper['core']);index=backing._index(_body(result))
    for row,value in zip(wrapper['bindings'],solved['target_intervals']):
        index[row['target_ref']][1]['voicing_interval']=value
    if result['schema']==backing.PLAIN:
        rhythm.refresh(result);music.validate(result)
    else:
        backing.expand(result)
    return result


def validate_execution(wrapper, tier1, *, normal=None):
    if normal is None:
        core=expand(wrapper)
        normal=backing.expand(core) if core['schema']==backing.MEMBER_SCHEMA else core
    from source_fact_tier1 import project_documents
    from backing_motion_intervention import original_contact
    documents=project_documents(tier1);index=backing._index(normal)
    refs=[r['target_ref'] for r in wrapper['bindings']]
    for ref in refs:
        _,part,bar,voice,beat,note=backing.address(ref)
        doc=documents[f'track-{part}.json']
        raw=doc['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]
        group,member=index[ref]
        original_contact(doc,raw,music.member_pitch(group,member))
    ties.validate_tier1(wrapper['written_tie_constraints'],normal,tier1,refs)
    execution.validate(wrapper['execution_constraints'],tier1,refs)


def validate_controls(controls):
    if type(controls) is not dict or set(controls) != {'context_policy','voicing','intent','seed'} or controls['context_policy']!=POLICY:
        raise ValueError('Explicit upper-motion controls required')
    if type(controls['voicing']) is not int or not 0<=controls['voicing']<=100 or type(controls['seed']) is not int:
        raise ValueError('Integer percentage and seed required')
    if controls['intent'] not in INTENTS: raise ValueError('Explicit repeat/follow intention required')


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize
    validate_controls(controls)
    wrapper=upper['musical_relationships'];validate_origin(wrapper,upper.get('source_origin'))
    before=realize(upper);result=deepcopy(upper)
    released=random.Random(f"upper-voicing-motion:{controls['seed']}").random()<controls['voicing']/100
    signed=wrapper['schema']==STEP_SCHEMA
    if released:
        parameters=result['musical_relationships']['parameters']
        if signed:
            value=REFERENCE_STEP if controls['intent']==INTENTS[1] else '0'
            parameters['steps']=[value for _ in parameters['steps']]
        else:
            parameters['motion']=INTENTS.index(controls['intent'])
    paths=[('musical_relationships','parameters','steps',i) for i in range(len(wrapper['parameters']['steps']))] if signed else [('musical_relationships','parameters','motion')]
    assert_only_parameter_changes(upper,result,paths)
    after=realize(result)
    return result,dict(context_policy=POLICY,intent=controls['intent'],released=released,
                       changed=digest(after)!=digest(before),
                       relationships_changed=digest(result['musical_relationships'])!=digest(wrapper))
