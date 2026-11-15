"""Exact finite-state, lexicographic Drop E fingering search.

This module assigns physical locations; it never rewrites a musical event.
The reach/contact and timing models are explicit proxies, not a human comfort
certificate. The search is exhaustive inside that discrete model, without a
beam or a weighted tradeoff between the user's five priority tiers.
"""
from dataclasses import dataclass
from functools import lru_cache
from collections import defaultdict
from math import isfinite

from fretting_contacts import analyze as contact_coverage
from fretboard_efficiency_shapes import shape_cost

DROP_E = (64, 59, 55, 50, 45, 40, 35, 28)  # conventional strings 1 to 8


@dataclass(frozen=True)
class Grip:
    assignments: tuple  # (original note id, string number, fret)
    placements: tuple
    pitches: tuple
    new_ids: tuple
    new_strings: tuple
    anchors: tuple
    open_misses: int
    contact_count: int
    span: int
    fretted_release_tick: object


@dataclass
class State:
    cost: tuple
    grip: object
    position: object
    last_fretted_tick: object
    last_fretted_release_tick: object
    last_fretted_grip: tuple
    last_pick: object
    parent: object
    tick: int
    shape_labels: tuple
    pick_order: tuple


@lru_cache(maxsize=10000)
def _contacts(placements):
    if not placements or not any(f for s, f in placements):
        return 0
    result = contact_coverage([dict(string=s, fret=f) for s, f in placements])
    return result['minimum_contacts'] if result['status'] == 'COVERED' else None


@lru_cache(maxsize=100000)
def _shape(placements, pitches, previous_placements, previous_pitches):
    cost, labels = shape_cost(placements, pitches, previous_placements, previous_pitches)
    return int(cost), tuple(labels)


def _validated(notes, ticks_per_beat, tempo_bpm, max_fret, max_span, rapid_frets_per_second):
    if not notes:
        raise ValueError('At least one MIDI note is required.')
    if not isinstance(ticks_per_beat, int) or ticks_per_beat <= 0:
        raise ValueError('Positive integer ticks_per_beat required.')
    if not isfinite(tempo_bpm) or tempo_bpm <= 0:
        raise ValueError('Positive tempo required.')
    if not isinstance(max_fret, int) or not 0 <= max_fret <= 24:
        raise ValueError('Invalid fret limit.')
    if not isinstance(max_span, int) or not 0 <= max_span <= 8:
        raise ValueError('Invalid fretted span.')
    if not isfinite(rapid_frets_per_second) or rapid_frets_per_second <= 0:
        raise ValueError('Positive rapid-shift threshold required.')
    out, ids = [], set()
    for n in notes:
        if n.get('id') in ids:
            raise ValueError('Every source occurrence needs a unique note id.')
        ids.add(n.get('id'))
        if n.get('id') is None:
            raise ValueError('Missing note id.')
        if any(not isinstance(n.get(k), int) for k in ('pitch', 'start_tick', 'end_tick')):
            raise ValueError('Pitch and exact MIDI ticks must be integers.')
        if n['start_tick'] < 0 or n['end_tick'] <= n['start_tick']:
            raise ValueError('Notes require positive, ordered source durations.')
        if not any(0 <= n['pitch'] - p <= max_fret for p in DROP_E):
            raise ValueError(f'Note {n["id"]} pitch {n["pitch"]} is outside this guitar range.')
        out.append(dict(n))
    return sorted(out, key=lambda n: (n['start_tick'], str(n['id'])))


