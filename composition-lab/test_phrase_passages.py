import unittest
from copy import deepcopy
from fractions import Fraction
from test_phrase_experiments import fixture
from phrase_passages import transform


class PassageTests(unittest.TestCase):
    def test_rhythm_has_breath_and_exact_bar_coverage_without_accompaniment_edits(self):
        base=fixture();frozen=deepcopy(base)
        for contour in (False,True):
            out=transform(base,contour)
            self.assertEqual(out['tracks'][0],base['tracks'][0]);self.assertEqual(out['tracks'][2],base['tracks'][2])
            for m in out['tracks'][1]['measures']:
                cursor=Fraction(0);rests=0
                for e in m['voices'][0]:
                    self.assertEqual(Fraction(e['local_onset_q']),cursor)
                    duration=Fraction(e['duration_q']);self.assertGreater(duration,0);cursor+=duration
                    if not e['notes']:rests+=duration
                    for n in e['notes']:self.assertEqual(n['midi'],out['tracks'][1]['tunings'][0][n['string']]+n['fret'])
                self.assertEqual(cursor,4);self.assertGreater(rests,0)
        self.assertEqual(base,frozen)

    def test_reject_incompatible_meter(self):
        base=fixture();base['tracks'][1]['measures'][0]['time_signature']='3/4'
        with self.assertRaises(ValueError):transform(base)


if __name__=='__main__':unittest.main()
