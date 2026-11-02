"""Incident written-tie relationships for the bounded backing pitch owner.

Only IDs/types/declaration references are persisted. Pitch, contact and time
come from the ordinary current inverse; the accepted written-lane predicate
is shared by admission and reconstruction. No acoustic sustain is inferred.
"""
from fractions import Fraction as F
import re
import musical_tier2 as music

SCHEMA = 'backing-written-tie-constraints/1'
REF = re.compile(r'event:(?:0|[1-9]\d*)(?::(?:0|[1-9]\d*)){5}')
RELATION_FIELDS = {'id', 'kind', 'origin_ref', 'destination_ref', 'declaration_ref'}


def address(ref):
    if type(ref) is not str or not REF.fullmatch(ref):
        raise ValueError('Canonical written-tie occurrence required')
    return tuple(map(int, ref.split(':')[1:]))


def relation(edge):
    origin, destination = edge['origin'], edge['destination']
    _, part, bar, voice, beat, note = address(destination)
    return dict(id=f'written-tie:{origin}->{destination}', kind=edge['kind'],
                origin_ref=origin, destination_ref=destination,
                declaration_ref=f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}/tie')


def empty(refs):
    refs = sorted(refs, key=address)
    if not refs or len(set(refs)) != len(refs):
        raise ValueError('Unique written-tie owner scope required')
    return dict(schema=SCHEMA, relations=[],
                incidence=[dict(occurrence_ref=ref, relation_refs=[]) for ref in refs])


def shape(scope, refs):
    expected = empty(refs)
    if type(scope) is not dict or set(scope) != {'schema', 'relations', 'incidence'} or scope['schema'] != SCHEMA:
        raise ValueError('Saved written-tie constraint scope required')
    if type(scope['relations']) is not list or type(scope['incidence']) is not list:
        raise ValueError('Typed written-tie relationships/incidence required')
    ordered = []
    owners = set(refs)
    for row in scope['relations']:
        if type(row) is not dict or set(row) != RELATION_FIELDS:
            raise ValueError('Unexpected written-tie payload or old note values')
        a, b = row['origin_ref'], row['destination_ref']
        address(a); address(b)
        if row['kind'] != 'written_pitched_tie' or a == b or not owners.intersection((a, b)):
            raise ValueError('Unsupported or unrelated written-tie constraint')
        if row != relation(dict(origin=a, destination=b, kind=row['kind'])):
            raise ValueError('Written-tie identity/declaration mismatch')
        ordered.append(row)
    if ordered != sorted(ordered, key=lambda r: (address(r['destination_ref']), address(r['origin_ref']))) or len({r['id'] for r in ordered}) != len(ordered):
        raise ValueError('Canonical unique written-tie constraints required')
    for row in expected['incidence']:
        row['relation_refs'] = [r['id'] for r in ordered if row['occurrence_ref'] in (r['origin_ref'], r['destination_ref'])]
    if scope['incidence'] != expected['incidence']:
        raise ValueError('Missing, dangling or duplicate written-tie incidence')


def context(core, notation):
    return music.written_tie_context(notation, core)


def _affected_unknown(nodes, unresolved, refs):
    owners = set(refs); result = []
    for row in unresolved:
        destination = row['destination']; b = nodes[destination]
        adjacent = [ref for ref in owners if ref == destination or
                    nodes[ref]['lane'] is not None and b['lane'] is not None and
                    nodes[ref]['lane'][:2] == b['lane'][:2] and
                    nodes[ref]['onset'] + nodes[ref]['duration'] == b['onset']]
        if adjacent:
            result.append(dict(destination=destination, reason=row['reason'], adjacent_owned_refs=sorted(adjacent, key=address)))
    return result


def build(nodes, true_ids, refs):
    result = empty(refs)
    if not set(refs) <= set(nodes):
        raise ValueError('Dangling written-tie owner scope')
    links, unresolved = music.written_tie_edges(nodes, true_ids)
    if _affected_unknown(nodes, unresolved, refs):
        raise ValueError('UNRESOLVED_AFFECTED_WRITTEN_TIE: endpoint cannot be established')
    result['relations'] = sorted((relation(r) for r in links if set(refs).intersection((r['origin'], r['destination']))),
                                 key=lambda r: (address(r['destination_ref']), address(r['origin_ref'])))
    for row in result['incidence']:
        row['relation_refs'] = [r['id'] for r in result['relations'] if row['occurrence_ref'] in (r['origin_ref'], r['destination_ref'])]
    shape(result, refs)
    return result


def validate(scope, nodes, true_ids, refs):
    """The SAME predicate for a proposed projection and reconstructed output."""
    shape(scope, refs)
    if not set(refs) <= set(nodes):
        raise ValueError('Dangling written-tie owner scope')
    links, unresolved = music.written_tie_edges(nodes, true_ids)
    present = {(r['origin'], r['destination'], r['kind']) for r in links}
    for row in scope['relations']:
        if (row['origin_ref'], row['destination_ref'], row['kind']) not in present:
            raise ValueError('WRITTEN_TIE_LOCK_CONFLICT: saved endpoints no longer share contiguous same-string written pitch')
    if _affected_unknown(nodes, unresolved, refs):
        raise ValueError('UNRESOLVED_AFFECTED_WRITTEN_TIE: endpoint cannot be established')
    current = build(nodes, true_ids, refs)
    if current != scope:
        raise ValueError('Incomplete or changed saved written-tie constraints')


def proposed(scope, nodes, true_ids, refs, edits):
    """Edits contain current proposed pitch/string only; never persist nodes.

    A source-validated empty incidence is safe to reuse while clocks and tie
    declarations remain fixed. No complete score is rebuilt per contact tuple.
    """
    shape(scope, refs)
    if not scope['relations']:
        return
    changed = dict(nodes)
    for ref, edit in edits.items():
        if ref not in refs or set(edit) != {'pitch', 'string', 'valid_position'}:
            raise ValueError('Bounded written-tie projection required')
        old = nodes[ref]
        if old['lane'] is None or type(edit['string']) is not int or edit['string'] < 0 or type(edit['valid_position']) is not bool:
            raise ValueError('Known proposed written contact required')
        changed[ref] = dict(old, position=F(edit['pitch']), lane=(*old['lane'][:2], edit['string']), valid_position=edit['valid_position'])
    validate(scope, changed, true_ids, refs)


def from_tier1(core, tier1, refs):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    # This shortcut avoids importing a second source-pitch stream merely to
    # establish that the scoped parts contain no true tie declarations.
    parts = {address(ref)[1] for ref in refs}
    declarations = [r for r in tier1['facts'] if r['id'].endswith('/tie') and r.get('value') is True and
                    r['document'] in {f'track-{part}.json' for part in parts}]
    if not declarations:
        return empty(refs)
    notation = extract_documents(project_documents(tier1))['tie_notation']
    nodes, true_ids = context(core, notation)
    return build(nodes, true_ids, refs)


def validate_tier1(scope, core, tier1, refs):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    shape(scope, refs)
    if not scope['relations']:
        # Rebuild scope to detect an omitted incident relationship rather than
        # treating an arbitrary empty list as proof that no dependency exists.
        if from_tier1(core, tier1, refs) != scope:
            raise ValueError('Incomplete saved written-tie constraints')
        return
    notation = extract_documents(project_documents(tier1))['tie_notation']
    nodes, true_ids = context(core, notation)
    validate(scope, nodes, true_ids, refs)
