"""Authored acceptance contrasts for selected-context membership, not key inference."""
from copy import deepcopy
import unittest

import stable_pitch_membership as membership


ORIGIN = dict(schema='declared-source-observation-origin/1', facts_sha256='a' * 64)
C_MAJOR = dict(id='C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])
A_MINOR = dict(id='A-natural-minor', tonic_pc=9, intervals=[0, 2, 3, 5, 7, 8, 10])
C_MINOR = dict(id='C-natural-minor', tonic_pc=0, intervals=[0, 2, 3, 5, 7, 8, 10])


def packet(candidates=None):
    return dict(schema=membership.SCHEMA, origin=deepcopy(ORIGIN),
                basis=membership.BASIS, pitch_frame=membership.PITCH_FRAME,
                selection_reason='Authored collection choice; tonic unresolved',
                selection_reference='authored-test-selection',
                contexts=[dict(id='context:0', start_q='0', end_q='4',
                               candidates=deepcopy([C_MAJOR, A_MINOR] if candidates is None else candidates))])


def span(pitch=64, start='0', end='4'):
    return dict(occurrence_refs=['note:1'], start_q=start, end_q=end, pitch=pitch)


class StablePitchMembershipTests(unittest.TestCase):
    def test_ambiguous_tonic_shared_collection_is_sufficient(self):
        result = membership.assess_spans(packet(), [span()])
        self.assertEqual(result['status'], membership.IN_COLLECTION)
        cells = result['spans'][0]['cells']
        self.assertEqual(len(cells[0]['memberships']), 2)
        self.assertEqual(cells[0]['memberships'][0]['collection_pitch_classes'],
                         cells[0]['memberships'][1]['collection_pitch_classes'])
        self.assertEqual(result['basis'], 'explicit_selected_context')

    def test_in_key_nonchord_tone_is_allowed(self):
        # D is outside the accompanying C/E/G/B chord but inside both collections.
        result = membership.assess_spans(packet(), [span(62)])
        self.assertEqual(result['status'], membership.IN_COLLECTION)

    def test_chromatic_stable_destination_is_excluded(self):
        result = membership.assess_spans(packet(), [span(63)])
        self.assertEqual(result['status'], membership.OUT_OF_COLLECTION)
        self.assertTrue(all(not row['inside'] for row in result['spans'][0]['cells'][0]['memberships']))

    def test_moving_approach_is_not_a_stable_span_input(self):
        # Caller derives only the E plateau, excluding the earlier D# approach.
        result = membership.assess_spans(packet(), [span(64, '3/8', '2')])
        self.assertEqual(result['status'], membership.IN_COLLECTION)
        self.assertEqual(result['spans'][0]['cells'][0]['start_q'], '3/8')

    def test_empty_hypotheses_and_empty_spans_cannot_vacuously_pass(self):
        result = membership.assess_spans(packet([]), [span()])
        self.assertEqual(result['status'], membership.NOT_KEY_VERIFIED)
        self.assertIn('NO_SELECTED_HYPOTHESES', result['reasons'])
        self.assertEqual(membership.assess_spans(packet(), [])['status'], membership.NOT_KEY_VERIFIED)

    def test_gap_anywhere_in_held_span_is_unresolved(self):
        selected = packet()
        selected['contexts'][0]['end_q'] = '1'
        selected['contexts'].append(dict(selected['contexts'][0], id='context:1', start_q='2', end_q='4'))
        result = membership.assess_spans(selected, [span()])
        self.assertEqual(result['status'], membership.NOT_KEY_VERIFIED)
        self.assertEqual([(row['start_q'], row['end_q']) for row in result['spans'][0]['cells']],
                         [('0', '1'), ('1', '2'), ('2', '4')])
        self.assertIn('UNCOVERED_STABLE_SPAN', result['reasons'])
        for start, end in [('-1', '1'), ('3', '5')]:
            self.assertEqual(membership.assess_spans(packet(), [span(start=start, end=end)])['status'],
                             membership.NOT_KEY_VERIFIED)

    def test_disagreeing_collections_remain_unresolved(self):
        result = membership.assess_spans(packet([C_MAJOR, C_MINOR]), [span()])
        self.assertEqual(result['status'], membership.NOT_KEY_VERIFIED)
        self.assertIn('SELECTED_COLLECTIONS_DISAGREE', result['reasons'])

    def test_hold_is_checked_after_context_change_and_boundary_is_half_open(self):
        selected = packet([C_MAJOR])
        selected['contexts'][0]['end_q'] = '2'
        selected['contexts'].append(dict(id='context:1', start_q='2', end_q='4', candidates=[C_MINOR]))
        self.assertEqual(membership.assess_spans(selected, [span()])['status'], membership.OUT_OF_COLLECTION)
        self.assertEqual(membership.assess_spans(selected, [span(end='2')])['status'], membership.IN_COLLECTION)
        self.assertEqual(membership.assess_spans(selected, [span(start='2')])['status'], membership.OUT_OF_COLLECTION)

    def test_unknown_cell_does_not_hide_known_exclusion_evidence(self):
        selected = packet()
        selected['contexts'][0]['end_q'] = '2'
        result = membership.assess_spans(selected, [span(63)])
        self.assertEqual(result['status'], membership.NOT_KEY_VERIFIED)
        self.assertEqual(result['spans'][0]['cells'][0]['status'], membership.OUT_OF_COLLECTION)
        self.assertIn('UNCOVERED_STABLE_SPAN', result['reasons'])

    def test_fractional_pitch_is_unresolved_without_rounding(self):
        result = membership.assess_spans(packet(), [span('127/2')])
        self.assertEqual(result['status'], membership.NOT_KEY_VERIFIED)
        self.assertIn('NONINTEGER_STABLE_PITCH_NOT_SUPPORTED', result['reasons'])

    def test_origin_must_match_enclosing_score(self):
        with self.assertRaisesRegex(ValueError, 'origin mismatch'):
            membership.validate_context(packet(), dict(ORIGIN, facts_sha256='b' * 64))

    def test_inputs_and_returned_packet_are_independent(self):
        selected, spans = packet(), [span('64', '0/2', '8/2')]
        before = deepcopy((selected, spans))
        validated = membership.validate_context(selected, ORIGIN)
        result = membership.assess_spans(selected, spans)
        self.assertEqual((selected, spans), before)
        self.assertEqual(result['spans'][0]['end_q'], '4')
        validated['contexts'][0]['candidates'][0]['intervals'].append(1)
        result['origin']['facts_sha256'] = 'b' * 64
        self.assertEqual((selected, spans), before)

    def test_malformed_contexts_fail_instead_of_blessing_admission(self):
        corruptions = []
        for name, value in [('admitted', True), ('basis', 'inferred_key'), ('pitch_frame', 'written_midi'),
                            ('selection_reason', ''), ('selection_reference', None), ('contexts', [])]:
            selected = packet(); selected[name] = value; corruptions.append(selected)
        for name, value in [('tonic_pc', True), ('tonic_pc', 12), ('intervals', [0, 2, 2]),
                            ('intervals', [0, 2.0]), ('intervals', [2, 4]), ('intervals', [])]:
            selected = packet(); selected['contexts'][0]['candidates'][0][name] = value; corruptions.append(selected)
        for name, value in [('start_q', False), ('end_q', 4.0), ('end_q', '0'), ('end_q', '1/0')]:
            selected = packet(); selected['contexts'][0][name] = value; corruptions.append(selected)
        selected = packet(); selected['contexts'].append(deepcopy(selected['contexts'][0])); corruptions.append(selected)
        selected = packet(); selected['contexts'].append(dict(selected['contexts'][0], id='overlap', start_q='2')); corruptions.append(selected)
        selected = packet(); selected['contexts'][0]['candidates'].append(deepcopy(C_MAJOR)); corruptions.append(selected)
        for selected in corruptions:
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                membership.validate_context(selected, ORIGIN)

    def test_malformed_spans_fail_instead_of_coercing(self):
        for name, value in [('pitch', True), ('pitch', 64.0), ('pitch', 'NaN'),
                            ('start_q', 0.0), ('end_q', '0'), ('occurrence_refs', []),
                            ('occurrence_refs', ['note:1', 'note:1']), ('occurrence_refs', [None]),
                            ('original_pitch', 64)]:
            invalid = span(); invalid[name] = value
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                membership.assess_spans(packet(), [invalid])


if __name__ == '__main__':
    unittest.main()
