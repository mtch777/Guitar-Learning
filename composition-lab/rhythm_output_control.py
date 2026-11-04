"""Count actual changed attacks when choosing existing material clock offsets.

The denominator is frozen before feasibility. A dynamic program only removes
arithmetically impossible combinations of disjoint local clocks; distinct offset
vectors with the same count remain distinct. Every committed choice passes the
existing complete inverse and a final occurrence-based onset comparison.
"""
from copy import deepcopy
from fractions import Fraction as F
import math
import random

import material_rhythm_control as rhythm
import support_material_uses as uses
from group_rhythm_relations import relation as clock_relation
from output_change_targets import freeze_targets, evaluate_targets
from source_fact_tier1 import project_documents
from source_key_tier1 import extract_documents
from source_observation_evidence import digest


FEATURE = 'attack_onset_q'
SCHEMA = 'rhythm-output-control/1'


def _requests(upper, requests):
    uses._shape(upper)
    if upper['schema'] != uses.DIRECT_SCHEMA:
        raise ValueError('Direct T3 material uses required')
    if type(requests) is not list or not requests:
        raise ValueError('Nonempty explicit rhythmic use requests required')
    seen, occupied = set(), set()
    for request in requests:
        if type(request) is not dict or set(request) != {'use_id', 'scope', 'intention'}:
            raise ValueError('Exact use/scope/earlier-or-later request required')
        identity, scope = request['use_id'], request['scope']
        if type(identity) is not str or identity in seen:
            raise ValueError('Unique stable rhythmic use identities required')
        seen.add(identity)
        use = rhythm._use(upper, identity)
        if type(scope) is not dict or set(scope) != {'parts', 'first_bar', 'last_bar'}:
            raise ValueError('Exact rhythmic destination scope required')
        uses.material._scope(scope['parts'], scope['first_bar'], scope['last_bar'])
        if scope != upper['slots'][use['slot_ref']]['scope']:
            raise ValueError('Rhythmic request scope differs from its saved use')
        if request['intention'] not in ('earlier', 'later'):
            raise ValueError('Explicit earlier/later rhythmic intention required')
        cells = {(p, b) for p in scope['parts']
                 for b in range(scope['first_bar'], scope['last_bar'] + 1)}
        if occupied & cells:
            raise ValueError('Disjoint part/bar scopes required for rhythmic count composition')
        occupied.update(cells)


def _inside(event, scope):
    return (event['part_id'] in scope['parts']
            and scope['first_bar'] <= event['bar'] <= scope['last_bar'])


def _source(documents, event):
    measure = documents[f'track-{event["part_id"]}.json']['measures'][event['bar'] - 1]
    voice = measure['voices'][event['voice']]
    beat = voice['beats'][event['beat']]
    return measure, voice, beat, beat['notes'][event['note']]


def _beat_ref(event):
    return (f'track-{event["part_id"]}.json#/measures/{event["bar"]-1}'
            f'/voices/{event["voice"]}/beats/{event["beat"]}')


def _inventory(documents, events, requests):
    """A written dead/grace/unknown attack stays visible even if editing refuses."""
    rows, excluded = {}, []
    for request in requests:
        selected = []
        for event in events:
            if not _inside(event, request['scope']):
                continue
            measure, voice, beat, note = _source(documents, event)
            if any(v.get('rest') is True for v in (measure, voice, beat, note)):
                excluded.append(dict(id=event['id'], reason='explicit_rest'))
                continue
            if note.get('tie') is True:
                excluded.append(dict(id=event['id'], reason='tied_continuation_not_new_attack'))
                continue
            kind = ('unknown_tie' if 'tie' in note and type(note['tie']) is not bool
                    else 'grace' if beat.get('graceNote') else 'dead' if note.get('dead')
                    else 'unknown_pitch' if event['pitch'] is None else 'pitched')
            selected.append(dict(id=event['id'], onset_q=event['onset_q'],
                                 beat_ref=_beat_ref(event), kind=kind))
        # The normalized event reader omits explicit note rests. Record their
        # structural exclusion without turning silent placeholders into attacks.
        scope = request['scope']
        for part in scope['parts']:
            track = documents[f'track-{part}.json']
            for bar in range(scope['first_bar'], scope['last_bar'] + 1):
                measure = track['measures'][bar - 1]
                for vi, voice in enumerate(measure['voices']):
                    for bi, beat in enumerate(voice['beats']):
                        for ni, note in enumerate(beat.get('notes', [])):
                            if note.get('rest') is True:
                                excluded.append(dict(
                                    id=f'track-{part}.json#/measures/{bar-1}/voices/{vi}/beats/{bi}/notes/{ni}',
                                    reason='explicit_rest'))
        rows[request['use_id']] = selected
    return rows, excluded


