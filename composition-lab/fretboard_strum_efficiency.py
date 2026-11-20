"""Independent exact Drop E search for open strings, strums, and rapid picks.

The three primary costs are strictly lexicographic. Direction reversals and
repeated-shape continuity and the existing hand-movement model break ties only
after all three primary costs are equal. The original optimizer remains unchanged.
"""
from dataclasses import dataclass
from math import isfinite

from fretboard_efficiency import (
    State as DiagnosticState, _advance, _compatible, _frames, _result, _validated,
)


@dataclass
class PickState:
    cost: tuple
    grip: object
    position: object
    last_fretted_tick: object
    last_fretted_release_tick: object
    last_fretted_grip: tuple
    last_shape_tick: object
    last_fretted_pitch_positions: tuple
    singleton_string: object
    run_direction: int
    parent: object
    tick: int
    order_key: tuple
    rank: int = 0


def _pick_delta(previous, grip, tick, seconds_per_tick, rapid_max_gap_seconds):
    struck = grip.new_strings
    chord_skips = sum(max(0, b - a - 1) for a, b in zip(struck, struck[1:])) if len(struck) > 1 else 0
    single = struck[0] if len(struck) == 1 else None
    rapid_pair = (single is not None and previous.singleton_string is not None
                  and (tick - previous.tick) * seconds_per_tick <= rapid_max_gap_seconds)
    skips = reversals = direction = 0
    if rapid_pair:
        step = single - previous.singleton_string
        skips = max(0, abs(step) - 1)
        step_direction = (step > 0) - (step < 0)
        # Repeated-string attacks do not invent a direction or reset an
        # established run. A chord or a long onset gap does reset the run.
        direction = step_direction or previous.run_direction
        reversals = int(bool(step_direction and previous.run_direction
                             and step_direction != previous.run_direction))
    return chord_skips, skips, reversals, single, direction, rapid_pair


def _movement_delta(previous, grip, tick, position, seconds_per_tick, rapid_rate):
    """Same declared hand proxy as before, subordinate to all pick priorities."""
    positive = tuple(sorted((s, f) for s, f in grip.placements if f))
    last_tick = previous.last_fretted_tick
    last_release = previous.last_fretted_release_tick
    last_grip = previous.last_fretted_grip
    last_shape_tick = previous.last_shape_tick
    last_pitches = previous.last_fretted_pitch_positions
    shift = rapid = changes = shape_remaps = 0
    if positive:
        new_fretted = any(note_id in grip.new_ids and fret > 0
                          for note_id, _, fret in grip.assignments)
        if new_fretted:
            pitch_positions = tuple(sorted((pitch, string, fret)
                for pitch, (string, fret) in zip(grip.pitches, grip.placements) if fret))
            if last_shape_tick is not None and (tick - last_shape_tick) * seconds_per_tick <= 0.75:
                old_by_pitch = {pitch: (string, fret) for pitch, string, fret in last_pitches}
                shared = [(pitch, string, fret) for pitch, string, fret in pitch_positions
                          if pitch in old_by_pitch]
                # A repeated fretted dyad/shape can keep its physical contacts,
                # including when only open strings sound between the two attacks.
                if len(shared) >= 2:
                    shape_remaps = sum(old_by_pitch[pitch] != (string, fret)
                                       for pitch, string, fret in shared)
            last_shape_tick, last_pitches = tick, pitch_positions
        if previous.position is not None:
            shift = abs(position - previous.position)
        if last_tick is not None:
            spacing = (tick - last_tick) * seconds_per_tick
            available = min(spacing, max(0.0, (tick - last_release) * seconds_per_tick)
                            + min(0.125, spacing))
            excess = max(0.0, shift - rapid_rate * available)
            rapid = round(1000 * excess * excess / max(available, 0.0625))
            changes = len(set(positive) ^ set(last_grip))
        last_tick, last_release, last_grip = tick, grip.fretted_release_tick, positive
    effort = 4 * grip.contact_count + 8 * max(0, grip.span - 3) + changes
    return (shape_remaps, rapid, shift, effort, last_tick, last_release,
            last_grip, last_shape_tick, last_pitches)


