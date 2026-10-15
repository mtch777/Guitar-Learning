import tempfile
import unittest
from pathlib import Path
from controlled_generation import demo_plan, realize
from generation_validation import validate_split, copying_ngrams, track_metrics


class ValidationTests(unittest.TestCase):
    def test_renamed_duplicate_cannot_be_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'train.gp',Path(tmp)/'renamed.gp'
            a.write_bytes(b'same song'); b.write_bytes(b'same song')
            with self.assertRaisesRegex(ValueError,'leakage'): validate_split([a],[b])
            b.write_bytes(b'other song')
            self.assertFalse(validate_split([a],[b])['byte_duplicate_leakage'])

    def test_transposed_copy_detected_and_metrics_separate_tracks(self):
        plan=demo_plan(); reference=realize(plan)
        for bar in plan['bars']: bar['root']+=1
        candidate=realize(plan)
        self.assertEqual(copying_ngrams(reference,candidate)['exact_relative_match_share'],1)
        metrics=track_metrics(reference)
        self.assertEqual([m['notes'] for m in metrics],[32,24,16])
        self.assertEqual(metrics[1]['polyphonic_events'],8)


if __name__=='__main__': unittest.main()
