"""Immutable original expression evidence, separate from current realization.

Only the three existing policies' observation values, context fingerprints and
independence identities live here. No source notes or score reconstruction is
stored. Current contexts must still be measured by the respective policies.
Lineage projects existing observations onto edited addresses; it never creates
an additional original observation or changes a context fingerprint.
"""
from copy import deepcopy
import re

from source_observation_evidence import digest, origin as source_origin, validate_origin

SCHEMA = 'observed-expression-evidence/1'
ACCENT = 'source_local_note_accent'
MUTE = 'source_local_palm_mute'
TEMPO = 'source_rhythmic_component_tempo'
POLICIES = frozenset((ACCENT, MUTE, TEMPO))
_HEX = re.compile(r'[0-9a-f]{64}')
_EVENT = re.compile(r'event:(0|[1-9]\d*):(0|[1-9]\d*):([1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*):(0|[1-9]\d*)')
_FACT = re.compile(r'track-(0|[1-9]\d*)\.json#(/.*)')
_BEAT = re.compile(r'track-(0|[1-9]\d*)\.json#/measures/(0|[1-9]\d*)/voices/(0|[1-9]\d*)/beats/(0|[1-9]\d*)')


def context_id(value):
    return None if value is None else digest(value)


def _selected(row, fields):
    return {key: deepcopy(row[key]) for key in fields}


def capture(tier1):
    """Analyze a caller-declared ORIGINAL T1 once; never call on edited T1."""
    import local_accents
    import local_palm_mutes
    import local_step_tempos
    accents = local_accents.inventory(tier1)
    mute = local_palm_mutes.inventory(tier1)
    tempo = local_step_tempos.inventory(tier1)
    observations = {ACCENT: [], MUTE: [], TEMPO: []}
    for row in accents['occurrences']:
        observations[ACCENT].append(dict(
            **_selected(row, ('occurrence_ref', 'beat_ref', 'sound_level', 'state')),
            context_sha256=context_id(row['context_key'])))
    for row in mute['coattacks']:
        observations[MUTE].append(dict(
            **_selected(row, ('coattack_ref', 'part_id', 'onset_q', 'end_q',
                'member_refs', 'beat_refs', 'closure_refs', 'declarations', 'mute_mode')),
            context_sha256=context_id(row['context_key'])))
    for row in tempo['components']['events']:
        event = next(event for event in tempo['clock']['global_events'] if event['id'] == row['event_id'])
        components = [dict(**_selected(component, ('part_id', 'voice', 'activity',
            'attacks', 'source_refs')), context_sha256=context_id(component['context_key']))
            for component in row['components']]
        observations[TEMPO].append(dict(**_selected(row, ('event_id', 'onset_q',
            'end_q', 'bpm', 'incoming_bpm', 'outgoing_bpm', 'global_reasons',
            'source_lifetime_q', 'closure_start_q', 'closure_end_q', 'closure_refs')),
            alias_refs=deepcopy(event['alias_refs']), components=components,
            ensemble_sha256=context_id(row['ensemble_key'])))
    result = dict(schema=SCHEMA, origin=source_origin(tier1), observations=observations)
    result['evidence_sha256'] = digest(evidence(result))
    validate(result)
    return result


def evidence(model):
    return {key: deepcopy(model[key]) for key in ('schema', 'origin', 'observations')}


def _domains(model):
    refs = set()
    for row in model['observations'][ACCENT]:
        refs.update((row['occurrence_ref'], row['beat_ref']))
    for row in model['observations'][MUTE]:
        for key in ('member_refs', 'beat_refs', 'closure_refs'):
            refs.update(row[key])
    for row in model['observations'][TEMPO]:
        refs.update(row['closure_refs'])
        for component in row['components']:
            refs.update(component['source_refs'])
    events = {ref for ref in refs if ref.startswith('event:')}
    return dict(event_map=events, fact_map=refs-events)


def _scope(ref, events):
    if type(ref) is not str:
        raise ValueError('Typed expression lineage identity required')
    if events:
        match = _EVENT.fullmatch(ref)
        if match is None:
            raise ValueError('Typed expression event identity required')
        values = match.groups()
        return values[0], values[1], values[3]
    match = _FACT.fullmatch(ref)
    if match is None:
        raise ValueError('Typed expression fact identity required')
    voice = re.search(r'/voices/(0|[1-9]\d*)(?:/|$)', match[2])
    return match[1], voice[1] if voice else None


def _validate_map(mapping, events):
    if type(mapping) is not dict:
        raise ValueError('Explicit expression lineage map required')
    targets_seen = set()
    for original, targets in mapping.items():
        scope = _scope(original, events)
        if type(targets) is not list or not targets or len(targets) != len(set(targets)):
            raise ValueError('Nonempty distinct expression lineage targets required')
        for target in targets:
            if _scope(target, events) != scope:
                raise ValueError('Expression lineage crossed its song/part/voice')
            if target in targets_seen:
                raise ValueError('Conflicting expression original identities')
            targets_seen.add(target)


def _lineage(model):
    domains = _domains(model)
    if 'lineage' not in model:
        return {key: {ref: [ref] for ref in sorted(refs)} for key, refs in domains.items()}
    lineage = model['lineage']
    if type(lineage) is not dict or set(lineage) != {'event_map', 'fact_map'}:
        raise ValueError('Closed expression lineage required')
    for key, refs in domains.items():
        _validate_map(lineage[key], key == 'event_map')
        if set(lineage[key]) != refs:
            raise ValueError('Complete original expression lineage domain required')
    return lineage


