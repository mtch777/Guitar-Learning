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


def evidence(model):
    """No current realization selection contributes to original-observation votes."""
    return {k: deepcopy(model[k]) for k in ('schema', 'origin', 'definitions', 'observations', 'transition_error')}


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
    if type(model) is not dict or set(model) != expected or model['schema'] != SCHEMA:
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
    for row in model['current']:
        if type(row) is not dict or set(row) != {'fact_ref', 'structure', 'definition_ref'}:
            raise ValueError('Exact current dynamic binding required')
        ref, shape = row['fact_ref'], row['structure']
        if ref not in seen or ref in current_seen or row['definition_ref'] not in model['definitions']:
            raise ValueError('Missing or duplicate current dynamic owner')
        current_seen.add(ref)
        if type(shape) is not dict or set(shape) != META or shape['id'] != ref or shape['type'] != 'string':
            raise ValueError('Exact dynamic source shape required')
        owner = identify(shape)
        if owner is None or owner['field'] != 'velocity' or ref != shape['document']+'#'+shape['pointer'] or shape['slot'] != 'velocity' or shape['parent'] != owner['owner_ref']:
            raise ValueError('Dynamic scalar escaped its source occurrence')
    if current_seen != seen:
        raise ValueError('Missing current dynamic selection')


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
    for original in model['observations']:
        ref = original['fact_ref']
        row = declarations.get(ref)
        if row is None or not row['known']:
            raise ValueError('Original dynamic declaration absent from current source structure')
        influence = original['declaration']['influence_refs']
        if any(occurrence not in occurrences for occurrence in influence):
            raise ValueError('Original dynamic influence references nonexistent note occurrence')
        if influence != row['influence_refs']:
            raise ValueError('Original dynamic influence differs from current declaration topology')


def realize(model, source_origin=None):
    validate(model, source_origin)
    return [dict(deepcopy(row['structure']), value=scalar_relation('string', parameter=model['definitions'][row['definition_ref']]))
            for row in model['current']]


def choose(model, fact_ref, marking):
    validate(model)
    ref = definition(marking)
    if ref not in model['definitions']:
        raise ValueError('No original observation for requested dynamic level')
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
