"""Observed written-pitch correspondence, without inferred chord identity.

Pure preceding-tier values only. Matching does not receive a focal target note.
It retains competing translations, unmatched tones, occurrence provenance and
supplied context qualifications. Selection concerns written pitches; sounding
execution, musical intent and comfortable fingering require separate evidence.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
from itertools import product

from musical_tier2 import relation

SCHEMA = 'observed-backing-translation/1'


def _number(value, name):
    if type(value) is int:
        return Fraction(value)
    if type(value) is str:
        try:
            result = Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError(f'{name} requires a canonical rational string or integer') from exc
        if str(result) == value:
            return result
    raise ValueError(f'{name} requires a canonical rational string or integer')


def _integer(value, name):
    result = _number(value, name)
    if result.denominator != 1:
        raise ValueError(f'{name} requires an integral written pitch or coordinate')
    return int(result)


def _occurrences(rows, side):
    if type(rows) is not list:
        raise ValueError(f'{side} requires a list of occurrence references and pitches')
    seen = set(); by_pitch = defaultdict(list); unavailable = []
    for row in rows:
        if type(row) is not dict or set(row) != {'ref', 'pitch'}:
            raise ValueError('Each occurrence requires exactly ref and pitch')
        ref = row['ref']
        if type(ref) is not str or not ref or ref in seen:
            raise ValueError('Unique nonempty occurrence references required on each side')
        seen.add(ref)
        if row['pitch'] is None:
            unavailable.append(dict(ref=ref, reason='UNKNOWN_WRITTEN_PITCH'))
            continue
        value = _number(row['pitch'], 'Written pitch')
        if value.denominator != 1:
            unavailable.append(dict(ref=ref, reason='NONINTEGER_WRITTEN_PITCH'))
            continue
        by_pitch[int(value)].append(ref)
    return {pitch: sorted(refs) for pitch, refs in by_pitch.items()}, unavailable, sorted(seen)


def _context(value, refs):
    if value is None:
        return dict(time_q=None, context_refs=list(refs), qualifications=[],
                    metadata_status='UNSPECIFIED')
    if type(value) is not dict or set(value) != {'time_q', 'context_refs', 'qualifications'}:
        raise ValueError('Context requires exactly time_q, context_refs and qualifications')
    _number(value['time_q'], 'Context time')
    context_refs = value['context_refs']; qualifications = value['qualifications']
    if (type(context_refs) is not list or any(type(r) is not str or not r for r in context_refs)
            or len(context_refs) != len(set(context_refs)) or not set(refs) <= set(context_refs)):
        raise ValueError('Context references must include every supplied occurrence exactly once')
    if type(qualifications) is not list or any(type(q) is not str or not q for q in qualifications):
        raise ValueError('Explicit qualification strings required')
    return dict(time_q=str(_number(value['time_q'], 'Context time')),
                context_refs=deepcopy(context_refs), qualifications=deepcopy(qualifications),
                metadata_status='SUPPLIED_NOT_INDEPENDENTLY_VERIFIED')


def maximum_translations(source, target, *, source_context=None, target_context=None):
    """Enumerate every actual target-minus-source shift, preserving octaves.

