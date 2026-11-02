"""One fixed span partitioned between a written note and its existing rest.

The shared span/share equation owns both notation and note time. Source donor
observations stay separate from the current partition. This is a transfer of an
observed temporal proportion, not a claim about style or acoustic sustain.
"""
from copy import deepcopy
from fractions import Fraction as F
from math import gcd
import re

from group_rhythm_relations import body_of, relation, refresh
from source_observation_evidence import digest, origin, validate_origin, assert_only_parameter_changes

SCHEMA = 'source-note-rest-timing/1'
POLICY = 'source_note_rest_timing'
BEAT = re.compile(r'track-(0|[1-9]\d*)\.json#/measures/(0|[1-9]\d*)/voices/(0|[1-9]\d*)/beats/(0|[1-9]\d*)')
BINDING_FIELDS = {'note_beat_ref', 'rest_beat_ref', 'donor_note_beat_ref', 'donor_rest_beat_ref'}
OBSERVATION_FIELDS = {'note_beat_ref', 'rest_beat_ref', 'next_beat_ref', 'occurrence_refs',
                      'part_id', 'bar', 'voice', 'start_q', 'span_q', 'shares'}
PAIR_FIELDS = {'id', 'coattack_ref', 'slots', 'shares', 'observations', 'observation_sha256'}
VIEWS = ('ensemble_coattacks', 'nominal_written_spans', 'tonal_evidence', 'temporal_tonal_evidence')


def address(ref):
    match = BEAT.fullmatch(ref) if type(ref) is str else None
    if match is None:
        raise ValueError('Canonical source beat identity required')
    return tuple(map(int, match.groups()))


def pair_id(note_beat_ref, rest_beat_ref):
    address(note_beat_ref); address(rest_beat_ref)
    return 'source-note-rest:' + note_beat_ref + '|' + rest_beat_ref


def _notation(beat, ref):
    from source_rhythm_groups import duration, TYPES
    value = duration(beat)
    typ, dots = beat.get('type'), beat.get('dots', 0)
    if (value is None or type(typ) is not int or typ not in TYPES
            or type(dots) is not int or dots not in (0, 1)
            or value != F(4, typ) * (F(3, 2) if dots else 1)):
        raise ValueError('Only exact flat or single-dot source notation is admitted')
    return dict(beat_ref=ref, fraction_scale=gcd(*beat['duration']), dots_present='dots' in beat)


def notation_values(slot, duration_q):
    from source_rhythm_groups import TYPES
    if (type(slot) is not dict or set(slot) != {'beat_ref', 'fraction_scale', 'dots_present'}
            or type(slot['fraction_scale']) is not int or slot['fraction_scale'] <= 0
            or type(slot['dots_present']) is not bool):
        raise ValueError('Typed existing notation slots required')
    address(slot['beat_ref'])
    value = F(duration_q)
    for dots in ((0, 1) if slot['dots_present'] else (0,)):
        typ = F(4) * (F(3, 2) if dots else 1) / value
        if typ.denominator == 1 and int(typ) in TYPES:
            whole = value / 4; scale = slot['fraction_scale']; ref = slot['beat_ref']
            result = {ref + '/type': int(typ), ref + '/duration/0': whole.numerator * scale,
                      ref + '/duration/1': whole.denominator * scale}
            if slot['dots_present']:
                result[ref + '/dots'] = dots
            return result
    raise ValueError('Selected source proportion has no existing-slot notation solution')


def _context(tier1):
    from source_fact_tier1 import project_documents
    from source_key_tier1 import extract_documents
    docs = project_documents(tier1)
    normal = extract_documents(docs)
    return docs, normal, {e['id']: e for e in normal['events']}


def _plain(beat):
    from source_rhythm_groups import BEAT_EXPR, NOTE_EXPR, SAFE_BEAT, SAFE_NOTE
    if set(beat) - SAFE_BEAT or any(beat.get(k) for k in BEAT_EXPR):
        raise ValueError('Unknown or active beat execution cannot change release')
    if any(beat.get(k) for k in ('graceNote', 'dotted', 'tuplet', 'tupletStart', 'tupletStop')):
        raise ValueError('Grace or tuplet timing cannot use the plain note/rest partition')
    for note in beat.get('notes', []):
        if set(note) - SAFE_NOTE or any(note.get(k) for k in NOTE_EXPR):
            raise ValueError('Tie, curve, ringing or unknown note execution cannot change release')


