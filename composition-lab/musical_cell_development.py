"""An exact repeated three-role cell, its development, and a live middle ending.

LOW/CENTER/OUTER describe written pitch order, not harmony or artistic intent.
The bounded grammar has one stable low and middle, one changing upper role,
one shared change boundary, and a final middle note. No note residual is stored.
"""
from copy import deepcopy
from fractions import Fraction as F
import random

import musical_tier2 as music
import melodic_movement_ownership as movement
import backing_pitch_ownership as backing
from source_observation_evidence import digest, validate_origin, assert_only_parameter_changes

SCHEMA = 'musical-cell-development/1'
SLOT = 'musical_cell_development'
TIER3_SCHEMA = 'source-musical-cell-development/1'
POLICY = 'source_musical_cell_phase'
ROLES = ('LOW', 'CENTER', 'OUTER')


def _q(value):
    if type(value) is not str:
        raise ValueError('Canonical rational string required')
    result = music.fraction(value)
    if str(result) != value:
        raise ValueError('Canonical rational string required')
    return result


def _pitch(value):
    result = _q(value)
    if result.denominator != 1:
        raise ValueError('Integral written pitch/interval required')
    return result


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Explicit integer coordinate required')
    return value


def _add(anchor, interval):
    return music.relation(anchor=str(anchor), interval=str(interval))['pitch']


def _difference(anchor, pitch):
    return music.relation(anchor=str(anchor), pitch=str(pitch))['interval']


def _input(instance):
    if type(instance) is not dict or set(instance) != {'pitches', 'timing'}:
        raise ValueError('Pitches and their complete ordered timing required')
    pitches, timing = instance['pitches'], instance['timing']
    if type(pitches) is not list or type(timing) is not list or len(pitches) != len(timing):
        raise ValueError('One timing entry per attack required')
    values = [_pitch(p) for p in pitches]
    if len(values) < 10:
        raise ValueError('At least three complete cells and an ending required')
    onsets, durations = [], []
    for row in timing:
        if type(row) is not dict or set(row) != {'onset_q', 'duration_q'}:
            raise ValueError('Explicit written onset and duration required')
        onsets.append(_q(row['onset_q'])); durations.append(_q(row['duration_q']))
    if any(d <= 0 for d in durations) or onsets != sorted(set(onsets)):
        raise ValueError('Positive durations and distinct chronological attacks required')
    if any(t+d > following for t,d,following in zip(onsets,durations,onsets[1:])):
        raise ValueError('Overlapping attack holds are outside this cell grammar')
    return values, onsets, durations


def _rhythm(onsets, durations, period, cells):
    start = onsets[0]
    span = onsets[period] - start
    offsets = [v-start for v in onsets[:period]]
    cell_durations = durations[:period]
    expected = [start+c*span+offset for c in range(cells) for offset in offsets]
    expected.append(start+cells*span)
    if onsets != expected or durations[:-1] != cell_durations*cells:
        raise ValueError('Internal timing does not repeat with the cell')
    return dict(offsets_q=list(map(str, offsets)), durations_q=list(map(str, cell_durations)),
                span_q=str(span), ending_duration_q=str(durations[-1]))


