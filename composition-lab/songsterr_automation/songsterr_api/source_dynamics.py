"""Written dynamic inheritance, without inferring loudness or ghost-note attenuation.

State is local to a track/voice, carries across bars and rests, and follows source
beat order (including grace beats). A note override does not change voice state.
This is not a playback-repeat traversal or a physical/MIDI loudness estimate.
"""

MARKINGS = frozenset(('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff'))


def dynamic_observations(part):
    """Return per-note dynamic value, provenance and written marking location.

    Missing markings remain unknown until an explicit voice marking appears.
    Unknown explicit beat values invalidate inherited state, rather than silently
    retaining a prior known marking. Raw unknown values remain in the result.
    """
    state = {}
    observations = []
    for mi, measure in enumerate(part.get('measures', []), 1):
        for vi, voice in enumerate(measure.get('voices', [])):
            for bi, beat in enumerate(voice.get('beats', [])):
                location = dict(bar=mi, voice=vi, beat=bi)
                explicit_beat = beat.get('velocity') is not None
                if explicit_beat:
                    state[vi] = (beat['velocity'], location)
                for ni, note in enumerate(beat.get('notes', [])):
                    if note.get('rest'):
                        continue
                    if note.get('velocity') is not None:
                        raw, origin, provenance = note['velocity'], dict(location, note=ni), 'note_explicit'
                    elif vi in state:
                        raw, origin = state[vi]
                        provenance = 'beat_explicit' if explicit_beat else 'inherited_explicit'
                    else:
                        raw, origin, provenance = None, None, 'unspecified'
                    known = isinstance(raw, str) and raw in MARKINGS
                    observations.append(dict(
                        occurrence=f'{part.get("partId", 0)}:{mi}:{vi}:{bi}:{ni}',
                        marking=raw if known else None, raw_value=raw,
                        provenance=provenance, marking_origin=origin,
                        known=known, ghost=bool(note.get('ghost')),
                        dead=bool(note.get('dead')), grace=bool(beat.get('graceNote')),
                    ))
    return observations
