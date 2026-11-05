"""Aggregate complete existing gesture candidates into evidence-backed UI presets.

No segmentation, classification, generation, cropping, source edits, or score export.
Run: python -B -X utf8 composition-lab/analyze_riff_section_presets.py
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'composition-lab/local-artifacts/fretboard-study-2026-11-04'
ARTISTS = ('Invent Animate', 'Currents', 'ERRA')
STYLE_TAGS = {'arpeggio': 'arpeggio_style', 'chordal': 'harmonic_response',
              'melodic': 'melodic_phrase', 'pedal': 'pedal',
              'rhythmic': 'rhythmic_phrase', 'other': 'other_riff_construction'}
LABELS = {'arpeggio': 'Arpeggio', 'chordal': 'Chordal', 'melodic': 'Melodic',
          'pedal': 'Pedal', 'rhythmic': 'Rhythmic', 'other': 'Other'}
FOCUS_LABELS = {'single': 'Single notes', 'interval': 'Intervals', 'triad': 'Triads',
                'chord': 'Chords', 'mixed': 'Mixed'}
# Explicitly labelled adaptation, not an automatic fuzzy-title merge.
SONG_ALIASES = {('Invent Animate', 722881): 460099}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def song_identity(artist, song_id):
    return artist, SONG_ALIASES.get((artist, song_id), song_id)


def focus(counts):
    c = Counter('single' if n == 1 else 'interval' if n == 2 else
                'triad' if n == 3 else 'chord' for n in counts if n > 0)
    return next((k for k, n in c.items() if n * 2 > sum(c.values())),
                'mixed' if c else 'none')


def stats(values):
    values = [F(v) for v in values]
    if not values:
        return None
    return {'mean_q': str(sum(values) / len(values)), 'median_q': str(median(values)),
            'min_q': str(min(values)), 'max_q': str(max(values))}


def support(rows):
    return {'distinct_songs': len({r['song'] for r in rows}),
            'captures': len({c for r in rows for c in r['captures']}),
            'occurrences': len(rows)}


def presence(rows, field):
    result = {}
    for value in sorted({v for r in rows for v in r[field]}):
        selected = [r for r in rows if value in r[field]]
        result[value] = {'occurrences': len(selected),
                         'distinct_songs': len({r['song'] for r in selected})}
    return result


def summarize(rows):
    lengths = defaultdict(list)
    song_lengths = defaultdict(list)
    for row in rows:
        lengths[row['length']].append(row)
        song_lengths[row['song']].append(row['length'])
    result = {**support(rows), 'duration_histogram': [
        {'length_q': str(length), 'distinct_songs': len({r['song'] for r in group}),
         'occurrences': len(group)} for length, group in sorted(lengths.items())],
        'duration': stats(r['length'] for r in rows),
        'song_balanced_mean_q': str(sum(sum(v)/len(v) for v in song_lengths.values()) /
                                    len(song_lengths)) if song_lengths else None}
    if rows and 'metrics' in rows[0]:
        result.update(metrics={key: stats(r['metrics'][key] for r in rows)
                               for key in rows[0]['metrics']},
            technique_presence=presence(rows, 'techniques'),
            grammar_kind_presence=presence(rows, 'kinds'),
            focus_presence=presence(rows, 'focus_set'),
            shape_usage={
                'no_reported_shape_occurrences': sum(r['metrics']['linked_shape_count'] == 0 for r in rows),
                'multi_shape_occurrences': sum(r['metrics']['linked_shape_count'] > 1 for r in rows),
                'orientation_presence': presence(rows, 'orientations'),
                'range_presence': presence(rows, 'ranges')})
    return result


def rows_from_library(library):
    unique, captures = {}, []
    input_count = 0
    for reference in library['references']:
        prov = reference['provenance']
        artist = prov['artist']
        if artist not in ARTISTS:
            raise ValueError('Unexpected artist in frozen reference library')
        song = song_identity(artist, prov['song_id'])
        start, end = map(F, reference['scope']['passage_q'])
        captures.append({'song': song, 'artist': artist, 'captures': {reference['id']},
                         'length': end-start})
        observations = {o['id']: o for o in reference['rhythm_observations']}
        shapes = {s['id']: s for s in reference['shapes']}
        event_map = {e['index']: e for e in reference['events']}
        styles = {style for style, tag in STYLE_TAGS.items()
                  if tag in reference['labels']['type_ids']}
        for gesture in reference['grammar']['gestures']:
            input_count += 1
            observation = observations[gesture['rhythm_observation_id']]
            assert observation['unit_kind'] == 'existing_grammar_candidate_gesture'
            pattern = library['rhythm_patterns'][observation['rhythm_pattern_id']]
            length = F(gesture['end_q']) - F(gesture['start_q'])
            assert length == F(pattern['duration_q']) and length > 0
            events = [event_map[i] for i in gesture['event_indices']]
            members = [m for e in events for m in e['members']]
            actual_focus = focus(len(e['members']) for e in events)
            key = (artist, prov['song_id'], prov['revision_id'], prov['part_id'],
                   gesture['start_q'], gesture['end_q'], tuple(gesture['occurrence_ids']))
            shape_ids = {s if isinstance(s, str) else s['shape_id']
                         for s in gesture['shape_refs']}
            linked_shapes = [shapes[s] for s in shape_ids]
            empty = sum(F(b)-F(a) for a, b in pattern['written_note_empty_spans_rel_q'])
            assert 0 <= empty <= length
            row = {'song': song, 'artist': artist, 'captures': {reference['id']},
                'length': length, 'styles': styles.copy(), 'focus': actual_focus,
                'focus_set': {actual_focus}, 'kinds': {gesture['kind']},
                'techniques': {effect for m in members for effect in m.get('effects', [])},
                'orientations': {s['orientation'] for s in linked_shapes},
                'ranges': {s['range_class'] for s in linked_shapes},
                'metrics': {'attacks_per_quarter': F(len(events))/length,
                    'written_empty_fraction': empty/length,
                    'attack_count': F(len(events)), 'member_count': F(len(members)),
                    'linked_shape_count': F(len(shape_ids)),
                    'target_open_member_fraction': F(sum(m.get('target_fret') == 0 for m in members), len(members)) if members else F(0)}}
            if key in unique:
                previous = unique[key]
                assert previous['length'] == length and previous['focus'] == actual_focus
                previous['captures'].add(reference['id'])
                previous['styles'].update(styles)
            else:
                unique[key] = row
    return list(unique.values()), captures, input_count


def recommend(histogram):
    """UI recommendation: observed supported length, else explicit nearest mapping."""
    offered = [F(4), F(8), F(16)]
    exact = [r for r in histogram if F(r['length_q']) in offered]
    candidates = exact or histogram
    if not candidates:
        return None
    chosen = min(candidates, key=lambda r: (-r['distinct_songs'], F(r['length_q'])))
    observed = F(chosen['length_q'])
    output = observed if exact else min(offered, key=lambda q: (abs(q-observed), q))
    return {'length_q': str(output), 'observed_length_q': str(observed),
            'method': 'observed_supported_length' if exact else 'nearest_supported_builder_length',
            'observed_length_song_support': chosen['distinct_songs'],
            'not_average_section_length': True}


def self_checks():
    # Same song's versions/occurrences never become additional song votes.
    rows = [{'song': ('Invent Animate', 460099), 'captures': {'a'}, 'length': F(1, 3)},
            {'song': song_identity('Invent Animate', 722881), 'captures': {'b'}, 'length': F(1, 3)}]
    check = summarize(rows)
    assert check['distinct_songs'] == 1 and check['occurrences'] == 2
    assert check['duration_histogram'][0] == {'length_q': '1/3', 'distinct_songs': 1, 'occurrences': 2}
    assert focus([2, 2, 1]) == 'interval' and focus([1, 2]) == 'mixed'
    assert stats([F(1, 3), F(1, 2)])['mean_q'] == '5/12'
    assert recommend([{'length_q': '1/2', 'distinct_songs': 4}])['method'] == 'nearest_supported_builder_length'
    assert recommend([{'length_q': '8', 'distinct_songs': 2}, {'length_q': '4', 'distinct_songs': 2}])['length_q'] == '4'
    assert recommend([]) is None


def build(library_path, pack_path):
    before = {str(p): sha(p) for p in (library_path, pack_path)}
    library = json.loads(library_path.read_bytes())
    raw_pack = pack_path.read_bytes()
    pack = json.loads(gzip.decompress(raw_pack) if pack_path.suffix == '.gz' else raw_pack)
    assert pack['source_library_sha256'] == before[str(library_path)]
    rows, captures, input_count = rows_from_library(library)
    presets = []
    for style in STYLE_TAGS:
        for selected_focus in FOCUS_LABELS:
            selected = [r for r in rows if style in r['styles'] and r['focus'] == selected_focus]
            if not selected:
                continue
            evidence = summarize(selected)
            availability = {artist: len({t['id'] for t in pack['templates'].values()
                if t['focus'] == selected_focus and any(s['artist'] == artist and style in s['style_ids']
                                                       for s in t['support'])}) for artist in ARTISTS}
            presets.append({'id': style+'-'+selected_focus,
                'label': LABELS[style]+' · '+FOCUS_LABELS[selected_focus],
                'style': style, 'focus': selected_focus, 'support': support(selected),
                'evidence': evidence, 'recommendation': recommend(evidence['duration_histogram']),
                'by_artist': {a: summarize([r for r in selected if r['artist'] == a]) for a in ARTISTS},
                'pack_rhythm_template_counts_by_artist': availability,
                'style_scope': 'inherited_containing_riff',
                'length_scope': 'existing_grammar_candidate_gesture_not_verified_phrase',
                'traits_are_descriptive_not_enforced': True})
    presets.sort(key=lambda p: (-p['support']['distinct_songs'], p['id']))
    out = {'schema': 'riff-section-presets/1', 'artists': list(ARTISTS),
        'provenance': {'source_library_sha256': before[str(library_path)],
            'pattern_pack_file_sha256': before[str(pack_path)],
            'pattern_pack_content_sha256': pack['content_sha256'], 'script_sha256': sha(__file__)},
        'denominator': {'reference_captures': len(library['references']),
            'source_song_ids': len({(r['provenance']['artist'], r['provenance']['song_id']) for r in library['references']}),
            'canonical_song_identities': len({r['song'] for r in rows}),
            'input_gesture_observations': input_count, 'deduplicated_gesture_occurrences': len(rows),
            'duplicate_source_gesture_observations_removed': input_count-len(rows),
            'gestures_without_positive_inherited_style': sum(not r['styles'] for r in rows)},
        'units': {'gestures': summarize(rows), 'whole_riff_captures': summarize(captures),
            'by_artist': {a: {'gestures': summarize([r for r in rows if r['artist'] == a]),
                             'whole_riff_captures': summarize([r for r in captures if r['artist'] == a])}
                          for a in ARTISTS}},
        'presets': presets,
        'method': {'unit': 'Complete existing grammar candidate gesture, including units longer than eight quarter notes; no new segmentation.',
            'song_votes': 'One vote per canonical artist/song identity within each group or exact duration; occurrences are separate. Artist populations add without balancing.',
            'duplicate_observations': 'Identical source song/revision/part, bounds and occurrence membership are merged across captures.',
            'song_aliases': [{'artist': 'Invent Animate', 'song_ids': [460099, 722881],
                'reason': 'Cloud Cascade and explicitly labelled Cloud Cascade (6-string adapted riff). No fuzzy title matching.'}],
            'rank': 'Distinct-song support within selected artists, descending; ID breaks ties. Multi-label groups overlap and must not be added as total songs.',
            'length': 'Prefer exact observed 4/8/16q duration with most distinct-song support; otherwise map most-supported observed duration to nearest offered length. Ties choose shorter. This is a builder recommendation, not an average natural section.',
            'metrics': 'Observation-weighted descriptive summaries; song_balanced_mean_q gives each song equal total weight. Written empty time includes held occupancy, not acoustic silence.',
            'source_focus': 'More than half actual attack groups determines single/interval/triad/chord; otherwise mixed. Duplicate pitch members count separately.',
            'shape_scope': 'Existing reported Drop E shape links; open strings and unreported single-contact contexts are not shapes.'},
        'limits': ['Candidate gestures are not human-verified phrase or section boundaries.',
            'Styles are inherited whole-capture annotations, not independently classified local gestures.',
            'Existing fixed bar windows and maximum-eight-quarter-note package limits do not determine measured lengths.',
            'Known explicit adaptation is one song vote; unrecognized title variants may remain separate identities.',
            'Preset changes only style, focus and builder length. Traits do not become new engine controls.',
            'Current artist/mode/template availability and bounded realization still apply; support is not a guarantee of generation or listening quality.']}
    assert before == {str(p): sha(p) for p in (library_path, pack_path)}
    return out


def report(data):
    d = data['denominator'];g = data['units']['gestures'];c = data['units']['whole_riff_captures']
    lines = ['# Observed riff-unit evidence and builder presets', '',
        'Command: `python -B -X utf8 composition-lab/analyze_riff_section_presets.py`', '',
        f"Frozen input: {d['reference_captures']} captures, {d['source_song_ids']} source song IDs, {d['canonical_song_identities']} canonical song identities.",
        f"{d['input_gesture_observations']} grammar observations -> {d['deduplicated_gesture_occurrences']} distinct source gesture windows; {d['gestures_without_positive_inherited_style']} lack any positive inherited style.", '',
        f"Complete gesture proxy: median {g['duration']['median_q']}q, mean {g['duration']['mean_q']}q, song-balanced mean {g['song_balanced_mean_q']}q, range {g['duration']['min_q']}–{g['duration']['max_q']}q.",
        f"Whole riff captures, separately: median {c['duration']['median_q']}q, mean {c['duration']['mean_q']}q, range {c['duration']['min_q']}–{c['duration']['max_q']}q.", '',
        'These are different units. Neither proves an average natural musical section. Bar windows and the short-template export limit are excluded from gesture-length estimation.', '',
        '| Preset | Songs | Occurrences | Recommended q | Length basis | Executable template count IA/Currents/ERRA |',
        '|---|---:|---:|---:|---|---|']
    for p in data['presets']:
        r = p['recommendation'];counts = '/'.join(str(p['pack_rhythm_template_counts_by_artist'][a]) for a in ARTISTS)
        lines.append(f"| {p['label']} | {p['support']['distinct_songs']} | {p['support']['occurrences']} | {r['length_q']} | {r['method']}; observed {r['observed_length_q']}q, {r['observed_length_song_support']} songs | {counts} |")
    lines += ['', 'Local grammar kinds, independent of inherited style:', '',
        *[f"- {k}: {v['occurrences']} occurrences, {v['distinct_songs']} songs."
          for k, v in g['grammar_kind_presence'].items()], '',
        'Validation: internal counterexamples pass; immutable library and pack hashes rechecked. No source scores, timelines, note sequences or private annotations are published.', '',
        'The public aggregate includes all measured groups, including those with zero packaged templates. The UI must report unavailable stronger groups rather than silently substituting weaker ones.', '',
        'Presets only set style, focus and length. Density, gaps, techniques and shapes describe reference evidence; they are not added controls or promises of generated behavior.', '',
        'Source library SHA-256: '+data['provenance']['source_library_sha256'],
        'Pack content SHA-256: '+data['provenance']['pattern_pack_content_sha256'], '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=STUDY/'reference-library-001/REFERENCE_LIBRARY.json')
    parser.add_argument('--pack', type=Path, default=ROOT/'public/riff-builder/pattern-pack.json.gz')
    parser.add_argument('--output', type=Path, default=ROOT/'public/riff-builder/section-presets.json')
    parser.add_argument('--report', type=Path, default=STUDY/'riff-engine-001/SECTION_PRESETS_REPORT.md')
    args = parser.parse_args();self_checks();data = build(args.library,args.pack)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    args.report.write_text(report(data),encoding='utf8')
    print(json.dumps({'status':'PASS','denominator':data['denominator'],
        'presets':len(data['presets']),'public_bytes':args.output.stat().st_size,
        'public_sha256':sha(args.output),'top_six':[{k:p[k] for k in ('id','support','recommendation')} for p in data['presets'][:6]]}))


if __name__ == '__main__':
    main()
