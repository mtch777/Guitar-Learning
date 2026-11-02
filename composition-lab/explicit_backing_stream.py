"""Explicit written occurrence-stream relationships, not sonority matching.

API: stream_relation() accepts one declared backing occurrence per side and
explicit part/voice/time contexts. canonical_bindings() verifies a sequence
against the current owned core and returns reference-only links for BOTH sides.
The existing pitch = anchor + interval equation supplies the signed movement.
Focal pitches never select an anchor. Expression qualifications are carried as
supplied metadata; execution safety remains a separate caller responsibility.
"""
import json

import backing_motion_relations as motion
import backing_pitch_ownership as owner
import musical_tier2 as music

SCHEMA = 'explicit-backing-stream/1'
KIND = 'explicit_occurrence_stream'


def _identity(part, voice):
    if type(part) is not int or part < 0 or type(voice) is not int or voice < 0:
        raise ValueError('Explicit nonnegative integer backing part and voice required')


def _one(rows, part, voice):
    if type(rows) is not list or len(rows) != 1:
        raise ValueError('Exactly one backing occurrence per side required; unisons are not collapsed')
    row = rows[0]
    if type(row) is not dict or set(row) != {'ref', 'pitch'}:
        raise ValueError('Backing occurrence requires exactly ref and pitch')
    address = owner.address(row['ref'])
    if (address[1], address[3]) != (part, voice):
        raise ValueError('Backing address differs from the explicit part and voice')
    return row['ref'], motion._integer(row['pitch'], 'Known written backing pitch')


def _context(value, ref):
    if value is None:
        raise ValueError('Explicit written context required')
    result = motion._context(value, [ref])
    if result['context_refs'] != [ref]:
        raise ValueError('Stream context must contain exactly its one occurrence')
    return result


def stream_relation(source, target, *, backing_part, backing_voice,
                    source_context, target_context):
    """One explicitly identified line: target pitch minus source pitch.

    No focal pitch is an input, and no alternative anchor or voice is selected.
    Held occurrences may be reused at separate queried attacks. This function
    checks supplied identities, not activity; canonical_bindings checks activity
    against the current owned representation before links can be persisted.
    """
    _identity(backing_part, backing_voice)
    a, p = _one(source, backing_part, backing_voice)
    b, q = _one(target, backing_part, backing_voice)
    if owner.address(a)[0] != owner.address(b)[0]:
        raise ValueError('Backing occurrences must belong to the same source song')
    sc = _context(source_context, a); tc = _context(target_context, b)
    solved = motion.solve_pitch(source_pitch=p, target_pitch=q)
    return dict(schema=SCHEMA, kind=KIND, backing_part=backing_part,
                backing_voice=backing_voice, source_refs=[a], target_refs=[b],
                source_context=sc, target_context=tc,
                source_pitch=p, target_pitch=q, selected_delta=solved['delta'],
                status='EXPLICIT_WRITTEN_OCCURRENCE_STREAM',
                pitch_domain='written_base_not_sounding',
                claim='Caller-declared part/voice and occurrence identities; not an inferred artistic voice or sonority match')


def _complete_at(normal, index, focal, backing, part, voice):
    owner._active(normal, [dict(occurrence_ref=focal, backing_ref=backing)])
    group, note = index[backing]
    if (group['part_id'], note['voice']) != (part, voice):
        raise ValueError('Owned backing location differs from the declared stream')
    onset = music.fraction(index[focal][0]['onset_q'])
    active = []
    for ref, (group, member) in index.items():
        if (group['part_id'], member['voice']) != (part, voice):
            continue
        start = music.fraction(group['onset_q'])
        duration = music.fraction(member['duration_q'])
        if start <= onset < start + duration:
            if group['timing_uncertain'] is not False:
                raise ValueError('Unknown written clock in active stream')
            active.append(ref)
    if active != [backing]:
        raise ValueError('Exactly one complete active occurrence in the declared part and voice required')
    return str(onset), music.member_pitch(*index[backing])


def _typed(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError('Plain finite stream relationship data required') from error


def canonical_bindings(shared, correspondences):
    """Validate current activity and return canonical reference-only ownership.

    Every supplied match is recomputed from the owned backing notes, including
    time, identity and typed pitch values. All rows retain one declared stream.
    Other explicitly numbered voices are outside this declared voice scope.
    This does not validate sounding sustain, performance, or expression metadata.
    """
    if type(correspondences) is not list or not correspondences:
        raise ValueError('Nonempty explicit stream correspondences required')
    try:
        normal = owner._normal(shared); index = owner._index(normal)
        links = []; streams = set()
        for row in correspondences:
            if type(row) is not dict or not {'source_ref', 'target_ref', 'match'} <= set(row):
                raise ValueError('Complete explicit stream correspondence required')
            match = row['match']
            if type(match) is not dict or match.get('schema') != SCHEMA or match.get('kind') != KIND:
                raise ValueError('Explicit stream relationship required; no sonority fallback')
            part = match['backing_part']; voice = match['backing_voice']
            _identity(part, voice); streams.add((part, voice))
            if len(streams) != 1:
                raise ValueError('One explicit backing part and voice must span every correspondence')
            sides = []; contexts = []
            for side, focal in (('source', row['source_ref']), ('target', row['target_ref'])):
                owner.address(focal)
                refs = match[side + '_refs']
                if type(refs) is not list or len(refs) != 1:
                    raise ValueError('Exactly one declared backing occurrence per side required')
                ref = refs[0]; owner.address(ref)
                at, pitch = _complete_at(normal, index, focal, ref, part, voice)
                supplied = match[side + '_context']
                if supplied['time_q'] != at:
                    raise ValueError('Written context time differs from the owned focal attack')
                contexts.append(dict(time_q=at, context_refs=[ref],
                                     qualifications=supplied['qualifications']))
                sides.append([dict(ref=ref, pitch=pitch)])
                links.append(dict(occurrence_ref=focal, backing_ref=ref))
            current = stream_relation(*sides, backing_part=part, backing_voice=voice,
                                      source_context=contexts[0], target_context=contexts[1])
            if _typed(current) != _typed(match):
                raise ValueError('Supplied stream relationship differs from current owned evidence')
        return owner._links(links, {'occurrence_ref', 'backing_ref'})
    except (KeyError, TypeError, ZeroDivisionError) as error:
        raise ValueError('Incomplete or malformed owned stream context') from error