def _observe(context, note_ref, rest_ref):
    from source_rhythm_groups import duration
    docs, normal, events = context
    pid, mi, vi, bi = address(note_ref)
    if address(rest_ref) != (pid, mi, vi, bi + 1):
        raise ValueError('An adjacent same-voice note and explicit rest are required')
    part = docs[f'track-{pid}.json']; measure = part['measures'][mi]
    if type(part.get('instrumentId')) is not int or not 0 <= part['instrumentId'] <= 127:
        raise ValueError('Known pitched GM instrument required; percussion or unknown domains cannot use note/rest release')
    voices = measure.get('voices', []); voice = voices[vi]; beats = voice.get('beats', [])
    if measure.get('rest') or voice.get('rest') or any(i != vi and v.get('beats') for i, v in enumerate(voices)):
        raise ValueError('Unambiguous single current voice is required for release')
    if bi + 2 >= len(beats):
        raise ValueError('Complete pause needs its following attack in the same measure')
    note, rest, following = beats[bi:bi + 3]
    if (note.get('rest') or not note.get('notes') or any(n.get('rest') for n in note['notes'])
            or rest.get('rest') is not True or not rest.get('notes')
            or any(n != {'rest': True} for n in rest['notes'])
            or following.get('rest') or not following.get('notes') or any(n.get('rest') for n in following['notes'])):
        raise ValueError('Complete note/rest/next-attack boundary required; consecutive rests are not a complete pause')
    # A declared sustained pedal/ring can decouple nominal and performed release.
    if any(b.get('letRing') or b.get('sustainPedal') for m in part.get('measures', [])
           for v in m.get('voices', []) for b in v.get('beats', [])):
        raise ValueError('Unresolved ringing or pedal end in this part')
    for b in beats[max(0, bi - 1):bi + 3]:
        _plain(b)
    slots = [_notation(note, note_ref), _notation(rest, rest_ref)]
    frames = {f['ordinal']: f for f in normal['measure_geometry']['frames']}
    frame = frames[mi + 1]
    warnings = normal['source_coverage']['layout_warnings'] + normal['source_coverage']['timing_warnings']
    if any(w.get('bar') == mi + 1 and w.get('part_id') in (None, pid) for w in warnings):
        raise ValueError('Uncertain selected source clock')
    lengths = [duration(b) for b in beats]
    if any(d is None for d in lengths) or any(b.get('graceNote') for b in beats):
        raise ValueError('Complete known written measure clock required')
    if sum(lengths, F(0)) != F(frame['span_q']):
        raise ValueError('Selected voice must fill the declared measure frame')
    start = F(frame['start_q']) + sum(lengths[:bi], F(0))
    span = lengths[bi] + lengths[bi + 1]
    song = docs['metadata.json']['songId']
    refs = [f'event:{song}:{pid}:{mi + 1}:{vi}:{bi}:{ni}' for ni in range(len(note['notes']))]
    for ref in refs:
        event = events[ref]
        if event['pitch'] is None or F(event['onset_q']) != start or F(event['duration_q']) != lengths[bi]:
            raise ValueError('Selected source attack/clock must agree with the musical projection')
    for ni in range(len(following['notes'])):
        event = events[f'event:{song}:{pid}:{mi + 1}:{vi}:{bi + 2}:{ni}']
        if F(event['onset_q']) != start + span:
            raise ValueError('Following attack must close the selected pause')
    solved = relation(start_q=str(start), span_q=str(span), durations_q=list(map(str, lengths[bi:bi + 2])))
    row = dict(note_beat_ref=note_ref, rest_beat_ref=rest_ref,
               next_beat_ref=rest_ref.rsplit('/', 1)[0] + '/' + str(bi + 2), occurrence_refs=refs,
               part_id=pid, bar=mi + 1, voice=vi, start_q=str(start), span_q=str(span), shares=solved['shares'])
    return row, slots


