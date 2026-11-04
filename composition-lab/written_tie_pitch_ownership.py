"""Written sustains own their continuation pitches through one equality.

This is an ownership representation, not a note selector. Independent members
of a mixed coattack retain their own pitch coordinates, even when a tied member
is the lowest note. No source score, contact copy, or old pitch stream is saved.
"""
from copy import deepcopy
import hashlib
import json

import backing_pitch_ownership as backing
import backing_written_tie_constraints as ties
import group_rhythm_relations as rhythm
import musical_tier2 as music

SCHEMA = 'written-tie-pitch-ownership/1'
PLAIN = 'musical-context-relations/2'
FIELDS = {'schema', 'core', 'relationships', 'groups', 'unresolved'}
GROUP_FIELDS = {'member_refs', 'basis_ref'}
KINDS = {'written_pitched_tie', 'written_dead_tie'}


def _coordinate(value):
    if type(value) is not str or str(music.fraction(value)) != value:
        raise ValueError('Canonical rational pitch coordinate required')
    return music.fraction(value)


def _plain(core):
    if (type(core) is not dict or core.get('schema') != PLAIN or
            'input' in core or 'written_ties' in core):
        raise ValueError('Plain stripped musical core required; do not flatten another owner')
    music.validate(core)
    return core


def _notation(tier1):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    return extract_documents(project_documents(tier1))['tie_notation']


def _predicate_fingerprint(refs, nodes, declarations, index):
    """Commit current predicate inputs, not an inverse pitch/contact payload.

    Addresses are stored separately as identities. A preceding subdivision may
    readdress this unchanged neighborhood, so the digest uses canonical ordered
    values and absolute musical clocks, not serialization positions.
    """
    values = []
    for ref in refs:
        node = nodes[ref]; _, part, _, voice, _, _ = ties.address(ref)
        values.append(dict(part=part, voice=voice, onset_q=str(node['onset']),
            duration_q=str(node['duration']), kind=node['kind'],
            written_position=None if node['position'] is None else str(node['position']),
            valid_position=node['valid_position'], dead=node['dead'],
            pitch=music.member_pitch(*index[ref]), declarations=declarations[ref]))
    encoded = [json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False) for row in values]
    return hashlib.sha256(json.dumps(sorted(encoded), separators=(',', ':')).encode()).hexdigest()


def _observed(core, tier1):
    notation = _notation(tier1)
    nodes, true = music.written_tie_context(notation, core)
    links, unknown = music.written_tie_edges(nodes, true)
    relationships = sorted((ties.relation(row) for row in links),
                           key=lambda r: (ties.address(r['destination_ref']),
                                          ties.address(r['origin_ref'])))
    unresolved = []
    declarations = {row['occurrence_ref']: row['fields'] for row in notation['occurrences']}
    index = backing._index(core)
    for row in unknown:
        ref = row['destination']; node = nodes[ref]
        # Protect only the detector's actual same-string neighborhood. A fresh
        # member on another string is not an implied dependency of this failure.
        nearby = [ref]
        if node['lane'] is not None:
            lane = [(other, n) for other, n in nodes.items()
                    if n['lane'] == node['lane'] and n['onset'] <= node['onset']]
            prior = [n['onset'] for _, n in lane if n['onset'] < node['onset']]
            boundary = {node['onset']} | ({max(prior)} if prior else set())
            nearby += [other for other, n in lane if n['onset'] in boundary]
        refs = sorted(set(nearby), key=ties.address)
        unresolved.append(dict(destination_ref=ref, reason=row['reason'], neighborhood_refs=refs,
            context_fingerprint=_predicate_fingerprint(refs, nodes, declarations, index)))
    unresolved.sort(key=lambda r: ties.address(r['destination_ref']))
    return relationships, unresolved


def lift(core, *, tier1):
    """Remove independent tail pitches; consume only the current preceding tier."""
    _plain(core)
    relationships, unresolved = _observed(core, tier1)
    tails = {r['destination_ref'] for r in relationships if r['kind'] == 'written_pitched_tie'}
    saved = deepcopy(core); owned = []
    for group in saved['coattacks']:
        group.pop('interpretation')
        if not tails.intersection(m['id'] for m in group['members']):
            continue
        independent = [(m['id'], music.member_pitch(group, m))
                       for m in group['members'] if m['id'] not in tails]
        known = [(ref, pitch) for ref, pitch in independent if pitch is not None]
        basis_ref, basis_pitch = known[0] if known else (None, None)
        owned.append(dict(member_refs=[m['id'] for m in group['members']],
                          basis_ref=basis_ref))
        if basis_ref is None:
            del group['bass_register_anchor']
        else:
            group['bass_register_anchor'] = basis_pitch
        pitches = dict(independent)
        for member in group['members']:
            if member['id'] in tails:
                del member['voicing_interval']
            else:
                value = pitches[member['id']]
                member['voicing_interval'] = (None if value is None else
                    music.relation(anchor=basis_pitch, pitch=value)['interval'])
    for name in rhythm.VIEWS:
        del saved[name]
    wrapper = dict(schema=SCHEMA, core=saved, relationships=relationships,
                   groups=owned, unresolved=unresolved)
    if expand(wrapper) != core:
        raise ValueError('Written-tie ownership changed its preceding core')
    validate_contacts(wrapper, tier1, expanded=core)
    return wrapper


