"""Collection-degree paths and complete coattack shapes inside existing material.

An explicit tonal interpretation supplies the same pitch/degree equation in both
directions. Scale-step displacement preserves member degree spacing unless an
explicit member displacement changes it. This owner does not infer a key or
choose a preferred variation.
"""
from collections import defaultdict
from copy import deepcopy

import musical_support_material as material
import musical_tier2 as music
from source_observation_evidence import digest


SCHEMA = 'coordinated-support-material-degree-path/1'
_FIELDS = {'schema', 'scope', 'source_start_q', 'span_q', 'bar_spans_q',
           'pulse_shares', 'slots', 'pitch_paths', 'voicings', 'bindings',
           'lower_tier', 'observed_execution', 'provenance', 'degree_paths'}
_SPEC = {'paths', 'shapes', 'bindings', 'owned_voicing_refs', 'evidence_ref'}


def _integer(value, name):
    if type(value) is not int:
        raise ValueError(f'{name} must be an exact integer')
    return value


def _coordinate(pitch, hypothesis):
    return music.collection_degree_relation(hypothesis['tonic_pc'],
        hypothesis['intervals'], pitch=pitch)['diatonic_coordinate']


def _pitch(coordinate, hypothesis):
    octave, index = divmod(coordinate, 7)
    return music.collection_degree_relation(hypothesis['tonic_pc'],
        hypothesis['intervals'], degree=index + 1, relative_octaves=octave)['pitch']


def _coordinates(hypothesis):
    result = [_integer(hypothesis['anchor'], 'Degree anchor')]
    if type(hypothesis['steps']) is not list:
        raise ValueError('Explicit signed degree steps required')
    for step in hypothesis['steps']:
        result.append(result[-1] + _integer(step, 'Degree step'))
    return result


def _pool(pool, value):
    if value not in pool:
        pool.append(deepcopy(value))
    return pool.index(value)


def fit(definition, *, path_refs, interpretations, evidence_ref):
    """Own complete pitch paths; interpretations maps each path index to hypotheses.

    Selected coattacks include every member and every binding of those paths.
    Displacements later apply by stable coattack ID, never by current pitch rank.
    """
    if type(definition) is not dict or definition.get('schema') != material.MATERIAL:
        raise ValueError('Only an ordinary unowned material can be constructed')
    material.expand(definition)
    if (type(path_refs) is not list or not path_refs
            or any(type(ref) is not int for ref in path_refs)
            or len(set(path_refs)) != len(path_refs)
            or any(not 0 <= ref < len(definition['pitch_paths']) for ref in path_refs)):
        raise ValueError('Unique complete existing pitch path indices required')
    if (type(interpretations) is not dict or set(interpretations) != set(path_refs)
            or any(type(ref) is not int for ref in interpretations)):
        raise ValueError('An explicit interpretation set for every selected path required')
    if type(evidence_ref) is not str or not evidence_ref.strip():
        raise ValueError('Frozen interpretation evidence reference required')
    groups = {group['id']: group for group in definition['lower_tier']['coattacks']}
    selected = [b for b in definition['bindings'] if b['pitch_path_ref'] in path_refs]
    external = {r['occurrence_ref']: r['kind'] for r in definition.get('external_pitch_refs', [])}
    if any(m['id'] in external and external[m['id']] != 'tied_member'
           for b in selected for m in groups[b['coattack_ref']]['members']):
        raise ValueError('Selected coattack conflicts with an existing external pitch owner')
    paths = []
    for ref in path_refs:
        pitches = material.pitch_path(**definition['pitch_paths'][ref])['pitches']
        hypotheses = interpretations[ref]
        if type(hypotheses) is not list or not hypotheses:
            raise ValueError('Nonempty frozen hypotheses required for every path')
        seen = set()
        owned = []
        for h in hypotheses:
            if (type(h) is not dict or set(h) != {'id', 'tonic_pc', 'intervals'}
                    or type(h['id']) is not str or not h['id'].strip() or h['id'] in seen):
                raise ValueError('Distinct closed tonal hypothesis records required')
            seen.add(h['id'])
            coordinates = [_coordinate(p, h) for p in pitches]
            owned.append(dict(deepcopy(h), anchor=coordinates[0],
                              steps=[b-a for a, b in zip(coordinates, coordinates[1:])]))
        paths.append(dict(path_ref=ref, hypotheses=owned))
    indexed = {p['path_ref']: p for p in paths}
    shapes = []
    bindings = []
    for b in selected:
        shape = definition['voicings'][b['voicing_ref']]
        hypotheses = indexed[b['pitch_path_ref']]['hypotheses']
        shape_refs = []
        for h in hypotheses:
            anchor = _coordinates(h)[b['attack']]
            bass = _pitch(anchor, h)
            degree_shape = [None if interval is None else
                _coordinate(music.relation(anchor=bass, interval=interval)['pitch'], h)-anchor
                for interval in shape]
            shape_refs.append(_pool(shapes, degree_shape))
        bindings.append(dict(coattack_ref=b['coattack_ref'],
            original_voicing_ref=b['voicing_ref'],
            member_refs=[m['id'] for m in groups[b['coattack_ref']]['members']],
            shape_refs=shape_refs))
    selected_ids = {b['coattack_ref'] for b in selected}
    retained_voicings = {b['voicing_ref'] for b in definition['bindings']
                         if b['coattack_ref'] not in selected_ids}
    owned_voicings = sorted({b['voicing_ref'] for b in selected} - retained_voicings)
    out = deepcopy(definition)
    out['schema'] = SCHEMA
    out['degree_paths'] = dict(paths=paths, shapes=shapes, bindings=bindings,
        owned_voicing_refs=owned_voicings, evidence_ref=evidence_ref)
    for ref in path_refs:
        out['pitch_paths'][ref] = None
    for ref in owned_voicings:
        out['voicings'][ref] = None
    for binding in out['bindings']:
        if binding['coattack_ref'] in selected_ids:
            binding['voicing_ref'] = None
    if expand(out) != definition:
        raise ValueError('Degree ownership failed exact original material reconstruction')
    return out


