"""An ordered, stepwise approach to one arrival in explicit tonal collections.

The same collection-degree equation fits and realizes the approach. This module
does not infer a key, choose a preferred direction, own score events, or group
ties. A caller supplies ordered attacks and retains their timing and identity.
"""
from copy import deepcopy

from musical_tier2 import collection_degree_relation, fraction


SCHEMA = 'melodic-arrival-relation/1'
_FIELDS = {'schema', 'count', 'original_direction', 'arrival_pitch', 'interpretations'}


def _pitch(value):
    if type(value) is not str or fraction(value).denominator != 1:
        raise ValueError('An integral pitch as a canonical rational string is required')
    return value


def _interpretations(values, arrival):
    if type(values) is not list or not values:
        raise ValueError('A nonempty explicit list of tonal interpretations is required')
    identifiers = set()
    for item in values:
        if type(item) is not dict or set(item) != {'id', 'tonic_pc', 'intervals'}:
            raise ValueError('Each interpretation requires exactly id, tonic_pc, and intervals')
        if type(item['id']) is not str or not item['id'].strip() or item['id'] in identifiers:
            raise ValueError('Distinct nonempty interpretation identities are required')
        identifiers.add(item['id'])
        # The existing equation validates the reference and exact membership.
        collection_degree_relation(item['tonic_pc'], item['intervals'], pitch=arrival)


def _check(model):
    if type(model) is not dict or set(model) != _FIELDS or model['schema'] != SCHEMA:
        raise ValueError('An exact melodic-arrival relationship without extra payloads is required')
    if type(model['count']) is not int or model['count'] < 3:
        raise ValueError('At least three ordered attacks are required')
    if type(model['original_direction']) is not int or model['original_direction'] not in (-1, 1):
        raise ValueError('Original direction must be exactly -1 or +1')
    _interpretations(model['interpretations'], _pitch(model['arrival_pitch']))


def _consensus(model, direction):
    result = None
    first_id = None
    for item in model['interpretations']:
        intervals = item['intervals']
        arrival = collection_degree_relation(
            item['tonic_pc'], intervals, pitch=model['arrival_pitch'])['diatonic_coordinate']
        pitches = []
        for index in range(model['count']):
            coordinate = arrival - direction * (model['count'] - 1 - index)
            octave, degree_index = divmod(coordinate, len(intervals))
            pitches.append(collection_degree_relation(
                item['tonic_pc'], intervals,
                degree=degree_index + 1, relative_octaves=octave)['pitch'])
        if result is not None and pitches != result:
            raise ValueError(f'Tonal interpretations disagree on exact realization: {first_id} / {item["id"]}')
        result, first_id = pitches, item['id']
    return result


def validate(model):
    """Check the complete payload and original-direction agreement.

    An exactly representable original may still have an ambiguous flip. Such a
    flip is refused by realize(), while the original remains reconstructable.
    """
    _check(model)
    _consensus(model, model['original_direction'])


def realize(model, mode='original'):
    """Derive all pitches from the arrival and signed consecutive degree distances."""
    if mode not in ('original', 'flip'):
        raise ValueError('Mode must be original or flip')
    _check(model)
    original = _consensus(model, model['original_direction'])
    return original if mode == 'original' else _consensus(model, -model['original_direction'])


def fit(pitches, interpretations):
    """Abstract consecutive, monotone attacks without retaining their pitch stream."""
    if type(pitches) is not list or len(pitches) < 3:
        raise ValueError('At least three ordered attacks are required')
    source = [_pitch(pitch) for pitch in pitches]
    _interpretations(interpretations, source[-1])
    direction = None
    for item in interpretations:
        coordinates = [collection_degree_relation(
            item['tonic_pc'], item['intervals'], pitch=pitch)['diatonic_coordinate']
            for pitch in source]
        steps = [b - a for a, b in zip(coordinates, coordinates[1:])]
        if steps[0] not in (-1, 1) or any(step != steps[0] for step in steps):
            raise ValueError(f'Not a strictly consecutive monotone approach under {item["id"]}')
        if direction is not None and direction != steps[0]:
            raise ValueError('Tonal interpretations disagree on approach direction')
        direction = steps[0]
    model = dict(schema=SCHEMA, count=len(source), original_direction=direction,
                 arrival_pitch=source[-1], interpretations=deepcopy(interpretations))
    if realize(model) != source:
        raise ValueError('Original pitches were not exactly reconstructed')
    return model
