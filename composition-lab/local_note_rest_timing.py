"""Public source-supported release of an existing note/rest boundary.

Percentages select whether the observed alternative is released. They never
interpolate a duration or create new note/rest occurrences.
"""
from copy import deepcopy
import random

import note_rest_timing as timing
from source_observation_evidence import (
    assert_only_parameter_changes, controlled_update, validate_origin,
)

POLICY = timing.POLICY
OWNER = 'source_note_rest_timing'


def attach(upper, bindings):
    """Transfer existing scalar/time ownership once, before source edits."""
    from connected_tier2 import realize, strip_lower
    original = strip_lower(upper)
    validate_origin(original.get('source_origin'))
    if original['musical_relationships'].get('schema') == timing.SCHEMA:
        raise ValueError('Existing note/rest observations must be updated, never relearned')
    before = realize(original)
    model = timing.lift(before, original['musical_relationships'], bindings, original['source_origin'])
    _, values = timing.expand(model)
    choices = original['owned_parameters']['source_choices']
    ledger = original['coverage']
    fixed = ledger['fixed'] if type(ledger) is dict else ledger
    for ref, value in values.items():
        selected = [row for row in choices if row['fact_ref'] == ref]
        covered = [row for row in fixed if row['fact_ref'] == ref]
        if (len(selected) != 1 or selected[0]['owner'] != 'source_notation_choice'
                or len(covered) != 1 or covered[0]['owner'] != 'source_notation_choice'):
            raise ValueError('Exactly one existing source-notation owner must transfer to note/rest timing')
        source = [row for row in before['facts'] if row['id'] == ref]
        if len(source) != 1 or source[0].get('value') != value:
            raise ValueError('Notation owner transfer must preserve the original source scalar')
    result = deepcopy(original)
    result['musical_relationships'] = model
    result['owned_parameters']['source_choices'] = [row for row in result['owned_parameters']['source_choices']
                                                   if row['fact_ref'] not in values]
    coverage = result['coverage']
    for row in coverage['fixed'] if type(coverage) is dict else coverage:
        if row['fact_ref'] in values:
            row['owner'] = OWNER
    timing.validate_source(model, before)
    if realize(result) != before:
        raise ValueError('Note/rest ownership changed the complete source realization')
    return result


def validate_controls(controls):
    if (type(controls) is not dict or set(controls) != {'context_policy', 'rhythm', 'target_ref', 'seed'}
            or controls['context_policy'] != POLICY):
        raise ValueError('Exact source note/rest timing controls required; other dimensions are locked')
    if type(controls['rhythm']) is not int or not 0 <= controls['rhythm'] <= 100 or type(controls['seed']) is not int:
        raise ValueError('Integer rhythm release 0..100 and integer seed required')
    ref = controls['target_ref']
    if type(ref) is not str or not ref.startswith('source-note-rest:'):
        raise ValueError('Explicit owned note/rest identity required')
    pair = ref[len('source-note-rest:'):].split('|')
    if len(pair) != 2 or timing.pair_id(*pair) != ref:
        raise ValueError('Canonical owned note/rest identity required')
    pid, mi, vi, bi = timing.address(pair[0])
    if timing.address(pair[1]) != (pid, mi, vi, bi + 1):
        raise ValueError('Adjacent same-voice note/rest identity required')


@controlled_update
def intervene(upper, controls):
    from connected_tier2 import realize
    validate_controls(controls)
    model = upper['musical_relationships']
    timing.validate_model(model, upper.get('source_origin'))
    validate_origin(upper.get('source_origin'))
    found = [(i, pair) for i, pair in enumerate(model['pairs']) if pair['id'] == controls['target_ref']]
    if len(found) != 1:
        raise ValueError('The selected note/rest pair must already be owned')
    index, pair = found[0]
    before = realize(upper)
    timing.validate_source(model, before)
    released = random.Random(controls['seed']).random() < controls['rhythm'] / 100
    result = deepcopy(upper)
    if released:
        result['musical_relationships'] = timing.apply(model, controls['target_ref'])
    prefix = ('musical_relationships', 'pairs', index, 'shares')
    assert_only_parameter_changes(upper, result, [prefix + (i,) for i in range(2)])
    after = realize(result)
    check = timing.verify_effect(before, after, result['musical_relationships'], controls['target_ref'])
    changed = after != before
    status = ('EXACT_ZERO_LOCK' if controls['rhythm'] == 0 else 'REFERENCE_RETAINED' if not released
              else 'SOURCE_SUPPORTED_NOTE_REST_CHANGE' if changed else 'OBSERVED_COINCIDENCE')
    return result, dict(status=status, released=released, changed=changed,
                        relationships_changed=result != upper, target_ref=pair['id'],
                        rhythm=controls['rhythm'], seed=controls['seed'],
                        donor_basis=pair['observations']['basis'],
                        cross_part_donor=pair['observations']['target']['part_id'] != pair['observations']['donor']['part_id'],
                        influence_check=check)
