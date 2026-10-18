"""Independent raw-readback and notation-rule audit; never a musical accuracy score.

Does not import production detectors. Tests every eligible attack group, including
negative groups, and keeps source-located review samples private.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def labels(notes):
    if len(notes) < 2 or any(n['midi'] is None or n['string'] is None for n in notes):
        return set()
    if len({n['string'] for n in notes}) != len(notes):
        return set()
    pitches = sorted(n['midi'] for n in notes)
    intervals = {(p - pitches[0]) % 12 for p in pitches}
    out = set()
    if len(notes) == 2:
        out.add('double_stop')
        if pitches[-1] - pitches[0] == 1:
            out.add('close_interval_texture')
    if intervals == {0, 7}:
        out.add('power_chord')
    elif {0, 7}.issubset(intervals) and len(intervals) == 3:
        out.add('extended_power_chord')
    return out


def audit(report, corpus):
    counts = Counter(); errors = []; matrices = defaultdict(Counter)
    samples = defaultdict(list)

    def check(ok, kind, location):
        counts[kind + '_checked'] += 1
        if not ok:
            counts[kind + '_failed'] += 1
            if len(errors) < 100:
                errors.append(dict(kind=kind, location=location))

    def sample(kind, location, details):
        # Deterministic per-stratum coverage, rather than first-song-only examples.
        bucket = samples[kind]
        candidate = dict(location=location, details=details)
        candidate['rank'] = hashlib.sha256(json.dumps(candidate, sort_keys=True).encode()).hexdigest()
        bucket.append(candidate)
        bucket.sort(key=lambda x: x['rank'])
        del bucket[12:]

    for song in report['songs']:
        folder = corpus / str(song['song_id'])
        for track in song['tracks']:
            part = json.loads((folder / f"track-{track['part_id']}.json").read_text(encoding='utf-8-sig'))
            raw = {}
            for bar, measure in enumerate(part.get('measures', []), 1):
                for voice, v in enumerate(measure.get('voices', [])):
                    for beat, b in enumerate(v.get('beats', [])):
                        for note, n in enumerate(b.get('notes', [])):
                            if not n.get('rest'):
                                raw[f"{part.get('partId', 0)}:{bar}:{voice}:{beat}:{note}"] = (n, b)
            rows = track['rows'] + track['grace_rows']
            observed = {r['occurrence'] for r in rows}
            loc = [song['song_id'], track['part_id']]
            check(len(rows) == len(observed) and observed == set(raw), 'occurrence_coverage', loc)
            by_id = {r['occurrence']: r for r in rows}
            attacks = defaultdict(list)
            for r in rows:
                location = loc + [r['occurrence']]
                if r['occurrence'] not in raw:
                    continue
                n, b = raw[r['occurrence']]
                check(r['raw_note'] == n, 'raw_note_preserved', location)
                check(r['string'] == n.get('string') and r['fret'] == n.get('fret') and r['tie_destination'] == bool(n.get('tie')), 'identity_fields', location)
                check(F(r['duration_q']) == F(*b['duration']) * 4, 'duration', location)
                string = n.get('string'); fret = n.get('fret'); tuning = part.get('tuning') or []
                expected = None
                if not n.get('dead') and isinstance(string, int) and 0 <= string < len(tuning) and isinstance(fret, (int, float)):
                    expected = tuning[string] + fret + (part.get('capo') or 0)
                check(r['midi'] == expected, 'written_pitch', location)
                if not b.get('graceNote') and not n.get('tie'):
                    attacks[r['onset_q']].append(dict(midi=expected, string=string))
                for key in ('bend', 'vibrato', 'hp'):
                    sample(key + ('_marked' if n.get(key) else '_unmarked'), location, dict(bar=r['bar'], fret=fret, duration_q=r['duration_q']))
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:
                counts['tracks_excluded_from_temporal_rules'] += 1
                continue
            actual = {g['onset_q']: set(g['labels']) for g in track['coattack_groups']}
            for onset, notes in attacks.items():
                expected = labels(notes)
                got = actual.get(onset, set())
                location = loc + [onset]
                check(got == expected, 'coattack_rule', location)
                for label in ('double_stop', 'close_interval_texture', 'power_chord', 'extended_power_chord'):
                    state = ('positive' if label in expected else 'negative')
                    matrices[label][state + ('_agree' if (label in expected) == (label in got) else '_disagree')] += 1
                    sample(label + '_' + state, location, dict(notes=notes, expected=sorted(expected), observed=sorted(got)))
            check(set(actual).issubset(attacks), 'no_extra_attack_groups', loc)
            for pair in track['hopo_transition_candidates']:
                a, b = by_id[pair['origin']], by_id[pair['destination']]
                check(a['string'] == b['string'] and a['voice'] == b['voice'] and bool(raw[a['occurrence']][0].get('hp')) and not b['tie_destination'] and a['fret'] != b['fret'], 'hp_pair_invariants', loc + [pair['origin']])
    public = dict(schema='technique-analysis-validation-v1', entries=len(report['songs']), checks=dict(counts),
                  notation_rule_agreement={k: dict(v) for k, v in matrices.items()},
                  failed_checks=sum(v for k, v in counts.items() if k.endswith('_failed')),
                  review_strata={k: len(v) for k, v in samples.items()},
                  limitations=['Rule agreement is not independently labeled musical precision/recall.',
                               'Raw readback verifies preservation, not the transcription or performed technique.',
                               'Pedal function, phrase boundaries, resolution, feel and physical execution need independent adjudication.',
                               'No human judgment or model inference is used by this audit.'])
    return public, dict(errors=errors, samples=dict(samples), human_labels=[])


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('corpus', type=Path); p.add_argument('--report', type=Path, required=True)
    p.add_argument('--public', type=Path, required=True); p.add_argument('--private', type=Path, required=True)
    a = p.parse_args()
    if 'local-artifacts' not in a.private.resolve().parts:
        p.error('Source evidence must remain private')
    report = json.loads(a.report.read_text(encoding='utf-8'))
    public, private = audit(report, a.corpus)
    public['analyzer_report_sha256'] = hashlib.sha256(a.report.read_bytes()).hexdigest()
    public['validator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    a.public.write_text(json.dumps(public, indent=2), encoding='utf-8')
    a.private.write_text(json.dumps(private, indent=2), encoding='utf-8')
    print(json.dumps(public))
    raise SystemExit(bool(public['failed_checks']))