def fit(instances):
    """Find one exact shared interpretation; ambiguity and outliers refuse.

    Candidate periods and development boundaries are examined jointly. This
    grammar admits exactly three distinct ranked roles, at least three complete
    cells, and a stable CENTER ending. It is not a general phrase recognizer.
    """
    if type(instances) is not list or len(instances) < 2:
        raise ValueError('At least two explicitly supplied instances required')
    source = [_input(row) for row in instances]
    lengths = {len(row[0]) for row in source}
    if len(lengths) != 1:
        raise ValueError('Shared cell instances require the same attack count')
    count = lengths.pop(); candidates = []
    for period in range(1, count):
        if (count-1) % period or period != len(ROLES):
            continue
        cells = (count-1)//period
        if cells < 3:
            continue
        for split in range(1, cells):
            records = []; center = order = timing = None
            try:
                for pitches, onsets, durations in source:
                    initial = pitches[:period]
                    if len(set(initial)) != period:
                        raise ValueError('Distinct LOW/CENTER/OUTER roles required')
                    ranked = sorted(initial)
                    names = {value:role for value,role in zip(ranked,ROLES)}
                    actual_order = [names[p] for p in initial]
                    if order is None:
                        order = actual_order
                    phases = [p for p in range(period) if order[p:]+order[:p] == actual_order]
                    if len(phases) != 1:
                        raise ValueError('Instances do not share one cyclic ordered cell')
                    middle = ranked[1]
                    if center is None:
                        center = middle
                    if center != middle or pitches[-1] != middle:
                        raise ValueError('Shared live CENTER ending not established')
                    columns = {role:[pitches[c*period+i] for c in range(cells)]
                               for i,role in enumerate(actual_order)}
                    if len(set(columns['LOW'])) != 1 or len(set(columns['CENTER'])) != 1:
                        raise ValueError('LOW and CENTER are not stable')
                    outer = columns['OUTER']
                    if len(set(outer[:split])) != 1 or len(set(outer[split:])) != 1:
                        raise ValueError('OUTER has an internal outlier or another development')
                    if not ranked[0] < center < min(outer):
                        raise ValueError('A developed role crosses the stable CENTER')
                    clock = _rhythm(onsets, durations, period, cells)
                    if timing is None:
                        timing = clock
                    if timing != clock:
                        raise ValueError('Instances do not share the exact cell timing')
                    records.append(dict(onset_q=str(onsets[0]), phase=phases[0],
                        low_interval=_difference(center,ranked[0]),
                        outer_interval=_difference(center,outer[0]),
                        development_interval=_difference(outer[0],outer[split])))
                candidate = dict(schema=SCHEMA, center_pitch=str(center),
                    structure=dict(period=period, cell_count=cells, development_start=split,
                                   role_order=order, ending_role='CENTER'),
                    rhythm=timing, instances=records)
                if realize(candidate) != instances:
                    raise ValueError('Shared relation does not recreate the supplied instances')
                candidates.append(candidate)
            except ValueError:
                continue
    if len(candidates) != 1:
        raise ValueError(f'Unique exact cell interpretation required; found {len(candidates)}')
    return candidates[0]


def realize(model):
    """Solve the SAME center-plus-role-width relation for every cell and ending."""
    if type(model) is not dict or set(model) != {'schema','center_pitch','structure','rhythm','instances'} or model['schema'] != SCHEMA:
        raise ValueError('Exact versioned cell relation fields required')
    center = _pitch(model['center_pitch']); structure = model['structure']; rhythm = model['rhythm']
    if type(structure) is not dict or set(structure) != {'period','cell_count','development_start','role_order','ending_role'}:
        raise ValueError('Complete shared cell structure required')
    period = _integer(structure['period'],1); cells = _integer(structure['cell_count'],3)
    split = _integer(structure['development_start'],1); order = structure['role_order']
    if period != len(ROLES) or split >= cells or type(order) is not list or sorted(order) != sorted(ROLES) or structure['ending_role'] != 'CENTER':
        raise ValueError('Unsupported period, roles, development or ending')
    if type(rhythm) is not dict or set(rhythm) != {'offsets_q','durations_q','span_q','ending_duration_q'}:
        raise ValueError('Exact repeated timing witness required')
    if type(rhythm['offsets_q']) is not list or type(rhythm['durations_q']) is not list or len(rhythm['offsets_q']) != period or len(rhythm['durations_q']) != period:
        raise ValueError('One timing coordinate per cell position required')
    offsets = [_q(v) for v in rhythm['offsets_q']]; durations = [_q(v) for v in rhythm['durations_q']]
    span = _q(rhythm['span_q']); ending_duration = _q(rhythm['ending_duration_q'])
    if offsets[0] != 0 or offsets != sorted(set(offsets)) or any(d <= 0 for d in durations) or ending_duration <= 0 or span <= 0:
        raise ValueError('Invalid cell rhythm')
    if any(t+d > following for t,d,following in zip(offsets,durations,offsets[1:]+[span])):
        raise ValueError('Cell holds overlap following attacks')
    if type(model['instances']) is not list or len(model['instances']) < 2:
        raise ValueError('Shared relation requires at least two instances')
    result = []
    for row in model['instances']:
        if type(row) is not dict or set(row) != {'onset_q','phase','low_interval','outer_interval','development_interval'}:
            raise ValueError('Exact instance coordinates required; no note residuals')
        onset = _q(row['onset_q']); phase = _integer(row['phase'])
        low, outer, development = [_pitch(row[k]) for k in ('low_interval','outer_interval','development_interval')]
        if phase >= period or low >= 0 or outer <= 0 or outer+development <= 0:
            raise ValueError('Invalid role width or phase')
        cell_order = order[phase:]+order[:phase]
        pitches = []; timing = []
        for cell in range(cells):
            widths = {'LOW':low,'CENTER':F(0),'OUTER':outer+(development if cell >= split else 0)}
            for i,role in enumerate(cell_order):
                pitches.append(_add(center,widths[role]))
                timing.append(dict(onset_q=str(onset+cell*span+offsets[i]),duration_q=str(durations[i])))
        pitches.append(str(center))
        timing.append(dict(onset_q=str(onset+cells*span),duration_q=str(ending_duration)))
        result.append(dict(pitches=pitches,timing=timing))
    return result


