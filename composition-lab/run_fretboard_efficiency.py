"""Reproduce the frozen MIDI fingering comparisons and string exports."""
from pathlib import Path
from collections import defaultdict, deque, Counter
import argparse
import hashlib
import json
import time

import mido
from fretboard_efficiency import optimize_fingering, greedy_fingering, DROP_E
from fretboard_strum_efficiency import optimize_strum_fingering

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = 'b86db9f73d1adf8a5552dc81a475437a36b4ae2c'
FIXTURES = (
    ('cfa029a2', 'A · Low response', '6_review_cfa029a287078971a412e05347b5612f6d9ef8c0ea69a1e9b0b58a82fb71aafd.mid'),
    ('da80eca9', 'B · High dyads', '6_review_da80eca929e874d93378b26542ed63cb17be1735f2470a387fe0ad284431535a.mid'),
    ('c5a35486', 'C · MIDI rewrite', '2026-11-15_midi_rewrite.mid'),
)
STRATEGIES = (
    ('greedy', greedy_fingering),
    ('optimized', optimize_fingering),
    ('strumPick', optimize_strum_fingering),
)


def read_source(path):
    midi = mido.MidiFile(path)
    tick, notes = 0, []
    pending = defaultdict(deque)
    tempos = []
    for message in mido.merge_tracks(midi.tracks):
        tick += message.time
        if message.type == 'set_tempo':
            tempos.append((tick, message.tempo))
        elif message.type == 'note_on' and message.velocity > 0:
            note = dict(id=len(notes), pitch=message.note, start_tick=tick, end_tick=None,
                        velocity=message.velocity, channel=message.channel)
            pending[(message.channel, message.note)].append(note)
            notes.append(note)
        elif message.type == 'note_off' or (message.type == 'note_on' and message.velocity == 0):
            queue = pending[(message.channel, message.note)]
            if not queue:
                raise ValueError(f'Unmatched note-off in {path.name}')
            queue.popleft()['end_tick'] = tick
        elif message.type in ('pitchwheel', 'control_change'):
            raise ValueError('This pilot requires explicit treatment of bends/pedal controls before mapping them.')
    if any(note['end_tick'] is None for note in notes):
        raise ValueError('Unterminated MIDI occurrence.')
    if not tempos:
        tempos = [(0, 500000)]
    if any(t != 0 or value != tempos[0][1] for t, value in tempos):
        raise ValueError('Tempo-map conversion is outside this fixed-tempo pilot; input is retained unchanged.')
    tempo = tempos[0][1]
    seconds_per_tick = tempo / 1000000 / midi.ticks_per_beat
    for note in notes:
        note['start_seconds'] = note['start_tick'] * seconds_per_tick
        note['end_seconds'] = note['end_tick'] * seconds_per_tick
    return notes, midi.ticks_per_beat, tempo, tick, seconds_per_tick


