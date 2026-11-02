"""Binding adapter: serialization uses backing identities, never focal fit."""
import backing_motion_relations as motion
import backing_pitch_ownership as owner
import musical_tier2 as music


def _pairs(maxima):
    return {(a, b) for option in maxima for match in option['matched']
            for a in match['source_refs'] for b in match['target_refs']}


def _maxima_values(maxima):
    return {(option['delta'], option['distinct_pitch_matches'], match['source_pitch'], match['target_pitch'], a, b)
            for option in maxima for match in option['matched']
            for a in match['source_refs'] for b in match['target_refs']}


def canonical_bindings(shared, correspondences):
    """Own both sides using the first numeric address pair among ALL maxima.

Recompute backing matches from current owned pitches; verify the supplied maxima,
complete written backing activity, and agreement of every pair's released pitch.
The returned list contains only references, ready for owner.lift. Diagnostics in
the caller remain diagnostics and never become duplicate pitch owners.
"""
    if type(correspondences) is not list or not correspondences:
        raise ValueError('Explicit correspondence sequence required')
    import explicit_backing_stream as stream
    if any(type(row) is dict and type(row.get('match')) is dict
           and row['match'].get('schema')==stream.SCHEMA for row in correspondences):
        # A different explicit correspondence, not a fallback for a failed
        # sonority match. Its verifier rejects mixed or falsely declared modes.
        return stream.canonical_bindings(shared,correspondences)
    normal = owner._normal(shared); index = owner._index(normal); bindings = []
    for row in correspondences:
        if type(row) is not dict or not {'source_ref','target_ref','match'} <= set(row):
            raise ValueError('Complete correspondence required')
        source = row['source_ref']; target = row['target_ref']; supplied = row['match']
        sides = []; parts = []
        for key, focal in (('source_refs', source), ('target_refs', target)):
            refs = supplied[key]
            if type(refs) is not list or not refs or len(set(refs)) != len(refs):
                raise ValueError('Complete unique backing occurrences required')
            links = [dict(occurrence_ref=focal, backing_ref=ref) for ref in refs]
            owner._active(normal, links)
            owned_parts = {index[ref][0]['part_id'] for ref in refs}
            if len(owned_parts) != 1:
                raise ValueError('One explicit backing part required')
            part = next(iter(owned_parts)); parts.append(part)
            onset = music.fraction(index[focal][0]['onset_q'])
            complete = {ref for ref,(group,note) in index.items() if group['part_id']==part
                        and music.fraction(group['onset_q']) <= onset < music.fraction(group['onset_q'])+music.fraction(note['duration_q'])}
            if set(refs) != complete:
                raise ValueError('Incomplete owned backing context')
            sides.append([dict(ref=ref, pitch=music.member_pitch(*index[ref])) for ref in refs])
        if parts[0] != parts[1]:
            raise ValueError('Correspondence must retain the same explicit backing part')
        current = motion.maximum_translations(*sides)
        if current['selected_delta'] is None:
            raise ValueError('Ambiguous, unknown or insufficient backing correspondence')
        for key in ('selected_delta', 'max_cardinality', 'status'):
            if supplied[key] != current[key]:
                raise ValueError('Claimed backing correspondence differs from owned pitches')
        if _maxima_values(supplied['maxima']) != _maxima_values(current['maxima']):
            raise ValueError('Claimed maximal pairs are incomplete or inconsistent')
        pairs = _pairs(current['maxima'])
        source_pitch = music.member_pitch(*index[source])
        if source_pitch is None:
            raise ValueError('Known reference pitch required')
        released = set()
        for a,b in pairs:
            interval = music.relation(anchor=music.member_pitch(*index[a]), pitch=source_pitch)['interval']
            released.add(music.relation(anchor=music.member_pitch(*index[b]), interval=interval)['pitch'])
        if len(released) != 1:
            raise ValueError('Maximal pairs disagree on the released pitch')
        # Only source identities determine this choice; no target pitch is read.
        a,b = min(pairs, key=lambda pair:(owner.address(pair[0]),owner.address(pair[1])))
        bindings.extend([dict(occurrence_ref=source, backing_ref=a), dict(occurrence_ref=target, backing_ref=b)])
    return owner._links(bindings, {'occurrence_ref','backing_ref'})