def phase_relation(model, instance, phase):
    """Change role order inside each cell; keep development and ending attached."""
    realize(model)
    _integer(instance); _integer(phase)
    if instance >= len(model['instances']) or phase >= model['structure']['period']:
        raise ValueError('Unknown instance or cell phase')
    result = deepcopy(model); result['instances'][instance]['phase'] = phase
    realize(result)
    return result


def _binding_groups(groups, attacks):
    if type(groups) is not list or len(groups) < 2 or any(type(g) is not list for g in groups):
        raise ValueError('Explicit complete ordered instance attack identities required')
    flattened = [ref for group in groups for ref in group]
    if flattened != [row['attack_ref'] for row in attacks] or any(len(g) < 10 for g in groups):
        raise ValueError('Instance partition must own every movement attack exactly once')
    return flattened


def _contexts(lower, origin, refs, source):
    if type(refs) not in (list,tuple) or len(set(refs)) != len(refs):
        raise ValueError('Unique explicitly permitted direct dependent identities required')
    selected = set(movement._members(source['attacks']))
    shared = source['shared']; links = {r['occurrence_ref']:r for r in shared.get('relationships',[])}
    by_part = {}
    for ref in refs:
        address = backing.address(ref)
        link = links.get(ref)
        if ref in selected or link is None or set(link) != backing.LINK_FIELDS or link['backing_ref'] not in selected:
            raise ValueError('Only existing direct dependent pitch links may accompany this cell')
        by_part.setdefault(address[1],[]).append(ref)
    result = []
    for part in sorted(by_part):
        members = sorted(by_part[part],key=backing.address)
        closure = movement.closure.closure(lower,members)
        rows,_ = movement._attack_rows(lower,closure['attack_root_refs'])
        if set(movement._members(rows)) != set(members):
            raise ValueError('Complete dependent tie membership required')
        result.append(movement._original_register_context(lower,origin,members))
    return result


def _timed_instances(lower, attacks, groups, pitches):
    rows,data = movement._attack_rows(lower,[r['attack_ref'] for r in attacks])
    if rows != attacks:
        raise ValueError('Movement attack/tie identity changed')
    index = {row['attack_ref']:row for row in attacks}; pitch_map = dict(zip(index,pitches))
    result = []; previous_end = None
    for group in groups:
        timing = []
        for ref in group:
            row = index[ref]; onset = F(data['events'][ref]['onset_q'])
            if any(data['events'][member]['pitch'] != pitch_map[ref] for member in row['member_refs']):
                raise ValueError('Current complete attack pitches contradict their cell roles')
            end = max(F(data['events'][r]['onset_q'])+F(data['events'][r]['duration_q']) for r in row['member_refs'])
            timing.append(dict(onset_q=str(onset),duration_q=str(end-onset)))
        if previous_end is not None and F(timing[0]['onset_q']) < previous_end:
            raise ValueError('Instance holds overlap the following instance')
        previous_end = F(timing[-1]['onset_q'])+F(timing[-1]['duration_q'])
        result.append(dict(pitches=[pitch_map[r] for r in group],timing=timing))
    return result


