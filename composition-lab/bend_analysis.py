"""Deterministic GP7 bend queries; standard library only, no model calls."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import json
import importlib
from pathlib import Path
import statistics
import sys
import types
from xml.etree import ElementTree as ET

# Namespace the historical extractor: root extract.py has a different schema.
_package = types.ModuleType('_bend_checkpoint')
_package.__path__ = [str(Path(__file__).parent / 'checkpoints' / '2026-10-14')]
sys.modules.setdefault('_bend_checkpoint', _package)
extract_score = importlib.import_module('_bend_checkpoint.extract').extract_score
validate_events = importlib.import_module('_bend_checkpoint.music_events').validate_events


def bend_shape(xml):
    root = ET.fromstring(xml)
    props = {p.get('name'): p for p in root.findall('./Properties/Property')}
    if 'Bended' not in props or props['Bended'].find('Enable') is None:
        return None
    def value(name, default):
        node = props.get(name)
        text = node.findtext('Float') if node is not None else None
        return F(text) if text is not None else default
    points = [(value('BendOriginOffset', F(0)), value('BendOriginValue', F(0)))]
    mid = value('BendMiddleValue', F(0))
    if mid:
        points += [(value('BendMiddleOffset1', F(50)), mid),
                   (value('BendMiddleOffset2', F(50)), mid)]
    points += [(value('BendDestinationOffset', F(100)), value('BendDestinationValue', F(0)))]
    points = sorted(set(points))
    vals = [v for _, v in points]
    directions = {1 if b > a else -1 for a, b in zip(vals, vals[1:]) if b != a}
    kind = ('rise-and-fall' if directions == {1, -1} else
            'rise' if directions == {1} else 'fall' if directions == {-1} else 'constant')
    return {'points': [{'offset_fraction': str(x / 100), 'semitones': str(y / 50)} for x, y in points],
            'peak_semitones': str(max(vals) / 50), 'excursion_semitones': str((max(vals)-min(vals))/50),
            'start_semitones': str(vals[0]/50), 'end_semitones': str(vals[-1]/50),
            'shape': kind, 'prebent': vals[0] != 0,
            'changing_segments': [{'span_fraction': str((x2-x1)/100),
                                   'change_semitones': str((v2-v1)/50)}
                                  for (x1,v1),(x2,v2) in zip(points, points[1:]) if v1 != v2]}


def ratio(n, d):
    return {'numerator': n, 'denominator': d, 'percent': round(100*n/d, 3) if d else None}


def median(values):
    return str(statistics.median(values)) if values else None


def tie_chains(rows):
    """Link explicit ties only, by exact lane/string/pitch/end time; never guess."""
    chains = []
    pending = defaultdict(list)
    unresolved = []
    for r in sorted(rows, key=lambda r: (F(r['onset_q']), r['occurrence'])):
        key = (r['voice'], r['string'], r['midi'], F(r['onset_q']))
        candidates = pending.pop(key, []) if r['tie_destination'] else []
        if len(candidates) == 1:
            chain = candidates[0]
            chain.append(r)
        else:
            if r['tie_destination']:
                unresolved.append(r['occurrence'])
            chain = [r]
            chains.append(chain)
        if r['tie_origin']:
            endkey = (r['voice'], r['string'], r['midi'], F(r['onset_q'])+F(r['duration_q']))
            pending[endkey].append(chain)
    return chains, unresolved, sum(len(v) for v in pending.values())


def chain_summary(chains):
    valid = [c for c in chains if not c[0]['tie_destination']]
    bent = [c for c in valid if any(r['bend'] for r in c)]
    def length(c):
        return sum((F(r['duration_q']) for r in c), F(0))
    return {'bend_anywhere_in_sustain_rate': ratio(len(bent),len(valid)),
            'median_bent_sustain_q': median([length(c) for c in bent]),
            'median_nonbent_sustain_q': median([length(c) for c in valid if not any(r['bend'] for r in c)]),
            'bend_sustain_note_time_share': ratio(float(sum(map(length,bent),F(0))),
                                                 float(sum(map(length,valid),F(0)))),
            'bent_sustain_peak_semitones': dict(Counter(str(max(F(r['bend']['peak_semitones']) for r in c if r['bend'])) for c in bent))}


def conditional_tables(rows):
    """Each grouping retains its own denominator, including zero-bend groups."""
    result = {}
    for field in ('string', 'fret', 'midi', 'local_onset_q', 'duration_q'):
        grouped = defaultdict(list)
        for r in rows:
            if not r['tie_destination']:
                grouped[str(r[field])].append(r)
        result[field] = {key: ratio(sum(bool(r['bend']) for r in values),len(values))
                         for key,values in sorted(grouped.items())}
    return result


def summary(rows):
    attacks = [r for r in rows if not r['tie_destination']]
    bends = [r for r in rows if r['bend']]
    ba = [r for r in attacks if r['bend']]
    duration = sum((F(r['duration_q']) for r in rows), F(0))
    bend_duration = sum((F(r['duration_q']) for r in bends), F(0))
    return {'note_occurrences': len(rows), 'attacks': len(attacks),
            'bend_occurrence_rate': ratio(len(bends),len(rows)),
            'bend_attack_rate': ratio(len(ba),len(attacks)),
            'bend_notated_note_time_share': ratio(float(bend_duration),float(duration)),
            'median_bend_segment_q': median([F(r['duration_q']) for r in bends]),
            'median_nonbend_segment_q': median([F(r['duration_q']) for r in rows if not r['bend']]),
            'peak_semitones': dict(Counter(r['bend']['peak_semitones'] for r in bends)),
            'shapes': dict(Counter(r['bend']['shape'] for r in bends)),
            'prebent_occurrences': sum(r['bend']['prebent'] for r in bends),
            'bend_occurrences_with_vibrato': sum(r['vibrato'] for r in bends)}


def analyze(score):
    tracks = []
    allrows = []
    for track in score['tracks']:
        rows = []
        section = '(unlabeled)'
        section_start = 1
        for measure in track['measures']:
            if measure['section']:
                section = measure['section']
                section_start = measure['number']
            for vi, voice in enumerate(measure['voices']):
                for event in voice:
                    for ni, note in enumerate(event['notes']):
                        root = ET.fromstring(note['note_xml'])
                        bend = bend_shape(note['note_xml'])
                        tie = note['tie'] or {}
                        row = {'occurrence': f"{track['index']}:{measure['number']}:{vi}:{event['beat_id']}:{ni}",
                               'note_id': note['note_id'], 'bar': measure['number'], 'voice': vi,
                               'section': section, 'section_start_bar': section_start,
                               'onset_q': note['onset_q'], 'duration_q': note['duration_q'],
                               'local_onset_q': event['local_onset_q'],
                               'string': note['string'], 'fret': note['fret'], 'midi': note['midi'],
                               'grace_type': note['grace_type'],
                               'tie_destination': tie.get('destination') == 'true',
                               'tie_origin': tie.get('origin') == 'true',
                               'vibrato': root.find('Vibrato') is not None or any('Vibrato' in p for p in note['property_names']) or 'Vibrato' in event['beat_tags'],
                               'bend': bend}
                        rows.append(row)
        lanes = defaultdict(list)
        for row in rows:
            lanes[row['voice']].append(row)
        relations = []
        for voice, lane in lanes.items():
            groups = defaultdict(list)
            for r in lane:
                groups[F(r['onset_q'])].append(r)
            onsets = sorted(groups)
            for i, onset in enumerate(onsets):
                group = groups[onset]
                prev = groups[onsets[i-1]] if i else []
                nxt = groups[onsets[i+1]] if i+1 < len(onsets) else []
                for r in group:
                    if r['bend']:
                        relations.append({'occurrence': r['occurrence'],
                                          'preceding_group_gap_q': str(max(F(0),onset-max(F(p['onset_q'])+F(p['duration_q']) for p in prev))) if prev else None,
                                          'next_onset_delta_q': str(onsets[i+1]-onset) if nxt else None,
                                          'gap_to_next_group_q': str(max(F(0),onsets[i+1]-onset-F(r['duration_q']))) if nxt else None,
                                          'previous_group_midi': [p['midi'] for p in prev],
                                          'next_group_midi': [p['midi'] for p in nxt]})
        sections = defaultdict(list)
        for r in rows:
            sections[(r['section_start_bar'], r['section'])].append(r)
        probes = []
        lane_groups = []
        for lane in lanes.values():
            grouped = defaultdict(list)
            for r in lane:
                grouped[F(r['onset_q'])].append(r)
            lane_groups.append(grouped)
        for threshold in (F(1,2), F(1), F(2)):
            endings = []
            for grouped in lane_groups:
                onsets = sorted(grouped)
                for i,onset in enumerate(onsets):
                    group = grouped[onset]
                    end = max(onset+F(r['duration_q']) for r in group)
                    # Last event is excluded: score/track end is not evidence of a rest.
                    if i+1 < len(onsets) and onsets[i+1]-end >= threshold:
                        endings.extend(r for r in group if not r['tie_destination'])
            probes.append({'rest_gap_threshold_q': str(threshold),
                           'bend_rate_at_pre_gap_attacks': ratio(sum(bool(r['bend']) for r in endings), len(endings))})
        chains, unresolved, dangling = tie_chains(rows)
        tracks.append({'index': track['index'], 'name': track['name'], 'program': track['program'],
                       'is_percussion': track['is_percussion'], **summary(rows),
                       'sustains': chain_summary(chains), 'unresolved_tie_destinations': unresolved,
                       'unmatched_tie_origins': dangling,
                       'bend_chains': [[r['occurrence'] for r in c] for c in chains if any(r['bend'] for r in c)],
                       'conditional_attack_rates': conditional_tables(rows),
                       'sections': [{'start_bar': k[0], 'label': k[1], **summary(v)} for k,v in sections.items()],
                       'rest_gap_sensitivity': probes, 'bend_contexts': relations,
                       'occurrences': rows})
        allrows.extend(rows)
    return {'schema':'gp-bend-analysis-v1', 'source_sha256': score['source_sha256'],
            'source_file':score['source_file'], 'measure_count':score['measure_count'],
            'duration_q':score['duration_q'], 'voice_meter_discrepancies':len(validate_events(score)),
            'method':'Deterministic GPIF queries; no AI/model calls or inferred musical roles.',
            'scope':'Written score order; repeats not unfolded; percentages count annotated note events, not audio.',
            'limitations':['One song cannot estimate artist prevalence.',
                           'Section labels are source annotations; rest-gap groups are not verified phrases.',
                           'No emotional purpose, harmonic resolution, or performance speed inferred.',
                           'Note-time sums count simultaneous notes separately; not wall-clock occupancy.',
                           'Duration statistics describe segments, not merged tied sustains.',
                           'Technique annotation completeness is unknown.'],
            'all_tracks': summary(allrows), 'tracks': tracks}


def markdown_report(report):
    lines = ['# Scripted bend measurements', '',
             f"Source: `{report['source_file']}`; SHA256 `{report['source_sha256']}`.",
             f"{report['measure_count']} written bars; {len(report['tracks'])} tracks; "
             f"{report['voice_meter_discrepancies']} voice/meter discrepancies.", '',
             'No model inference. Track names and section labels are supplied by the score.', '',
             '| Track | Attacks | Sustains containing bends | Rate | Median bent / unbent duration (quarter beats) |',
             '|---|---:|---:|---:|---|']
    for t in report['tracks']:
        s = t['sustains']; rate = s['bend_anywhere_in_sustain_rate']
        lines.append(f"| {t['index']}: {t['name'].replace('|','/')} | {t['attacks']} | {rate['numerator']} | "
                     f"{rate['percent']}% | {s['median_bent_sustain_q']} / {s['median_nonbent_sustain_q']} |")
    for t in report['tracks']:
        if not t['bend_occurrence_rate']['numerator']:
            continue
        lines += ['', f"## Track {t['index']}: {t['name']}", '',
                  f"Peak displacement per bent sustain (semitones → count): {t['sustains']['bent_sustain_peak_semitones']}",
                  f"Encoded segment shapes: {t['shapes']}",
                  f"Unresolved tie destinations: {len(t['unresolved_tie_destinations'])}; unmatched origins: {t['unmatched_tie_origins']}.", '',
                  '| Section start bar | Source label | Bend-bearing attacks / attacks |', '|---:|---|---:|']
        for s in t['sections']:
            r = s['bend_attack_rate']
            lines.append(f"| {s['start_bar']} | {s['label']} | {r['numerator']} / {r['denominator']} ({r['percent']}%) |")
    lines += ['', '## Limits', ''] + [f'- {x}' for x in report['limitations']]
    lines += ['- Complete per-note provenance, curves, neighboring groups, conditional pitch/string/fret/timing rates and rest-gap sensitivity tables are in the accompanying JSON.',
              '- A positive starting bend on a tied segment is not counted as a newly performed pre-bend technique.',
              '- Constant or zero curves are retained as encoded; presence of a bend flag does not guarantee audible movement.']
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(extract_score(args.source))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    args.output.with_suffix('.md').write_text(markdown_report(result),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='tracks'},indent=2))