def _validated(definition):
    if type(definition) is not dict:
        raise ValueError('Closed degree-path material dictionary required')
    fields = _FIELDS | ({'external_pitch_refs', 'unresolved_execution_locks'} & set(definition))
    if type(definition) is not dict or set(definition) != fields or definition['schema'] != SCHEMA:
        raise ValueError('Closed degree-path material required; extra payload forbidden')
    spec = definition['degree_paths']
    if (type(spec) is not dict or set(spec) != _SPEC
            or type(spec['evidence_ref']) is not str or not spec['evidence_ref'].strip()
            or type(spec['paths']) is not list or not spec['paths']
            or type(spec['shapes']) is not list or not spec['shapes']
            or type(spec['bindings']) is not list or not spec['bindings']):
        raise ValueError('Closed degree paths, shapes, bindings and evidence required')
    paths = {}
    for path in spec['paths']:
        if type(path) is not dict or set(path) != {'path_ref', 'hypotheses'}:
            raise ValueError('Closed degree path required')
        ref = _integer(path['path_ref'], 'Path reference')
        if (not 0 <= ref < len(definition['pitch_paths']) or ref in paths
                or definition['pitch_paths'][ref] is not None):
            raise ValueError('Unique path with no duplicate lower pitch authority required')
        if type(path['hypotheses']) is not list or not path['hypotheses']:
            raise ValueError('Nonempty complete hypothesis set required')
        ids = set()
        lengths = set()
        for h in path['hypotheses']:
            if (type(h) is not dict or set(h) != {'id', 'tonic_pc', 'intervals', 'anchor', 'steps'}
                    or type(h['id']) is not str or not h['id'].strip() or h['id'] in ids):
                raise ValueError('Distinct closed degree hypotheses required')
            ids.add(h['id'])
            values = _coordinates(h)
            lengths.add(len(values))
            _pitch(values[0], h)  # validates the unchanged shared collection equation
        if len(lengths) != 1:
            raise ValueError('Hypotheses disagree on occurrence count')
        paths[ref] = path
    for shape in spec['shapes']:
        if (type(shape) is not list or not shape
                or any(v is not None and type(v) is not int for v in shape)
                or 0 not in shape):
            raise ValueError('Complete signed member-degree shape with retained free basis required')
    if len({tuple(s) for s in spec['shapes']}) != len(spec['shapes']):
        raise ValueError('Duplicate degree shape definitions forbidden')
    groups = {g['id']: g for g in definition['lower_tier']['coattacks']}
    ordinary = deepcopy(definition['bindings'])
    bindings = {b['coattack_ref']: b for b in ordinary}
    if len(bindings) != len(ordinary):
        raise ValueError('Unique stable coattack bindings required')
    selected = {}
    used_shapes = set()
    for row in spec['bindings']:
        if (type(row) is not dict or set(row) != {'coattack_ref', 'original_voicing_ref', 'member_refs', 'shape_refs'}
                or row['coattack_ref'] in selected or row['coattack_ref'] not in groups
                or row['coattack_ref'] not in bindings):
            raise ValueError('Unique complete selected binding required')
        ref = row['coattack_ref']; binding = bindings[ref]
        p = binding['pitch_path_ref']
        vi = row['original_voicing_ref']
        if (p not in paths or binding['voicing_ref'] is not None
                or type(vi) is not int or not 0 <= vi < len(definition['voicings'])
                or row['member_refs'] != [m['id'] for m in groups[ref]['members']]
                or type(row['shape_refs']) is not list
                or len(row['shape_refs']) != len(paths[p]['hypotheses'])):
            raise ValueError('Selected occurrence/voicing identity changed or duplicated')
        for shape_ref in row['shape_refs']:
            if (type(shape_ref) is not int or not 0 <= shape_ref < len(spec['shapes'])
                    or len(spec['shapes'][shape_ref]) != len(row['member_refs'])):
                raise ValueError('Complete member shape required for every hypothesis')
            used_shapes.add(shape_ref)
        binding['voicing_ref'] = vi
        selected[ref] = row
    if (used_shapes != set(range(len(spec['shapes'])))
            or set(selected) != {b['coattack_ref'] for b in ordinary if b['pitch_path_ref'] in paths}
            or digest(ordinary) != definition['provenance']['bindings_sha256']):
        raise ValueError('Complete unchanged path/binding membership required')
    expected_owned = sorted({r['original_voicing_ref'] for r in selected.values()} -
        {b['voicing_ref'] for b in ordinary if b['coattack_ref'] not in selected})
    if (type(spec['owned_voicing_refs']) is not list
            or any(type(ref) is not int for ref in spec['owned_voicing_refs'])
            or spec['owned_voicing_refs'] != expected_owned
            or any(definition['voicings'][ref] is not None for ref in expected_owned)):
        raise ValueError('Exact removed lower voicing authority required')
    external = {r['occurrence_ref']: r['kind'] for r in definition.get('external_pitch_refs', [])}
    members = set()
    for row in selected.values():
        shapes = [spec['shapes'][ref] for ref in row['shape_refs']]
        if (len({shape.index(0) for shape in shapes}) != 1
                or any([v is None for v in shape] != [v is None for v in shapes[0]]
                       for shape in shapes[1:])):
            raise ValueError('Hypotheses must retain the same stable free basis and member ownership')
        for index, ref in enumerate(row['member_refs']):
            if ref in members:
                raise ValueError('A member occurrence cannot have duplicate degree ownership')
            members.add(ref)
            if ref in external and (external[ref] != 'tied_member'
                    or any(shape[index] is not None for shape in shapes)):
                raise ValueError('Selected material conflicts with an external pitch owner')
    return spec, paths, selected, groups, ordinary