def _project_onsets(definition, slot, attacks):
    """Use the existing shared clock equation and existing occurrence mapping."""
    clock = clock_relation(start_q='0', span_q=definition['span_q'],
                           shares=definition['pulse_shares'])
    fact, _, _ = uses._maps(definition, slot)
    by_beat = {fact(s['beat_ref']): str(F(slot['start_q']) + F(clock['onsets_q'][s['from_pulse']]))
               for s in definition['slots']}
    if len(by_beat) != len(definition['slots']):
        raise ValueError('Noninjective rhythmic beat placement')
    if any(a['beat_ref'] not in by_beat for a in attacks):
        raise ValueError('Declared attack lacks a complete shared-clock slot')
    return {a['id']: by_beat[a['beat_ref']] for a in attacks}


def measurements(lower, requests):
    """Measure a supplied realized T1; this checker does not authorize an edit.

    Composed callers can use their final existing-inverse result without another
    reconstruction. The target contract must still come from the initial input.
    """
    documents = project_documents(lower)
    events = extract_documents(documents)['events']
    inventory, _ = _inventory(documents, events, requests)
    values = {a['id']: a['onset_q'] for rows in inventory.values() for a in rows}
    if len(values) != sum(map(len, inventory.values())):
        raise ValueError('An attack cannot belong to two requested rhythmic uses')
    return {FEATURE: values}


def _options(upper, request, documents, events, attacks):
    from material_approaches import SCHEMA as approach_schema, expand as expand_approach
    from material_rhythm_displacement import solve
    use = rhythm._use(upper, request['use_id'])
    current = use.get('rhythm_offset_q', '0')
    baseline = {a['id']: a['onset_q'] for a in attacks}
    unchanged = dict(offset_q=current, changed_count=0, changed_ids=[], onsets=baseline)
    choices = [unchanged]
    row = dict(**deepcopy(request), current_offset_q=current, attacks=attacks,
               admitted=choices, rejected=[], evidence=None)
    try:
        if any(a['kind'] == 'unknown_tie' for a in attacks):
            raise ValueError('Unresolved tie flag remains in attack denominator; timing edit unsupported')
        # Same backing vocabulary and clock/notation admission as the existing
        # control. Context was realized once, before ANY candidate was examined.
        evidence = rhythm._options_from_context(upper, request['use_id'], documents, events)
        row['evidence'] = evidence
        definition = upper['materials'][use['material_ref']]
        if definition['schema'] == approach_schema:
            definition = expand_approach(definition, use['approach_mode'])
        definition = uses.material.rhythm_context(definition, upper['lower_tier'])
        slot = upper['slots'][use['slot_ref']]
        solved, _ = solve(definition, current)
        if _project_onsets(solved, slot, attacks) != baseline:
            raise ValueError('Shared clock projection differs from the current realized attacks')
    except ValueError as error:
        row['rejected'].append(dict(status='CURRENT_SCOPE_UNSUPPORTED', reason=str(error)))
        row['fixed_attack_ids'] = sorted(baseline)
        return row
    sign = 1 if request['intention'] == 'later' else -1
    for attempt in evidence['attempts']:
        offset = attempt['offset_q']
        if offset == current:
            continue
        if attempt['status'] != 'CLOCK_AND_NOTATION_FIT':
            row['rejected'].append(deepcopy(attempt))
            continue
        if (F(offset) - F(current)) * sign <= 0:
            row['rejected'].append(dict(offset_q=offset, status='OUTSIDE_DECLARED_INTENTION'))
            continue
        try:
            solved, _ = solve(definition, offset)
            proposed = _project_onsets(solved, slot, attacks)
            changed = sorted(k for k in baseline if proposed[k] != baseline[k])
            if not changed:
                raise ValueError('Offset changes no declared attack onset')
            choices.append(dict(offset_q=offset, changed_count=len(changed),
                                changed_ids=changed, onsets=proposed))
        except ValueError as error:
            row['rejected'].append(dict(offset_q=offset, status='REFUSED', reason=str(error)))
    row['fixed_attack_ids'] = sorted(k for k in baseline
                                    if all(c['onsets'][k] == baseline[k] for c in choices))
    return row


