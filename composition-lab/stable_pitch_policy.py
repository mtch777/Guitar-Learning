"""Saved user preference for newly introduced stable pitches.

The existing inverse remains authoritative. This policy evaluates transitions;
it never repairs source notes or chooses a key. Unchanged stable spans, including
an unchanged bend arrival with a different approach, need no invented key claim.
"""
from copy import deepcopy
from fractions import Fraction as F

from source_observation_evidence import validate_origin
from stable_pitch_membership import validate_context, assess_spans, IN_COLLECTION

SLOT = 'stable_pitch_preference'
SCHEMA = 'new-stable-pitch-preference/1'


def validate(upper):
    policy = upper[SLOT]
    if type(policy) is not dict or set(policy) != {'schema', 'origin', 'context', 'held_refs'} or policy['schema'] != SCHEMA:
        raise ValueError('Exact stable-pitch preference required')
    validate_origin(policy['origin'])
    if policy['origin'] != upper.get('source_origin'):
        raise ValueError('Stable-pitch preference origin differs')
    refs = policy['held_refs']
    if type(refs) is not list or any(type(ref) is not str for ref in refs) or refs != sorted(set(refs)):
        raise ValueError('Explicit unique held occurrence refs required')
    from backing_pitch_ownership import address
    for ref in refs:
        address(ref)
    if policy['context'] is not None:
        validate_context(policy['context'], policy['origin'])
    return policy


def attach(upper, *, context=None, held_refs=()):
    """Select nominal plain holds explicitly; owned bend holds are automatic.

    Context is selected composition intent, not automatically inferred tonality.
    None records the default while honestly keeping the context unresolved.
    """
    from connected_tier2 import realize
    if SLOT in upper:
        raise ValueError('Never silently replace a saved tonal preference')
    result = deepcopy(upper)
    result[SLOT] = dict(schema=SCHEMA, origin=deepcopy(upper.get('source_origin')),
                        context=deepcopy(context), held_refs=sorted(held_refs))
    validate(result)
    stable_spans(result, realize(upper))
    if realize(result) != realize(upper):
        raise ValueError('Preference attachment changed source realization')
    return result


def stable_spans(upper, lower):
    """Use existing source clocks and normalized bend curves, with no cutoff.

    Supported holds: explicitly selected plain nominal notes and the existing
    verified simple bend/tie owner. No inference from an arbitrary long duration.
    """
    policy = validate(upper)
    from source_fact_tier1 import project_documents
    from run_reversible_tier_qa import extract_documents
    from technique_observation_relations import lift
    from backing_pitch_ownership import address
    import bend_gesture_ownership as bend
    docs = project_documents(lower)
    normalized_events = extract_documents(docs)
    events = {e['id']: e for e in normalized_events['events']}
    spans = []
    bend_refs = []
    if bend.SLOT in upper['owned_parameters']:
        bend_refs = upper['owned_parameters'][bend.SLOT]['target_refs']
        if len(bend_refs) != 2 or any(ref not in events for ref in bend_refs):
            raise ValueError('Complete owned bend hold required')
        effects = lift(lower)
        normalized = {'owned_parameters': {'technique_declarations': effects}}
        extent, points = bend._curve(bend._group(normalized, bend_refs[0]))
        first, last = (events[ref] for ref in bend_refs)
        plateau = next(time for time, height in points if height == extent)
        start = F(first['onset_q']) + F(first['duration_q']) * plateau
        end = F(last['onset_q']) + F(last['duration_q'])
        if (first['pitch'] is None or last['pitch'] != first['pitch']
                or F(first['onset_q']) + F(first['duration_q']) != F(last['onset_q'])):
            raise ValueError('Supported contiguous same-base bend hold required')
        spans.append(dict(occurrence_refs=list(bend_refs), start_q=str(start),
                          end_q=str(end), pitch=str(F(first['pitch']) + extent)))
    tie_context = None
    if policy['held_refs']:
        import musical_tier2 as music
        from source_tie_tier1 import extract_documents as extract_ties
        import backing_written_tie_constraints as ties
        current_core = music.strip_lower(music.analyze(normalized_events))
        tie_context = ties.context(current_core, extract_ties(docs)['tie_notation'])
    for ref in policy['held_refs']:
        if ref in bend_refs or ref not in events:
            raise ValueError('Distinct located plain hold required')
        event = events[ref]
        _, part, bar, voice, beat, note = address(ref)
        document = docs[f'track-{part}.json']
        source_beat = document['measures'][bar-1]['voices'][voice]['beats'][beat]
        source_note = source_beat['notes'][note]
        if ties.build(*tie_context, [ref])['relations']:
            raise ValueError('Held-note execution requires complete tied closure support')
        if (type(document.get('instrumentId')) is not int or not 0 <= document['instrumentId'] <= 127
                or event['pitch'] is None or F(event['duration_q']) <= 0
                or any(key in source_note for key in ('bend', 'tie', 'slide', 'hp', 'harmonic', 'trill', 'dead', 'rest', 'staccato', 'grace', 'vibrato', 'wideVibrato', 'leftHandVibrato'))
                or any(key in source_beat for key in ('letRing', 'tremoloBar', 'graceNote', 'staccato', 'palmMute', 'tapping'))):
            raise ValueError('Held-note execution requires explicit support')
        start = F(event['onset_q'])
        spans.append(dict(occurrence_refs=[ref], start_q=str(start),
                          end_q=str(start+F(event['duration_q'])), pitch=str(F(event['pitch']))))
    return spans


def _new_spans(before, after):
    """Only newly introduced pitch/time coverage needs admission; zero is literal."""
    result = []
    for span in after:
        pieces = [(F(span['start_q']), F(span['end_q']))]
        for old in before:
            if old['occurrence_refs'] != span['occurrence_refs'] or F(old['pitch']) != F(span['pitch']):
                continue
            a, b = F(old['start_q']), F(old['end_q'])
            remaining = []
            for left, right in pieces:
                if b <= left or a >= right:
                    remaining.append((left, right))
                else:
                    if left < a: remaining.append((left, a))
                    if b < right: remaining.append((b, right))
            pieces = remaining
        result.extend(dict(span, start_q=str(a), end_q=str(b)) for a, b in pieces)
    return result


def enforce_transition(upper, before, after):
    """Refuse new unsupported destinations atomically, without touching either input."""
    if SLOT not in upper:
        return dict(status='PREFERENCE_NOT_ATTACHED', scope='legacy mechanical operation')
    policy = validate(upper)
    if before == after:
        return dict(status='UNCHANGED_SOURCE', new_stable_spans=[])
    previous = stable_spans(upper, before)
    current = stable_spans(upper, after)
    introduced = _new_spans(previous, current)
    if not introduced:
        return dict(status='UNCHANGED_STABLE_PITCHES', new_stable_spans=[])
    if policy['context'] is None:
        raise ValueError('NOT_KEY_VERIFIED: new stable pitches require a selected or independently admitted tonal context')
    report = assess_spans(policy['context'], introduced)
    if report['status'] != IN_COLLECTION:
        raise ValueError(report['status'] + ': stable pitch preference refused; ' + ','.join(report['reasons']))
    return report
