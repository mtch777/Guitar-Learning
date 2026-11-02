"""Release one observed three-note figure through the existing pitch owner.

The comparison unit is three adjacent written attacks, not a claimed phrase.
Accompaniment is conditioned independently of ALL edited notes. Pitch, contour
and note roles are outcomes; requiring their old values would prohibit melody.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
import math
import re
import melodic_contour_choices as neighborhoods
import melodic_contour_intervention as owner
import context_membership as harmony

POLICY = 'source_local_melodic_figure'


def octave(pitch):
    value = F(pitch)
    if value.denominator != 1:
        raise ValueError('Known integer written pitch required')
    return int(value) // 12 - 1


def matching_key(row):
    if row['reasons'] or row['context_key'] is None:
        return None
    key = {k: deepcopy(v) for k, v in row['context_key'].items()
           if k not in ('outer_pitches', 'directions')}
    key['letter_octaves'] = [octave(p) for p in row['pitches']]
    return neighborhoods.encoded(key)


def prepare(upper):
    prepared = owner.prepare(upper)
    prepared.update(figure_packets={}, by_ref={}, by_key=defaultdict(list))
    for row in prepared['inventory']['neighborhoods']:
        prepared['by_ref'][row['target_ref']] = row
        key = matching_key(row)
        if key is not None:
            prepared['by_key'][key].append(row)
    return prepared


def packet(prepared, row):
    ref = row['target_ref']
    if ref not in prepared['figure_packets']:
        prepared['figure_packets'][ref] = harmony.from_context(
            prepared['context'], prepared['harmony'],
            dict(edited_refs=sorted(row['occurrence_refs']), scope='ensemble_minus_edited'),
            pitch_support='verified_written_ties')
    return prepared['figure_packets'][ref]


def signature(row, contract):
    """Complete relative-time accompaniment, without locking melody outcomes."""
    start = F(row['times'][0][0])
    indices = {ref: i for i, ref in enumerate(row['occurrence_refs'])}
    return [dict(span_q=[str(F(cell['start_q'])-start), str(F(cell['end_q'])-start)],
                 part_ids=cell['part_ids'], hypotheses=cell['hypotheses'],
                 note_indices=[indices[m['occurrence_ref']] for m in cell['memberships']])
            for cell in contract['contexts']]


def apply(upper, target, pitches):
    """No fret generator: the same owned pitch equation solves each fret."""
    if len(target['occurrence_refs']) != 3 or len(pitches) != 3:
        raise ValueError('Complete ordered three-note figure required')
    result = upper
    for ref, pitch in zip(target['occurrence_refs'], pitches):
        result = owner.apply_pitch(result, ref, pitch)
    return result


def bass_profile(prepared, row, contract, pitches):
    """Lock the lowest known written ensemble pitch, not all chord tones."""
    events = prepared['context']['events']
    docs = prepared['context']['documents']
    proposed = dict(zip(row['occurrence_refs'], pitches))
    result = []
    for cell in contract['contexts']:
        refs = set(cell['support_refs']) | {m['occurrence_ref'] for m in cell['memberships']}
        old, new, omitted = [], [], []
        for ref in sorted(refs):
            event = events[ref]
            instrument = docs[f"track-{event['part_id']}.json"].get('instrumentId')
            if type(instrument) is int and instrument == 1024:
                omitted.append(ref)
                continue
            if type(instrument) is not int or not 0 <= instrument < 128 or event['pitch'] is None:
                raise ValueError('Ensemble bass lock has an unknown pitched domain')
            old.append(F(event['pitch']))
            new.append(F(proposed.get(ref, event['pitch'])))
        if not old or min(old) != min(new):
            raise ValueError('Lowest written ensemble pitch changed')
        result.append(dict(start_q=cell['start_q'], end_q=cell['end_q'],
                           lowest_pitch=str(min(old)), excluded_unpitched_refs=omitted))
    return result


def note_path(ref):
    _, _, part, bar, voice, beat, note = ref.split(':')
    return f'track-{part}.json#/measures/{int(bar)-1}/voices/{voice}/beats/{beat}/notes/{note}'


def boundary_intervals(prepared, target, pitches):
    """All nearest outside coattack members; no selected top/bass voice."""
    events = prepared['context']['events']
    proposed = dict(zip(target['occurrence_refs'], pitches))
    first, last = (events[target['occurrence_refs'][i]] for i in (0, -1))
    lane = [e for e in events.values() if e['part_id'] == target['part_id'] and e['voice'] == target['voice']]
    pairs = []
    for boundary, edge, before in (('entry', first, True), ('exit', last, False)):
        neighbors = [e for e in lane if (F(e['onset_q']) < F(edge['onset_q']) if before else F(e['onset_q']) > F(edge['onset_q']))]
        if not neighbors:
            pairs.append(dict(boundary=boundary, status='NO_OUTSIDE_ATTACK'))
            continue
        onset = (max if before else min)(F(e['onset_q']) for e in neighbors)
        for neighbor in neighbors:
            if F(neighbor['onset_q']) != onset:
                continue
            a, b = (neighbor, edge) if before else (edge, neighbor)
            result = dict(boundary=boundary, from_ref=a['id'], to_ref=b['id'],
                          gap_q=str(F(b['onset_q'])-F(a['onset_q'])-F(a['duration_q'])))
            if a['pitch'] is None or b['pitch'] is None:
                result['status'] = 'UNKNOWN_WRITTEN_PITCH'
            else:
                result.update(status='KNOWN_WRITTEN_INTERVAL',
                    before=str(F(b['pitch'])-F(a['pitch'])),
                    after=str(F(proposed.get(b['id'], b['pitch']))-F(proposed.get(a['id'], a['pitch']))))
            pairs.append(result)
    return pairs


def verify(before, after, target, donor, contract, prepared):
    """Entire actual source comparison, execution and harmonic dependencies."""
    from source_fact_tier1 import project_documents
    from execution_dependencies import build as dependencies
    from freeze_technique_baseline import retained
    from chord_degree_relations import note_role
    if matching_key(target) is None or matching_key(target) != matching_key(donor):
        raise ValueError('Written context or octave lock changed')
    expected = deepcopy(before)
    facts = {f['id']: f for f in before['facts']}
    lookup = {f['id']: f for f in expected['facts']}
    allowed = []
    for target_ref, donor_ref in zip(target['occurrence_refs'], donor['occurrence_refs']):
        a, b = note_path(target_ref), note_path(donor_ref)
        if facts[a+'/string']['value'] != facts[b+'/string']['value']:
            raise ValueError('Observed source string differs')
        value = facts[b+'/fret']['value']
        if type(value) is not int or value < 0:
            raise ValueError('Observed nonnegative integer fret required')
        lookup[a+'/fret']['value'] = value
        allowed.append(a+'/fret')
    if expected != after:
        raise ValueError('Actual source differs outside observed figure fret changes')
    current = harmony.compile_lock(after, contract['request'], pitch_support='verified_written_ties')
    if current['status'] != 'SUPPORTED' or harmony._split(contract)[0] != harmony._split(current['packet'])[0]:
        raise ValueError('Independent accompaniment context changed')
    bass = bass_profile(prepared, target, contract, donor['pitches'])
    if dependencies(before)['signature'] != dependencies(after)['signature']:
        raise ValueError('Linked execution relationship changed')
    # Retain the full source layout/catalog; analyzing a part alone could alter
    # its meter/header or instrument context and hide a protected pedal result.
    old_docs = project_documents(before)
    new_docs = project_documents(after)
    if 'approved_pedals' not in prepared:
        prepared['approved_pedals'] = [r['approved_pedal_phrases'] for r in retained(old_docs)['tracks']]
    old_pedals = prepared['approved_pedals']
    new_pedals = [r['approved_pedal_phrases'] for r in retained(new_docs)['tracks']]
    if old_pedals != new_pedals:
        raise ValueError('Approved pedal relationship changed')
    proposed = dict(zip(target['occurrence_refs'], donor['pitches']))
    original = dict(zip(target['occurrence_refs'], target['pitches']))
    roles = [dict(occurrence_ref=m['occurrence_ref'], start_q=cell['start_q'], end_q=cell['end_q'],
                  hypotheses=[dict(hypothesis=h, before=note_role(original[m['occurrence_ref']], h),
                                   after=note_role(proposed[m['occurrence_ref']], h))
                              for h in cell['hypotheses']])
             for cell in contract['contexts'] for m in cell['memberships']]
    return dict(status='EXACT_OBSERVED_FIGURE_SCOPE', bass=bass, roles=roles,
                changed_fact_refs=[a['id'] for a, b in zip(before['facts'], after['facts']) if a != b],
                before_directions=neighborhoods.contour(target['pitches']),
                after_directions=neighborhoods.contour(donor['pitches']),
                before_intervals=[str(F(b)-F(a)) for a, b in zip(target['pitches'], target['pitches'][1:])],
                after_intervals=[str(F(b)-F(a)) for a, b in zip(donor['pitches'], donor['pitches'][1:])],
                boundary_intervals=boundary_intervals(prepared, target, donor['pitches']),
                meaning='Observed joint pitch choice over fixed accompaniment; note roles and boundary intervals are released consequences',
                limits='No inferred phrase, key, emotional intent, artist preference or human playability claim')


def options(upper, target_ref, prepared=None):
    from connected_tier2 import realize
    c = prepare(upper) if prepared is None else prepared
    if target_ref not in c['by_ref']:
        raise ValueError('Original middle occurrence identifying a three-note figure required')
    target = c['by_ref'][target_ref]
    result = dict(target=target, options=[], rejected=[], source_donor_refs=[])
    key = matching_key(target)
    if key is None:
        return dict(result, status='REFUSED_SOURCE_NEIGHBORHOOD')
    candidates = [r for r in c['by_key'][key]
                  if not set(r['closure_refs']).intersection(target['closure_refs'])]
    result['source_donor_refs'] = [r['target_ref'] for r in candidates]
    # No useful alternative exists before harmonic validation; avoid redoing a
    # whole-song context query for every occurrence of an identical figure.
    if not any(r['pitches'] != target['pitches'] for r in candidates):
        return dict(result, status='NO_DIFFERENT_SOURCE_FIGURE')
    wanted = packet(c, target)
    if wanted['status'] != 'SUPPORTED':
        return dict(result, status='MISSING_INDEPENDENT_ACCOMPANIMENT', harmony_reasons=wanted['reasons'])
    contract = wanted['packet']
    result['membership_contract'] = contract
    target_closure = owner.closure(target, contract)
    grouped = defaultdict(list)
    for donor in candidates:
        observed = packet(c, donor)
        reason = None
        if observed['status'] != 'SUPPORTED':
            reason = 'DONOR_INDEPENDENT_ACCOMPANIMENT_MISSING'
        elif signature(target, contract) != signature(donor, observed['packet']):
            reason = 'DONOR_ACCOMPANIMENT_DIFFERS'
        elif target_closure.intersection(owner.closure(donor, observed['packet'])):
            reason = 'SHARED_TARGET_DONOR_SUPPORT'
        if reason:
            result['rejected'].append(dict(donor_ref=donor['target_ref'], reason=reason))
        else:
            grouped[tuple(donor['pitches'])].append(donor)
    for pitches, donors in sorted(grouped.items(), key=lambda item: tuple(F(p) for p in item[0])):
        changed = list(pitches) != target['pitches']
        try:
            proof = verify(c['before'], realize(apply(upper, target, list(pitches))), target,
                           donors[0], contract, c) if changed else dict(status='UNCHANGED_OBSERVED_FIGURE')
            result['options'].append(dict(pitches=list(pitches), donor_refs=sorted(d['target_ref'] for d in donors),
                                          changed=changed, relationships=proof))
        except (ValueError, KeyError, TypeError) as error:
            result['rejected'].append(dict(pitches=list(pitches), donor_refs=[d['target_ref'] for d in donors], reason=str(error)))
    return dict(result, status='OBSERVED_FIGURE_CHOICES' if any(o['changed'] for o in result['options']) else 'NO_ADMITTED_CHANGED_FIGURE')


def validate_controls(controls):
    if type(controls) is not dict or set(controls) != {'context_policy', 'melody', 'target_ref', 'seed'} or controls['context_policy'] != POLICY:
        raise ValueError('Explicit whole-figure melody controls required')
    level = controls['melody']
    if type(level) not in (int, float) or not math.isfinite(level) or not 0 <= level <= 100:
        raise ValueError('Melody release must be finite 0..100')
    if type(controls['seed']) is not int or type(controls['target_ref']) is not str or not re.fullmatch(r'event:\d+:\d+:\d+:\d+:\d+:\d+', controls['target_ref']):
        raise ValueError('Original note identity and typed seed required')


def sample(evidence, controls):
    from declared_degree_choices import sample as release
    validate_controls(controls)
    chosen, report = release(evidence, dict(voicing=controls['melody'], seed=controls['seed']))
    if chosen is not None:
        report['status'] = 'OBSERVED_MELODIC_FIGURE' if report['changed'] else 'OBSERVED_COINCIDENCE'
    return chosen, report


from source_observation_evidence import guarded as _original_observations_required


from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
@_original_observations_required
def intervene(upper, controls):
    from connected_tier2 import realize
    validate_controls(controls)
    realize(upper)
    if controls['melody'] == 0:
        return deepcopy(upper), dict(status='EXACT_ZERO_LOCK', released=False, changed=False)
    evidence = options(upper, controls['target_ref'])
    selected, report = sample(evidence, controls)
    report['evidence'] = evidence
    return (deepcopy(upper) if selected is None else apply(upper, evidence['target'], selected['pitches'])), report
