"""One categorical definition, original observation, and current selection.

Only dynamic declarations are owned here, not a second T1 or note stream.
Immutable source contexts support choices; the inverse follows current selections.
"""
from copy import deepcopy
from fractions import Fraction
import re
from source_observation_evidence import digest, validate_origin
from technique_observation_relations import identify, scalar_relation

SCHEMA = 'observed-dynamic-relations/1'
PROJECTED_SCHEMA = 'observed-dynamic-relations/2'
RELATIVE_SCHEMA = 'observed-dynamic-relations/3'
# Ordered notation values, not a palette of additional original observations.
LEVELS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')
META = {'id', 'document', 'pointer', 'parent', 'slot', 'type'}
DECLARATION = {'part_id', 'voice', 'scope', 'bar', 'beat', 'note', 'influence_refs', 'reasons'}
TRANSITION = {'incoming_fact_ref', 'following_boundary_fact_ref', 'source_meter',
              'position_q', 'meter_source_refs', 'reasons', 'dependency_refs', 'influence_refs'}


def _canonical_fraction(value, label):
    if type(value) is not str:
        raise ValueError(label)
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(label) from exc
    if str(result) != value:
        raise ValueError(label)
    return result


def _occurrence_identity(ref):
    match = re.fullmatch(r'event:(0|[1-9]\d*):(0|[1-9]\d*):([1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*)', ref)
    if match is None:
        raise ValueError('Typed original note occurrence required')
    return tuple(map(int, match.groups()))


def definition(marking):
    return 'dynamic-level:' + marking


def relative_level(source_marking, *, offset=None, marking=None):
    """The SAME equation: current rank = original rank + integer offset.

    This defines realization coordinates, not a source preference or an acoustic
    loudness scale. Caller intent/evidence chooses the permitted displacement.
    """
    if type(source_marking) is not str or source_marking not in LEVELS:
        raise ValueError('Known original dynamic marking required')
    if (offset is None) == (marking is None):
        raise ValueError('Exactly one side of the relative dynamic equation required')
    source = LEVELS.index(source_marking)
    if marking is not None:
        if type(marking) is not str or marking not in LEVELS:
            raise ValueError('Known current dynamic marking required')
        offset = LEVELS.index(marking) - source
    if type(offset) is not int or not 0 <= source + offset < len(LEVELS):
        raise ValueError('Integer dynamic offset within notation bounds required')
    return dict(offset=offset, marking=LEVELS[source + offset])


def evidence(model):
    """No current realization selection contributes to original-observation votes."""
    result = {k: deepcopy(model[k]) for k in ('schema', 'origin', 'definitions', 'observations', 'transition_error')}
    # Version 2 only projects current realization addresses. The evidence still
    # has exactly its original version-1 identity and checksum.
    if model.get('schema') in (PROJECTED_SCHEMA, RELATIVE_SCHEMA):
        result['schema'] = SCHEMA
    return result


def _dynamic_address(ref):
    if type(ref) is not str:
        raise ValueError('Typed dynamic declaration address required')
    match = re.fullmatch(r'track-(0|[1-9]\d*)\.json#/measures/(0|[1-9]\d*)/voices/(0|[1-9]\d*)/beats/(0|[1-9]\d*)(?:/notes/(0|[1-9]\d*))?/velocity', ref)
    if match is None:
        raise ValueError('Typed dynamic declaration address required')
    return tuple(int(value) if value is not None else -1 for value in match.groups())


def _mapping(mapping, *, events):
    if type(mapping) is not dict:
        raise ValueError('Explicit current-address projection map required')
    address = _occurrence_identity if events else _dynamic_address
    seen = set()
    for original, targets in mapping.items():
        if type(original) is not str:
            raise ValueError('Typed projection reference required')
        source = address(original)
        if (type(targets) is not list or not targets
                or any(type(ref) is not str for ref in targets)
                or len(targets) != len(set(targets))):
            raise ValueError('Every projected occurrence needs distinct nonempty materialized targets')
        for ref in targets:
            target = address(ref)
            same_lane = source[:2] == target[:2] and source[3] == target[3] if events else (
                source[0] == target[0] and source[2] == target[2] and (source[4] < 0) == (target[4] < 0))
            if not same_lane:
                raise ValueError('Dynamic projection escaped its song/part/voice/declaration scope')
            if ref in seen:
                raise ValueError('Projected targets have conflicting original owners')
            seen.add(ref)


