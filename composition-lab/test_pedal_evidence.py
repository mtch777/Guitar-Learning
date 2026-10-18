"""Source-free acceptance and adversarial tests, separate from frozen baseline."""
import copy
import unittest
from fractions import Fraction as F
from pedal_evidence import analyze_evidence
from test_pedal_regions import rows


class EvidenceTests(unittest.TestCase):
    def test_same_onset_upper_is_never_an_answer(self):
        r = analyze_evidence(rows([[40,71],[55],[40],[59],[40],[60]] * 2))
        self.assertTrue(r['accepted'])
        self.assertNotEqual(r['roles'].get('0:1'), 'response')
        byid = {n['occurrence']:n for n in r['events'] for n in n['notes']}
        for c in r['cycles']:
            self.assertLess(max(F(byid[i]['onset_q']) for i in c['call_members']),
                            min(F(byid[i]['onset_q']) for i in c['response_members']))

    def test_chords_in_lockstep_are_not_an_exchange(self):
        self.assertFalse(analyze_evidence(rows([[40,47,52],[42,49,54]] * 8))['accepted'])
        self.assertFalse(analyze_evidence(rows([[40,47,52]] * 8 + [[55]] +
                                              [[42,49,54]] * 8 + [[57]] + [[40,47,52]]))['accepted'])

    def test_changing_blocks_cannot_substitute_for_anchor_return(self):
        self.assertFalse(analyze_evidence(rows([[28]]*8 + [[51]]*8 + [[37]]*8 +
                                              [[52]]*8 + [[33]]*8))['accepted'])

    def test_uniform_chord_walk_rejects_but_rhythmic_development_survives(self):
        data = rows([[40],[44],[47],[44]] * 4)
        self.assertFalse(analyze_evidence(data)['accepted'])
        for n in data:
            if n['midi'] == 40:n['duration_q'] = '1/2'
        self.assertTrue(analyze_evidence(data)['accepted'])

    def test_single_exchange_does_not_count_as_recurrence(self):
        self.assertFalse(analyze_evidence(rows([[40],[40],[55],[59],[40],[40]]))['accepted'])

    def test_answer_may_begin_before_anchor_releases(self):
        data = rows([[40],[55],[40],[59],[40]])
        for n in data:
            if n['midi'] == 40:n['duration_q'] = '3'
        self.assertTrue(analyze_evidence(data)['accepted'])

    def test_occasional_lower_answer_is_not_mislabeled_as_anchor(self):
        r = analyze_evidence(rows([[40],[55],[40],[58],[40],[35],[40],[57],[40],[62],[40]]))
        self.assertTrue(r['accepted'])
        self.assertEqual(r['roles'].get('5:0'),'response')
        self.assertEqual(r['anchor_pitches'],[40])

    def test_unknown_breaks_but_explicit_dead_strike_does_not_supply_pitch(self):
        data = rows([[40],[None],[40],[55],[40],[59],[40]])
        data[1]['effects'] = ['dead']
        result = analyze_evidence(data)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['roles'].get('0:0'), 'call')
        self.assertNotIn('1:0',result['roles'])

    def test_disconnected_exchanges_are_not_pooled(self):
        data = rows([[40],[55],[40],[59],[40]])
        for n in data[2:]:n['onset_q'] = str(F(n['onset_q']) + 100)
        self.assertFalse(analyze_evidence(data)['accepted'])

    def test_sequential_pedals_established_independently(self):
        data = rows([[45],[57],[45],[59],[45],[40],[52],[40],[55],[40]])
        self.assertEqual(analyze_evidence(data)['anchor_pitches'],[40,45])

    def test_interval_and_reduced_voicing(self):
        data = rows([[28,35],[55],[28,35],[59],[28,35],[60],[28]])
        r = analyze_evidence(data)
        self.assertEqual(r['anchor_pitches'],[28,35])
        self.assertEqual(r['roles'].get('0:1'),'call')
        self.assertEqual(r['roles'].get('6:0'),'call')

    def test_input_immutable_and_transposition_and_time_scale_invariant(self):
        data = rows([[40],[55],[40],[59],[40]])
        before = copy.deepcopy(data); first = analyze_evidence(data)
        self.assertEqual(data,before)
        for n in data:
            n['midi'] += 7
            n['onset_q'] = str(F(n['onset_q'])*F(7,3)+F(11,5))
            n['duration_q'] = str(F(n['duration_q'])*F(7,3))
        other = analyze_evidence(data)
        self.assertEqual(first['roles'],other['roles'])
        self.assertEqual(other['anchor_pitches'],[47])


if __name__ == '__main__':unittest.main()