def _shape(wrapper):
    if type(wrapper) is not dict or set(wrapper) != FIELDS or wrapper.get('schema') != SCHEMA:
        raise ValueError('Exact written-tie ownership interface required')
    core = wrapper['core']
    if (type(core) is not dict or set(core) != backing.BASE_FIELDS or
            core.get('schema') != PLAIN or any('interpretation' in g for g in core['coattacks'])):
        raise ValueError('Saved source, derived views, or undeclared pitch payload forbidden')
    index = backing._index(core)
    rows = wrapper['relationships']
    if type(rows) is not list or type(wrapper['groups']) is not list or type(wrapper['unresolved']) is not list:
        raise ValueError('Typed written-tie owner lists required')
    targets = {}; outgoing = set()
    for row in rows:
        if type(row) is not dict or set(row) != ties.RELATION_FIELDS or row['kind'] not in KINDS:
            raise ValueError('Only typed written-tie relationships are permitted')
        a, b = row['origin_ref'], row['destination_ref']
        if a not in index or b not in index or a == b or b in targets or a in outgoing:
            raise ValueError('Dangling, duplicate, or branching written-tie owner')
        if ties.address(a)[:2] != ties.address(b)[:2] or ties.address(a)[3] != ties.address(b)[3]:
            raise ValueError('Written ties require the same song, part and voice')
        if row != ties.relation(dict(origin=a, destination=b, kind=row['kind'])):
            raise ValueError('Written-tie declaration identity changed')
        targets[b] = row; outgoing.add(a)
    if rows != sorted(rows, key=lambda r: (ties.address(r['destination_ref']), ties.address(r['origin_ref']))):
        raise ValueError('Canonical written-tie order required')
    for ref in targets:
        visited = set(); current = ref
        while current in targets:
            if current in visited:
                raise ValueError('Cyclic written-tie dependency')
            visited.add(current); current = targets[current]['origin_ref']
    unknown_refs = set()
    for row in wrapper['unresolved']:
        if (type(row) is not dict or set(row) != {'destination_ref', 'reason', 'neighborhood_refs', 'context_fingerprint'} or
                row['destination_ref'] not in index or row['destination_ref'] in targets or
                row['destination_ref'] in unknown_refs or type(row['reason']) is not str or
                not row['reason'] or type(row['neighborhood_refs']) is not list):
            raise ValueError('Exact unresolved source declaration required')
        fingerprint = row['context_fingerprint']
        if type(fingerprint) is not str or len(fingerprint) != 64 or any(c not in '0123456789abcdef' for c in fingerprint):
            raise ValueError('Immutable unresolved predicate-input fingerprint required')
        refs = row['neighborhood_refs']
        if (row['destination_ref'] not in refs or not set(refs) <= set(index) or
                refs != sorted(set(refs), key=ties.address)):
            raise ValueError('Invalid unresolved tie neighborhood')
        unknown_refs.add(row['destination_ref'])
    if wrapper['unresolved'] != sorted(wrapper['unresolved'], key=lambda r: ties.address(r['destination_ref'])):
        raise ValueError('Canonical unresolved order required')
    return core, index, targets


def attack_head(wrapper, occurrence_ref):
    """Stable written attack identity; a continuation is never a new pitch unit."""
    _, index, targets = _shape(wrapper)
    if occurrence_ref not in index:
        raise ValueError('Unknown written occurrence')
    return _head(occurrence_ref, targets)


def _head(occurrence_ref, targets):
    while occurrence_ref in targets:
        occurrence_ref = targets[occurrence_ref]['origin_ref']
    return occurrence_ref