def _projection(model):
    facts = {row['fact_ref'] for row in model['observations']}
    events = {ref for row in model['observations'] for ref in row['declaration']['influence_refs']}
    if model['schema'] == SCHEMA or model['schema'] == RELATIVE_SCHEMA and 'projection' not in model:
        return dict(fact_map={ref:[ref] for ref in sorted(facts)},
                    event_map={ref:[ref] for ref in sorted(events)})
    projection = model['projection']
    if type(projection) is not dict or set(projection) != {'fact_map','event_map'}:
        raise ValueError('Closed dynamic occurrence projection required')
    for name, domain in (('fact_map',facts),('event_map',events)):
        values = projection[name]
        _mapping(values, events=name=='event_map')
        if set(values) != domain:
            raise ValueError('Complete original dynamic projection domain required')
        address = _occurrence_identity if name=='event_map' else _dynamic_address
        if any(targets != sorted(targets,key=address) for targets in values.values()):
            raise ValueError('Canonical materialized occurrence order required')
    return projection


def project(model, fact_map, event_map):
    """Project CURRENT addresses, retaining immutable original evidence/choices.

    Full affected-score maps may include unrelated references; only this owner's
    domain is retained. Missing keys mean identity. Version-2 calls compose with
    existing current addresses, so an omitted map never resets a prior edit.
    Original IDs are current IDs for an unprojected version-1 model.
    """
    validate(model)
    _mapping(fact_map,events=False); _mapping(event_map,events=True)
    prior = _projection(model)
    projection = {}
    for name, updates in (('fact_map',fact_map),('event_map',event_map)):
        address = _occurrence_identity if name=='event_map' else _dynamic_address
        projection[name] = {original:sorted(
            [new for current in targets for new in updates.get(current,[current])],key=address)
            for original,targets in prior[name].items()}
    result = deepcopy(model)
    if 'current_influence'in result:
        result['current_influence']['assignments']={ref:sorted(new for old in targets for new in event_map.get(old,[old]))
            for ref,targets in result['current_influence']['assignments'].items()}
        for allocation in result['current_influence']['allocations']:
            allocation['assigned_refs']=sorted(new for old in allocation['assigned_refs']for new in event_map.get(old,[old]))
    identity = all(targets == [ref] for values in projection.values() for ref,targets in values.items())
    result['schema'] = (RELATIVE_SCHEMA if model['schema'] == RELATIVE_SCHEMA
                        else SCHEMA if identity else PROJECTED_SCHEMA)
    if identity:
        result.pop('projection',None)
    else:
        result['projection'] = projection
    validate(result)
    if evidence(result) != evidence(model) or result['evidence_sha256'] != model['evidence_sha256']:
        raise ValueError('Projection changed original dynamic evidence')
    return result


def lift(tier1, source_origin):
    import local_dynamics
    import dynamic_context
    from source_fact_tier1 import validate as validate_source
    validate_source(tier1)
    if source_origin['facts_sha256'] != digest(tier1):
        raise ValueError('Original input differs from declared observation origin')
    base = local_dynamics.inventory(tier1)
    try:
        contextual = dynamic_context.inventory(tier1)
        contexts = {r['fact_ref']: r for r in contextual['contexts']}
        error = None
    except ValueError as exc:
        # Invalid/missing musical clock is retained, not invented to admit choices.
        contexts = {}
        error = str(exc)
    facts = {r['id']: r for r in tier1['facts']}
    observations, current, definitions = [], [], {}
    for row in base['declarations']:
        if not row['known']:
            continue
        ref = row['fact_ref']; value = definition(row['marking'])
        definitions[value] = scalar_relation('string', source=row['marking'])
        transition = contexts.get(ref)
        observations.append(dict(id='observed:' + ref, fact_ref=ref,
            definition_ref=value,
            declaration={k: deepcopy(row[k]) for k in DECLARATION},
            transition={k: deepcopy(transition[k]) for k in TRANSITION} if transition else None))
        current.append(dict(fact_ref=ref, structure={k: deepcopy(facts[ref][k]) for k in META}, definition_ref=value))
    model = dict(schema=SCHEMA, origin=deepcopy(source_origin), definitions=dict(sorted(definitions.items())),
                 observations=observations, current=current, transition_error=error)
    model['evidence_sha256'] = digest(evidence(model))
    validate(model, source_origin)
    return model


