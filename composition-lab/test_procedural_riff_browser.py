"""Public, corpus-free contract checks for the actual browser composer pack."""
import gzip
import hashlib
import importlib.util
import json
from fractions import Fraction as Q
from pathlib import Path
import unittest

PUBLIC = Path(__file__).resolve().parents[1] / 'public/riff-builder'
MANIFEST = json.loads((PUBLIC / 'procedural-manifest.json').read_bytes())
ENGINE_BYTES = (PUBLIC / MANIFEST['engine']['file']).read_bytes()
PACK_BYTES = (PUBLIC / MANIFEST['pack']['file']).read_bytes()
PACK_JSON = gzip.decompress(PACK_BYTES)
PACK = json.loads(PACK_JSON)
SPEC = importlib.util.spec_from_file_location('public_procedural_composer', PUBLIC / MANIFEST['engine']['file'])
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ProceduralBrowserTests(unittest.TestCase):
    def test_content_addressed_pack_and_no_original_pitch_oracle(self):
        self.assertEqual(sha(ENGINE_BYTES), MANIFEST['engine']['sha256'])
        self.assertEqual(sha(PACK_BYTES), MANIFEST['pack']['sha256'])
        self.assertEqual(sha(PACK_JSON), MANIFEST['pack']['json_sha256'])
        self.assertEqual(len(PACK['programs']), MANIFEST['programs'])
        self.assertEqual(len(PACK['palettes']), MANIFEST['palettes'])
        forbidden = {'source_absolute_fingerprint', 'source_relative_fingerprint',
                     'source_roles', 'original_pitch', 'source_pitches', 'old_roles',
                     'original_ordered_pitches'}

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(PACK)

    def test_complete_programs_and_explicit_riff_authority(self):
        eligible = []
        for program in PACK['programs']:
            instances = program['plan']['instances']
            owned = [i for instance in instances for i in instance['event_indices']]
            self.assertEqual(sorted(owned), list(range(len(program['template']['events']))))
            self.assertTrue(program['novelty_certificate']['verified'])
            self.assertEqual(program['novelty_certificate']['version'], 'private-order-proof/1')
            authority = program['closure_status']['authority']
            if authority['whole_riff_eligible']:
                eligible.append(program)
        self.assertTrue(eligible)
        self.assertEqual({p['artist'] for p in eligible}, set(ENGINE.ARTISTS))

    def test_six_modes_three_artists_written_events_and_reproducibility(self):
        before = json.dumps(PACK, sort_keys=True, separators=(',', ':'))
        by_id = {p['id']: p for p in PACK['programs']}
        for index, mode in enumerate(ENGINE.MODES):
            artist = ENGINE.ARTISTS[index % 3]
            request = {'artists': [artist], 'mode': mode, 'seed': 606}
            with self.subTest(artist=artist, mode=mode):
                result = ENGINE.generate(request, PACK)
                self.assertEqual(result['status'], 'generated', result.get('reason'))
                self.assertEqual(result['request'], request)
                self.assertEqual(result['program_artist'], artist)
                source = by_id[result['program_id']]
                self.assertIs(source['closure_status']['authority']['whole_riff_eligible'], True)
                expected = source['template']['events']
                self.assertEqual(len(expected), len(result['events']))
                for template, event in zip(expected, result['events']):
                    self.assertEqual(Q(template['onset_q']), Q(event['onset_q']))
                    self.assertEqual(len(template['members']), len(event['members']))
                    for intended, note in zip(template['members'], event['members']):
                        self.assertEqual(Q(intended['hold_q']), Q(note['duration_q']))
                        self.assertEqual(intended['marks'], note['marks'])
                        self.assertEqual(note['pitch'], ENGINE.TUNING[note['string_number']-1]+note['fret'])
                        self.assertIn((note['pitch']-4) % 12, ENGINE.MODES[mode])
                        self.assertGreaterEqual(note['fret'], 0)
                        self.assertLessEqual(note['fret'], 24)
                at = Q(0)
                for phrase in result['phrases']:
                    self.assertEqual(Q(phrase['offset_q']), at)
                    self.assertGreater(Q(phrase['length_q']), 0)
                    at += Q(phrase['length_q'])
                self.assertEqual(at, Q(result['duration_q']))
                for relation in result.get('operative_parent_relations', []):
                    for pair in relation['slot_pairs']:
                        a, b = pair['from'], pair['to']
                        left = result['events'][a[0]]['members'][a[1]]
                        right = result['events'][b[0]]['members'][b[1]]
                        if pair['preserve_pitch']:
                            self.assertEqual(left['pitch'], right['pitch'])
                        if pair['preserve_execution']:
                            for field in ('pitch', 'string_number', 'fret', 'duration_q', 'marks'):
                                self.assertEqual(left[field], right[field])
                if index == 0:
                    self.assertEqual(result, ENGINE.generate(request, PACK))
        self.assertEqual(before, json.dumps(PACK, sort_keys=True, separators=(',', ':')))

    def test_invalid_inputs_do_not_change_scope(self):
        for request in ({'artists': [], 'mode': 'Aeolian'},
                        {'artists': ['Other artist'], 'mode': 'Aeolian'},
                        {'artists': ['Invent Animate'], 'mode': 'Locrian'}):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    ENGINE.generate(request, PACK)


if __name__ == '__main__':
    unittest.main()
