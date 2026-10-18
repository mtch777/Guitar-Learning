import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).parent / 'songsterr_automation' / 'songsterr_api'
spec = importlib.util.spec_from_file_location('validation', ROOT / 'validate_technique_analysis.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)


class ValidationTests(unittest.TestCase):
    def test_oracle_edge_cases(self):
        def group(*ps):
            return [dict(midi=p, string=i) for i, p in enumerate(ps)]
        self.assertEqual(v.labels(group(40, 41)), {'double_stop', 'close_interval_texture'})
        self.assertEqual(v.labels(group(40, 42)), {'double_stop'})
        self.assertEqual(v.labels(group(40, 52)), {'double_stop'})
        self.assertIn('power_chord', v.labels(group(40, 47, 52)))
        self.assertNotIn('power_chord', v.labels(group(47, 52)))
        self.assertIn('extended_power_chord', v.labels(group(40, 44, 47)))
        self.assertNotIn('extended_power_chord', v.labels(group(40, 44, 47, 50)))
        self.assertEqual(v.labels([dict(midi=40, string=0), dict(midi=41, string=0)]), set())
        self.assertEqual(v.labels(group(40, None)), set())

    def test_audit_detects_missing_negative_and_corruption(self):
        notes = [dict(string=0, fret=0), dict(string=1, fret=0)]
        beat = dict(duration=[1, 4], notes=notes)
        part = dict(partId=0, tuning=[40, 41], measures=[dict(voices=[dict(beats=[beat])])])
        rows = [dict(occurrence=f'0:1:0:0:{i}', raw_note=n, string=i, fret=0,
                     tie_destination=False, duration_q='1', midi=40+i, onset_q='0', bar=1)
                for i, n in enumerate(notes)]
        track = dict(part_id=0, rows=rows, grace_rows=[], guitar_or_bass=True,
                     temporal_relationships_eligible=True, coattack_groups=[], hopo_transition_candidates=[])
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / '1'; folder.mkdir()
            (folder / 'track-0.json').write_text(json.dumps(part), encoding='utf-8')
            report = dict(songs=[dict(song_id=1, tracks=[track], shared_layout=[dict(start_q='0')])])
            public, _ = v.audit(report, Path(d))
            self.assertEqual(public['checks']['coattack_rule_failed'], 1)
            track['coattack_groups'] = [dict(onset_q='0', labels=['double_stop', 'close_interval_texture'])]
            self.assertEqual(v.audit(report, Path(d))[0]['failed_checks'], 0)
            rows[0]['duration_q'] = '2'
            self.assertEqual(v.audit(report, Path(d))[0]['checks']['duration_failed'], 1)
            rows[0]['duration_q'] = '1'
            rows[0]['onset_q'] = '1/3'
            self.assertEqual(v.audit(report, Path(d))[0]['checks']['onset_within_shared_layout_failed'], 1)


if __name__ == '__main__':
    unittest.main()