def validate(model, source_origin=None):
    expected = {'schema', 'origin', 'definitions', 'observations', 'current', 'transition_error', 'evidence_sha256'}
    if type(model) is dict and (model.get('schema') == PROJECTED_SCHEMA or
            model.get('schema') == RELATIVE_SCHEMA and 'projection' in model):
        expected.add('projection')
    if type(model)is dict and 'current_influence'in model:expected.add('current_influence')
    if type(model) is not dict or set(model) != expected or model['schema'] not in (SCHEMA,PROJECTED_SCHEMA,RELATIVE_SCHEMA):
        raise ValueError('Exact observed-dynamics ownership required')
    validate_origin(model['origin'])
    if source_origin is not None and model['origin'] != source_origin:
        raise ValueError('Observation origin differs from package origin')
    if model['evidence_sha256'] != digest(evidence(model)):
        raise ValueError('Original dynamic observations changed')
    if type(model['definitions']) is not dict or type(model['observations']) is not list or type(model['current']) is not list:
        raise ValueError('Typed dynamic definitions and bindings required')
    if type(model['transition_error']) not in (str, type(None)):
        raise ValueError('Typed transition uncertainty required')
    from local_dynamics import source_rules
    _, allowed = source_rules()
    for ref, parameter in model['definitions'].items():
        value = scalar_relation('string', parameter=parameter)
        if value not in allowed or ref != definition(value):
            raise ValueError('Unknown observed dynamic definition')
    seen, used = set(), set()
    for row in model['observations']:
        if type(row) is not dict or set(row) != {'id', 'fact_ref', 'definition_ref', 'declaration', 'transition'}:
            raise ValueError('Exact source observation binding required')
        ref = row['fact_ref']
        if type(ref) is not str or ref in seen or row['id'] != 'observed:' + ref or row['definition_ref'] not in model['definitions']:
            raise ValueError('Duplicate or unknown original dynamic observation')
        seen.add(ref); used.add(row['definition_ref'])
        declaration = row['declaration']
        if type(declaration) is not dict or set(declaration) != DECLARATION:
            raise ValueError('Exact original declaration context required')
        match = re.fullmatch(r'track-(\d+)\.json#/measures/(\d+)/voices/(\d+)/beats/(\d+)(?:/notes/(\d+))?/velocity', ref)
        if match is None:
            raise ValueError('Original dynamic address required')
        part, bar, voice, beat, note = match.groups()
        wanted = dict(part_id=int(part), bar=int(bar)+1, voice=int(voice), beat=int(beat),
                      note=int(note) if note is not None else None, scope='note' if note is not None else 'beat')
        if any(type(declaration[k]) is not type(v) or declaration[k] != v for k, v in wanted.items()):
            raise ValueError('Observation address and context conflict')
        for name in ('influence_refs', 'reasons'):
            values = declaration[name]
            if type(values) is not list or any(type(x) is not str for x in values) or values != sorted(set(values)):
                raise ValueError('Canonical observation references required')
        for occurrence in declaration['influence_refs']:
            _, occurrence_part, occurrence_bar, occurrence_voice, occurrence_beat, occurrence_note = _occurrence_identity(occurrence)
            if occurrence_part != wanted['part_id'] or occurrence_voice != wanted['voice']:
                raise ValueError('Original dynamic influence escaped its part/voice')
            if declaration['scope'] == 'note' and (occurrence_bar, occurrence_beat, occurrence_note) != (wanted['bar'], wanted['beat'], wanted['note']):
                raise ValueError('Original note dynamic influence escaped its occurrence')
        transition = row['transition']
        if transition is not None:
            if type(transition) is not dict or set(transition) != TRANSITION or model['transition_error'] is not None:
                raise ValueError('Exact original transition context required')
            for key in ('incoming_fact_ref', 'following_boundary_fact_ref'):
                if type(transition[key]) not in (str, type(None)):
                    raise ValueError('Typed original transition reference required')
            for key in ('meter_source_refs', 'reasons', 'dependency_refs', 'influence_refs'):
                if type(transition[key]) is not list or any(type(x) is not str for x in transition[key]) or transition[key] != sorted(set(transition[key])):
                    raise ValueError('Typed transition evidence required')
            _canonical_fraction(transition['position_q'], 'Exact source metric position required')
            if transition['influence_refs'] != declaration['influence_refs']:
                raise ValueError('Original transition influence differs from declaration')
            required = {ref, *declaration['influence_refs']}
            for name in ('incoming_fact_ref', 'following_boundary_fact_ref'):
                other = transition[name]
                if other is not None:
                    if re.fullmatch(r'track-\d+\.json#/measures/\d+/voices/\d+/beats/\d+(?:/notes/\d+)?/velocity', other) is None:
                        raise ValueError('Original transition boundary is not a declaration')
                    if not other.startswith(f'track-{part}.json#') or f'/voices/{voice}/' not in other or other == ref:
                        raise ValueError('Original transition escaped its part/voice')
                    required.add(other)
            if transition['dependency_refs'] != sorted(required):
                raise ValueError('Original transition dependencies differ')
            meter = transition['source_meter']
            if meter is not None:
                if type(meter) is not dict or set(meter) != {'beats', 'beat_unit_q'} or type(meter['beats']) is not int or meter['beats'] <= 0 or type(meter['beat_unit_q']) is not str:
                    raise ValueError('Typed original meter required')
                beat_unit = _canonical_fraction(meter['beat_unit_q'], 'Canonical positive original beat unit required')
                if beat_unit <= 0:
                    raise ValueError('Canonical positive original beat unit required')
            if any(re.fullmatch(r'track-\d+\.json#/measures/\d+/signature', value) is None for value in transition['meter_source_refs']):
                raise ValueError('Original meter references differ')
            if not transition['reasons'] and (meter is None or transition['incoming_fact_ref'] is None):
                raise ValueError('Supported original transition lacks context')
    if used != set(model['definitions']):
        raise ValueError('Unobserved extra dynamic definition')
    for row in model['observations']:
        transition = row['transition']
        if transition is not None and not transition['reasons'] and transition['incoming_fact_ref'] not in seen:
            raise ValueError('Known incoming dynamic observation missing')
    current_seen = set()
    original_definitions = {r['fact_ref']: r['definition_ref'] for r in model['observations']}
    for row in model['current']:
        choice_field = 'offset' if model['schema'] == RELATIVE_SCHEMA else 'definition_ref'
        if type(row) is not dict or set(row) != {'fact_ref', 'structure', choice_field}:
            raise ValueError('Exact current dynamic binding required')
        ref, shape = row['fact_ref'], row['structure']
        if ref not in seen or ref in current_seen:
            raise ValueError('Missing or duplicate current dynamic owner')
        if model['schema'] == RELATIVE_SCHEMA:
            source = model['definitions'][original_definitions[ref]]['symbol']
            relative_level(source, offset=row['offset'])
        elif row['definition_ref'] not in model['definitions']:
            raise ValueError('Missing or duplicate current dynamic owner')
        current_seen.add(ref)
        if type(shape) is not dict or set(shape) != META or shape['id'] != ref or shape['type'] != 'string':
            raise ValueError('Exact dynamic source shape required')
        owner = identify(shape)
        if owner is None or owner['field'] != 'velocity' or ref != shape['document']+'#'+shape['pointer'] or shape['slot'] != 'velocity' or shape['parent'] != owner['owner_ref']:
            raise ValueError('Dynamic scalar escaped its source occurrence')
    if current_seen != seen:
        raise ValueError('Missing current dynamic selection')
    if model['schema'] in (PROJECTED_SCHEMA, RELATIVE_SCHEMA):
        _projection(model)
    if 'current_influence'in model:
        owned=model['current_influence']
        if (type(owned)is not dict or set(owned)!={'schema','assignments','allocations'}
                or owned['schema']!='allocated-dynamic-influence/1'or type(owned['allocations'])is not list or not owned['allocations']):
            raise ValueError('Typed current dynamic influence assignment required')
        assignments=owned['assignments']
        if type(assignments)is not dict or set(assignments)!=seen:raise ValueError('Complete original-declaration current assignment required')
        assigned=set()
        for declaration,refs in assignments.items():
            if type(refs)is not list or refs!=sorted(set(refs)):raise ValueError('Unique current dynamic influence required')
            declaration_address=_dynamic_address(declaration)
            for ref in refs:
                address=_occurrence_identity(ref)
                if (address[1],address[3])!=(declaration_address[0],declaration_address[2]):
                    raise ValueError('Current dynamic influence escaped its declared part/voice')
                if ref in assigned:raise ValueError('A note has competing dynamic influences')
                assigned.add(ref)
        for record in owned['allocations']:
            if type(record)is not dict or set(record)!={'instance_id','scope','assigned_refs','retired_refs'}or type(record['instance_id'])is not str:
                raise ValueError('Closed dynamic allocation witness required')
            from musical_support_material import _event,_scope
            scope=record['scope'];_scope(scope['parts'],scope['first_bar'],scope['last_bar'])
            for field in ('assigned_refs','retired_refs'):
                refs=record[field]
                if type(refs)is not list or refs!=sorted(set(refs)):
                    raise ValueError('Canonical current allocation references required')
            if not set(record['assigned_refs'])<=assigned:
                raise ValueError('Dynamic allocation witness names a missing current note')
            if any(not _event(ref,scope)for ref in record['assigned_refs']+record['retired_refs']):raise ValueError('Dynamic assignment escaped allocation scope')