def validate(model, origin=None):
    required = {'schema', 'origin', 'observations', 'evidence_sha256'}
    if type(model) is not dict or set(model) not in (required, required|{'lineage'}) or model.get('schema') != SCHEMA:
        raise ValueError('Closed original-expression observation model required')
    validate_origin(model['origin'])
    if origin is not None and model['origin'] != origin:
        raise ValueError('Original expression origin disagrees with composition')
    if type(model['observations']) is not dict or set(model['observations']) != POLICIES:
        raise ValueError('Exactly three original expression observation domains required')
    keys = {ACCENT: 'occurrence_ref', MUTE: 'coattack_ref', TEMPO: 'event_id'}
    fields = {
        ACCENT: {'occurrence_ref','beat_ref','sound_level','state','context_sha256'},
        MUTE: {'coattack_ref','part_id','onset_q','end_q','member_refs','beat_refs',
               'closure_refs','declarations','mute_mode','context_sha256'},
        TEMPO: {'event_id','onset_q','end_q','bpm','incoming_bpm','outgoing_bpm',
                'global_reasons','source_lifetime_q','closure_start_q','closure_end_q',
                'closure_refs','alias_refs','components','ensemble_sha256'}}
    for policy, identity in keys.items():
        rows = model['observations'][policy]
        if type(rows) is not list or any(type(row) is not dict or type(row.get(identity)) is not str for row in rows):
            raise ValueError('Typed original expression observation identity required')
        if len({row[identity] for row in rows}) != len(rows):
            raise ValueError('Duplicate original expression observation')
        for row in rows:
            if set(row) != fields[policy]:
                raise ValueError('Closed expression evidence fields required')
            if policy == TEMPO and any(set(component) != {'part_id','voice','activity',
                    'attacks','source_refs','context_sha256'} for component in row['components']):
                raise ValueError('Closed tempo component evidence fields required')
            hashes = ([row['ensemble_sha256']]+[c['context_sha256'] for c in row['components']]
                      if policy == TEMPO else [row['context_sha256']])
            if any(value is not None and (type(value) is not str or _HEX.fullmatch(value) is None) for value in hashes):
                raise ValueError('Exact semantic context fingerprint required')
    if digest(evidence(model)) != model['evidence_sha256']:
        raise ValueError('Original expression observations changed')
    _lineage(model)


def source_view(upper, policy=None):
    """Read saved evidence only; no source-file lookup or current observation."""
    model = upper if upper.get('schema') == SCHEMA else upper.get('owned_parameters', {}).get('observed_expression')
    if model is None:
        return None
    validate(model, upper.get('source_origin') if model is not upper else None)
    if policy is not None and policy not in POLICIES:
        raise ValueError('Unsupported retained expression policy')
    return deepcopy(model)


def project(model, fact_map, event_map):
    """Project CURRENT references; preserve evidence and original vote identity."""
    validate(model)
    _validate_map(fact_map, False)
    _validate_map(event_map, True)
    prior = _lineage(model)
    # Raw rest-note observations have event identities but no pitched coattack.
    # Their addresses still move with their enclosing beat. Derive this purely
    # structural projection for every current observed member, never a pitch.
    complete_events = deepcopy(event_map)
    for targets in prior['event_map'].values():
        for current in targets:
            song,part,bar,voice,beat,note = _EVENT.fullmatch(current).groups()
            beat_ref=f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}'
            if beat_ref not in fact_map:
                continue
            derived=[]
            for target in fact_map[beat_ref]:
                match = _BEAT.fullmatch(target)
                if match is None:
                    raise ValueError('Expression event projection requires exact beat identities')
                new_part,measure,new_voice,new_beat=match.groups()
                derived.append(f'event:{song}:{new_part}:{int(measure)+1}:{new_voice}:{new_beat}:{note}')
            if current in event_map and event_map[current] != derived:
                raise ValueError('Explicit expression event mapping conflicts with enclosing beat mapping')
            complete_events[current]=derived
    _validate_map(complete_events,True)
    maps = dict(fact_map=fact_map, event_map=complete_events)
    lineage = {key: {original: sorted(new for current in targets
                  for new in maps[key].get(current, [current]))
                  for original, targets in prior[key].items()} for key in prior}
    result = deepcopy(model)
    if all(targets == [ref] for mapping in lineage.values() for ref, targets in mapping.items()):
        result.pop('lineage', None)
    else:
        result['lineage'] = lineage
    validate(result)
    if evidence(result) != evidence(model):
        raise ValueError('Projection changed original expression evidence')
    return result


class _Prepared:
    """Ephemeral validated observation snapshot, never a serialized owner."""
    def __init__(self, model):
        validate(model)
        self.rows = deepcopy(model['observations'])
        self.reverse = {current: original for mapping in _lineage(model).values()
                        for original, targets in mapping.items() for current in targets}


def prepare(model):
    """Validate/copy once for a batch; later model edits cannot change its votes."""
    return _Prepared(model)


def original_refs(model, current_refs, *, require_all=False):
    """Resolve edited addresses to original identities without adding votes."""
    if isinstance(model, _Prepared):
        reverse = model.reverse
    else:
        lineage = _lineage(model)
        reverse = {current: original for mapping in lineage.values()
                   for original, targets in mapping.items() for current in targets}
    missing = set(current_refs)-set(reverse)
    if require_all and missing:
        raise ValueError('Current expression target has no original lineage')
    return {reverse[ref] for ref in current_refs if ref in reverse}


def observations(model, policy):
    if policy not in POLICIES:
        raise ValueError('Unsupported retained expression policy')
    if isinstance(model, _Prepared):
        return model.rows[policy]
    validate(model)
    return deepcopy(model['observations'][policy])