def expand(wrapper):
    """Solve tie equality and independent member offsets into the SAME core."""
    core, index, targets = _shape(wrapper)
    pitched = {ref for ref, row in targets.items() if row['kind'] == 'written_pitched_tie'}
    affected = [g for g in core['coattacks'] if pitched.intersection(m['id'] for m in g['members'])]
    if len(affected) != len(wrapper['groups']):
        raise ValueError('Missing or extra tied coattack owner')
    independent = {}; group_map = {}
    for group, owned in zip(affected, wrapper['groups']):
        if (type(owned) is not dict or set(owned) != GROUP_FIELDS or
                owned['member_refs'] != [m['id'] for m in group['members']]):
            raise ValueError('Duplicate, missing, or redirected tied member pitch authority')
        free = [m for m in group['members'] if m['id'] not in pitched]
        if (any('voicing_interval' in m for m in group['members'] if m['id'] in pitched) or
                any('voicing_interval' not in m for m in free)):
            raise ValueError('Only independent members may own pitch parameters')
        known = [m for m in free if m['voicing_interval'] is not None]
        if known:
            if owned['basis_ref'] != known[0]['id'] or known[0]['voicing_interval'] != '0':
                raise ValueError('Independent pitch basis must use its stable original member identity')
            _coordinate(group.get('bass_register_anchor'))
        elif owned['basis_ref'] is not None or 'bass_register_anchor' in group:
            raise ValueError('A fully dependent coattack cannot hide an independent pitch')
        for row in free:
            interval = row['voicing_interval']
            if interval is not None:
                _coordinate(interval)
            independent[row['id']] = (None if interval is None else
                music.relation(anchor=group['bass_register_anchor'], interval=interval)['pitch'])
        group_map[group['id']] = owned
    for group in core['coattacks']:
        if group['id'] in group_map:
            continue
        if 'bass_register_anchor' not in group or any('voicing_interval' not in m for m in group['members']):
            raise ValueError('Missing independent coattack pitch authority')
        for member in group['members']:
            independent[member['id']] = music.member_pitch(group, member)
    solved = dict(independent)
    def pitch(ref):
        if ref not in solved:
            row = targets[ref]
            base = pitch(row['origin_ref'])
            if base is None:
                raise ValueError('Known tied pitch cannot derive from unknown pitch')
            solved[ref] = music.relation(anchor=base, interval='0')['pitch']
        return solved[ref]
    for ref in pitched:
        pitch(ref)
    for row in wrapper['relationships']:
        ga, ma = index[row['origin_ref']]; gb, mb = index[row['destination_ref']]
        duration = _coordinate(ma['duration_q'])
        if duration <= 0 or _coordinate(mb['duration_q']) <= 0 or _coordinate(ga['onset_q']) + duration != _coordinate(gb['onset_q']):
            raise ValueError('WRITTEN_TIE_CLOCK_CONFLICT: adjacent spans must remain contiguous')
        if row['kind'] == 'written_dead_tie' and (solved[row['origin_ref']] is not None or solved[row['destination_ref']] is not None):
            raise ValueError('Dead tie must not acquire a guessed pitch')
    result = deepcopy(core)
    for group in result['coattacks']:
        if group['id'] not in group_map:
            continue
        known = [solved[m['id']] for m in group['members'] if solved[m['id']] is not None]
        anchor = str(min(map(music.fraction, known))) if known else None
        group['bass_register_anchor'] = anchor
        for member in group['members']:
            value = solved[member['id']]
            member['voicing_interval'] = (None if value is None else
                music.relation(anchor=anchor, pitch=value)['interval'])
    rhythm.refresh(result)
    music.validate(result)
    return result


def validate_contacts(wrapper, tier1, *, expanded=None):
    """Mandatory after complete realization: current strings/flags are T1-owned."""
    normal = expand(wrapper) if expanded is None else _plain(expanded)
    relationships, unresolved = _observed(normal, tier1)
    if relationships != wrapper['relationships']:
        raise ValueError('WRITTEN_TIE_CONTACT_CONFLICT: saved pitch/string/time dependencies changed')
    if unresolved != wrapper['unresolved']:
        raise ValueError('UNRESOLVED_AFFECTED_WRITTEN_TIE: source declaration or protected predicate inputs changed')


def assert_preserved(before, after, *, mutable_heads=()):
    """Historical guarantee for updates; standalone validity cannot prove this."""
    left = expand(before); right = expand(after)
    if (before['relationships'] != after['relationships'] or before['unresolved'] != after['unresolved'] or
            before['groups'] != after['groups']):
        raise ValueError('Untouched written-tie relationships changed')
    a = backing._index(left); b = backing._index(right)
    if set(a) != set(b):
        raise ValueError('Written occurrence identity changed')
    allowed = set(mutable_heads)
    _, _, targets = _shape(before)
    if not allowed <= set(a):
        raise ValueError('Unknown mutable attack head')
    if any(_head(ref, targets) != ref for ref in allowed):
        raise ValueError('Independent continuation edit forbidden; address its attack head')
    protected = {ref for row in before['unresolved'] for ref in row['neighborhood_refs']}
    for ref in a:
        old_group, old_note = a[ref]; new_group, new_note = b[ref]
        old = (music.member_pitch(old_group, old_note), old_group['onset_q'], old_note['duration_q'])
        new = (music.member_pitch(new_group, new_note), new_group['onset_q'], new_note['duration_q'])
        if ref in protected and old != new:
            raise ValueError('UNRESOLVED_AFFECTED_WRITTEN_TIE: preserve unknown neighborhood')
        if _head(ref, targets) not in allowed and old != new:
            raise ValueError('Unselected written pitch or clock changed')