def _grips(active, new_ids, max_fret, max_span):
    if len(active) > 8:
        return []
    new_ids = set(new_ids)
    options = {
        n['id']: [(i + 1, n['pitch'] - p) for i, p in enumerate(DROP_E)
                  if 0 <= n['pitch'] - p <= max_fret] for n in active
    }
    # Constrained notes first. Original identities remain intact in the result.
    order = sorted(active, key=lambda n: (len(options[n['id']]), n['pitch'], str(n['id'])))
    candidates = []

    def visit(i, used, chosen, positive):
        if i == len(order):
            placements = tuple(sorted(chosen.values()))
            count = _contacts(placements)
            if count is None:
                return
            span = max(positive) - min(positive) if positive else 0
            anchors = tuple(range(max(1, max(positive) - max_span), min(positive) + 1)) if positive else ()
            assignments = tuple((n['id'], *chosen[n['id']]) for n in active)
            ordered_places = tuple(chosen[n['id']] for n in active)
            misses = sum(n['id'] in new_ids and n['pitch'] in DROP_E and chosen[n['id']][1] != 0 for n in active)
            candidates.append(Grip(assignments, ordered_places, tuple(n['pitch'] for n in active),
                tuple(n['id'] for n in active if n['id'] in new_ids),
                tuple(sorted(chosen[n['id']][0] for n in active if n['id'] in new_ids)),
                anchors, misses, count, span,
                max((n['end_tick'] for n in active if chosen[n['id']][1] > 0), default=None)))
            return
        n = order[i]
        for string, fret in options[n['id']]:
            if string in used:
                continue
            fp = positive + ([fret] if fret else [])
            if fp and max(fp) - min(fp) > max_span:
                continue
            chosen[n['id']] = (string, fret)
            visit(i + 1, used | {string}, chosen, fp)
            del chosen[n['id']]

    visit(0, set(), {}, [])
    return candidates


def _frames(notes, max_fret, max_span):
    starts = sorted({n['start_tick'] for n in notes})
    frames = []
    for tick in starts:
        active = [n for n in notes if n['start_tick'] <= tick < n['end_tick']]
        new = tuple(n['id'] for n in active if n['start_tick'] == tick)
        candidates = _grips(active, new, max_fret, max_span)
        if not candidates:
            raise ValueError(f'No playable assignment at tick {tick} within the declared string/reach/contact limits.')
        frames.append((tick, active, new, candidates))
    # With no held notes crossing attack boundaries, every attack is independent
    # at Tier 1. Removing worse-open grips is then exact, not greedy pruning.
    cross_onset_holds = any(any(n['start_tick'] < tick < n['end_tick'] for n in notes) for tick in starts)
    if not cross_onset_holds:
        frames = [(tick, active, new, [g for g in gs if g.open_misses == min(x.open_misses for x in gs)])
                  for tick, active, new, gs in frames]
    return frames


def _compatible(previous, grip, held):
    if not held:
        return True
    if previous.grip is None:
        return False
    old = {note_id: (s, f) for note_id, s, f in previous.grip.assignments}
    return all(old.get(note_id) == (s, f) for note_id, s, f in grip.assignments if note_id in held)


def _with_held_continuation(frames):
    """Remove only grips with no complete, held-contact-compatible future.

    A greedy choice must not strand a still-ringing note when a later note
    enters. Backward reachability uses only identical held occurrence/string/
    fret assignments, never movement, opens, picking, shape, or future cost.
    Hand shifts have a soft cost, so they do not add a hard transition gate.
    """
    viable = list(frames)
    for index in range(len(viable) - 2, -1, -1):
        next_tick, next_active, _, next_grips = viable[index + 1]
        held = {n['id'] for n in next_active if n['start_tick'] < next_tick}
        if not held:
            continue
        # Frames retain the same original occurrence order, so these tuple
        # projections match even when other notes enter or leave the grip.
        def signature(grip):
            return tuple(a for a in grip.assignments if a[0] in held)
        continuations = {signature(grip) for grip in next_grips}
        tick, active, new_ids, grips = viable[index]
        grips = [grip for grip in grips if signature(grip) in continuations]
        if not grips:
            raise ValueError(f'No globally compatible fingering at tick {next_tick}; held notes cannot be reassigned or shortened.')
        viable[index] = (tick, active, new_ids, grips)
    return viable