One distinct source pitch matching one distinct target pitch supplies one match,
regardless of repeated occurrences. A unique maximum needs at least two matches;
unknown/fractional pitches keep selection unavailable, not silently omitted.
Context metadata is carried, not treated as proof of physical execution.
"""
    a, unavailable_a, refs_a = _occurrences(source, 'Source')
    b, unavailable_b, refs_b = _occurrences(target, 'Target')
    sc = _context(source_context, refs_a); tc = _context(target_context, refs_b)
    deltas = sorted({solve_pitch(source_pitch=p, target_pitch=q)['delta'] for p in a for q in b})
    alternatives = []
    for delta in deltas:
        matches = [dict(source_pitch=p, target_pitch=p+delta,
                        source_refs=list(a[p]), target_refs=list(b[p+delta]))
                   for p in sorted(a) if p+delta in b]
        matched_a = {m['source_pitch'] for m in matches}
        matched_b = {m['target_pitch'] for m in matches}
        alternatives.append(dict(delta=delta, distinct_pitch_matches=len(matches), matched=matches,
            unmatched_source=[dict(pitch=p, refs=list(a[p])) for p in sorted(a) if p not in matched_a],
            unmatched_target=[dict(pitch=p, refs=list(b[p])) for p in sorted(b) if p not in matched_b]))
    maximum = max((r['distinct_pitch_matches'] for r in alternatives), default=0)
    maxima = [deepcopy(r) for r in alternatives if r['distinct_pitch_matches'] == maximum]
    if unavailable_a or unavailable_b:
        status = 'INCOMPLETE_WRITTEN_PITCH_CONTEXT'
    elif maximum < 2:
        status = 'INSUFFICIENT_DISTINCT_PITCH_MATCHES'
    elif len(maxima) != 1:
        status = 'AMBIGUOUS_MAXIMUM_TRANSLATION'
    else:
        status = 'UNIQUE_WRITTEN_TRANSLATION'
    return dict(schema=SCHEMA, source_context=sc, target_context=tc,
        source_refs=refs_a, target_refs=refs_b,
        unavailable_source=unavailable_a, unavailable_target=unavailable_b,
        alternatives=alternatives, maxima=maxima, max_cardinality=maximum,
        selected_delta=maxima[0]['delta'] if status == 'UNIQUE_WRITTEN_TRANSLATION' else None,
        status=status, pitch_domain='written_base_not_sounding',
        claim='Partial observed pitch correspondence; no selected root, chord identity or intent')


def solve_pitch(*, source_pitch=None, delta=None, target_pitch=None):
    """The SAME target = source + delta equation, solved in either direction."""
    values = [None if v is None else _integer(v, name) for v, name in
              ((source_pitch, 'Source pitch'), (delta, 'Signed translation'),
               (target_pitch, 'Target pitch'))]
    result = relation(anchor=values[0], interval=values[1], pitch=values[2])
    return dict(source_pitch=int(result['anchor']), delta=int(result['interval']),
                target_pitch=int(result['pitch']))


def _instrument(tuning, capo, max_fret):
    if type(tuning) is not list or not tuning:
        raise ValueError('Nonempty declared string tuning required')
    tuning = [_integer(p, 'Open-string pitch') for p in tuning]
    capo = _integer(capo, 'Capo')
    if capo < 0:
        raise ValueError('Capo cannot be negative')
    if max_fret is not None:
        max_fret = _integer(max_fret, 'Declared maximum fret')
        if max_fret < 0:
            raise ValueError('Declared maximum fret cannot be negative')
    return tuning, capo, max_fret


def physical_contacts(pitch, tuning, capo=0, *, max_fret=None):
    """All exact nominal string/fret solutions; no invented fret ceiling."""
    pitch = _integer(pitch, 'Contact pitch')
    tuning, capo, max_fret = _instrument(tuning, capo, max_fret)
    contacts = []
    for string, open_pitch in enumerate(tuning):
        fret = solve_pitch(source_pitch=open_pitch+capo, target_pitch=pitch)['delta']
        if fret >= 0 and (max_fret is None or fret <= max_fret):
            contacts.append(dict(string=string, fret=fret))
    return contacts


def minimum_string_changes(pitches, original_strings, tuning, capo=0, *, max_fret=None):
    """All minimum-count string-change assignments for an ordered note sequence.

Keep each original string wherever its exact pitch contact exists. Otherwise
every alternative costs one changed string; equal-cost assignments remain tied.
This is a nominal contact objective, not a reach, comfort or movement model.
"""
    if type(pitches) is not list or not pitches or type(original_strings) is not list or len(pitches) != len(original_strings):
        raise ValueError('Nonempty aligned pitch and original-string lists required')
    tuning, capo, max_fret = _instrument(tuning, capo, max_fret)
    if any(type(s) is not int or not 0 <= s < len(tuning) for s in original_strings):
        raise ValueError('Known original string indices required')
    all_contacts = [physical_contacts(p, tuning, capo, max_fret=max_fret) for p in pitches]
    if any(not contacts for contacts in all_contacts):
        return dict(status='NO_NOMINAL_CONTACT_ASSIGNMENT', all_contacts=all_contacts,
                    minimum_changes=None, assignments=[],
                    unresolved_note_indices=[i for i,c in enumerate(all_contacts) if not c])
    best = []
    for contacts, original in zip(all_contacts, original_strings):
        retained = [c for c in contacts if c['string'] == original]
        best.append(retained or contacts)
    assignments = [[deepcopy(c) for c in choices] for choices in product(*best)]
    costs = {sum(c['string'] != s for c,s in zip(assignment, original_strings)) for assignment in assignments}
    if len(costs) != 1:
        raise ValueError('Inconsistent independent string-change objective')
    return dict(status='ALL_MINIMUM_STRING_CHANGE_ASSIGNMENTS', all_contacts=all_contacts,
                minimum_changes=costs.pop(), assignments=assignments,
                unresolved_note_indices=[],
                limitations=['Nominal contact only; no reach, speed, comfort or physical authenticity claim'])
