"""One explicit figure's common octave parameter over existing backing links.

For each selected occurrence:
    backing interval = interval_class + signed offset + 12 * octave

This is an ownership transform, not a source-choice policy or phrase detector.
The current selected intervals supply the shape; no reference figure replaces
them at zero. Expansion restores transient interval scalars and delegates to the
existing backing inverse. The connected inverse still validates physical contacts
and the persisted written execution obligations against its reconstructed facts.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json

import backing_pitch_ownership as backing


SCHEMA = 'figure-register-ownership/1'
EXPRESSIVE_SCHEMA = 'figure-register-ownership/2'
MUTED_SCHEMA = 'figure-register-ownership/3'
SCHEMAS = (SCHEMA, EXPRESSIVE_SCHEMA, MUTED_SCHEMA)
GROUP_FIELDS = {'id', 'occurrence_refs', 'interval_class', 'offsets_semitones', 'octave'}
GROUP_LINK_FIELDS = {'occurrence_ref', 'backing_ref', 'figure_register_ref'}


def _coordinate(value):
    if type(value) is not str:
        raise ValueError('Canonical rational semitone string required')
    try:
        result = F(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('Invalid semitone coordinate') from error
    if str(result) != value:
        raise ValueError('Canonical rational semitone string required')
    return result


def relation(*, intervals=None, interval_class=None, offsets_semitones=None, octave=None):
    """Solve either side of the same equation, returning both sides.

    ``octave`` is an absolute integer parameter, not a semitone delta. For
    [-3, -5, -8], the class is 9, offsets are [0, -2, -5], and octave is -1.
    Setting octave to 0 raises that figure by twelve semitones.
    """
    if intervals is not None:
        if any(v is not None for v in (interval_class, offsets_semitones, octave)):
            raise ValueError('Supply exactly one side of the register relation')
        if type(intervals) is not list or len(intervals) < 2:
            raise ValueError('At least two explicit intervals required')
        values = [_coordinate(v) for v in intervals]
        first = values[0]
        octave = first // 12
        interval_class = str(first - 12 * octave)
        offsets_semitones = [str(v - first) for v in values]
    else:
        if type(octave) is not int:
            raise ValueError('Explicit integer octave parameter required')
        value = _coordinate(interval_class)
        if not 0 <= value < 12:
            raise ValueError('Interval class must lie in [0, 12)')
        if type(offsets_semitones) is not list or len(offsets_semitones) < 2:
            raise ValueError('At least two signed offsets required')
        offsets = [_coordinate(v) for v in offsets_semitones]
        if offsets[0] != 0:
            raise ValueError('First signed offset must be zero')
        values = [value + offset + 12 * octave for offset in offsets]
    return dict(interval_class=interval_class, offsets_semitones=list(offsets_semitones),
                octave=octave, intervals=list(map(str, values)))


def _ordered_refs(refs):
    if type(refs) is not list or len(refs) < 2:
        raise ValueError('At least two explicitly ordered occurrence refs required')
    addresses = [backing.address(ref) for ref in refs]
    if len(set(refs)) != len(refs):
        raise ValueError('Duplicate figure occurrence')
    if len({(a[0], a[1], a[3]) for a in addresses}) != 1:
        raise ValueError('Figure refs must share source song, part and voice')
    if addresses != sorted(addresses):
        raise ValueError('Figure refs must follow structural bar/beat/note order')
    return list(refs)


def identifier(ordered_refs):
    refs = _ordered_refs(ordered_refs)
    encoded = json.dumps(refs, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return 'figure-register:' + hashlib.sha256(encoded).hexdigest()


def _plan(wrapper):
    """Validate this owner's stored shape without rebuilding unrelated music."""
    if type(wrapper) is not dict or wrapper.get('schema') not in SCHEMAS:
        raise ValueError('Unknown figure-register payload')
    expressive = wrapper['schema'] == EXPRESSIVE_SCHEMA
    muted = wrapper['schema'] == MUTED_SCHEMA
    fields = {'schema', 'core', 'groups'} | ({'execution_contract'} if expressive or muted else set())
    if set(wrapper) != fields:
        raise ValueError('Unknown figure-register fields or missing execution contract')
    if (expressive or muted) and type(wrapper['execution_contract']) is not dict:
        raise ValueError('Explicit expressive register contract required')
    groups = wrapper['groups']
    if type(groups) is not list or len(groups) != 1:
        raise ValueError('Exactly one explicit register group is supported')
    group = groups[0]
    if type(group) is not dict or set(group) != GROUP_FIELDS:
        raise ValueError('Unknown register group fields or missing authority')
    refs = _ordered_refs(group['occurrence_refs'])
    if group['id'] != identifier(refs):
        raise ValueError('Stale register group identity')
    solved = relation(interval_class=group['interval_class'],
                      offsets_semitones=group['offsets_semitones'], octave=group['octave'])
    if len(solved['intervals']) != len(refs):
        raise ValueError('Register group cardinality differs')
    core = wrapper['core']
    if type(core) is not dict or core.get('schema') not in backing.SCHEMAS:
        raise ValueError('Existing backing owner required')
    if expressive and core['schema'] != backing.SCHEMA:
        raise ValueError('Expressive register requires its own contract over written-tie-aware backing v2')
    if muted and core['schema'] != backing.EXECUTION_SCHEMA:
        raise ValueError('Muted register requires complete backing v3 execution ownership')
    fields = {'schema', 'core', 'relationships'}
    if core['schema'] in (backing.SCHEMA, backing.EXECUTION_SCHEMA):
        fields.add('written_tie_constraints')
    if core['schema'] == backing.EXECUTION_SCHEMA:
        fields.add('execution_constraints')
    if set(core) != fields or type(core['relationships']) is not list or not core['relationships']:
        raise ValueError('Backing payload/obligations differ')
    wanted = set(refs); owned = set(); all_refs = []
    for row in core['relationships']:
        if type(row) is not dict or type(row.get('occurrence_ref')) is not str:
            raise ValueError('Typed backing relationship required')
        ref = row['occurrence_ref']; all_refs.append(ref)
        if ref in wanted:
            if set(row) != GROUP_LINK_FIELDS or row['figure_register_ref'] != group['id']:
                raise ValueError('Missing, stale or duplicate figure interval authority')
            owned.add(ref)
        else:
            if set(row) != backing.LINK_FIELDS:
                raise ValueError('Unrelated backing interval authority changed')
            _coordinate(row['interval_semitones'])
        backing.address(ref); backing.address(row['backing_ref'])
    if len(set(all_refs)) != len(all_refs) or owned != wanted:
        raise ValueError('Missing/duplicate register occurrence owner')
    if all_refs != sorted(all_refs, key=backing.address):
        raise ValueError('Backing relationship order differs')
    return core, group, dict(zip(refs, solved['intervals']))