def _advance(previous, grip, tick, position, pick_order, seconds_per_tick, rapid_rate):
    positive = tuple(sorted((s, f) for s, f in grip.placements if f))
    shift = rapid = contact_changes = 0
    last_tick, last_release, last_grip = previous.last_fretted_tick, previous.last_fretted_release_tick, previous.last_fretted_grip
    if positive:
        if previous.position is not None:
            shift = abs(position - previous.position)
        if last_tick is not None:
            # A long held fretted chord is NOT free repositioning time. Add
            # actual released/open time to a bounded 125ms transition proxy.
            spacing = (tick - last_tick) * seconds_per_tick
            elapsed = min(spacing, max(0.0, (tick - last_release) * seconds_per_tick) + min(0.125, spacing))
            excess = max(0.0, shift - rapid_rate * elapsed)
            rapid = round(1000 * excess * excess / max(elapsed, 0.0625))
            contact_changes = len(set(positive) ^ set(last_grip))
        last_tick, last_release, last_grip = tick, grip.fretted_release_tick, positive
    # Within Tier 3: first total longitudinal travel, then fretting/contact effort.
    fretting = 4 * grip.contact_count + 8 * max(0, grip.span - 3) + contact_changes
    picking = (abs(pick_order[0] - previous.last_pick) if previous.last_pick is not None else 0)
    picking += sum(abs(a - b) + 2 * max(0, abs(a - b) - 1) for a, b in zip(pick_order, pick_order[1:]))
    if previous.last_pick is not None:
        picking += 2 * max(0, abs(pick_order[0] - previous.last_pick) - 1)
    prior_places = previous.grip.placements if previous.grip else ()
    prior_pitches = previous.grip.pitches if previous.grip else ()
    shapes, labels = _shape(grip.placements, grip.pitches, prior_places, prior_pitches)
    delta = (grip.open_misses, rapid, shift, fretting, picking, shapes)
    cost = tuple(a + b for a, b in zip(previous.cost, delta))
    return State(cost, grip, position, last_tick, last_release, last_grip, pick_order[-1], previous, tick, labels, pick_order)


def _result(last, notes, seconds_per_tick, rapid_rate, optimized, states_examined):
    chain = []
    while last.parent is not None:
        chain.append(last)
        last = last.parent
    chain.reverse()
    assigned = {}
    positions = []
    for state in chain:
        for note_id, string, fret in state.grip.assignments:
            if note_id in assigned and assigned[note_id] != (string, fret):
                raise AssertionError('Held assignment changed.')
            assigned[note_id] = (string, fret)
        positions.append(dict(time_seconds=state.tick * seconds_per_tick, tick=state.tick,
            position=state.position, attack_note_ids=list(state.grip.new_ids),
            active_note_ids=[n for n, s, f in state.grip.assignments],
            shape_labels=list(state.shape_labels), picking_order=list(state.pick_order)))
    eligible = sum(n['pitch'] in DROP_E for n in notes)
    opens = sum(fret == 0 for string, fret in assigned.values())
    travel = max_shift = rapid_count = rapid_cost = 0
    prior_position = prior_tick = prior_release = None
    spans = []
    for state in chain:
        spans.append(state.grip.span)
        if not state.grip.anchors:
            continue
        if prior_position is not None:
            move = abs(state.position - prior_position)
            spacing = (state.tick - prior_tick) * seconds_per_tick
            elapsed = min(spacing, max(0.0, (state.tick - prior_release) * seconds_per_tick) + min(0.125, spacing))
            excess = max(0.0, move - rapid_rate * elapsed)
            travel += move
            max_shift = max(max_shift, move)
            rapid_count += move > rapid_rate * elapsed + 1e-9
            rapid_cost += round(1000 * excess * excess / max(elapsed, 0.0625))
        prior_position, prior_tick, prior_release = state.position, state.tick, state.grip.fretted_release_tick
    cost = chain[-1].cost
    return dict(id='optimized' if optimized else 'greedy',
        label='Ordered priorities' if optimized else 'Greedy comparison',
        description=('Whole-sequence minimum under the declared ordered objectives and discrete reach model.' if optimized else
                     'Each attack prefers opens and lower frets among grips with a feasible held-note continuation, '
                     'then the nearest reachable hand position. Future costs are not optimized.'),
        assignments=[dict(note_id=n['id'], string_number=assigned[n['id']][0], fret=assigned[n['id']][1]) for n in notes],
        positions=positions,
        metrics=dict(note_count=len(notes), attack_count=len(chain), open_eligible=eligible, open_used=opens,
            open_exceptions=eligible-opens, rapid_shift_count=rapid_count, rapid_shift_cost=rapid_cost,
            hand_travel_frets=travel, max_shift_frets=max_shift, max_fret_span=max(spans, default=0),
            mean_fret_span=round(sum(spans)/len(spans), 4), fretting_effort=cost[3],
            picking_cost=cost[4], shape_cost=cost[5], tier_cost=[cost[0], cost[1], [cost[2],cost[3]], cost[4], cost[5]],
            states_examined=states_examined, search='exhaustive_discrete_dp' if optimized else 'local_greedy'))