def validate_source(model, tier1):
    """Bind references to the current score's unchanged declaration topology.

    This validates existing note identities/inheritance, not original marking
    authenticity. The accepted projection reads only the reconstructed input;
    no original score is retained or retrieved.
    """
    validate(model)
    from local_dynamics import inventory
    current = inventory(tier1)
    declarations = {r['fact_ref']: r for r in current['declarations']}
    occurrences = {r['occurrence_ref'] for r in current['states']}
    projection = _projection(model)
    for original in model['observations']:
        ref = original['fact_ref']
        rows = [declarations.get(target) for target in projection['fact_map'][ref]]
        if any(row is None or not row['known'] for row in rows):
            raise ValueError('Original dynamic declaration absent from current source structure')
        influence = (model['current_influence']['assignments'][ref] if 'current_influence'in model else
            sorted(target for occurrence in original['declaration']['influence_refs']for target in projection['event_map'][occurrence]))
        if any(occurrence not in occurrences for occurrence in influence):
            raise ValueError('Original dynamic influence references nonexistent note occurrence')
        actual = [occurrence for row in rows for occurrence in row['influence_refs']]
        if len(actual) != len(set(actual)) or influence != sorted(actual):
            raise ValueError('Original dynamic influence differs from current declaration topology')


def allocate_influence(model, *, instance_id, scope, assignment, retired=()):
    """Assign derived notes to existing destination declarations, retaining evidence."""
    validate(model);out=deepcopy(model);projection=_projection(model)
    from musical_support_material import _event
    if type(assignment)is not dict or any(not _event(ref,scope)for ref in list(assignment)+list(retired)):
        raise ValueError('Explicit allocation-owned dynamic assignments required')
    reverse={current:original for original,refs in projection['fact_map'].items()for current in refs}
    previous=(deepcopy(model['current_influence']['assignments'])if 'current_influence'in model else
        {row['fact_ref']:sorted(target for ref in row['declaration']['influence_refs']for target in projection['event_map'][ref])for row in model['observations']})
    removed=set(retired)|set(assignment)
    current={ref:[event for event in events if event not in removed]for ref,events in previous.items()}
    for ref,declaration in assignment.items():
        if declaration not in reverse:raise ValueError('Current destination dynamic declaration is unknown')
        current[reverse[declaration]].append(ref)
    out['current_influence']=dict(schema='allocated-dynamic-influence/1',assignments={ref:sorted(values)for ref,values in current.items()},
        allocations=deepcopy(model.get('current_influence',{}).get('allocations',[]))+[dict(instance_id=instance_id,scope=deepcopy(scope),assigned_refs=sorted(assignment),retired_refs=sorted(retired))])
    validate(out)
    if evidence(out)!=evidence(model):raise ValueError('Allocation changed original dynamic observations')
    return out