def selected_refs(definition):
    """Selected stable coattack IDs in the original binding order."""
    _, _, selected, _, ordinary = _validated(definition)
    return [b['coattack_ref'] for b in ordinary if b['coattack_ref'] in selected]


def expand(definition, displacements=None, octaves=None, member_steps=None):
    """Solve each retained hypothesis; refuse if their changed pitches disagree.

    Member steps add signed collection degrees to the saved member shape. The
    first original zero-offset member remains the free basis, owned by the common
    path. Tied and unknown members never become independent pitch choices.
    """
    spec, paths, selected, groups, ordinary = _validated(definition)
    controls = []
    for values in (displacements, octaves):
        values = {} if values is None else values
        if (type(values) is not dict or set(values) - set(selected)
                or any(type(v) is not int for v in values.values())):
            raise ValueError('Exact integer controls keyed by selected coattack identity required')
        controls.append(values)
    displacements, octaves = controls
    member_steps = {} if member_steps is None else member_steps
    allowed = set()
    bases = set()
    for row in selected.values():
        shape = spec['shapes'][row['shape_refs'][0]]
        bases.add(row['member_refs'][shape.index(0)])
        allowed.update(ref for ref, offset in zip(row['member_refs'], shape) if offset is not None)
    if (type(member_steps) is not dict or set(member_steps) - allowed
            or any(type(value) is not int for value in member_steps.values())):
        raise ValueError('Exact integer member steps require selected independent known member identities')
    if any(member_steps.get(ref, 0) != 0 for ref in bases):
        raise ValueError('The stable free basis is owned by the common degree path')
    tied = {r['occurrence_ref'] for r in definition.get('external_pitch_refs', [])
            if r['kind'] == 'tied_member'}
    out = deepcopy(definition)
    out.pop('degree_paths'); out['schema'] = material.MATERIAL
    out['bindings'] = ordinary
    lanes = defaultdict(list)
    for binding in ordinary:
        ref = binding['coattack_ref']
        if ref not in selected:
            continue
        row = selected[ref]; p = binding['pitch_path_ref']
        ordinal = _integer(binding['attack'], 'Attack ordinal')
        candidates = []
        for h, shape_ref in zip(paths[p]['hypotheses'], row['shape_refs']):
            coordinates = _coordinates(h)
            if not 0 <= ordinal < len(coordinates):
                raise ValueError('Attack ordinal outside its complete pitch path')
            coordinate = coordinates[ordinal] + displacements.get(ref, 0) + 7 * octaves.get(ref, 0)
            bass = _pitch(coordinate, h)
            pitches = [None if offset is None else
                       _pitch(coordinate + offset + member_steps.get(member, 0), h)
                       for member, offset in zip(row['member_refs'], spec['shapes'][shape_ref])]
            # Ordinary core groups use the lowest pitch as their serialization
            # basis. A tie-stripped group instead keeps its stable free basis;
            # its tie owner restores the canonical complete coattack later.
            if not tied.intersection(row['member_refs']):
                bass = min(pitch for pitch in pitches if pitch is not None)
            candidates.append((bass, pitches))
        if any(candidate != candidates[0] for candidate in candidates[1:]):
            raise ValueError(f'Tonal interpretations disagree on exact realization: {ref}')
        bass, pitches = candidates[0]
        shape = [None if pitch is None else music.relation(anchor=bass, pitch=pitch)['interval']
                 for pitch in pitches]
        vi = row['original_voicing_ref']
        if out['voicings'][vi] is None:
            out['voicings'][vi] = shape
        if out['voicings'][vi] != shape:
            vi = _pool(out['voicings'], shape)
        binding['voicing_ref'] = vi
        lanes[(p, groups[ref]['part_id'])].append((ordinal, bass, binding))
    for (p, _), rows in lanes.items():
        rows.sort(key=lambda row: row[0])
        count = len(_coordinates(paths[p]['hypotheses'][0]))
        if [row[0] for row in rows] != list(range(count)):
            raise ValueError('Each selected part must retain its complete path membership')
        value = material.pitch_path(pitches=[row[1] for row in rows])
        value.pop('pitches')
        if out['pitch_paths'][p] is None:
            out['pitch_paths'][p] = value
        destination = p if out['pitch_paths'][p] == value else _pool(out['pitch_paths'], value)
        for _, _, binding in rows:
            binding['pitch_path_ref'] = destination
    out['provenance']['bindings_sha256'] = digest(out['bindings'])
    material.expand(out)
    return out