def _annotate_winner(last, source, seconds_per_tick, rapid_rate, rapid_max_gap_seconds, examined, *, stable_mode=False):
    chain = []
    state = last
    while state.parent is not None:
        chain.append(state)
        state = state.parent
    chain.reverse()

    # Only after choosing the new optimizer's winning path, reuse the existing
    # diagnostics. These helpers never choose or prune a new-search state.
    diagnostic = DiagnosticState((0, 0, 0, 0, 0, 0), None, None, None, None,
                                 (), None, None, -1, (), ())
    chord_count = contiguous_count = pair_count = skip_pair_count = 0
    for state in chain:
        grip = state.grip
        # A canonical bass-to-treble chord annotation, not a claim of optimal
        # stroke direction. Both monotonic strum directions have the same gaps.
        pick_order = tuple(reversed(grip.new_strings))
        diagnostic = _advance(diagnostic, grip, state.tick, state.position,
                              pick_order, seconds_per_tick, rapid_rate)
        chord_skips, skips, _, _, _, rapid_pair = _pick_delta(
            state.parent, grip, state.tick, seconds_per_tick, rapid_max_gap_seconds)
        if len(grip.new_strings) > 1:
            chord_count += 1
            contiguous_count += chord_skips == 0
        pair_count += rapid_pair
        skip_pair_count += bool(rapid_pair and skips)

    result = _result(diagnostic, source, seconds_per_tick, rapid_rate, False, examined)
    if stable_mode:
        metrics = result['metrics']
        if [metrics['open_exceptions'], metrics['rapid_shift_cost'],
                metrics['hand_travel_frets'], metrics['fretting_effort']] != [
                    last.cost[0], last.cost[2], last.cost[3], last.cost[7]]:
            raise AssertionError('Fret-stability search and selected-path diagnostics disagree.')
        result.update(
            id='stable', label='Stable frets',
            description='Preserve opens and adjacent-string chords, then minimize fast neck-position '
                        'shifts and total movement along the frets; rapid single-note string skips '
                        'are a lower priority. Shape continuity, direction, and fretting effort break ties.')
        metrics.update(
            chord_skipped_strings=last.cost[1], chord_attack_count=chord_count,
            contiguous_chord_count=contiguous_count,
            rapid_single_skipped_strings=last.cost[4], rapid_single_pair_count=pair_count,
            rapid_single_skip_transition_count=skip_pair_count,
            rapid_run_direction_reversals=last.cost[5], repeated_shape_remaps=last.cost[6],
            priority_cost=list(last.cost[:5]), tie_break_cost=list(last.cost[5:]),
            tier_cost=list(last.cost[:5]), search='exhaustive_fret_stability_dp')
        result['objective'] = dict(
            priority_order=['open_misses', 'chord_skipped_strings', 'rapid_shift_cost',
                            'hand_travel_frets', 'rapid_single_skipped_strings'],
            priority_labels=['Exact-pitch open strings', 'Adjacent strings for simultaneous notes',
                             'Avoid rapid hand-position changes along frets',
                             'Minimize total neck travel in frets',
                             'Minimize skipped strings in rapid single-note passages'],
            rapid_max_gap_seconds=rapid_max_gap_seconds,
            tie_break_order=['rapid_run_direction_reversals', 'repeated_shape_remaps',
                             'fretting_effort'],
            repeated_shape_definition='Retain recurring fretted dyads through open-string passages '
                                      'when higher-priority fret movement and picking goals tie.',
            hand_shift_definition='Release-aware hand-position travel using the existing '
                                  'five-fret hand window; an open-only passage preserves the '
                                  'previous anchor but allows elapsed release time.',
            rapid_frets_per_second=rapid_rate, transition_allowance_seconds=0.125)
        return result
    result.update(id='strumPick', label='Strum + pick',
                  description='Minimize missed exact-pitch opens, then skipped strings within co-attacks, '
                              'then skips between rapid single attacks. Picking direction, repeated '
                              'fretted-shape continuity, and movement '
                              'break otherwise equal results.')
    metrics = result['metrics']
    if [metrics['open_exceptions'], metrics['rapid_shift_cost'],
        metrics['hand_travel_frets'], metrics['fretting_effort']] != [last.cost[0], *last.cost[5:]]:
        raise AssertionError('Independent search and selected-path diagnostics disagree.')
    metrics.update(
        chord_skipped_strings=last.cost[1], chord_attack_count=chord_count,
        contiguous_chord_count=contiguous_count, rapid_single_skipped_strings=last.cost[2],
        rapid_single_pair_count=pair_count, rapid_single_skip_transition_count=skip_pair_count,
        rapid_run_direction_reversals=last.cost[3], priority_cost=list(last.cost[:3]),
        repeated_shape_remaps=last.cost[4],
        tie_break_cost=list(last.cost[3:]), tier_cost=list(last.cost[:3]),
        search='exhaustive_strum_pick_dp')
    result['objective'] = dict(
        priority_order=['open_misses', 'chord_skipped_strings', 'rapid_single_skipped_strings'],
        priority_labels=['Exact-pitch open strings', 'Fewest skipped strings in co-attacked chords',
                         'Fewest string skips between rapid single attacks'],
        rapid_max_gap_seconds=rapid_max_gap_seconds,
        chord_skip_definition='Sum of unstruck strings between adjacent sorted strings in an exact '
                              'co-attack. Held-only notes are not new attacks.',
        rapid_skip_definition='For consecutive attack groups that each contain exactly one new note, '
                              'with onset gap at most rapid_max_gap_seconds, add max(0, abs(string '
                              'difference) - 1). Same and adjacent strings both cost zero. Chords and '
                              'longer gaps break the run; other ringing notes do not.',
        tie_break_order=['rapid_run_direction_reversals', 'repeated_shape_remaps', 'rapid_shift_cost',
                         'hand_travel_frets', 'fretting_effort'],
        repeated_shape_definition='For successive fretted attacks within 0.75 seconds, if at least '
                                  'two pitches recur, count recurring pitches moved to a different '
                                  'string/fret. Open-only attacks preserve the previous shape memory.',
        direction_definition='Count nonzero string-direction changes within a rapid single-attack run. '
                             'Repeated-string attacks retain the last nonzero direction; chords and '
                             'long gaps reset it. Chord orders are canonical bass-to-treble annotations.',
        rapid_frets_per_second=rapid_rate, transition_allowance_seconds=0.125,
        deterministic_tie_break='Lexicographic occurrence-ordered string/fret and anchor path, after '
                                'all three primary and all four secondary costs are equal.')
    return result