def expand(wrapper):
    """Return a complete backing wrapper with transient selected scalars.

    The stored core, all unrelated owners and all guard records remain unchanged.
    Existing backing.expand validates the resulting shared pitch/time relations;
    it is not used to flatten or relift the stored representation.
    """
    core, _, intervals = _plan(wrapper)
    result = deepcopy(core)
    for row in result['relationships']:
        if row['occurrence_ref'] in intervals:
            del row['figure_register_ref']
            row['interval_semitones'] = intervals[row['occurrence_ref']]
    backing.expand(result)
    return result


def validate(wrapper):
    """Validate this owner and return its expanded backing representation."""
    return expand(wrapper)


def lift(current_backing, ordered_refs):
    """Own the CURRENT figure's intervals with one shared octave parameter."""
    refs = _ordered_refs(ordered_refs)
    if type(current_backing) is not dict or current_backing.get('schema') not in backing.SCHEMAS:
        raise ValueError('Fresh existing backing representation required; no stacked register groups')
    backing.expand(current_backing)
    index = {row['occurrence_ref']: row for row in current_backing['relationships']}
    if any(ref not in index for ref in refs):
        raise ValueError('Every selected occurrence must already have a backing owner')
    solved = relation(intervals=[index[ref]['interval_semitones'] for ref in refs])
    group = dict(id=identifier(refs), occurrence_refs=refs,
                 interval_class=solved['interval_class'],
                 offsets_semitones=solved['offsets_semitones'], octave=solved['octave'])
    core = deepcopy(current_backing)
    selected = set(refs)
    for row in core['relationships']:
        if row['occurrence_ref'] in selected:
            del row['interval_semitones']
            row['figure_register_ref'] = group['id']
    result = dict(schema=SCHEMA, core=core, groups=[group])
    expand(result)
    return result


