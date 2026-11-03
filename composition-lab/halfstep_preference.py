"""Small, explicit preference for literal half steps in declared context.

This is an engineering default, not a learned musical-quality estimate. It
never changes feasibility, release probability, source evidence or an inverse.
Melodic and simultaneous precedents are distinct; octave-equivalent pitch
classes do not stand in for actual one-semitone adjacency.
"""
from copy import deepcopy
from fractions import Fraction as F

from source_observation_evidence import digest

SCHEMA = 'literal-halfstep-preference/1'
NOVEL_WEIGHT = F(19, 20)


def _events(tier1):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    documents = project_documents(tier1)
    normalized = extract_documents(documents)
    return {e['id']: e for e in normalized['events']
            if type(documents[f"track-{e['part_id']}.json"].get('instrumentId')) is int
            and 0 <= documents[f"track-{e['part_id']}.json"]['instrumentId'] < 128}


def _line(rows):
    if type(rows) is not list or not rows:
        raise ValueError('An explicit nonempty ordered attack line is required')
    roots, members = [], []
    for row in rows:
        if (type(row) is not dict or set(row) != {'attack_ref', 'member_refs'}
                or type(row['attack_ref']) is not str or type(row['member_refs']) is not list
                or not row['member_refs'] or row['member_refs'][0] != row['attack_ref']):
            raise ValueError('Explicit attack roots and complete tied members required')
        roots.append(row['attack_ref']); members.extend(row['member_refs'])
    if len(set(members)) != len(members):
        raise ValueError('Unique declared line members required')
    return roots, members


def _profile(events, lines):
    melodic, vertical, unknown = [], [], set()
    selected = set()
    for line in lines:
        roots, members = _line(line)
        if any(ref not in events for ref in members):
            raise ValueError('Declared pitched line occurrence is unavailable')
        times = [F(events[ref]['onset_q']) for ref in roots]
        if times != sorted(set(times)):
            raise ValueError('Declared attack order must have distinct chronological onsets')
        selected.update(members)
        for left, right in zip(roots, roots[1:]):
            a, b = events[left], events[right]
            if a['pitch'] is None or b['pitch'] is None:
                unknown.update((left, right)); continue
            if abs(F(a['pitch'])-F(b['pitch'])) == 1:
                melodic.append(dict(from_ref=left, to_ref=right))
    seen = set()
    for ref in sorted(selected):
        a = events[ref]; start = F(a['onset_q']); end = start+F(a['duration_q'])
        if a['pitch'] is None:
            unknown.add(ref); continue
        for other_ref, b in events.items():
            if ref == other_ref:
                continue
            overlap_start = max(start, F(b['onset_q']))
            overlap_end = min(end, F(b['onset_q'])+F(b['duration_q']))
            if overlap_start >= overlap_end:
                continue
            if b['pitch'] is None:
                unknown.add(other_ref); continue
            pair = tuple(sorted((ref, other_ref)))
            if pair not in seen and abs(F(a['pitch'])-F(b['pitch'])) == 1:
                seen.add(pair)
                vertical.append(dict(member_refs=list(pair), start_q=str(overlap_start), end_q=str(overlap_end)))
    return dict(melodic=melodic, simultaneous=vertical, unknown_pitch_refs=sorted(unknown))


def freeze(tier1, attacks, *, reference_attacks=None, original_reference_steps=None, source_origin=None):
    """Freeze evidence before alternatives exist. Current context is not source votes."""
    lines = [attacks]+([] if reference_attacks is None else [reference_attacks])
    profile = _profile(_events(tier1), lines)
    steps = [] if original_reference_steps is None else list(original_reference_steps)
    original_halfsteps = [i for i, step in enumerate(steps) if abs(F(step)) == 1]
    return dict(schema=SCHEMA, input_sha256=digest(tier1), attacks=deepcopy(attacks),
        reference_attacks=deepcopy(reference_attacks), current_context=profile,
        evidence_role='CURRENT_INPUT_TARGET_AND_DECLARED_REFERENCE_CONTEXT',
        source_origin=deepcopy(source_origin), original_reference_halfstep_indices=original_halfsteps,
        original_evidence_role='Existing immutable reference-step observations; never candidate output',
        supported=dict(melodic=bool(profile['melodic'] or original_halfsteps),
                       simultaneous=bool(profile['simultaneous'])),
        interpretation='Actual absolute pitch distance 1 only; not interval classes 1/11 or compound intervals')


def evaluate(tier1, context):
    """Evaluate every selected member and its held overlaps in the complete candidate."""
    if type(context) is not dict or context.get('schema') != SCHEMA:
        raise ValueError('Explicit frozen half-step context required')
    profile = _profile(_events(tier1), [context['attacks']])
    introduced = [kind for kind in ('melodic', 'simultaneous')
                  if profile[kind] and not context['supported'][kind]]
    # Unknown pitch evidence cannot establish the absence of a precedent.
    uncertain = bool(context['current_context']['unknown_pitch_refs'])
    weight = NOVEL_WEIGHT if introduced and not uncertain else F(1)
    return dict(weight=str(weight), introduced_categories=introduced,
        candidate=profile, context_sha256=digest(context), absence_uncertain=uncertain,
        discount_applied=weight != 1, discount_count=int(weight != 1),
        meaning='At most one 5% relative candidate-weight discount; never a ban or 5-percentage-point probability change')


def choose(evaluations, rng):
    """Positive weighted draw. Preserve legacy uniform draws for equal weights."""
    if type(evaluations) is not list or not evaluations:
        raise ValueError('Nonempty complete candidate evaluations required')
    weights = [F(row['weight']) for row in evaluations]
    if any(weight not in (F(1), NOVEL_WEIGHT) for weight in weights):
        raise ValueError('Only the explicit bounded positive preference is supported')
    if len(set(weights)) == 1:
        index = rng.randrange(len(weights))
    else:
        draw = F(str(rng.random()))*sum(weights)
        total = F(0); index = len(weights)-1
        for i, weight in enumerate(weights):
            total += weight
            if draw < total:
                index = i; break
    return index