def write_string_midi(path, notes, version, ticks_per_beat, tempo, duration_ticks):
    midi = mido.MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    conductor = mido.MidiTrack()
    conductor.append(mido.MetaMessage('track_name', name='Exact source tempo'))
    conductor.append(mido.MetaMessage('set_tempo', tempo=tempo))
    conductor.append(mido.MetaMessage('end_of_track', time=duration_ticks))
    midi.tracks.append(conductor)
    assignment = {a['note_id']: a for a in version['assignments']}
    for string in range(1, 9):
        track = mido.MidiTrack()
        track.append(mido.MetaMessage('track_name', name=f'Drop E string {string}'))
        events = []
        for note in notes:
            if assignment[note['id']]['string_number'] != string:
                continue
            events.append((note['start_tick'], 1, note['id'], mido.Message('note_on', channel=string-1,
                          note=note['pitch'], velocity=note['velocity'])))
            events.append((note['end_tick'], 0, note['id'], mido.Message('note_off', channel=string-1,
                          note=note['pitch'], velocity=0)))
        clock = 0
        for tick, _, _, message in sorted(events, key=lambda e: (e[0], e[1], e[2])):
            track.append(message.copy(time=tick-clock))
            clock = tick
        track.append(mido.MetaMessage('end_of_track', time=duration_ticks-clock))
        midi.tracks.append(track)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def build(source_dir, output, fixture_ids=None, strategy_ids=None, *, rapid_max_gap_seconds=0.25):
    selected = None if fixture_ids is None else set(fixture_ids)
    selected_strategies = None if strategy_ids is None else set(strategy_ids)
    if selected is not None and not selected <= {item[0] for item in FIXTURES}:
        raise ValueError('An unregistered source fixture was requested.')
    if selected_strategies is not None and not selected_strategies <= {item[0] for item in STRATEGIES}:
        raise ValueError('An unregistered fingering strategy was requested.')
    # Targeted additions preserve previously verified mappings and their receipts.
    existing = {}
    if (selected is not None or selected_strategies is not None) and output.exists():
        saved = json.loads(output.read_text(encoding='utf-8'))
        if saved.get('schema') != 'drop-e-fretboard-efficiency/1':
            raise ValueError('The existing output is not a fretboard mapping bundle.')
        existing = {fixture['id']: fixture for fixture in saved['fixtures']}
    result = dict(schema='drop-e-fretboard-efficiency/1', tuning_high_to_low=list(DROP_E), max_fret=24,
        source_commit=SOURCE_COMMIT,
        model=dict(priority_order=['Exact-pitch opens', 'Rapid longitudinal shifts', 'Remaining hand/fretting movement',
                                   'Picking travel and skips', 'Explicit familiar shape fragments'],
                   max_fretted_span=4, max_fretting_contacts=4, rapid_frets_per_second=8,
                   transition_allowance_seconds=0.125,
                   rapid_shift_proxy='Available time = min(attack spacing, released-fretting gap + min(125ms, attack spacing)). '
                       'Open notes/rests count; time holding a fretted chord does not count as free travel. '
                       'Risk sums round(1000 * max(0, distance - 8*time)^2 / max(time, 0.0625)). '
                       'This estimates transition difficulty, not measured hand speed or guaranteed comfort.',
                   picking_proxy='Choose ascending/descending chord sweeps; minimize string travel and skipped-string effort. '
                       'No alternate/economy picking convention is imposed or inferred.',
                   shape_scope='Explicit drop-power and adjacent-string power shapes, CAGED major/common minor chord templates, '
                       'and E/A minor-pentatonic fragments. Complete 2/3-NPS and arpeggio phrase recognition is not claimed.',
                   search='Exact dynamic programming within the finite model. Priority tiers are compared lexicographically.',
                   baseline='Physically admitted per-attack open-first, lowest-fret greedy mapping with nearest reachable anchor.'),
        fixtures=[])
    for fixture_id, label, filename in FIXTURES:
        if selected is not None and fixture_id not in selected:
            if fixture_id not in existing:
                raise ValueError(f'Cannot preserve missing fixture {fixture_id}; generate the complete bundle first.')
            result['fixtures'].append(existing[fixture_id])
            continue
        source_path = source_dir / filename
        notes, ppqn, tempo, duration_ticks, spt = read_source(source_path)
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        fixture = dict(id=fixture_id, label=label, source_filename=filename,
            source_url=f'https://github.com/mtch777/Guitar-Learning/blob/{SOURCE_COMMIT}/generated-midi/{filename}',
            source_sha256=source_hash, ticks_per_beat=ppqn, tempo_bpm=mido.tempo2bpm(tempo),
            duration_ticks=duration_ticks, duration_seconds=duration_ticks*spt, notes=notes, versions=[],
            warnings=['Four sustained chords contain two identical B3 occurrences. Both are retained; '
                      'one copy in each chord must use a fretted string because there is only one open B3 string.',
                      'The source MIDI does not encode an original guitar fingering. Greedy is a comparison algorithm, '
                      'not the original guitarist’s fingering.'])
        if fixture_id == 'c5a35486':
            fixture.update(source_kind='user_upload', source_original_filename='2026-11-15 midi rewrite.mid',
                source_commit=None,
                source_url=f'https://github.com/mtch777/Guitar-Learning/blob/main/tests/fixtures/fretboard-efficiency/{filename}',
                tempo_source='MIDI default; the uploaded file has no explicit tempo event',
                warnings=['No tempo is embedded in this MIDI; playback uses the MIDI default of 120 BPM.',
                          'Held notes retain their original string and fret until release, including notes entering midway through a hold.',
                          'Greedy chooses local open/low-fret preferences only among grips with a feasible held-note continuation; '
                          'it is a comparison algorithm, not an original guitarist fingering.'])
        previous_versions = {}
        if selected_strategies is not None:
            previous = existing.get(fixture_id)
            if previous is None:
                raise ValueError(f'Cannot preserve missing fixture {fixture_id}; generate the complete bundle first.')
            for field in ('source_sha256', 'ticks_per_beat', 'tempo_bpm', 'duration_ticks', 'notes'):
                if previous.get(field) != fixture[field]:
                    raise ValueError(f'Cannot preserve mappings for changed source {fixture_id}: {field} differs.')
            # Keep source provenance, warnings and all unselected version objects
            # exactly as accepted; adding a strategy does not rerun the old ones.
            fixture = dict(previous)
            fixture['versions'] = []
            previous_versions = {version['id']: version for version in previous['versions']}
        source_snapshot = json.dumps(notes, sort_keys=True)
        for strategy_id, algorithm in STRATEGIES:
            if selected_strategies is not None and strategy_id not in selected_strategies:
                if strategy_id in previous_versions:
                    fixture['versions'].append(previous_versions[strategy_id])
                elif strategy_id in ('greedy', 'optimized'):
                    raise ValueError(f'Cannot preserve missing {strategy_id} mapping for {fixture_id}.')
                continue
            start = time.monotonic()
            options = dict(ticks_per_beat=ppqn, tempo_bpm=fixture['tempo_bpm'])
            if strategy_id == 'strumPick':
                options['rapid_max_gap_seconds'] = rapid_max_gap_seconds
            version = algorithm(notes, **options)
            if version['id'] != strategy_id:
                raise AssertionError(f'Unexpected strategy identity: {version["id"]}.')
            version['runtime_seconds'] = round(time.monotonic()-start, 4)
            export_name = f'{fixture_id}_{version["id"]}_strings.mid'
            export_path = ROOT / 'public' / 'fretboard-efficiency' / export_name
            write_string_midi(export_path, notes, version, ppqn, tempo, duration_ticks)
            version['midi_path'] = f'fretboard-efficiency/{export_name}'
            fixture['versions'].append(version)
            print(json.dumps(dict(fixture=fixture_id, version=version['id'], runtime_seconds=version['runtime_seconds'],
                                  metrics=version['metrics'])), flush=True)
        for strategy_id, version in previous_versions.items():
            if strategy_id not in {item[0] for item in STRATEGIES}:
                fixture['versions'].append(version)
        if json.dumps(notes, sort_keys=True) != source_snapshot:
            raise AssertionError('An optimizer mutated original note evidence.')
        result['fixtures'].append(fixture)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, default=ROOT/'tests'/'fixtures'/'fretboard-efficiency')
    parser.add_argument('--output', type=Path, default=ROOT/'public'/'data'/'fretboard-efficiency-fixtures.json')
    parser.add_argument('--fixture', action='append', choices=[item[0] for item in FIXTURES],
                        help='Regenerate only these fixtures, preserving other entries from the existing output.')
    parser.add_argument('--strategy', action='append', choices=[item[0] for item in STRATEGIES],
                        help='Regenerate only these strategies, preserving other version objects exactly.')
    parser.add_argument('--rapid-max-gap-seconds', type=float, default=0.25,
                        help='Largest source onset gap counted as rapid by Strum + pick (default: 0.25).')
    args = parser.parse_args()
    build(args.source_dir, args.output, args.fixture, args.strategy,
          rapid_max_gap_seconds=args.rapid_max_gap_seconds)