def _observations(pair, source_origin):
    obs = pair['observations']
    if type(obs) is not dict or set(obs) != {'target', 'donor', 'basis'} or obs['basis'] != 'explicit_same_source_complete_note_rest_proportion':
        raise ValueError('Explicit original complete-pause observations required')
    for row in (obs['target'], obs['donor']):
        if type(row) is not dict or set(row) != OBSERVATION_FIELDS:
            raise ValueError('Unknown original temporal observation')
        pid, mi, vi, bi = address(row['note_beat_ref'])
        if (address(row['rest_beat_ref']) != (pid, mi, vi, bi + 1)
                or address(row['next_beat_ref']) != (pid, mi, vi, bi + 2)
                or (row['part_id'], row['bar'], row['voice']) != (pid, mi + 1, vi)
                or any(type(row[k]) is not int for k in ('part_id', 'bar', 'voice'))
                or type(row['shares']) is not list or len(row['shares']) != 2
                or type(row['occurrence_refs']) is not list or not row['occurrence_refs']
                or len(set(row['occurrence_refs'])) != len(row['occurrence_refs'])):
            raise ValueError('Original pair incidence conflict')
        for ni, ref in enumerate(row['occurrence_refs']):
            if type(ref) is not str or re.fullmatch(r'event:(0|[1-9]\d*)(?::(?:0|[1-9]\d*)){5}', ref) is None:
                raise ValueError('Canonical original note occurrence required')
            if tuple(map(int, ref.split(':')[2:])) != (pid, mi + 1, vi, bi, ni):
                raise ValueError('Original note/beat incidence conflict')
        relation(start_q=row['start_q'], span_q=row['span_q'], shares=row['shares'])
    if obs['target']['occurrence_refs'][0].split(':')[1] != obs['donor']['occurrence_refs'][0].split(':')[1]:
        raise ValueError('Original target and donor must share the captured song identity')
    if set(obs['target']['occurrence_refs']) & set(obs['donor']['occurrence_refs']):
        raise ValueError('Separate explicit source donor required')
    if pair['observation_sha256'] != digest(dict(source_origin=source_origin, observations=obs)):
        raise ValueError('Original temporal observations changed')
    return obs


def lift(tier1, pitch, bindings, source_origin=None):
    declared = origin(tier1)
    if source_origin is not None and source_origin != declared:
        raise ValueError('Cannot relabel edited input as original timing observations')
    if type(bindings) is not list or not bindings:
        raise ValueError('Explicit note/rest source bindings required')
    result = deepcopy(pitch); body = body_of(result)
    context = _context(tier1); pairs = []; owned = set()
    index = {m['id']: (g, m) for g in body['coattacks'] for m in g['members']}
    for binding in bindings:
        if type(binding) is not dict or set(binding) != BINDING_FIELDS:
            raise ValueError('Explicit target and donor pair identities required')
        target, slots = _observe(context, binding['note_beat_ref'], binding['rest_beat_ref'])
        donor, _ = _observe(context, binding['donor_note_beat_ref'], binding['donor_rest_beat_ref'])
        refs = target['occurrence_refs']; group = index[refs[0]][0]
        if owned.intersection(refs) or [m['id'] for m in group['members']] != refs or group['timing_uncertain']:
            raise ValueError('A complete unambiguous coattack must have one release owner')
        if F(donor['shares'][0]) > F(target['shares'][0]):
            raise ValueError('This release policy shortens notes; extending holds needs a separate current-context admission')
        solved = relation(start_q=target['start_q'], span_q=target['span_q'], shares=donor['shares'])
        for slot, length in zip(slots, solved['durations_q']):
            notation_values(slot, length)
        if group['onset_q'] != target['start_q'] or any(index[r][1]['duration_q'] != relation(start_q=target['start_q'], span_q=target['span_q'], shares=target['shares'])['durations_q'][0] for r in refs):
            raise ValueError('Source and current pitch-core timing disagree')
        observations = dict(target=target, donor=donor, basis='explicit_same_source_complete_note_rest_proportion')
        pair = dict(id=pair_id(target['note_beat_ref'], target['rest_beat_ref']), coattack_ref=group['id'],
                    slots=slots, shares=target['shares'][:], observations=observations,
                    observation_sha256=digest(dict(source_origin=declared, observations=observations)))
        _observations(pair, declared)
        del group['onset_q']
        for ref in refs:
            del index[ref][1]['duration_q']
        pairs.append(pair); owned.update(refs)
    for view in VIEWS:
        body.pop(view, None)
    for group in body['coattacks']:
        group.pop('interpretation', None)
    model = dict(schema=SCHEMA, source_origin=declared, pitch_relationships=result, pairs=pairs)
    expand(model)
    return model