def bindings(wrapper):
    core, group, _ = _plan(wrapper)
    selected = set(group['occurrence_refs'])
    return [{k: row[k] for k in ('occurrence_ref', 'backing_ref')}
            for row in core['relationships'] if row['occurrence_ref'] in selected]


def lift_expressive(current_backing, *, tier1, seed_refs):
    """Fresh opt-in construction; never downgrade an existing execution owner."""
    from figure_execution_contract import closure, build
    if current_backing.get('schema') != backing.SCHEMA:
        raise ValueError('Fresh written-tie-aware backing v2 required; no execution-owner downgrade')
    scope = closure(tier1, seed_refs)
    result = lift(current_backing, scope['member_refs'])
    result['execution_contract'] = build(tier1, seed_refs, result['groups'][0], bindings(result))
    result['schema'] = EXPRESSIVE_SCHEMA
    validate_execution(result, tier1)
    return result


def validate_execution(wrapper, tier1):
    """The same expression/contact/relative-geometry predicate in both directions."""
    _plan(wrapper)
    if wrapper['schema'] == EXPRESSIVE_SCHEMA:
        from figure_execution_contract import validate as verify
        verify(wrapper['execution_contract'], tier1, wrapper['groups'][0], bindings(wrapper))
    elif wrapper['schema'] == MUTED_SCHEMA:
        from figure_execution_contract import validate_muted
        validate_muted(wrapper['execution_contract'], tier1, wrapper['groups'][0], bindings(wrapper))


def lift_muted(current_backing, *, tier1, ordered_refs):
    """Explicit palm-mute-only scope; keep the complete existing v3 guards."""
    from figure_execution_contract import build_muted
    if current_backing.get('schema') != backing.EXECUTION_SCHEMA:
        raise ValueError('Fresh complete backing v3 required for muted register')
    result = lift(current_backing, ordered_refs)
    result['execution_contract'] = build_muted(tier1, result['groups'][0], bindings(result))
    result['schema'] = MUTED_SCHEMA
    validate_execution(result, tier1)
    return result


def shift(wrapper, group_id, octave):
    """Set the named group's absolute octave parameter; alter nothing else.

    For a relative +12-semitone change, callers supply current octave + 1.
    A zero-percent variation control must retain the current parameter value.
    """
    _, group, _ = _plan(wrapper)
    if group_id != group['id'] or type(octave) is not int:
        raise ValueError('Known register group and explicit integer octave required')
    result = deepcopy(wrapper)
    result['groups'][0]['octave'] = octave
    expand(result)
    return result


def _same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if type(a) is list:
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def assert_preserved(before, after, *, mutable_groups=()):
    """Compare saved ownership history, allowing only named octave parameters.

    This history predicate is separate from complete inverse validity. Any core
    change, even a compensated backing rebind with identical current pitches,
    conflicts. Independent backing changes cannot be called rigid figure shifts.
    """
    old_core, old, _ = _plan(before)
    new_core, new, _ = _plan(after)
    if before['schema'] != after['schema'] or not _same(before.get('execution_contract'), after.get('execution_contract')):
        raise ValueError('FIGURE_REGISTER_HISTORY_CONFLICT: execution contract changed')
    if type(mutable_groups) not in (list, tuple, set, frozenset) or any(type(g) is not str for g in mutable_groups):
        raise ValueError('Explicit mutable register group IDs required')
    allowed = set(mutable_groups)
    if len(allowed) != len(mutable_groups) or allowed - {old['id']}:
        raise ValueError('Duplicate or unknown mutable register group')
    expected = deepcopy(old)
    if old['id'] in allowed:
        expected['octave'] = new['octave']
    if not _same(old_core, new_core) or not _same(expected, new):
        raise ValueError('FIGURE_REGISTER_HISTORY_CONFLICT: shape, backing owner or guard changed')
