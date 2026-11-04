"""Exercise new output requests and the actual source-denied saved inverse."""
from pathlib import Path
import json
import tempfile
import unittest

from run_output_change_controls import run
from test_melodic_movement_ownership import build_v2, v2_documents


class OutputControlBoundaryTests(unittest.TestCase):
    def test_changed_and_saved_source_denied_score_from_complete_upper_only(self):
        _, _, _, owned = build_v2(v2_documents(coattack=True, tied=True), unrelated=True)
        request = dict(kind='movement', max_candidates=64, controls=dict(
            melody=100, register=50, intent='follow_reference_motion',
            register_direction='up', seed=0))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'model.json').write_text(json.dumps(owned), encoding='utf8')
            (root/'request.json').write_text(json.dumps(request), encoding='utf8')
            result = run(root/'model.json', root/'request.json', root/'proof', denied=True)
            self.assertTrue(result['satisfied'])
            self.assertTrue(result['score_changed'])
            self.assertEqual(result['qa2'], {'baseline': 'PASS', 'current': 'PASS'})
            self.assertTrue(result['input_unchanged'])
            decision = json.loads((root/'proof/decision.json').read_text())
            self.assertEqual(decision['final_output']['features']['melody']['changed_count'], 2)
            # One attack crosses back into its old octave through the combined
            # contour/offset. Only two of three actual octave positions change.
            self.assertEqual(decision['final_output']['features']['register']['changed_count'], 2)
            self.assertEqual(json.loads((root/'model.json').read_text()), owned)


if __name__ == '__main__':
    unittest.main()