def _shape(upper):
    from connected_tier2 import strip_lower
    fields = {'tier','schema','lower_tier','relationship','instance_attack_refs','observations'}
    if type(upper) is not dict or set(upper) != fields or upper['tier'] != 3 or type(upper['tier']) is not int or upper['schema'] != TIER3_SCHEMA:
        raise ValueError('Explicit Tier3 cell envelope required')
    child = upper['lower_tier']
    if type(child) is not dict or type(child.get('tier')) is not int or child['tier'] != 2 or 'lower_tier_cache' in child:
        raise ValueError('Stripped preceding Tier2 skeleton required')
    if digest(child) != digest(strip_lower(child)):
        raise ValueError('Tier3 boundary cannot carry input or derived-view lower payloads')
    model = child.get('owned_parameters',{}).get(movement.SLOT)
    if type(model) is not dict or model.get('schema') != movement.SCHEMA_V2 or 'parameters' in model:
        raise ValueError('Tier3 must replace, not duplicate, the movement parameters')
    if model.get('reference_attacks') is not None:
        raise ValueError('An existing live movement reference cannot be silently replaced')
    groups = upper['instance_attack_refs']; _binding_groups(groups,model.get('attacks',[]))
    solved = realize(upper['relationship'])
    if len(solved) != len(groups) or any(len(row['pitches']) != len(group) for row,group in zip(solved,groups)):
        raise ValueError('Cell relation and bound occurrence cardinality differ')
    obs = upper['observations']
    if type(obs) is not dict or set(obs) != {'origin','original_relation_sha256','bindings_sha256','dependent_contexts','evidence_sha256'}:
        raise ValueError('Immutable semantic source observation provenance required')
    validate_origin(obs['origin'])
    if obs['origin'] != child.get('source_origin') or obs['bindings_sha256'] != digest(groups):
        raise ValueError('Original source or instance bindings changed')
    if type(obs['original_relation_sha256']) is not str or len(obs['original_relation_sha256']) != 64 or any(c not in '0123456789abcdef' for c in obs['original_relation_sha256']):
        raise ValueError('Original fitted semantic relation commitment required')
    if obs['evidence_sha256'] != digest({k:v for k,v in obs.items()if k!='evidence_sha256'}):
        raise ValueError('Original semantic observations changed')
    if type(obs['dependent_contexts']) is not list:
        raise ValueError('Original direct-dependent contexts required')
    refs = movement._members(model['attacks']); seen = set(refs)
    links = {r['occurrence_ref']:r for r in child['musical_relationships'].get('relationships',[])}
    for context in obs['dependent_contexts']:
        if type(context) is not dict or type(context.get('excluded_member_refs')) is not list or not context['excluded_member_refs']:
            raise ValueError('Explicit original dependent membership required')
        members = context['excluded_member_refs']
        movement._validate_register_context(context,obs['origin'],members)
        if len(set(members)) != len(members) or set(members)&seen:
            raise ValueError('Overlapping dependent placement contexts')
        for ref in members:
            if ref not in links or set(links[ref]) != backing.LINK_FIELDS or links[ref]['backing_ref'] not in refs:
                raise ValueError('Dependent context no longer binds an existing direct pitch link')
        seen.update(members)
    params = movement.relation(pitches=[p for row in solved for p in row['pitches']])
    params = {k:params[k] for k in ('pitch_class','octave','steps')}
    # Validate the existing authority without mutating its sparse nested owner.
    check = dict(child); check['owned_parameters'] = dict(child['owned_parameters'])
    check['owned_parameters'][movement.SLOT] = dict(model,parameters=params)
    movement._shape(check)
    return child,model,params


def lift(upper, instance_attack_refs, *, dependent_refs=()):
    """Own the preceding movement coordinates; do not keep their old payload."""
    from connected_tier2 import strip_lower
    child = strip_lower(upper)
    model,_,_ = movement._shape(child)
    if model['schema'] != movement.SCHEMA_V2 or model['reference_attacks'] is not None:
        raise ValueError('An independent Version2 movement owner is required')
    _binding_groups(instance_attack_refs,model['attacks'])
    lower = movement._realize(child)
    if digest(lower) != child['source_origin']['facts_sha256']:
        raise ValueError('Original source required when establishing cell observations')
    pitches = movement._solve(child)['pitches']
    relationship = fit(_timed_instances(lower,model['attacks'],instance_attack_refs,pitches))
    contexts = _contexts(lower,child['source_origin'],dependent_refs,
                         dict(attacks=model['attacks'],shared=child['musical_relationships']))
    obs = dict(origin=deepcopy(child['source_origin']), original_relation_sha256=digest(relationship),
               bindings_sha256=digest(instance_attack_refs),dependent_contexts=contexts)
    obs['evidence_sha256'] = digest(obs)
    del model['parameters']
    result = dict(tier=3,schema=TIER3_SCHEMA,lower_tier=child,relationship=relationship,
                  instance_attack_refs=deepcopy(instance_attack_refs),observations=obs)
    restored = expand(result)
    if digest(restored) != digest(strip_lower(upper)):
        raise ValueError('Cell ownership changed unrelated Tier2 authority')
    validate_execution(result,lower)
    return result


def expand(upper):
    """Tier3 -> Tier2: reconstruct the sole first-pitch/step parameters."""
    child,_,params = _shape(upper)
    result = deepcopy(child)
    result['owned_parameters'][movement.SLOT]['parameters'] = params
    return result