def validate_model(model, source_origin=None):
    if type(model) is not dict or set(model) != {'schema', 'source_origin', 'pitch_relationships', 'pairs'} or model['schema'] != SCHEMA:
        raise ValueError('Unknown note/rest time owner or hidden payload')
    validate_origin(model['source_origin'])
    if source_origin is not None and model['source_origin'] != source_origin:
        raise ValueError('Original timing source identity conflict')
    if type(model['pairs']) is not list or not model['pairs']:
        raise ValueError('Explicit complete note/rest owners required')
    seen = set()
    for pair in model['pairs']:
        if type(pair) is not dict or set(pair) != PAIR_FIELDS:
            raise ValueError('Unknown note/rest parameter payload')
        obs = _observations(pair, model['source_origin']); target = obs['target']
        if pair['id'] != pair_id(target['note_beat_ref'], target['rest_beat_ref']) or pair['id'] in seen:
            raise ValueError('Unique source note/rest identity required')
        seen.add(pair['id'])
        if type(pair['slots']) is not list or len(pair['slots']) != 2 or [s.get('beat_ref') for s in pair['slots']] != [target['note_beat_ref'], target['rest_beat_ref']]:
            raise ValueError('Note and rest notation incidence conflict')
        # This bounded policy exposes only original and explicitly observed donor.
        if pair['shares'] not in (target['shares'], obs['donor']['shares']):
            raise ValueError('Unobserved note/rest allocation')
        if F(obs['donor']['shares'][0]) > F(target['shares'][0]):
            raise ValueError('Unadmitted extension of a held note')


def expand(model):
    validate_model(model)
    pitch = deepcopy(model['pitch_relationships']); body = body_of(pitch)
    if 'input' in body or any(v in body for v in VIEWS) or any('interpretation' in g for g in body['coattacks']):
        raise ValueError('Hidden lower or derived timing payload')
    index = {m['id']: (g, m) for g in body['coattacks'] for m in g['members']}
    values = {}; seen = set()
    for pair in model['pairs']:
        target = pair['observations']['target']; refs = target['occurrence_refs']
        group = index[refs[0]][0]
        if (group['id'] != pair['coattack_ref'] or group['part_id'] != target['part_id']
                or [m['id'] for m in group['members']] != refs or group['timing_uncertain']
                or 'onset_q' in group or seen.intersection(refs)):
            raise ValueError('Duplicate, missing or ambiguous coattack time authority')
        solved = relation(start_q=target['start_q'], span_q=target['span_q'], shares=pair['shares'])
        group['onset_q'] = solved['onsets_q'][0]
        for ni, ref in enumerate(refs):
            member = index[ref][1]
            if ('duration_q' in member or (member['bar'], member['voice'], member['beat'], member['note'])
                    != (target['bar'], target['voice'], address(target['note_beat_ref'])[3], ni)):
                raise ValueError('Duplicate timing authority or changed occurrence incidence')
            member['duration_q'] = solved['durations_q'][0]
        for slot, length in zip(pair['slots'], solved['durations_q']):
            projected = notation_values(slot, length)
            if set(values).intersection(projected):
                raise ValueError('Duplicate notation time authority')
            values.update(projected)
        seen.update(refs)
    if pitch.get('schema') == 'musical-context-relations/2':
        import musical_tier2 as music
        refresh(body); music.validate(pitch)
    return pitch, values


