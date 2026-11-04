"""Check written bend arrivals against every retained tonal interpretation.

This reads the existing exact technique/unit relationship. It neither chooses
pitches nor changes curves. Continuous travel between targets is not constrained
to discrete scale notes. Negative excursions are explicitly unsupported here.
"""
from copy import deepcopy
from fractions import Fraction as F
import re

import bend_gesture_ownership as bend
import musical_tier2 as music
import technique_observation_relations as techniques


SCHEMA = 'declared-bend-target-constraints/1'


def _hypotheses(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('BEND_CONTEXT_MISSING: explicit retained interpretations required')
    result = []
    for row in rows:
        if not isinstance(row, dict) or not {'id', 'tonic_pc', 'intervals'} <= set(row):
            raise ValueError('Invalid bend tonal interpretation')
        h = {k: deepcopy(row[k]) for k in ('id', 'tonic_pc', 'intervals')}
        if not isinstance(h['id'], str) or not h['id']:
            raise ValueError('Explicit interpretation identity required')
        music.collection_degree_relation(h['tonic_pc'], h['intervals'], degree=1, relative_octaves=0)
        if any(p['id'] == h['id'] for p in result):
            raise ValueError('Duplicate bend interpretation identity')
        result.append(h)
    return result


def _targets(group):
    prefix = group['source_fact_ref']
    shape = {r['id']: r for r in group['structure']}
    values = {p['fact_ref']: p['parameter'].get('normalized') for p in group['parameters']}
    point_root = shape.get(prefix + '/points')
    if not point_root or point_root['type'] != 'array':
        raise ValueError('BEND_CURVE_UNSUPPORTED: explicit point array required')
    points = []
    for ref in point_root['children']:
        time_ref = ref + ('/precisePosition' if ref + '/precisePosition' in values else '/position')
        if values.get(time_ref) is None or values.get(ref + '/tone') is None:
            raise ValueError('BEND_CURVE_UNSUPPORTED: numerical point time and tone required')
        for field in ('vibrato',):
            value = next((p['parameter'] for p in group['parameters'] if p['fact_ref'] == ref + '/' + field), None)
            if value is not None and value not in ({'normalized': '0', 'negative_zero': False}, {'symbol': False}):
                raise ValueError('BEND_CURVE_UNSUPPORTED: point vibrato target range is unspecified')
        points.append((F(values[time_ref]), F(values[ref + '/tone'])))
    if len(points) < 2 or points[0][0] != 0 or points[-1][0] != 1 or any(
            b[0] <= a[0] for a, b in zip(points, points[1:])):
        raise ValueError('BEND_CURVE_UNSUPPORTED: ordered full-duration points required')
    if any(y < 0 for _, y in points):
        raise ValueError('BEND_CURVE_UNSUPPORTED: negative excursion is not implemented')
    peak = max(y for _, y in points)
    if peak <= 0:
        raise ValueError('BEND_CURVE_UNSUPPORTED: positive declared excursion required')
    if prefix + '/tone' in values and (values[prefix + '/tone'] is None or F(values[prefix + '/tone']) != peak):
        raise ValueError('BEND_CURVE_UNSUPPORTED: declared extent contradicts point maximum')
    targets = []
    for i, (x, y) in enumerate(points):
        roles = []
        if i == len(points) - 1:
            roles.append('arrival')
        if i == 0 and y:
            roles.append('prebend')
        if i < len(points) - 1 and points[i + 1][1] == y:
            roles.append('plateau')
        if 0 < i < len(points) - 1 and (y - points[i - 1][1]) * (points[i + 1][1] - y) < 0:
            roles.append('turn')
        if roles:
            row = dict(position=str(x), offset=str(y), roles=roles)
            if 'plateau' in roles:
                row['until_position'] = str(points[i + 1][0])
            targets.append(row)
    return targets


def capture(tier1, hypotheses_by_ref):
    """Return current occurrence -> exact target constraints; refuse unknowns.

    T1 is an in-memory score produced by the shared inverse, never a file/cache.
    All explicit bends must have context; an omitted bend cannot silently pass.
    """
    observed = techniques.lift(tier1)
    unsupported = [r for r in observed['unsupported'] if r['field'] == 'bend']
    if unsupported:
        raise ValueError('BEND_CURVE_UNSUPPORTED: ' + ', '.join(r['source_fact_ref'] for r in unsupported))
    facts = {r['id']: r for r in tier1['facts']}
    song = facts.get('metadata.json#/songId', {}).get('value')
    result = {}
    for group in observed['groups']:
        if group['field'] != 'bend':
            continue
        match = re.fullmatch(r'(track-\d+\.json)#/measures/(\d+)/voices/(\d+)/beats/(\d+)/notes/(\d+)', group['owner_ref'])
        if match is None or type(song) is not int:
            raise ValueError('BEND_IDENTITY_UNSUPPORTED: exact source note identity required')
        document, bar, voice, beat, note = match.groups()
        part = facts.get(document + '#/partId', {}).get('value')
        if type(part) is not int:
            raise ValueError('BEND_IDENTITY_UNSUPPORTED: exact part identity required')
        ref = f'event:{song}:{part}:{int(bar)+1}:{voice}:{beat}:{note}'
        if ref in result:
            raise ValueError('Duplicate bend occurrence')
        if any(facts.get(group['owner_ref'] + '/' + field, {}).get('value') for field in ('rest', 'dead')):
            raise ValueError('BEND_CURVE_UNSUPPORTED: unpitched bend occurrence')
        result[ref] = dict(schema=SCHEMA, occurrence_ref=ref, source_fact_ref=group['source_fact_ref'],
                           hypotheses=_hypotheses(hypotheses_by_ref.get(ref)), targets=_targets(group))
    return result


def evaluate(constraint, pitch):
    """Return target membership under ALL interpretations without selecting one."""
    if constraint.get('schema') != SCHEMA:
        raise ValueError('Unknown bend constraint interface')
    hypotheses = _hypotheses(constraint['hypotheses'])
    base = music.fraction(str(pitch))
    results = []
    for target in constraint['targets']:
        offset = F(target['offset'])
        if offset < 0:
            raise ValueError('BEND_CURVE_UNSUPPORTED: negative excursion is not implemented')
        # The existing bend equation requires positive extent. Zero is identity.
        arrival = (bend.relation(extent=str(offset), frame='start', base=str(base))['arrival']
                   if offset else str(base))
        interpretations = []
        for h in hypotheses:
            try:
                music.collection_degree_relation(h['tonic_pc'], h['intervals'], pitch=arrival)
                valid = True
            except ValueError as error:
                if 'outside this reference collection' not in str(error):
                    raise
                valid = False
            interpretations.append(dict(interpretation_id=h['id'], in_collection=valid))
        results.append(dict(**deepcopy(target), pitch=arrival, interpretations=interpretations))
    if not results:
        raise ValueError('Explicit bend targets required')
    return dict(admissible=all(i['in_collection'] for r in results for i in r['interpretations']), targets=results)


def filter_choices(constraint, choices):
    """Preserve caller ordering/metadata; report every rejected candidate."""
    admitted, rejected = [], []
    for choice in choices:
        if not isinstance(choice, dict) or choice.get('pitch') is None:
            raise ValueError('A written candidate pitch is required')
        result = evaluate(constraint, choice['pitch'])
        if result['admissible']:
            admitted.append(deepcopy(choice))
        else:
            rejected.append(dict(choice=deepcopy(choice), **result))
    return dict(admitted=admitted, rejected=rejected)