def optimize_strum_fingering(notes, *, ticks_per_beat=960, tempo_bpm=120, max_fret=24,
                            max_span=4, rapid_max_gap_seconds=0.25, rapid_frets_per_second=8.0,
                            prioritize_fret_stability=False):
    """Assign exact source occurrences without changing pitches, starts, or holds.

    The search reuses only admitted physical grips/input validation. All search
    states, transitions, dominance, objectives, and final selection live here.
    """
    if isinstance(rapid_max_gap_seconds, bool) or not isinstance(rapid_max_gap_seconds, (int, float)) \
            or not isfinite(rapid_max_gap_seconds) or rapid_max_gap_seconds <= 0:
        raise ValueError('Positive finite rapid_max_gap_seconds required.')
    source = _validated(notes, ticks_per_beat, tempo_bpm, max_fret, max_span, rapid_frets_per_second)
    frames = _frames(source, max_fret, max_span)
    seconds_per_tick = 60 / (tempo_bpm * ticks_per_beat)
    initial = PickState((0,) * 8, None, None, None, None, (), None, (), None, 0, None, -1, ())
    states, examined = [initial], 0
    for tick, active, _, grips in frames:
        held = {n['id'] for n in active if n['start_tick'] < tick}
        following = {}
        for previous in states:
            for grip in grips:
                if not _compatible(previous, grip, held):
                    continue
                chord_skips, single_skips, reversals, single, direction, _ = _pick_delta(
                    previous, grip, tick, seconds_per_tick, rapid_max_gap_seconds)
                for position in grip.anchors or (previous.position,):
                    shape_remaps, rapid, travel, effort, last_tick, last_release, last_grip, last_shape_tick, last_pitches = _movement_delta(
                        previous, grip, tick, position, seconds_per_tick, rapid_frets_per_second)
                    delta = ((grip.open_misses, chord_skips, rapid, travel, single_skips,
                              reversals, shape_remaps, effort) if prioritize_fret_stability else
                             (grip.open_misses, chord_skips, single_skips, reversals,
                              shape_remaps, rapid, travel, effort))
                    cost = tuple(a + b for a, b in zip(previous.cost, delta))
                    # Parent ranks order complete equal-length prefixes, so a
                    # bounded key gives deterministic full-path ordering without
                    # retaining a copied history tuple in every state.
                    order_key = (previous.rank, tuple((s, f) for _, s, f in grip.assignments), position or 0)
                    state = PickState(cost, grip, position, last_tick, last_release, last_grip,
                                      last_shape_tick, last_pitches,
                                      single, direction, previous, tick, order_key)
                    examined += 1
                    key = (grip.assignments, position, last_tick, last_release, last_grip,
                           last_shape_tick, last_pitches, single, direction)
                    incumbent = following.get(key)
                    if incumbent is None or (cost, order_key) < (incumbent.cost, incumbent.order_key):
                        following[key] = state
        if not following:
            raise ValueError(f'No globally compatible fingering at tick {tick}; held notes cannot be reassigned or shortened.')
        states = sorted(following.values(), key=lambda state: state.order_key)
        for rank, state in enumerate(states):
            state.rank = rank
    winner = min(states, key=lambda state: (state.cost, state.rank))
    return _annotate_winner(winner, source, seconds_per_tick, rapid_frets_per_second,
                           rapid_max_gap_seconds, examined, stable_mode=prioritize_fret_stability)


def optimize_fret_stable_fingering(notes, **kwargs):
    """Prefer a stable fretting-hand location over rapid single-note string hops."""
    return optimize_strum_fingering(notes, prioritize_fret_stability=True, **kwargs)
