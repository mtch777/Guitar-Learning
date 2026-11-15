"""A profile addition must preserve accepted mappings and their source identity."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

import run_fretboard_efficiency as runner


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / 'tests' / 'fixtures' / 'fretboard-efficiency'


def legacy_bundle():
    data = json.loads((ROOT / 'public/data/fretboard-efficiency-fixtures.json').read_text())
    for fixture in data['fixtures']:
        fixture['versions'] = [v for v in fixture['versions'] if v['id'] in ('greedy', 'optimized')]
    return data


class StrategyAdditionTests(unittest.TestCase):
    def test_appends_new_strategy_without_recomputing_or_altering_existing_results(self):
        original = legacy_bundle()

        def forbidden_original_search(*args, **kwargs):
            raise AssertionError('A profile addition reran an accepted original mapping.')

        strategies = tuple((name, fn if name == 'strumPick' else forbidden_original_search)
                           for name, fn in runner.STRATEGIES)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'bundle.json'
            output.write_text(json.dumps(original))
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'STRATEGIES', strategies), redirect_stdout(StringIO()):
                actual = runner.build(SOURCE_DIR, output, strategy_ids=['strumPick'])
            self.assertEqual(json.loads(output.read_text()), actual)
            for before, after in zip(original['fixtures'], actual['fixtures']):
                self.assertEqual(after['versions'][:2], before['versions'])
                restored = deepcopy(after)
                restored['versions'] = restored['versions'][:2]
                self.assertEqual(restored, before)
                self.assertEqual(after['versions'][2]['id'], 'strumPick')
                self.assertTrue((root / 'public' / after['versions'][2]['midi_path']).is_file())
            self.assertEqual(len(list((root / 'public/fretboard-efficiency').glob('*.mid'))), 3)

    def test_refuses_to_combine_new_mapping_with_stale_source_notes(self):
        original = legacy_bundle()
        source = next(f for f in original['fixtures'] if f['id'] == 'c5a35486')
        source['notes'][0]['end_tick'] += 1
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'bundle.json'
            output.write_text(json.dumps(original))
            before = output.read_bytes()
            with patch.object(runner, 'write_string_midi') as export:
                with self.assertRaisesRegex(ValueError, 'changed source c5a35486: notes differs'):
                    runner.build(SOURCE_DIR, output, ['c5a35486'], ['strumPick'])
                export.assert_not_called()
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
