"""Source-only pedal recurrence, sensitivity and sustained-construction audit.

No new music, model inference or inferred emotional/function labels. Raw patterns
remain private; public output contains aggregate counts only.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from validate_technique_analysis import labels


def pedal_record(candidate, rows):
    anchor = candidate['anchor_midi']
    events = [event for run in candidate['members'] for event in run]
    notes = [[rows[i] for i in event] for event in events]
    starts = [F(event[0]['onset_q']) for event in notes]
    end = max(F(n['onset_q']) + F(n['duration_q']) for event in notes for n in event)
    unit = next((q-starts[0] for q in starts if q > starts[0]), None)
    if unit is None:
        raise ValueError('Pedal candidate lacks distinct attack times')
    # Include durations and simultaneous pitch sets. Do not merge different riffs
    # merely because their anchor/counts agree. Normalization allows time scaling.
    shape = [(str((q-starts[0])/unit), sorted((n['midi']-anchor, str(F(n['duration_q'])/unit)) for n in event)) for q,event in zip(starts,notes)]
    signature = hashlib.sha256(json.dumps(shape, separators=(',', ':')).encode()).hexdigest()
    return dict(anchor=anchor, start_q=str(starts[0]), end_q=str(end), unit_q=str(unit),
                signature=signature, section=notes[0][0]['section_start'],
                error=candidate['relative_period_error'], source_bar=candidate['source_bar'])


def episodes(records):
    """Merge overlapping candidate windows by anchor, not by artistic meaning."""
    by_anchor = defaultdict(list)
    for r in records:
        by_anchor[r['anchor']].append(r)
    out = []
    for anchor, group in by_anchor.items():
        current = None
        for r in sorted(group, key=lambda r: F(r['start_q'])):
            if current is None or F(r['start_q']) >= F(current['end_q']) or r['section'] != current['section']:
                current = dict(anchor=anchor, section=r['section'], start_q=r['start_q'], end_q=r['end_q'], windows=1)
                out.append(current)
            else:
                current['end_q'] = str(max(F(current['end_q']), F(r['end_q'])))
                current['windows'] += 1
    return out


def recurrences(records):
    groups = defaultdict(list)
    for r in records:
        groups[r['signature']].append(r)
    out = []
    for signature, group in groups.items():
        chosen = []
        for r in sorted(group, key=lambda r: F(r['start_q'])):
            if not chosen or F(r['start_q']) >= F(chosen[-1]['end_q']):
                chosen.append(r)
        if len(chosen) > 1:
            base = chosen[0]
            out.append(dict(signature=signature, occurrences=chosen,
                            sections=len({r['section'] for r in chosen}),
                            transposed=any(r['anchor'] != base['anchor'] for r in chosen),
                            time_scaled=any(F(r['unit_q']) != F(base['unit_q']) for r in chosen)))
    return out


def sustained_groups(rows):
    changes = defaultdict(lambda: [[], []]); by_id = {}
    for r in rows:
        start = F(r['onset_q']); end = start + F(r['duration_q'])
        if end <= start:
            continue
        by_id[r['occurrence']] = r
        changes[start][0].append(r['occurrence']); changes[end][1].append(r['occurrence'])
    active = {}; out = []; points = sorted(changes)
    for i, q in enumerate(points[:-1]):
        added, removed = changes[q]
        for key in removed:
            active.pop(key, None)
        for key in added:
            active[key] = by_id[key]
        group = list(active.values()); found = labels(group)
        if found:
            out.append(dict(start_q=str(q), duration_q=str(points[i+1]-q), labels=sorted(found),
                            members=sorted(active), includes_held_notes=any(F(r['onset_q']) < q for r in group),
                            pitch_effects_unresolved=any(r['pitch_effects'] for r in group)))
    return out


def analyze(report):
    counts = Counter(); sensitivity = Counter(); interval_counts = Counter(); duration = defaultdict(F)
    private = []; excluded = 0
    for song in report['songs']:
        for track in song['tracks']:
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:
                excluded += 1; continue
            rows = {r['occurrence']: r for r in track['rows']}
            records = [pedal_record(c, rows) for c in track['pedal_candidates']]
            merged = episodes(records); repeated = recurrences(records)
            intervals = sustained_groups(track['rows'])
            counts['eligible_tracks'] += 1
            counts['raw_pedal_windows'] += len(records); counts['overlap_collapsed_episodes'] += len(merged)
            counts['recurring_nonoverlapping_shapes'] += len(repeated)
            counts['cross_section_shapes'] += sum(g['sections'] > 1 for g in repeated)
            counts['transposed_shapes'] += sum(g['transposed'] for g in repeated)
            counts['time_scaled_shapes'] += sum(g['time_scaled'] for g in repeated)
            for threshold in (F(0), F(1,8), F(1,4), F(1,2)):
                sensitivity[str(threshold)] += sum(F(r['error']) <= threshold for r in records)
            for interval in intervals:
                for label in interval['labels']:
                    interval_counts[label] += 1; duration[label] += F(interval['duration_q'])
                    if interval['includes_held_notes']:
                        interval_counts[label + '_with_held_notes'] += 1
            private.append(dict(song_id=song['song_id'], part_id=track['part_id'], pedal_records=records,
                                episodes=merged, recurrences=repeated, sustained_intervals=intervals))
    public = dict(schema='pattern-robustness-v1', counts=dict(counts), excluded_tracks=excluded,
                  pedal_window_counts_by_relative_period_tolerance=dict(sensitivity),
                  sustained_interval_counts=dict(interval_counts), sustained_duration_q={k:str(v) for k,v in duration.items()},
                  limitations=['Overlapping windows are not independent riffs; episodes are interval unions by anchor/section.',
                               'Recurrence is exact normalized pitch/rhythm/duration equality in nonoverlapping windows within a track, not verified motif identity.',
                               'Sensitivity holds other detector rules fixed; it is not precision/recall.',
                               'Sustained intervals are written pitches, split at every source boundary; effects may alter sounding intervals.',
                               'No phrase, call/response, emotional purpose or artist identity is inferred.'])
    return public, private


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('report',type=Path); p.add_argument('--public',type=Path,required=True); p.add_argument('--private',type=Path,required=True); a=p.parse_args()
    if 'local-artifacts' not in a.private.resolve().parts: p.error('Occurrence evidence must remain private')
    public, private = analyze(json.loads(a.report.read_text(encoding='utf-8')))
    public['input_sha256']=hashlib.sha256(a.report.read_bytes()).hexdigest()
    a.public.write_text(json.dumps(public,indent=2),encoding='utf-8'); a.private.write_text(json.dumps(private,separators=(',',':')),encoding='utf-8')
    print(json.dumps(public))
