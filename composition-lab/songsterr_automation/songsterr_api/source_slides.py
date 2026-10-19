"""Exact written slide relationships; no invented entry/exit pitches or intent."""
from collections import Counter, defaultdict
from fractions import Fraction as F

TYPES = ('downwards', 'upwards', 'legato', 'shift', 'below', 'above')


def slide_types(value):
    """Decode known atomic/combined source values; never partially accept junk."""
    if not isinstance(value, str):
        return []
    remaining, result = value, []
    while remaining:
        match = next((name for name in TYPES if remaining.startswith(name)), None)
        if match is None:
            return []
        result.append(match)
        remaining = remaining[len(match):]
    return result


def resolve_slides(rows, grace=()):
    """Return one event per marked type, including explicit unresolved statuses.

    Only regular, contiguous same-string/same-voice note targets resolve. Tied
    continuations may extend a non-tied origin when pitch/fret/time match exactly.
    Grace slides and transitions encountering grace stay unresolved: their written
    duration is not a performed duration. Intervals use written/base pitches only.
    """
    lanes = defaultdict(list)
    for row in rows:
        if row['string'] is not None:
            lanes[row['voice'], row['string']].append(row)
    for lane in lanes.values():
        lane.sort(key=lambda r: (F(r['onset_q']), r['bar'], r['beat'], r['note']))
    grace_at = {(r['voice'], r['string'], F(r['onset_q'])) for r in grace}
    locations = {r['occurrence']: (lane, i) for lane in lanes.values() for i, r in enumerate(lane)}
    grace_ids = {r['occurrence'] for r in grace}
    events = []
    for a in [*rows, *grace]:
        raw = a.get('raw_note', {}).get('slide')
        if not raw:
            continue
        kinds = slide_types(raw)
        for kind in kinds or ['unknown']:
            event = dict(occurrence=a['occurrence'], raw_value=raw, type=kind,
                         origin=None, destination=None, onset_q=a['onset_q'],
                         written_duration_q=a['duration_q'], voice=a['voice'], string=a['string'],
                         status=None, interval_semitones=None, tied_members=[],
                         interpretation='written notation; not physical trajectory or performed sound')
            if kind == 'unknown':
                event['status'] = 'unsupported_slide_value'
            elif kind in ('below', 'above'):
                event.update(destination=a['occurrence'], status='entry_origin_unspecified',
                             direction='ascending' if kind == 'below' else 'descending')
            elif kind in ('downwards', 'upwards'):
                event.update(origin=a['occurrence'], status='exit_target_unspecified',
                             direction='descending' if kind == 'downwards' else 'ascending')
            else:
                event['origin'] = a['occurrence']
                if a['occurrence'] in grace_ids:
                    event['status'] = 'grace_origin_order_unresolved'
                elif a['occurrence'] not in locations:
                    event['status'] = 'unknown_string'
                elif a['tie_destination']:
                    event['status'] = 'origin_tie_requires_chain'
                else:
                    lane, i = locations[a['occurrence']]
                    j, end = i, F(a['onset_q']) + F(a['duration_q'])
                    while j + 1 < len(lane):
                        tied = lane[j + 1]
                        if not (tied['tie_destination'] and a['midi'] is not None and
                                tied['midi'] == a['midi'] and tied['fret'] == a['fret'] and
                                F(tied['onset_q']) == end):
                            break
                        j += 1
                        event['tied_members'].append(tied['occurrence'])
                        end += F(tied['duration_q'])
                    b = lane[j + 1] if j + 1 < len(lane) else None
                    status = ('no_next_same_string_note' if b is None else
                              'gap_or_overlap' if F(b['onset_q']) != end else
                              'target_tie_unresolved' if b['tie_destination'] else
                              'unknown_or_dead_pitch' if a['midi'] is None or b['midi'] is None else
                              'same_fret' if a['fret'] == b['fret'] else
                              'grace_at_transition' if (a['voice'], a['string'], end) in grace_at else
                              'resolved_written_target')
                    event['status'] = status
                    if status == 'resolved_written_target':
                        event.update(destination=b['occurrence'], interval_semitones=b['midi'] - a['midi'],
                                     direction='ascending' if b['fret'] > a['fret'] else 'descending',
                                     transition_q=str(end), sustained_origin_duration_q=str(end-F(a['onset_q'])),
                                     pitch_effects_present=bool(a.get('pitch_effects') or b.get('pitch_effects')))
                        if event['tied_members']:
                            event['status'] = 'target_after_tie_candidate'
            events.append(event)
    return dict(events=events, status_counts=dict(Counter(e['status'] for e in events)),
                type_counts=dict(Counter(e['type'] for e in events)),
                limitations=['Written target candidates only; no acoustic execution or musical intent',
                             'Grace performance ordering is not inferred',
                             'Targets beyond tied continuations are candidates, not verified slide placement',
                             'Entry/exit slides intentionally have an unspecified endpoint'])
