"""Transparent, uncalibrated tonal hypotheses from exact symbolic events.

No source labels, file names, artist metadata or known-answer annotations enter
inference. This module does not reconstruct music or assert perceptual truth.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from math import sqrt

MODES = {
    'ionian': (0, 2, 4, 5, 7, 9, 11),
    'dorian': (0, 2, 3, 5, 7, 9, 10),
    'phrygian': (0, 1, 3, 5, 7, 8, 10),
    'lydian': (0, 2, 4, 6, 7, 9, 11),
    'mixolydian': (0, 2, 4, 5, 7, 9, 10),
    'aeolian': (0, 2, 3, 5, 7, 8, 10),
    'locrian': (0, 1, 3, 5, 6, 8, 10),
    'harmonic_minor': (0, 2, 3, 5, 7, 8, 11),
    'melodic_minor_ascending': (0, 2, 3, 5, 7, 9, 11),
}
CHORDS = {
    'major': (0, 4, 7), 'minor': (0, 3, 7),
    'diminished': (0, 3, 6), 'augmented': (0, 4, 8),
    'sus2': (0, 2, 7), 'sus4': (0, 5, 7), 'power': (0, 7),
    'dominant7': (0, 4, 7, 10), 'major7': (0, 4, 7, 11),
    'minor7': (0, 3, 7, 10), 'half_diminished7': (0, 3, 6, 10),
    'diminished7': (0, 3, 6, 9), 'minor_major7': (0, 3, 7, 11),
    'major6': (0, 4, 7, 9), 'minor6': (0, 3, 7, 9),
    'add9': (0, 2, 4, 7), 'minor_add9': (0, 2, 3, 7),
}
NAMES = ('C', 'C#/Db', 'D', 'D#/Eb', 'E', 'F', 'F#/Gb', 'G', 'G#/Ab', 'A', 'A#/Bb', 'B')
WEIGHTS = dict(occupancy=.10, attacks=.04, metric=.08, bass=.14,
               chord_roots=.14, arrivals=.14, returns=.06,
               leading_steps=.08, harmonic_resolutions=.22)
PROFILES = {
    'major': (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88),
    'minor': (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17),
}
LIMITATIONS = [
    'Heuristic scores and margins are not calibrated probabilities or measured accuracy.',
    'Written timeline only; repeats are not expanded. Source markers are section declarations, not inferred phrases.',
    'Nominal written duration is not measured acoustic sustain; unsupported pitch-changing techniques are excluded by the adapter.',
    'Chord labels are exact pitch-set template candidates, not confirmed functional roots; rootless/incomplete extended chords and arpeggiated harmony remain unresolved.',
    'Voice endings, rests and metric accents are structural proxies, not confirmed cadences or phrases.',
    'Major/minor profiles are diagnostic baselines only. Mode vocabulary is seven diatonic modes plus two minor collections.',
    'Mixture, applied harmony and ornament labels are competing explanations, not automatic proof of modulation.',
    'No learned model, audio/listening validation, corpus accuracy, polytonal diagnosis or exact inverse is claimed.',
]


def chord_candidates(pitch_classes, bass=None):
    """All exact templates; never substitute the bass for a harmonic root."""
    pcs = set(pitch_classes)
    if any(type(p) is not int or not 0 <= p < 12 for p in pcs):
        raise ValueError('Pitch classes must be integers in 0..11')
    out = []
    for root in sorted(pcs):
        intervals = {(p-root) % 12 for p in pcs}
        for quality, template in CHORDS.items():
            if intervals == set(template):
                out.append(dict(root=root, quality=quality,
                                bass_interval=(bass-root) % 12 if bass is not None else None))
    return out


def _distribution(values):
    total = sum(values)
    return [v/total for v in values] if total else [0.0]*12


def _correlation(a, b):
    am, bm = sum(a)/12, sum(b)/12
    x, y = [v-am for v in a], [v-bm for v in b]
    den = sqrt(sum(v*v for v in x)*sum(v*v for v in y))
    return sum(i*j for i, j in zip(x, y))/den if den else None


def _validated(score):
    if score.get('schema') != 'tonal-events/1':
        raise ValueError('Expected normalized tonal-events/1 input')
    def rational(value):
        if type(value) is not str or str(F(value)) != value:
            raise ValueError('Canonical rational timing strings required')
        return F(value)
    bars = score['bars']
    previous = F(0)
    bar_map = {}
    for index, b in enumerate(bars, 1):
        if type(b.get('bar')) is not int or b['bar'] != index:
            raise ValueError('Unique sequential bar identities required')
        start, span = rational(b['start_q']), rational(b['duration_q'])
        if start != previous or span <= 0:
            raise ValueError('Contiguous exact bar geometry required')
        sig = b['signature']
        if type(sig) is not list or len(sig) != 2 or any(type(x) is not int or x <= 0 for x in sig):
            raise ValueError('Explicit positive meter required')
        previous = start+span
        bar_map[index] = (start, previous)
    track_ids = [t['id'] for t in score['tracks']]
    if any(type(t) is not str for t in track_ids) or len(track_ids) != len(set(track_ids)):
        raise ValueError('Unique string track identities required')
    seen = set()
    events = []
    for e in score['events']:
        if not isinstance(e.get('id'), str) or e['id'] in seen:
            raise ValueError('Unique source occurrence IDs required')
        seen.add(e['id'])
        if type(e.get('eligible')) is not bool or type(e.get('attack')) is not bool:
            raise ValueError('Explicit boolean eligibility and attack required')
        if e.get('track_id') not in track_ids or type(e.get('bar')) is not int or e['bar'] not in bar_map:
            raise ValueError('Event must reference a declared track and bar')
        if type(e.get('voice')) is not int or e['voice'] < 0:
            raise ValueError('Nonnegative integer voice required')
        if not e['eligible']:
            continue
        if type(e.get('midi')) is not int or not 0 <= e['midi'] <= 127:
            raise ValueError('Eligible event requires integral MIDI pitch')
        start, duration = rational(e['onset_q']), rational(e['duration_q'])
        if start < 0 or duration <= 0:
            raise ValueError('Eligible event requires nonnegative onset and positive duration')
        if not bar_map[e['bar']][0] <= start < bar_map[e['bar']][1]:
            raise ValueError('Event onset does not belong to its declared bar')
        events.append(dict(e, _start=start, _end=start+duration))
    if any(e['_end'] > previous for e in events):
        raise ValueError('Eligible event extends outside source geometry')
    return events


def _deduplicate(events, excluded_tracks):
    """Deduplicate entire matching pitch/time/voice tracks, not individual notes."""
    by_track = defaultdict(list)
    for e in events:
        by_track[e['track_id']].append(e)
    signatures, kept, groups = {}, [], []
    for tid in sorted(by_track):
        rows = by_track[tid]
        signature = tuple(sorted((e['voice'], e['_start'], e['_end'], e['midi'],
                                  e['attack'], bool(e.get('accent'))) for e in rows))
        if tid in excluded_tracks:
            signature = (tid, signature)
        if signature in signatures:
            groups[signatures[signature]]['duplicate_track_ids'].append(tid)
        else:
            signatures[signature] = len(groups)
            groups.append(dict(representative_track_id=tid, duplicate_track_ids=[]))
            kept.extend(rows)
    return kept, groups


def _barriers(score):
    """Unresolved pitched material cannot become silence or a complete sonority."""
    bars = {b['bar']: b for b in score['bars']}
    out = []
    for e in score['events']:
        if e['eligible'] or any(r in e.get('exclusions', []) for r in ('unpitched_percussion', 'percussion', 'dead_note')):
            continue
        b = bars[e['bar']]
        start = F(e['onset_q']) if e.get('onset_q') is not None else F(b['start_q'])
        duration = F(e['duration_q']) if e.get('duration_q') is not None else F(b['duration_q'])
        if e.get('onset_q') is None or e.get('duration_q') is None or 'voice_overflows_bar' in e.get('exclusions', []):
            start, duration = F(b['start_q']), F(b['duration_q'])
        out.append(dict(id=e['id'], track_id=e['track_id'], voice=e['voice'], start=start, end=start+duration))
    for index, w in enumerate(score.get('warnings', [])):
        if w.get('reason') in ('invalid_duration', 'invalid_grace_flag', 'voice_overflows_bar') and w.get('bar') in bars:
            b = bars[w['bar']]
            out.append(dict(id=f'timing-warning:{index}', track_id=w['track_id'], voice=w['voice'],
                            start=F(b['start_q']), end=F(b['start_q'])+F(b['duration_q'])))
    return out


def _cells(events, barriers):
    changes = defaultdict(lambda: [[], []])
    for e in events:
        changes[e['_start']][1].append(e)
        changes[e['_end']][0].append(e)
    for b in barriers:
        changes[b['start']]
        changes[b['end']]
    active, cells = {}, []
    times = sorted(changes)
    for index, time in enumerate(times[:-1]):
        ends, starts = changes[time]
        for e in ends:
            active.pop(e['id'], None)
        for e in starts:
            active[e['id']] = e
        if not active:
            continue
        rows = list(active.values())
        blocked = [b['id'] for b in barriers if b['start'] < times[index+1] and b['end'] > time]
        pcs = sorted({e['midi'] % 12 for e in rows})
        bass = min(e['midi'] for e in rows)
        # Preserve every exact witness; activity is half-open [start, end).
        cell = dict(start_q=str(time), end_q=str(times[index+1]), pitch_classes=pcs,
                    bass=bass, note_refs=sorted(active), complete=not blocked,
                    excluded_note_refs=blocked, candidates=[] if blocked else chord_candidates(pcs, bass % 12))
        cells.append(cell)
    return cells


def _voice_evidence(events, barriers):
    voices = defaultdict(list)
    for e in events:
        voices[e['track_id'], e['voice']].append(e)
    arrivals, transitions, returns, ornaments = [], [], [], []
    for (track, voice), rows in voices.items():
        blocks = [b for b in barriers if b['track_id'] == track and b['voice'] == voice]
        def blocked(a, b):
            return any(x['start'] < b and x['end'] > a or a <= x['start'] < b and x['start'] == x['end'] for x in blocks)
        starts = defaultdict(list)
        for e in rows:
            starts[e['_start']].append(e)
        groups = []
        for t in sorted(starts):
            group = starts[t]
            pitches = {e['midi'] for e in group}
            groups.append(dict(start=t, end=max(e['_end'] for e in group),
                               pitches=pitches, refs=sorted(e['id'] for e in group),
                               attack=any(e['attack'] for e in group), members=group[:]))
        # Merge verified tied continuations so segmentation does not manufacture evidence.
        merged = []
        for g in groups:
            if merged and not g['attack'] and merged[-1]['end'] == g['start'] and merged[-1]['pitches'] == g['pitches']:
                merged[-1]['end'] = g['end']
                merged[-1]['refs'] += g['refs']
                merged[-1]['members'] += g['members']
            else:
                merged.append(g)
        groups = merged
        def monophonic(g):
            return len(g['pitches']) == 1 and not any(x is not g and x['start'] < g['end'] and x['end'] > g['start'] for x in groups)
        voice_end = max(g['end'] for g in groups)
        history = []
        for i, g in enumerate(groups):
            nxt = groups[i+1] if i+1 < len(groups) else None
            clear_end = g['end'] == voice_end and not any(b['end'] >= g['end'] for b in blocks)
            clear_gap = nxt is not None and nxt['start']-g['end'] >= 1 and not blocked(g['start'], nxt['start']) and not any(x['start'] < nxt['start'] and x['end'] > g['end'] for x in groups)
            if clear_end or clear_gap:
                landing = [e for e in g['members'] if e['_end'] == g['end']]
                arrivals.append(dict(at_q=str(g['end']), start_q=str(g['start']),
                                     pitch_classes=sorted({e['midi'] % 12 for e in landing}),
                                     reason='voice_end' if clear_end else 'before_rest_at_least_one_quarter',
                                     note_refs=sorted(e['id'] for e in landing)))
            # Only unambiguous monophonic neighbors in the SAME voice, no overlap/gap.
            mono = monophonic(g)
            if not mono or (i and (groups[i-1]['end'] != g['start'] or blocked(groups[i-1]['start'], g['start']))):
                history = []
            if mono:
                pitch = next(iter(g['pitches']))
                if pitch % 12 in history[:-1] and history and history[-1] != pitch % 12:
                    returns.append(dict(at_q=str(g['start']), tonic=pitch % 12, note_refs=g['refs']))
                history.append(pitch % 12)
            if mono and nxt and monophonic(nxt) and g['end'] == nxt['start'] and nxt['attack'] and not blocked(g['start'], nxt['end']):
                p, q = next(iter(g['pitches'])), next(iter(nxt['pitches']))
                transitions.append(dict(at_q=str(nxt['start']), context_start_q=str(g['start']), from_midi=p, to_midi=q,
                                        semitones=q-p, track_id=track, voice=voice,
                                        note_refs=g['refs']+nxt['refs']))
            if 0 < i < len(groups)-1:
                a, b, c = groups[i-1:i+2]
                if all(monophonic(x) for x in (a, b, c)) and a['end'] == b['start'] and b['end'] == c['start'] and not blocked(a['start'], c['end']):
                    p, q, r = [next(iter(x['pitches'])) for x in (a, b, c)]
                    kind = 'neighbor' if p == r and 0 < abs(q-p) <= 2 else 'passing' if 0 < abs(q-p) <= 2 and 0 < abs(r-q) <= 2 and (q-p)*(r-q) > 0 else None
                    if kind and b['end']-b['start'] <= min(a['end']-a['start'], c['end']-c['start']):
                        ornaments.append(dict(at_q=str(b['start']), pitch_class=q % 12, kind=kind+'_candidate',
                                              note_refs=a['refs']+b['refs']+c['refs']))
    return arrivals, transitions, returns, ornaments


def _harmonic_evidence(cells):
    rows = []
    for a, b in zip(cells, cells[1:]):
        if a['end_q'] != b['start_q'] or not a['complete'] or not b['complete'] or a['pitch_classes'] == b['pitch_classes']:
            continue
        for left in a['candidates']:
            for right in b['candidates']:
                step = (right['root']-left['root']) % 12
                kind, weight = None, 0
                if right['quality'] in ('major', 'minor', 'major7', 'minor7', 'major6', 'minor6'):
                    if step == 5 and left['quality'] in ('major', 'dominant7'):
                        kind, weight = 'dominant_to_tonic_pattern', 1.0 if left['quality'] == 'dominant7' else .6
                    elif step == 1 and left['quality'] in ('diminished', 'diminished7', 'half_diminished7'):
                        kind, weight = 'leading_chord_resolution_pattern', .8
                    elif step == 7 and left['quality'] in ('major', 'minor'):
                        kind, weight = 'plagal_or_modal_return_pattern', .35
                if kind:
                    rows.append(dict(at_q=b['start_q'], context_start_q=a['start_q'], target=right['root'], kind=kind,
                                     weight=weight/(len(a['candidates'])*len(b['candidates'])),
                                     from_chord=left, to_chord=right,
                                     note_refs=sorted(set(a['note_refs']+b['note_refs']))))
    return rows


def _metric(event, bars):
    b = bars[event['bar']]
    offset = event['_start']-F(b['start_q'])
    n, d = b['signature']
    if b.get('pickup'):
        offset += F(4*n, d)-F(b['duration_q'])
    if offset == 0:
        return 2.0
    unit = F(4, d)*(3 if n > 3 and n % 3 == 0 else 1)
    return 1.0 if offset % unit == 0 else .25


def _scope(events, cells, voice_data, harmonic, bars, start, end, top):
    arrivals, transitions, returns, ornaments = voice_data
    rows = [e for e in events if e['_start'] < end and e['_end'] > start]
    chans = {k: [0.0]*12 for k in WEIGHTS}
    attacked = [e for e in rows if e['attack'] and start <= e['_start'] < end]
    # Collapse coattacked octave/unison doubling within and between tracks.
    coattacks = defaultdict(list)
    for e in attacked:
        coattacks[e['_start'], e['midi'] % 12].append(e)
    for (_, pc), es in coattacks.items():
        chans['attacks'][pc] += 1
        chans['metric'][pc] += max(_metric(e, bars)*(1.25 if e.get('accent') else 1) for e in es)
    selected_cells, matched_duration, active_duration = [], F(0), F(0)
    for c in cells:
        left, right = max(start, F(c['start_q'])), min(end, F(c['end_q']))
        if left >= right:
            continue
        duration = right-left
        active_duration += duration
        for pc in c['pitch_classes']:
            chans['occupancy'][pc] += float(duration)
        if c['complete']:
            chans['bass'][c['bass'] % 12] += float(duration)
        for cand in c['candidates']:
            chans['chord_roots'][cand['root']] += float(duration)/len(c['candidates'])
        if c['candidates']:
            matched_duration += duration
        selected_cells.append(dict(c, clipped_start_q=str(left), clipped_end_q=str(right)))
    selected_arrivals = [a for a in arrivals if start < F(a['at_q']) <= end and F(a['start_q']) < end]
    for a in selected_arrivals:
        for pc in a['pitch_classes']:
            chans['arrivals'][pc] += 1/len(a['pitch_classes'])
    selected_transitions = [dict(t, uses_preceding_context=F(t['context_start_q']) < start) for t in transitions if start <= F(t['at_q']) < end]
    for t in selected_transitions:
        if t['semitones'] == 1:
            chans['leading_steps'][t['to_midi'] % 12] += 1
    selected_returns = [r for r in returns if start <= F(r['at_q']) < end]
    for r in selected_returns:
        chans['returns'][r['tonic']] += 1
    selected_harmonic = [dict(h, uses_preceding_context=F(h['context_start_q']) < start) for h in harmonic if start <= F(h['at_q']) < end]
    for h in selected_harmonic:
        chans['harmonic_resolutions'][h['target']] += h['weight']
    distributions = {k: _distribution(v) for k, v in chans.items()}
    # Weighted membership is separate from tonic evidence; no absent-note penalty.
    membership = [sum(distributions[k][p]*w for k, w in (('occupancy', .6), ('metric', .25), ('attacks', .15))) for p in range(12)]
    membership = _distribution(membership)
    pcs = sorted({e['midi'] % 12 for e in rows})
    fits = {}
    for tonic in range(12):
        for mode, intervals in MODES.items():
            scale = {(tonic+d) % 12 for d in intervals}
            fits[tonic, mode] = sum(membership[p] for p in scale)
    centers = []
    for tonic in range(12):
        components = {k: distributions[k][tonic] for k in WEIGHTS}
        base = sum(WEIGHTS[k]*components[k] for k in WEIGHTS)
        fit = max(fits[tonic, m] for m in MODES)
        centers.append(dict(tonic=tonic, name=NAMES[tonic], score=.85*base+.15*fit,
                            components=components, best_collection_fit=fit))
    centers.sort(key=lambda c: (-c['score'], c['tonic']))
    center_scores = {c['tonic']: c['score'] for c in centers}
    candidates = []
    for (tonic, mode), fit in fits.items():
        scale = {(tonic+d) % 12 for d in MODES[mode]}
        candidates.append(dict(tonic=tonic, tonic_name=NAMES[tonic], mode=mode,
                               score=center_scores[tonic]-.20*(1-fit),
                               components=dict(center_support=center_scores[tonic], scale_fit=fit),
                               outside_pitch_classes=sorted(set(pcs)-scale),
                               unobserved_scale_pitch_classes=sorted(scale-set(pcs))))
    candidates.sort(key=lambda c: (-c['score'], c['tonic'], c['mode']))
    margin = centers[0]['score']-centers[1]['score']
    distinct_attacks = len({e['_start'] for e in attacked})
    enough = len(pcs) >= 2 and distinct_attacks >= 3
    center = centers[0]['tonic'] if enough and margin >= .035 else None
    mode = None
    plausible = []
    if center is not None:
        best_fit = max(fits[center, m] for m in MODES)
        plausible = [m for m in MODES if best_fit-fits[center, m] <= .025]
        if len(plausible) == 1 and best_fit >= .90:
            mode = plausible[0]
    status = 'no_pitched_evidence' if not rows else 'center_unresolved' if center is None else 'mode_unresolved' if mode is None else 'ranked_hypothesis'
    profiles = []
    for tonic in range(12):
        for quality, profile in PROFILES.items():
            rotated = [profile[(p-tonic) % 12] for p in range(12)]
            profiles.append(dict(tonic=tonic, quality=quality, correlation=_correlation(chans['occupancy'], rotated)))
    profiles.sort(key=lambda p: (-(p['correlation'] if p['correlation'] is not None else -2), p['tonic'], p['quality']))
    if not rows:
        centers, candidates, profiles = [], [], []
    return dict(start_q=str(start), end_q=str(end), status=status, center=center, mode=mode,
                center_margin=margin if rows else None, plausible_modes=plausible,
                candidates=candidates[:top], centers=centers, profile_baseline=profiles[:top],
                evidence=dict(pitch_classes=pcs, channels=chans, distributions=distributions,
                              eligible_occurrences=len(rows), attack_positions=distinct_attacks,
                              chords=selected_cells, harmonic_patterns=selected_harmonic,
                              melodic_transitions=selected_transitions, arrivals=selected_arrivals,
                              returns=selected_returns,
                              ornament_candidates=[o for o in ornaments if start <= F(o['at_q']) < end],
                              matched_chord_duration_q=str(matched_duration), active_duration_q=str(active_duration)),
                interpretation_notes=(['Both major and minor thirds occur relative to the proposed center; mixture or chromatic function needs contextual review.']
                                      if center is not None and (center+3) % 12 in pcs and (center+4) % 12 in pcs else []))


def analyze(score, window_bars=4, top=5):
    """Analyze a normalized score without modifying it or consulting labels."""
    if type(window_bars) is not int or window_bars < 1 or type(top) is not int or not 1 <= top <= 108:
        raise ValueError('window_bars must be positive and top must be in 1..108')
    original_events = _validated(score)
    events, duplicate_groups = _deduplicate(original_events, {e['track_id'] for e in score['events'] if not e['eligible']})
    barriers = _barriers(score)
    cells = _cells(events, barriers)
    voice_data = _voice_evidence(events, barriers)
    harmonic = _harmonic_evidence(cells)
    bars = {b['bar']: b for b in score['bars']}
    end = max((F(b['start_q'])+F(b['duration_q']) for b in bars.values()), default=F(0))
    def scope(a, b):
        return _scope(events, cells, voice_data, harmonic, bars, a, b, top)
    result = dict(schema='tonal-analysis/1', global_=scope(F(0), end))
    result['global'] = result.pop('global_')
    ordered = score['bars']
    windows = []
    for i in range(max(0, len(ordered)-window_bars+1)):
        last = ordered[i+window_bars-1]
        windows.append(dict(scope(F(ordered[i]['start_q']), F(last['start_q'])+F(last['duration_q'])),
                            first_bar=ordered[i]['bar'], last_bar=last['bar']))
    sections, section_start, label = [], 0, ordered[0].get('section') if ordered else None
    explicit_sections = {d.get('bar') for d in score.get('declarations', []) if d.get('field') == 'marker' and d.get('value')}
    for i in range(1, len(ordered)+1):
        if i == len(ordered) or ordered[i].get('section') != label or ordered[i]['bar'] in explicit_sections:
            last = ordered[i-1]
            sections.append(dict(scope(F(ordered[section_start]['start_q']), F(last['start_q'])+F(last['duration_q'])),
                                 label=label, first_bar=ordered[section_start]['bar'], last_bar=last['bar']))
            if i < len(ordered):
                section_start, label = i, ordered[i].get('section')
    changes = []
    for a, b in zip(sections, sections[1:]):
        if a['center'] is not None and b['center'] is not None and a['center'] != b['center']:
            changes.append(dict(at_q=b['start_q'], from_center=a['center'], to_center=b['center'],
                                status='section_center_change_candidate_not_confirmed_modulation'))
    result.update(windows=windows, sections=sections, changes=changes,
                  configuration=dict(version='heuristic-v1', weights=WEIGHTS.copy(), window_bars=window_bars,
                                     center_margin_threshold=.035, mode_fit_gap=.025, minimum_mode_fit=.90,
                                     candidate_modes=list(MODES), score_type='uncalibrated_heuristic',
                                     repeat_policy='written_once', pitch_policy='eligible_written_base_pitch'),
                  coverage=dict(source_occurrences=len(score['events']), eligible_occurrences=len(original_events),
                                analyzed_after_track_deduplication=len(events), duplicate_track_groups=duplicate_groups,
                                exclusions=dict(Counter(reason for e in score['events'] for reason in e.get('exclusions', [])))),
                  declarations=score.get('declarations', []), source_warnings=score.get('warnings', []),
                  limitations=LIMITATIONS[:])
    return result
