"""Standalone generator smoke tests; source tabs are not required in CI."""
import random
import unittest
from collections import Counter
from generate_composition import compose_four_bars, transform_a, nearest_fret, pitch_node, weighted

TUNING=[26,31,38,43,48,53,57,62]
STATS={'rhythm_units':Counter({1:15,2:8,4:2}),
       'pitch_classes':Counter({2:10,5:7,9:5,0:4}),
       'intervals':Counter({0:10,3:6,-3:6,2:3,-2:3,5:2,-5:2})}
class GeneratorTests(unittest.TestCase):
    def test_weighted_seeded(self):
        self.assertEqual(weighted(random.Random(5),Counter({1:1})),1)
    def test_pitch_spelling(self):
        x=pitch_node(61)
        self.assertEqual(x.findtext('Step'),'C')
        self.assertEqual(x.findtext('Octave'),'4')
    def test_playability(self):
        self.assertIsNone(nearest_fret(10,TUNING))
        self.assertEqual(nearest_fret(31,TUNING),(1,0))
    def test_created_phrase(self):
        p=compose_four_bars(random.Random(17),STATS,TUNING)
        self.assertEqual(len(p),4)
        self.assertTrue(all(sum(x['units'] for x in bar)==16 for bar in p))
        self.assertGreater(sum(e['pitch'] is not None for bar in p for e in bar),0)
    def test_variation_preserves_timing(self):
        phrase=compose_four_bars(random.Random(17),STATS,TUNING)
        varied=transform_a(phrase,random.Random(18),TUNING)
        self.assertEqual([[e['units'] for e in bar] for bar in phrase],
                         [[e['units'] for e in bar] for bar in varied])
        self.assertNotEqual(phrase,varied)
        for bar in varied:
            for e in bar:
                if e['pitch'] is not None:
                    self.assertEqual(TUNING[e['string']]+e['fret'],e['pitch'])
if __name__=='__main__':unittest.main()
