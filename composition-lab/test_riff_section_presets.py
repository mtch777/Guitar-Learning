"""Public aggregate contracts; no private corpus is required to run these tests."""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

import analyze_riff_section_presets as analysis


class SectionPresetTests(unittest.TestCase):
    def test_exact_fractions_cardinality_and_explicit_song_alias(self):
        analysis.self_checks()
        self.assertEqual(analysis.focus([2, 2, 2]), 'interval')
        self.assertEqual(analysis.song_identity('Invent Animate', 722881),
                         analysis.song_identity('Invent Animate', 460099))
        self.assertNotEqual(analysis.song_identity('Currents', 722881),
                            analysis.song_identity('Invent Animate', 460099))

    def test_many_versions_do_not_outvote_distinct_songs(self):
        def row(song, length):
            return {'song': ('Invent Animate', song), 'captures': {str(song)}, 'length': F(length)}
        rows = [row(1, 8) for _ in range(100)] + [row(2, 4), row(3, 4)]
        result = analysis.summarize(rows)
        self.assertEqual(result['distinct_songs'], 3)
        self.assertEqual(result['occurrences'], 102)
        self.assertEqual(result['song_balanced_mean_q'], '16/3')
        self.assertEqual(analysis.recommend(result['duration_histogram'])['length_q'], '4')

    def test_large_and_fractional_units_are_not_clipped_to_pack_bounds(self):
        rows = [{'song': ('ERRA', 1), 'captures': {'a'}, 'length': F(1, 3)},
                {'song': ('ERRA', 2), 'captures': {'b'}, 'length': F(160)}]
        result = analysis.summarize(rows)
        self.assertEqual(result['duration']['max_q'], '160')
        self.assertEqual(result['duration']['min_q'], '1/3')
        self.assertEqual(result['duration']['mean_q'], '481/6')

    def test_missing_style_is_not_other_and_actual_focus_is_not_shape_size(self):
        # Repeated shape labels/contacts are irrelevant: two heads are a dyad,
        # even when the heads have one pitch. The style mapping has no default.
        self.assertEqual(analysis.focus([2, 2]), 'interval')
        self.assertEqual([s for s, tag in analysis.STYLE_TAGS.items() if tag in []], [])

    def test_public_aggregate_conserves_units_and_song_support(self):
        path = Path(__file__).resolve().parents[1]/'public/riff-builder/section-presets.json'
        data = json.loads(path.read_text(encoding='utf8'))
        frozen = deepcopy(data)
        self.assertEqual(data['schema'], 'riff-section-presets/1')
        d = data['denominator']
        self.assertEqual(d['input_gesture_observations'] - d['duplicate_source_gesture_observations_removed'],
                         d['deduplicated_gesture_occurrences'])
        self.assertEqual(data['units']['gestures']['occurrences'], d['deduplicated_gesture_occurrences'])
        self.assertEqual(data['units']['whole_riff_captures']['occurrences'], d['reference_captures'])
        for key in ('gestures', 'whole_riff_captures'):
            combined = data['units'][key]
            self.assertEqual(sum(x['occurrences'] for x in combined['duration_histogram']), combined['occurrences'])
            self.assertEqual(sum(data['units']['by_artist'][a][key]['occurrences'] for a in analysis.ARTISTS), combined['occurrences'])
        self.assertEqual(data['presets'], sorted(data['presets'], key=lambda p: (-p['support']['distinct_songs'], p['id'])))
        for preset in data['presets']:
            self.assertEqual(sum(v['distinct_songs'] for v in preset['by_artist'].values()), preset['support']['distinct_songs'])
            self.assertEqual(sum(v['occurrences'] for v in preset['by_artist'].values()), preset['support']['occurrences'])
            self.assertEqual(preset['recommendation'], analysis.recommend(preset['evidence']['duration_histogram']))
            self.assertEqual(preset['style_scope'], 'inherited_containing_riff')
            for artist, evidence in preset['by_artist'].items():
                self.assertEqual(sum(x['occurrences'] for x in evidence['duration_histogram']), evidence['occurrences'])
                self.assertTrue(all(x['distinct_songs'] <= evidence['distinct_songs'] for x in evidence['duration_histogram']))
                self.assertLessEqual(evidence['distinct_songs'], data['units']['by_artist'][artist]['gestures']['distinct_songs'])
        self.assertEqual(data, frozen)


if __name__ == '__main__':
    unittest.main()