def realize(model, source_origin=None):
    validate(model, source_origin)
    mapping = _projection(model)['fact_map']
    result = []
    for row in model['current']:
        marking = _current_marking(model, row)
        for target in mapping[row['fact_ref']]:
            shape = deepcopy(row['structure'])
            document,pointer = target.split('#',1)
            shape.update(id=target,document=document,pointer=pointer,
                         parent=document+'#'+pointer.rsplit('/',1)[0])
            result.append(dict(shape,value=marking))
    return result


def _current_marking(model, row):
    if model['schema'] != RELATIVE_SCHEMA:
        return scalar_relation('string', parameter=model['definitions'][row['definition_ref']])
    original = next(r for r in model['observations'] if r['fact_ref'] == row['fact_ref'])
    source = scalar_relation('string', parameter=model['definitions'][original['definition_ref']])
    return relative_level(source, offset=row['offset'])['marking']


def current_marking(model, row_or_ref):
    """Read the single current choice across legacy and relative interfaces."""
    validate(model)
    ref = row_or_ref.get('fact_ref') if type(row_or_ref) is dict else row_or_ref
    row = next((r for r in model['current'] if r['fact_ref'] == ref), None)
    if row is None or type(row_or_ref) is dict and row_or_ref != row:
        raise ValueError('Exact owned current dynamic occurrence required')
    return _current_marking(model, row)