def validate_execution(upper, lower):
    _,model,params = _shape(upper)
    pitches = movement.relation(**params)['pitches']
    actual = _timed_instances(lower,model['attacks'],upper['instance_attack_refs'],pitches)
    if actual != realize(upper['relationship']):
        raise ValueError('Current written timing contradicts the shared cell relationship')
    data = movement.closure._data(movement.execution.encoded(lower))
    for context in upper['observations']['dependent_contexts']:
        span = F(context['max_simultaneous_span'])
        for ref in context['excluded_member_refs']:
            event = data['events'][ref]
            _,_,note,_ = movement.closure._raw(data,event)
            if not movement._contact_span_ok(data,ref,note,span):
                raise ValueError('Dependent contact exceeds its saved original source-span experiment')


def _current_lower(upper):
    lower = movement._realize(expand(upper))
    validate_execution(upper,lower)
    return lower


def phase_candidate(upper, instance, phase):
    """Mathematical candidate only; the public operation verifies placement."""
    _shape(upper)
    result = deepcopy(upper)
    result['relationship'] = phase_relation(upper['relationship'],instance,phase)
    expand(result)
    return result


def intervene(upper, controls):
    fields = {'context_policy','variation','instance','phase','seed'}
    if type(controls) is not dict or set(controls) != fields or controls['context_policy'] != POLICY:
        raise ValueError('Exact musical-cell phase controls required')
    level = controls['variation']; instance = controls['instance']; phase = controls['phase']; seed = controls['seed']
    if type(level) is not int or not 0 <= level <= 100 or type(seed) is not int:
        raise ValueError('Integer release percentage and seed required')
    _integer(instance,1); _integer(phase)
    _shape(upper)
    if instance >= len(upper['relationship']['instances']) or phase >= upper['relationship']['structure']['period']:
        raise ValueError('Explicit later instance and supported phase required')
    before = _current_lower(upper)
    current_phase = upper['relationship']['instances'][instance]['phase']
    released = random.Random(f'musical-cell-phase:release:{seed}').random() < level/100
    report = dict(policy=POLICY,variation=level,seed=seed,instance=instance,
                  current_phase=current_phase,requested_phase=phase,released=released,
                  original_observations_unchanged=True)
    if not released:
        return deepcopy(upper),dict(report,changed=False,chosen_phase=current_phase,candidate_count=None)
    candidates = [(deepcopy(upper),current_phase,{})]
    if phase != current_phase:
        proposed = phase_candidate(upper,instance,phase)
        child = expand(upper); proposed_child = expand(proposed)
        placed,contacts = movement._placed_candidate(child,
            proposed_child['owned_parameters'][movement.SLOT]['parameters'],before,
            dependent_contexts=upper['observations']['dependent_contexts'])
        if placed['owned_parameters'][movement.SLOT]['parameters'] != proposed_child['owned_parameters'][movement.SLOT]['parameters']:
            raise ValueError('Placement changed the proposed cell equation')
        del placed['owned_parameters'][movement.SLOT]['parameters']
        proposed['lower_tier'] = placed
        # The shared placement path already validated the whole realized score.
        # This boundary additionally verifies retained authority below Tier3.
        _shape(proposed)
        allowed = [('relationship','instances',instance,'phase')]
        refs = movement._members(child['owned_parameters'][movement.SLOT]['attacks'])
        refs += [r for c in upper['observations']['dependent_contexts'] for r in c['excluded_member_refs']]
        for pi,ci in movement._string_paths(child,refs).values():
            allowed += [('lower_tier','owned_parameters','source_choices',ci,'parameter',key) for key in ('normalized','negative_zero')]
            allowed.append(('lower_tier','owned_parameters','physical_positions',pi,'negative_zero'))
        assert_only_parameter_changes(upper,proposed,allowed)
        candidates.append((proposed,phase,contacts))
    index = random.Random(f'musical-cell-phase:selection:{seed}').randrange(len(candidates))
    chosen,chosen_phase,contacts = candidates[index]
    return chosen,dict(report,changed=digest(chosen)!=digest(upper),chosen_phase=chosen_phase,
                       candidate_count=len(candidates),selected_index=index,contacts=contacts)


def reconstruct(upper, controls):
    """Production boundary adapter; no additional musical reconstruction rule."""
    if type(controls) is dict and set(controls) == {'variation'} and type(controls['variation']) is int and controls['variation'] == 0:
        return _current_lower(upper)
    edited,_ = intervene(upper,controls)
    return _current_lower(edited)