def _prepare(upper, requests, percent):
    _requests(upper, requests)
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError('Integer output percentage from 0 to 100 required')
    lower = uses.reconstruct(upper, {'variation': 0})
    documents = project_documents(lower)
    events = extract_documents(documents)['events']
    inventory, excluded = _inventory(documents, events, requests)
    baseline = {a['id']: a['onset_q'] for rows in inventory.values() for a in rows}
    if len(baseline) != sum(map(len, inventory.values())):
        raise ValueError('An attack cannot belong to two requested rhythmic uses')
    contract = freeze_targets({FEATURE: baseline}, {FEATURE: percent})
    measured = evaluate_targets(contract, {FEATURE: baseline})
    report = dict(schema=SCHEMA, input_sha256=digest(upper), requests=deepcopy(requests),
                  feature='Absolute written onset of each pitched/dead/grace/unknown attack; coattack members count individually.',
                  context='Current input only; alternatives do not become original observations.',
                  target_contract=contract, output=measured, structural_exclusions=excluded,
                  satisfied=measured['satisfied'], changed=False, committed=False, groups=[],
                  search=dict(method='disjoint_clock_counts_then_complete_inverse',
                              checked_combinations=0, failures=[]))
    if not baseline:
        report['status'] = 'NOT_APPLICABLE'
        return report, events
    if percent == 0:
        report['status'] = 'CURRENT_ZERO_LOCK'
        return report, events
    report['groups'] = [_options(upper, r, documents, events, inventory[r['use_id']]) for r in requests]
    return report, events


def _suffixes(groups):
    # Retain multiplicity: equally sized but different musical alternatives are
    # not collapsed into one representative that might fail a later dependency.
    suffix = [None] * (len(groups) + 1)
    suffix[-1] = {0: 1}
    for index in range(len(groups) - 1, -1, -1):
        counts = {}
        for option in groups[index]['admitted']:
            for remainder, combinations in suffix[index + 1].items():
                total = option['changed_count'] + remainder
                counts[total] = counts.get(total, 0) + combinations
        suffix[index] = counts
    return suffix


def _vectors(groups, suffix, target, seed):
    rng = random.Random(f'rhythm-output-control:{seed}')
    order = [list(g['admitted']) for g in groups]
    for choices in order:
        rng.shuffle(choices)
    def visit(index, remainder, path):
        if index == len(order):
            yield path
            return
        for option in order[index]:
            remaining = remainder - option['changed_count']
            if remaining in suffix[index + 1]:
                yield from visit(index + 1, remaining, path + [option])
    yield from visit(0, target, [])


def _protected(upper, changed, selected_ids):
    expected, actual = deepcopy(upper), deepcopy(changed)
    for model in (expected, actual):
        for use in model['uses']:
            if use['id'] in selected_ids:
                use.pop('rhythm_offset_q', None)
    if expected != actual:
        raise ValueError('Rhythmic choice changed an unrelated owner or original evidence')


