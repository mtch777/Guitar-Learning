"""Behavior checks for explicit Tier-5 templates, independent of path search."""
import unittest
from copy import deepcopy

from fretboard_efficiency_shapes import TUNING, shape_cost


def pitches(coords):
    return [TUNING[s - 1] + f for s, f in coords]


class FretboardEfficiencyShapeTests(unittest.TestCase):
    def score(self, coords, previous=()):
        return shape_cost(coords, pitches(coords), previous, pitches(previous))

    def test_drop_open_and_transposed_barre(self):
        self.assertEqual(self.score([(8, 0), (7, 0)]),
                         (0, ['Drop E open power chord']))
        self.assertEqual(self.score([(8, 3), (7, 3), (6, 3)]),
                         (0, ['Drop E power-chord barre']))
        self.assertNotIn('Drop E power-chord barre', self.score([(8, 3), (6, 3)])[1])
        self.assertEqual(self.score([(7, 3), (6, 3)]), (10, []))

    def test_all_five_caged_major_templates_transposed(self):
        # Literal independently written examples: D(C-shape), C(A), A(G),
        # G(E), and E(D). No template constants imported by these checks.
        shapes = {
            'C': [(5, 5), (4, 4), (3, 2), (2, 3), (1, 2)],
            'A': [(5, 3), (4, 5), (3, 5), (2, 5), (1, 3)],
            'G': [(6, 5), (5, 4), (4, 2), (3, 2), (2, 2), (1, 5)],
            'E': [(6, 3), (5, 5), (4, 5), (3, 4), (2, 3), (1, 3)],
            'D': [(4, 2), (3, 4), (2, 5), (1, 4)],
        }
        for name, coords in shapes.items():
            with self.subTest(name=name):
                self.assertEqual(self.score(coords), (1, [f'CAGED {name}-shape major chord']))

    def test_minor_templates_and_triads_are_labeled_precisely(self):
        em = [(6, 2), (5, 4), (4, 4), (3, 2), (2, 2), (1, 2)]
        self.assertEqual(self.score(em), (1, ['CAGED E-shape minor chord']))
        # Three upper strings of E major include all three pitch classes.
        self.assertEqual(self.score([(1, 0), (2, 0), (3, 1)]),
                         (4, ['CAGED E-shape major chord fragment']))

    def test_adjacent_power_shape_is_not_an_arbitrary_small_span(self):
        cost, labels = self.score([(6, 5), (5, 7), (4, 7)])
        self.assertEqual((cost, labels), (2, ['Adjacent-string power-chord shape']))
        cost, labels = self.score([(2, 3), (1, 3)])
        self.assertFalse(any('power' in label for label in labels))

    def test_pentatonic_fragments_transpose_and_require_actual_cells(self):
        self.assertEqual(self.score([(2, 2), (3, 4)], [(3, 2)]),
                         (6, ['E-shape minor-pentatonic fragment']))
        cost, labels = self.score([(2, 10)], [(5, 9)])
        self.assertEqual(cost, 6)
        self.assertIn('A-shape minor-pentatonic fragment', labels)
        # Adjacent semitone pitches cannot be a minor-pentatonic fragment.
        self.assertEqual(self.score([(2, 0), (3, 5)]), (10, []))
        self.assertEqual(self.score([(3, 5)], [(2, 0)]), (10, []))

    def test_pentatonic_label_does_not_expand_to_extra_low_strings(self):
        self.assertEqual(self.score([(8, 3)], [(8, 0)]), (10, []))

    def test_unison_is_not_enough_to_claim_a_scale_fragment(self):
        self.assertEqual(self.score([(2, 0), (3, 4)]), (10, []))

    def test_empty_invalid_and_nonmutation(self):
        self.assertEqual(shape_cost([], []), (0, []))
        coords = [[8, 3], [7, 3]]
        ps = pitches(coords)
        before = deepcopy((coords, ps))
        self.assertIsInstance(shape_cost(coords, ps)[0], int)
        self.assertEqual((coords, ps), before)
        with self.assertRaises(ValueError):
            shape_cost([(8, 0)], [64])
        with self.assertRaises(ValueError):
            shape_cost([(2, 0), (2, 0)], [59, 59])


if __name__ == '__main__':
    unittest.main()