def choose_relative(model, changes):
    """Atomically choose current levels; never add definitions or observations.

    All keys are ORIGINAL stable declaration identities, including after source
    subdivision. A child's independent expression needs a separate owner.
    """
    validate(model)
    if type(changes) is not dict or any(type(ref) is not str for ref in changes):
        raise ValueError('Explicit original-declaration to dynamic-marking mapping required')
    current = {r['fact_ref']: r for r in model['current']}
    originals = {r['fact_ref']: r for r in model['observations']}
    offsets = {}
    changed = False
    for ref, marking in changes.items():
        if ref not in current:
            raise ValueError('Original dynamic occurrence not owned')
        source = model['definitions'][originals[ref]['definition_ref']]['symbol']
        offsets[ref] = relative_level(source, marking=marking)['offset']
        changed = changed or marking != _current_marking(model, current[ref])
    result = deepcopy(model)
    if not changed:
        return result
    if model['schema'] != RELATIVE_SCHEMA:
        result['schema'] = RELATIVE_SCHEMA
        for row in result['current']:
            ref = row['fact_ref']
            source = model['definitions'][originals[ref]['definition_ref']]['symbol']
            row['offset'] = relative_level(source, marking=_current_marking(model, current[ref]))['offset']
            del row['definition_ref']
    for row in result['current']:
        if row['fact_ref'] in offsets:
            row['offset'] = offsets[row['fact_ref']]
    validate(result)
    if evidence(result) != evidence(model) or result['evidence_sha256'] != model['evidence_sha256']:
        raise ValueError('Relative dynamic choice changed original evidence')
    return result


def choose(model, fact_ref, marking):
    validate(model)
    ref = definition(marking)
    if ref not in model['definitions']:
        raise ValueError('No original observation for requested dynamic level')
    if model['schema'] == RELATIVE_SCHEMA:
        return choose_relative(model, {fact_ref: marking})
    result = deepcopy(model)
    row = next((r for r in result['current'] if r['fact_ref'] == fact_ref), None)
    if row is None:
        raise ValueError('Original dynamic occurrence not owned')
    row['definition_ref'] = ref
    validate(result)
    return result


def source_view(model):
    validate(model)
    levels = {r['fact_ref']: model['definitions'][r['definition_ref']]['symbol'] for r in model['observations']}
    declarations, contexts = [], []
    for row in model['observations']:
        ref = row['fact_ref']
        declaration = dict(deepcopy(row['declaration']), fact_ref=ref, marking=levels[ref], known=True)
        declarations.append(declaration)
        if row['transition'] is None:
            continue
        context = dict(deepcopy(row['transition']), **{k: declaration[k] for k in ('part_id', 'voice', 'scope')}, fact_ref=ref,
                       outcome_marking=levels[ref], incoming_marking=levels.get(row['transition']['incoming_fact_ref']))
        meter = context['source_meter']
        context['context_key'] = None if context['reasons'] else [context['part_id'], context['voice'], context['scope'],
            context['incoming_marking'], meter['beats'], str(Fraction(meter['beat_unit_q'])), context['position_q']]
        contexts.append(context)
    return dict(declarations=declarations, contexts=contexts)