def _final_values(changed, before_events, contract, groups, vector):
    documents = project_documents(uses.reconstruct(changed, {'variation': 0}))
    events = extract_documents(documents)['events']
    before, after = ({e['id']: e for e in rows} for rows in (before_events, events))
    if len(before) != len(before_events) or len(after) != len(events) or set(before) != set(after):
        raise ValueError('Rhythmic operation changed written occurrence identities')
    scopes = [g['scope'] for g in groups]
    for identity, event in before.items():
        actual = after[identity]
        if not any(_inside(event, scope) for scope in scopes):
            if actual != event:
                raise ValueError('Rhythmic operation changed an outside-scope event')
        elif any(actual[k] != v for k, v in event.items() if k not in ('onset_q', 'duration_q')):
            raise ValueError('Rhythmic operation changed a non-clock event field')
    selected = contract['baseline'][FEATURE]
    final = {k: after[k]['onset_q'] for k in selected}
    expected = {k: v for option in vector for k, v in option['onsets'].items()}
    if final != expected:
        raise ValueError('Complete inverse disagrees with disjoint clock projection; context coupling unresolved')
    return {FEATURE: final}


def intervene(upper, requests, percent, seed=0, max_combinations=64):
    """Return (model, report); unmet targets return the complete unchanged input.

    Percentages count final changed attacks, not released uses. No-op/unsupported
    units remain in the denominator. Seed orders equally eligible exact-target
    vectors; it neither changes the target nor supplies a musical preference.
    max_combinations bounds complete inverse attempts, not random sampler draws.
    """
    if type(seed) is not int or type(max_combinations) is not int or max_combinations < 1:
        raise ValueError('Integer seed and positive complete-combination budget required')
    report, events = _prepare(upper, requests, percent)
    report.update(seed=seed, max_combinations=max_combinations)
    if 'status' in report:
        return deepcopy(upper), report
    groups, search = report['groups'], report['search']
    suffix = _suffixes(groups)
    target = report['output']['features'][FEATURE]['target_count']
    matching = suffix[0].get(target, 0)
    search.update(clock_reachable_changed_counts=sorted(suffix[0]),
                  total_offset_vectors=math.prod(len(g['admitted']) for g in groups),
                  target_matching_vectors=matching,
                  enumeration='All distinct options retained; only impossible count suffixes pruned.')
    report['fixed_attack_ids'] = sorted(k for g in groups for k in g['fixed_attack_ids'])
    if not matching:
        report['status'] = 'TARGET_UNREACHABLE_WITH_DECLARED_CLOCK_OPTIONS'
        search['exhaustive_for_target'] = True
        return deepcopy(upper), report
    for vector in _vectors(groups, suffix, target, seed):
        if search['checked_combinations'] >= max_combinations:
            break
        search['checked_combinations'] += 1
        offsets = [dict(use_id=g['use_id'], scope=deepcopy(g['scope']), offset_q=c['offset_q'])
                   for g, c in zip(groups, vector) if c['offset_q'] != g['current_offset_q']]
        try:
            changed = rhythm.candidate_many(upper, offsets) if offsets else deepcopy(upper)
            _protected(upper, changed, {r['use_id'] for r in offsets})
            values = _final_values(changed, events, report['target_contract'], groups, vector)
            measured = evaluate_targets(report['target_contract'], values)
            if not measured['satisfied']:
                raise ValueError('Final changed-attack target was not satisfied')
        except ValueError as error:
            search['failures'].append(dict(offsets=offsets, reason=str(error)))
            continue
        report.update(status='SATISFIED', output=measured, satisfied=True, committed=True,
                      changed=bool(measured['features'][FEATURE]['changed_count']), offsets=offsets)
        search['exhaustive_for_target'] = search['checked_combinations'] == matching
        return changed, report
    search['exhaustive_for_target'] = search['checked_combinations'] == matching
    report['status'] = ('TARGET_REFUSED_BY_COMPLETE_INVERSE' if search['exhaustive_for_target']
                        else 'COMBINATION_BUDGET_EXHAUSTED')
    return deepcopy(upper), report
