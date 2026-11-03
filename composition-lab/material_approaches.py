"""An approach to a fixed arrival, owned inside a musical material.

Written occurrences keep their identities, ties and clocks. The arrival and
scale-degree relation replace the selected suffix's pitch-path parameters.
Changing direction is a per-use decision; the source definition stays fixed.
"""
from copy import deepcopy

import melodic_arrival_relation as arrival
import musical_tier2 as music
import melodic_movement_ownership as movement
from source_observation_evidence import digest

SCHEMA = 'coordinated-support-material-approach/1'


def _bindings(definition, path_ref):
    groups = {g['id']: g for g in definition['lower_tier']['coattacks']}
    rows = []
    for binding in definition['bindings']:
        if binding['pitch_path_ref'] != path_ref:
            continue
        group = groups[binding['coattack_ref']]
        if len(group['members']) != 1 or definition['voicings'][binding['voicing_ref']] != ['0']:
            raise ValueError('Approach requires a complete singleton line, not a chord-member guess')
        rows.append((binding['attack'], group['members'][0]['id']))
    rows.sort()
    if [i for i, _ in rows] != list(range(len(rows))):
        raise ValueError('Approach path must own one stable line without shared or missing ordinals')
    return rows


def fit(definition, lower, attack_refs, interpretations, evidence_ref):
    import musical_support_material as material
    material.expand(definition)
    if definition['schema'] != material.MATERIAL:
        raise ValueError('An existing approach cannot be replaced by a constructor')
    if type(evidence_ref) is not str or not evidence_ref:
        raise ValueError('Explicit frozen interpretation evidence reference required')
    attacks, data = movement._attack_rows(lower, attack_refs)
    members = [r for a in attacks for r in a['member_refs']]
    if any(a['attack_ref'] != refs for a, refs in zip(attacks, attack_refs)):
        raise ValueError('Stable attack roots required')
    candidates = []
    for path_ref in range(len(definition['pitch_paths'])):
        try:
            rows = _bindings(definition, path_ref)
        except ValueError:
            continue
        identities = [r for _, r in rows]
        if members and identities[-len(members):] == members:
            candidates.append((path_ref, rows))
    if len(candidates) != 1:
        raise ValueError('One complete tied-attack suffix of one path required')
    path_ref, rows = candidates[0]
    indices = {ref: i for i, ref in rows}
    groups = [[indices[r] for r in a['member_refs']] for a in attacks]
    pitches = [data['events'][a['attack_ref']]['pitch'] for a in attacks]
    if any(data['events'][r]['pitch'] != pitch for a, pitch in zip(attacks, pitches) for r in a['member_refs']):
        raise ValueError('A tied gesture must have one pitch')
    relation = arrival.fit(list(map(str, pitches)), interpretations)
    out = deepcopy(definition)
    out['schema'] = SCHEMA
    out['approach'] = dict(path_ref=path_ref, attack_groups=groups, relation=relation,
                           evidence_ref=evidence_ref, binding_sha256=digest(rows))
    first = groups[0][0]
    path = out['pitch_paths'][path_ref]
    if first == 0:
        path['start'] = None
    for i in range(max(0, first - 1), len(path['steps'])):
        path['steps'][i] = None
    if expand(out) != definition:
        raise ValueError('Approach failed exact preceding pitch-path reconstruction')
    return out


def expand(definition, mode='original'):
    """Solve the SAME scale-degree relation into existing signed pitch steps."""
    import musical_support_material as material
    if type(definition) is not dict or definition.get('schema') != SCHEMA:
        raise ValueError('Closed approach material required')
    out = deepcopy(definition)
    spec = out.pop('approach', None)
    out['schema'] = material.MATERIAL
    if type(spec) is not dict or set(spec) != {'path_ref', 'attack_groups', 'relation', 'evidence_ref', 'binding_sha256'}:
        raise ValueError('Closed approach ownership required')
    ref = spec['path_ref']
    if type(ref) is not int or not 0 <= ref < len(out['pitch_paths']):
        raise ValueError('Existing pitch path required')
    rows = _bindings(out, ref)
    if spec['binding_sha256'] != digest(rows) or type(spec['evidence_ref']) is not str or not spec['evidence_ref']:
        raise ValueError('Approach occurrence identities or interpretation evidence changed')
    groups = spec['attack_groups']
    pitches = arrival.realize(spec['relation'], mode=mode)
    if type(groups) is not list or len(groups) != len(pitches) or any(type(g) is not list or not g for g in groups):
        raise ValueError('Complete nonempty written membership for every attack required')
    indices = [i for g in groups for i in g]
    if any(type(i) is not int for i in indices) or indices != list(range(indices[0], len(rows))):
        raise ValueError('One contiguous chronological suffix required')
    path = out['pitch_paths'][ref]
    if set(path) != {'start', 'steps'} or len(path['steps']) != len(rows) - 1:
        raise ValueError('Exact original path geometry required')
    first = indices[0]
    owned_steps = range(max(0, first - 1), len(path['steps']))
    if any(path['steps'][i] is not None for i in owned_steps) or (first == 0 and path['start'] is not None):
        raise ValueError('Duplicate lower pitch authority in owned approach')
    prefix = material.pitch_path(start=path['start'], steps=path['steps'][:first-1])['pitches'] if first else []
    realized = prefix + [pitch for group, pitch in zip(groups, pitches) for _ in group]
    if len(realized) != len(rows):
        raise ValueError('Approach lost written membership')
    solved = material.pitch_path(pitches=realized)
    path.update(start=solved['start'], steps=solved['steps'])
    material.expand(out)
    return out


def validate_membership(definition, lower, *, event_map=lambda ref: ref):
    """A saved relation must still name the full actual tie closures."""
    spec = definition['approach']
    rows = _bindings(definition, spec['path_ref'])
    expected = [[event_map(rows[i][1]) for i in group] for group in spec['attack_groups']]
    attacks, _ = movement._attack_rows(lower, [group[0] for group in expected])
    if [a['member_refs'] for a in attacks] != expected:
        raise ValueError('Approach split, merged or lost a tied gesture')