def _solve(notes, *, ticks_per_beat=960, tempo_bpm=120, max_fret=24, max_span=4,
           rapid_frets_per_second=8.0, optimized=True):
    source = _validated(notes, ticks_per_beat, tempo_bpm, max_fret, max_span, rapid_frets_per_second)
    frames = _frames(source, max_fret, max_span)
    if not optimized:
        frames = _with_held_continuation(frames)
    seconds_per_tick = 60 / (tempo_bpm * ticks_per_beat)
    initial = State((0,0,0,0,0,0), None, None, None, None, (), None, None, -1, (), ())
    states, examined = [initial], 0
    for tick, active, new_ids, grips in frames:
        held = {n['id'] for n in active if n['start_tick'] < tick}
        next_states = {}
        for previous in states:
            candidates = [g for g in grips if _compatible(previous, g, held)]
            if not optimized and candidates:
                candidates = [min(candidates, key=lambda g: (g.open_misses,
                    max((f for s,f in g.placements), default=0), sum(f for s,f in g.placements), g.placements))]
            for grip in candidates:
                anchors = grip.anchors or (previous.position,)
                if not optimized and grip.anchors:
                    anchors = (min(grip.anchors, key=lambda p: (abs(p-previous.position),p)) if previous.position is not None
                               else max(grip.anchors),)
                orders = [grip.new_strings]
                if len(grip.new_strings) > 1:
                    orders.append(tuple(reversed(grip.new_strings)))
                for position in anchors:
                    for order in orders:
                        state = _advance(previous, grip, tick, position, order, seconds_per_tick, rapid_frets_per_second)
                        examined += 1
                        key = (grip.assignments, position, state.last_fretted_tick, state.last_fretted_release_tick,
                               state.last_fretted_grip, state.last_pick)
                        if key not in next_states or state.cost < next_states[key].cost:
                            next_states[key] = state
        if not next_states:
            raise ValueError(f'No globally compatible fingering at tick {tick}; held notes cannot be reassigned or shortened.')
        states = list(next_states.values())
        if not optimized:
            states = [min(states, key=lambda s: s.cost)]
    return _result(min(states, key=lambda s: s.cost), source, seconds_per_tick, rapid_frets_per_second, optimized, examined)


def optimize_fingering(notes, *, ticks_per_beat=960, tempo_bpm=120, max_fret=24, max_span=4, rapid_frets_per_second=8.0):
    return _solve(notes, ticks_per_beat=ticks_per_beat, tempo_bpm=tempo_bpm, max_fret=max_fret,
                  max_span=max_span, rapid_frets_per_second=rapid_frets_per_second, optimized=True)


def greedy_fingering(notes, *, ticks_per_beat=960, tempo_bpm=120, max_fret=24, max_span=4, rapid_frets_per_second=8.0):
    return _solve(notes, ticks_per_beat=ticks_per_beat, tempo_bpm=tempo_bpm, max_fret=max_fret,
                  max_span=max_span, rapid_frets_per_second=rapid_frets_per_second, optimized=False)