def apply(model, target_ref):
    expand(model)
    edited = deepcopy(model)
    matches = [(i, p) for i, p in enumerate(edited['pairs']) if p['id'] == target_ref]
    if len(matches) != 1:
        raise ValueError('One owned target pair required')
    i, pair = matches[0]
    pair['shares'] = pair['observations']['donor']['shares'][:]
    assert_only_parameter_changes(model, edited, [('pairs', i, 'shares', j) for j in range(2)])
    expand(edited)
    return edited


def validate_source(model, tier1):
    """Run current execution/clock admission at zero AND after a saved edit."""
    _, values = expand(model); context = _context(tier1)
    facts = {r['id']: r for r in tier1['facts']}
    if any(ref not in facts or facts[ref].get('value') != value for ref, value in values.items()):
        raise ValueError('Current notation does not solve owned note/rest time')
    for pair in model['pairs']:
        old = pair['observations']['target']
        current, slots = _observe(context, old['note_beat_ref'], old['rest_beat_ref'])
        if ({k: v for k, v in current.items() if k != 'shares'} != {k: v for k, v in old.items() if k != 'shares'}
                or current['shares'] != pair['shares'] or slots != pair['slots']):
            raise ValueError('Current note/rest identity, clock or notation slots changed')
    # Existing transition guards include incoming dependencies whose declaration
    # may live outside the selected note itself (for example a slide origin).
    from execution_dependencies import build
    pinned = set(build(tier1)['pinned_members'])
    if any(pinned.intersection(p['observations']['target']['occurrence_refs']) for p in model['pairs']):
        raise ValueError('Incident execution relationship needs its own release semantics')
    return True


def verify_effect(before, after, model, target_ref):
    """Compare complete source facts and independent source event projections."""
    from source_fact_tier1 import project_documents
    from run_reversible_tier_qa import extract_documents
    validate_source(model, after)
    pair = next(p for p in model['pairs'] if p['id'] == target_ref)
    target = pair['observations']['target']
    solved = relation(start_q=target['start_q'], span_q=target['span_q'], shares=pair['shares'])
    allowed = {ref for slot, length in zip(pair['slots'], solved['durations_q']) for ref in notation_values(slot, length)}
    if ({k: v for k, v in before.items() if k != 'facts'} != {k: v for k, v in after.items() if k != 'facts'}
            or len(before['facts']) != len(after['facts'])):
        raise ValueError('Note/rest edit changed source envelope')
    changed = []
    for left, right in zip(before['facts'], after['facts']):
        if left == right:
            continue
        if left['id'] not in allowed or {k: v for k, v in left.items() if k != 'value'} != {k: v for k, v in right.items() if k != 'value'}:
            raise ValueError('Note/rest edit changed a locked source fact')
        changed.append(left['id'])
    a, b = [extract_documents(project_documents(t)) for t in (before, after)]
    if {k: v for k, v in a.items() if k != 'events'} != {k: v for k, v in b.items() if k != 'events'} or len(a['events']) != len(b['events']):
        raise ValueError('Note/rest edit changed score scope')
    for left, right in zip(a['events'], b['events']):
        expected = deepcopy(left)
        if left['id'] in target['occurrence_refs']:
            expected['duration_q'] = solved['durations_q'][0]
        if right != expected:
            raise ValueError('Outside event, pitch or attack changed')
    from execution_dependencies import build
    if build(before) != build(after):
        raise ValueError('Note/rest edit changed an existing execution relationship')
    return dict(status='EXACT_NOTE_RELEASE_AND_EXISTING_REST_ONLY', changed_fact_refs=changed,
                occurrence_refs=target['occurrence_refs'], fixed_start_q=target['start_q'],
                fixed_next_attack_q=str(F(target['start_q']) + F(target['span_q'])),
                note_duration_q=solved['durations_q'][0], rest_duration_q=solved['durations_q'][1],
                donor_basis=pair['observations']['basis'], cross_part_donor=target['part_id'] != pair['observations']['donor']['part_id'])
