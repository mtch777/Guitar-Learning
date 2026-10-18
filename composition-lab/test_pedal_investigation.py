"""Counterexamples for competing pedal-evidence policies, not listening claims."""
import unittest
from pedal_regions import detect_regions
from test_pedal_regions import rows


class InvestigationTests(unittest.TestCase):
    def test_two_answer_notes_are_not_two_returns(self):
        data=rows([[40],[40],[52],[55],[40],[40]])
        self.assertTrue(detect_regions(data))
        self.assertFalse(detect_regions(data,minimum_return_pairs=2))

    def test_repeated_returns_survive(self):
        data=rows([[40],[52],[40],[55],[40]])
        self.assertEqual(detect_regions(data),detect_regions(data,minimum_return_pairs=2))

    def test_high_member_cannot_supply_its_own_higher_contrast(self):
        data=rows([[40,64],[52],[40,64],[55],[40,64]])
        self.assertTrue(detect_regions(data))
        self.assertFalse(detect_regions(data,contrast_above_entire_anchor=True))

    def test_real_dyad_with_higher_replies_survives(self):
        data=rows([[28,35],[55],[28,35],[59],[28,35]])
        self.assertEqual(detect_regions(data),detect_regions(data,
            minimum_return_pairs=2,contrast_above_entire_anchor=True))


if __name__=='__main__':unittest.main()
