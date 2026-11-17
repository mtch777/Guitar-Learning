import copy
import unittest
from section_functions import analyze_functions, DEFAULT_WEIGHTS
from section_repeats import analyze_repeats
from test_section_repeats import song, A, B, D, E, F


class FunctionTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(analyze_functions([])['bars'], [])

    def test_silence_is_unknown(self):
        r = analyze_functions(song([[], [], []]))
        self.assertFalse(r['hypotheses'])
        self.assertTrue(all(x['label'] == 'unknown' for x in r['bars']))

    def test_full_bar_coverage(self):
        f = song([A, B, D, E, F, A, B, D])
        r = analyze_functions(f)
        self.assertEqual([x['bar'] for x in r['bars']], list(range(1,9)))
        self.assertEqual(r['bars'][0]['start_q'], '0')
        self.assertEqual(r['bars'][-1]['end_q'], '32')

    def test_repetition_alone_not_chorus(self):
        r = analyze_functions(song([A, B, D, E, F, A, B, D]))
        for h in r['hypotheses']:
            self.assertEqual(h['label'], 'unknown')
            self.assertIsNone(h['evidence']['lead_return'])
            self.assertIsNone(h['confidence'])
            self.assertAlmostEqual(sum(h['support_weights'].values()), 1)

    def test_loop_not_promoted(self):
        r = analyze_functions(song([A]*12), lead_channels=[1])
        self.assertTrue(r['hypotheses'])
        for h in r['hypotheses']:
            self.assertIn('internal_loop_not_proof_of_section', h['warnings'])
            self.assertEqual(h['label'], 'unknown')

    def test_confirmed_lead_changes_support_not_fact(self):
        f = song([A, B, D, E, F, A, B, D])
        r = analyze_functions(f, lead_channels=[1])
        h = next(h for h in r['hypotheses'] if h['occurrences'][0]['bars'] == [1,2,3])
        self.assertEqual(h['evidence']['lead_return'], 1)
        self.assertGreater(h['support_weights']['chorus'], h['support_weights']['verse'])
        self.assertEqual(h['label'], 'unknown')

    def test_missing_lead_not_variation(self):
        r = analyze_functions(song([A, B, A, B]), lead_channels=['missing'])
        for h in r['hypotheses']:
            self.assertIsNone(h['evidence']['lead_variation'])

    def test_no_mutation(self):
        f = song([A,B,D,E,F,A,B,D]); repeats = analyze_repeats(f)
        old = copy.deepcopy((f,repeats))
        analyze_functions(f,repeats, lead_channels=[1])
        self.assertEqual(old, (f,repeats))

    def test_invalid_weights(self):
        for w in ({}, dict.fromkeys(DEFAULT_WEIGHTS,0),
                  {**DEFAULT_WEIGHTS,'lead_return':float('nan')},
                  {**DEFAULT_WEIGHTS,'lead_return':-1},
                  {**DEFAULT_WEIGHTS,'lead_return':True}):
            with self.assertRaises(ValueError): analyze_functions([],weights=w)

    def test_only_arrangement_does_not_choose_function(self):
        w = dict.fromkeys(DEFAULT_WEIGHTS,0); w['arrangement_lift']=1
        r = analyze_functions(song([A,B,A,B]),weights=w)
        self.assertTrue(all(h['label']=='unknown' for h in r['hypotheses']))

    def test_bad_repeat_count(self):
        with self.assertRaises(ValueError): analyze_functions(song([A]),{'bar_count':2,'groups':[]})

    def test_odd_length_no_grid_requirement(self):
        f = song([A,B,D,E,F,[80],A,B,D,E,F])
        r = analyze_functions(f)
        self.assertTrue(any(len(o['bars'])==5 for h in r['hypotheses'] for o in h['occurrences']))

if __name__ == '__main__': unittest.main()
