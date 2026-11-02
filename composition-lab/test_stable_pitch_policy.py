"""Integrated musical contrasts for a saved stable-pitch preference.

Raw authored score expectations are independent of the policy under test.
These checks establish conditional control behavior, not automatic key inference.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest

import backing_pitch_ownership as backing
import bend_gesture_ownership as gesture
import musical_tier2 as music
import stable_pitch_membership as membership
import stable_pitch_policy as policy
from connected_tier2 import realize, reconstruct, strip_lower
from source_fact_tier1 import extract_documents, project_documents
from test_bend_gesture_ownership import (
    BACKING, DEPENDENT, REFERENCE, TARGET, base_upper, changed_reference_extent,
    controls, curve, documents, expected_target, fixture, note,
)


C_MAJOR = dict(id='C-major', tonic_pc=0, intervals=[0, 2, 4, 5, 7, 9, 11])
A_MINOR = dict(id='A-natural-minor', tonic_pc=9, intervals=[0, 2, 3, 5, 7, 8, 10])
C_MINOR = dict(id='C-natural-minor', tonic_pc=0, intervals=[0, 2, 3, 5, 7, 8, 10])


def context(upper, candidates=None):
    return dict(schema=membership.SCHEMA, origin=deepcopy(upper['source_origin']),
                basis=membership.BASIS, pitch_frame=membership.PITCH_FRAME,
                selection_reason='Authored explicit collection choice',
                selection_reference='authored-policy-regression',
                contexts=[dict(id='whole-authored-span', start_q='0', end_q='12',
                               candidates=deepcopy([C_MAJOR, A_MINOR] if candidates is None else candidates))])


def changed_plain_pitch(upper, pitch):
    """Change the existing independent pitch parameter; retain all observations."""
    result = deepcopy(upper)
    group, _ = backing._index(gesture._body(result['musical_relationships']))[DEPENDENT]
    group['bass_register_anchor'] = str(pitch)
    # Refresh current derived views through the existing core equations. This
    # authored core has no dependent owner; source_origin is left untouched.
    result['musical_relationships'] = music.strip_lower(music.analyze(music.realize(result['musical_relationships'])))
    return result


def plain_fixture():
    docs = documents()
    # An authored Cmaj7 accompaniment makes D an audible nonchord alternative.
    docs['track-1.json']['tuning'] = [48, 52, 55, 59]
    docs['track-1.json']['measures'][2]['voices'][0]['beats'][0]['notes'] = [
        dict(string=index, fret=0) for index in range(4)]
    lower, upper = base_upper(docs)
    return docs, lower, upper


class StablePitchPolicyTests(unittest.TestCase):
    def test_unknown_context_allows_changed_approach_to_unchanged_arrival(self):
        docs, lower, upper = fixture()
        bound = policy.attach(upper)
        snapshot = deepcopy(bound)
        edited, decision = gesture.intervene(bound, controls(intent='keep_arrival'))
        # A -> B becomes Bb -> B. Only the approach becomes chromatic.
        self.assertEqual(project_documents(realize(edited)), expected_target(docs, fret=10, tone=50))
        self.assertEqual(decision['stable_pitch_check']['status'], 'UNCHANGED_STABLE_PITCHES')
        self.assertEqual(bound, snapshot)
        self.assertEqual(edited[policy.SLOT], bound[policy.SLOT])
        self.assertEqual(edited['source_origin'], upper['source_origin'])
        self.assertEqual(realize(bound), lower)

    def test_unknown_context_refuses_new_arrival_without_partial_change(self):
        _, _, upper = fixture()
        bound = policy.attach(upper)
        snapshot = deepcopy(bound)
        for operation in (gesture.intervene, reconstruct):
            with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, 'NOT_KEY_VERIFIED'):
                operation(bound, controls(intent='keep_start'))
            self.assertEqual(bound, snapshot)

    def test_selected_collection_rejects_new_bb_but_keeps_source_b(self):
        docs, _, upper = fixture()
        bound = policy.attach(upper, context=context(upper))
        snapshot = deepcopy(bound)
        with self.assertRaisesRegex(ValueError, 'OUT_OF_COLLECTION'):
            gesture.intervene(bound, controls(intent='keep_start'))
        self.assertEqual(bound, snapshot)
        edited, _ = gesture.intervene(bound, controls(intent='keep_arrival'))
        self.assertEqual(project_documents(realize(edited)), expected_target(docs, fret=10, tone=50))

    def test_source_outside_selected_collection_remains_exact_at_zero(self):
        docs, lower, upper = fixture()
        bound = policy.attach(upper, context=context(upper, [C_MINOR]))
        # Source arrival B is outside C natural minor; attachment is not cleanup.
        self.assertEqual(realize(bound), lower)
        saved = json.loads(json.dumps(bound))
        for request in ({'variation': 0}, controls(0), controls(0, 'keep_arrival')):
            self.assertEqual(project_documents(reconstruct(saved, request)), docs)
            self.assertEqual(saved, bound)
        zero, _ = gesture.intervene(saved, controls(0))
        self.assertEqual(zero, saved)
        self.assertEqual(strip_lower(zero)[policy.SLOT], bound[policy.SLOT])

    def test_plateau_clock_includes_origin_tail_and_complete_tied_hold(self):
        for explicit_hold in (False, True):
            with self.subTest(explicit_hold=explicit_hold):
                _, lower, upper = fixture(explicit_hold=explicit_hold)
                bound = policy.attach(upper)
                # Bar two starts at q4. The 3/2-quarter bend reaches B at 1/4
                # of that beat, then holds through its 1/2-quarter continuation.
                self.assertEqual(policy.stable_spans(bound, lower), [dict(
                    occurrence_refs=TARGET, start_q='35/8', end_q='6', pitch='71')])

    def test_live_reference_after_saved_binding_cannot_hide_new_destination(self):
        docs, _, upper = fixture()
        doubled = changed_reference_extent(upper, 2)
        bound = policy.attach(doubled, context=context(doubled))
        linked, _ = gesture.intervene(bound, controls(intent='keep_start'))
        saved = json.loads(json.dumps(linked))
        before = realize(saved)
        later = changed_reference_extent(saved, 2)
        after = realize(later)
        expected = expected_target(docs, fret=9, tone=200)
        for index in (0, 1):
            note(expected, 0, 0, index)['bend'] = curve(200, index == 1)
        self.assertEqual(project_documents(after), expected)
        snapshot = deepcopy((saved, before, after))
        with self.assertRaisesRegex(ValueError, 'OUT_OF_COLLECTION'):
            policy.enforce_transition(saved, before, after)
        self.assertEqual((saved, before, after), snapshot)
        self.assertEqual(later['owned_parameters'][gesture.SLOT]['observations'],
                         upper['owned_parameters'][gesture.SLOT]['observations'])

    def test_plain_in_key_nonchord_alternative_and_chromatic_refusal(self):
        docs, lower, upper = plain_fixture()
        bound = policy.attach(upper, context=context(upper), held_refs=[DEPENDENT])
        changed = changed_plain_pitch(bound, 74)
        after = realize(changed)
        expected = deepcopy(docs); note(expected, 0, 2, 0)['fret'] = 14
        self.assertEqual(project_documents(after), expected)
        report = policy.enforce_transition(bound, lower, after)
        self.assertEqual(report['status'], membership.IN_COLLECTION)
        self.assertEqual(report['spans'][0]['pitch'], '74')
        self.assertEqual(changed['source_origin'], upper['source_origin'])
        with self.assertRaisesRegex(ValueError, 'OUT_OF_COLLECTION'):
            policy.enforce_transition(bound, lower, realize(changed_plain_pitch(bound, 75)))

    def test_plain_hold_must_fit_later_context_not_only_its_onset(self):
        _, lower, upper = plain_fixture()
        selected = context(upper, [C_MAJOR])
        selected['contexts'][0]['end_q'] = '17/2'
        selected['contexts'].append(dict(id='later-minor', start_q='17/2', end_q='12', candidates=[C_MINOR]))
        bound = policy.attach(upper, context=selected, held_refs=[DEPENDENT])
        # E fits the context at q8 but not C minor from q8.5 through q9.
        with self.assertRaisesRegex(ValueError, 'OUT_OF_COLLECTION'):
            policy.enforce_transition(bound, lower, realize(changed_plain_pitch(bound, 76)))
        # D fits both, despite not belonging to the accompanying Cmaj7 chord.
        self.assertEqual(policy.enforce_transition(bound, lower, realize(changed_plain_pitch(bound, 74)))['status'],
                         membership.IN_COLLECTION)

    def test_direct_public_upper_motion_cannot_bypass_selected_hold_policy(self):
        import upper_voicing_motion as motion
        from test_upper_voicing_steps import stepped_fixture
        from test_upper_voicing_motion import TARGET as MOTION_TARGET, request
        _, _, upper, _ = stepped_fixture()
        for selected, failure in ((None, 'NOT_KEY_VERIFIED'), (context(upper), 'OUT_OF_COLLECTION')):
            with self.subTest(context_selected=selected is not None):
                bound = policy.attach(upper, context=selected, held_refs=[MOTION_TARGET[1]])
                snapshot = deepcopy(bound)
                self.assertEqual(motion.intervene(bound, request(0))[0], bound)
                # The public owner API changes the second held pitch to Bb;
                # it must enforce the saved preference without dispatcher help.
                with self.assertRaisesRegex(ValueError, failure):
                    motion.intervene(bound, request())
                self.assertEqual(bound, snapshot)

    def test_nested_melody_register_cancellation_checks_only_final_stable_pitches(self):
        import backing_motion_intervention as motion
        import figure_register_ownership as groups
        import observed_figure_register as register
        from test_observed_figure_register import (
            fixture as figure_fixture, fixture_documents, request, seed_for,
        )
        docs = fixture_documents()
        target = docs['track-0.json']['measures'][1]['voices'][0]['beats']
        for beat, (string, fret) in zip(target, ((2, 14), (3, 15), (2, 14))):
            beat['notes'][0] = dict(string=string, fret=fret)
        # Independent source observations make the returning octave available.
        docs['track-0.json']['measures'].append(dict(signature=[4, 4], voices=[dict(beats=[
            dict(duration=[1, 4], notes=[dict(string=2, fret=14)]),
            dict(duration=[1, 4], notes=[dict(string=3, fret=15)]),
            dict(duration=[1, 4], notes=[dict(string=2, fret=14)]),
            dict(duration=[1, 4], notes=[dict(string=3, fret=3)]),
        ])]))
        _, _, default = figure_fixture()
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(default['musical_relationships'])['relationships']]
        _, lower, full = figure_fixture(docs, bindings=bindings)
        upper = strip_lower(full)
        targets = request()['melody_controls']['target_refs']
        plain = deepcopy(upper)
        plain['musical_relationships'] = groups.expand(plain['musical_relationships'])
        middle, _ = motion.intervene(plain, request()['melody_controls'])
        expected_middle = deepcopy(docs)
        for beat in expected_middle['track-0.json']['measures'][1]['voices'][0]['beats'][:3]:
            beat['notes'][0]['fret'] -= 12
        self.assertEqual(project_documents(realize(middle)), expected_middle)
        prepared = register.prepare_original(upper, targets)
        options, _ = register.choices(prepared, realize(middle), targets)
        bound = policy.attach(upper, held_refs=targets)
        snapshot = deepcopy(bound)
        # With no selected context, the octave-down final result is refused.
        with self.assertRaisesRegex(ValueError, 'NOT_KEY_VERIFIED'):
            register.intervene(bound, request(0))
        # The same intermediate operation is valid inside the complete edit:
        # its register stage returns every protected pitch to its source value.
        final, decision = register.intervene(bound, request(seed=seed_for(options, 12)))
        self.assertEqual(realize(final), lower)
        self.assertEqual(decision['stable_pitch_check']['status'], 'UNCHANGED_SOURCE')
        self.assertTrue(decision['melody_changed'])
        self.assertTrue(decision['register_changed'])
        self.assertFalse(decision['changed'])
        self.assertEqual(final[policy.SLOT], bound[policy.SLOT])
        self.assertEqual(bound, snapshot)

    def test_unsupported_held_execution_and_duplicate_bend_scope_refuse(self):
        docs, _, upper = fixture()
        with self.assertRaisesRegex(ValueError, 'Distinct located plain hold'):
            policy.attach(upper, held_refs=[TARGET[0]])
        for field, value in [('vibrato', True), ('slide', 'shift'), ('harmonic', 'natural')]:
            with self.subTest(field=field):
                expressive = deepcopy(docs)
                note(expressive, 0, 2, 0)[field] = value
                _, plain = base_upper(expressive)
                with self.assertRaises(ValueError):
                    policy.attach(plain, held_refs=[DEPENDENT])

    def test_plain_tie_origin_cannot_omit_its_unselected_continuation(self):
        docs = documents()
        second = docs['track-0.json']['measures'][2]['voices'][0]['beats'][1]
        second['notes'] = [dict(string=0, fret=12, tie=True)]
        _, upper = base_upper(docs)
        # The origin does not carry tie=True, but its sounding hold continues.
        # The bounded plain-hold path must refuse rather than silently stop at q9.
        with self.assertRaises(ValueError):
            policy.attach(upper, held_refs=[DEPENDENT])

    def test_saved_held_reference_must_still_resolve_at_zero(self):
        _, _, upper = plain_fixture()
        bound = policy.attach(upper, context=context(upper), held_refs=[DEPENDENT])
        saved = json.loads(json.dumps(bound))
        saved[policy.SLOT]['held_refs'] = [DEPENDENT.replace(':3:', ':99:')]
        with self.assertRaises(ValueError):
            reconstruct(saved, {'variation': 0})

    def test_actual_source_denied_zero_changed_approach_and_refusal(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs, lower, upper = fixture()
        bound = policy.attach(upper, context=context(upper))
        code, _ = bundle(Path(__file__).parent)
        expected = extract_documents(expected_target(docs, fret=10, tone=50))
        with tempfile.TemporaryDirectory() as temporary:
            for name, request, output, accepted in (
                ('zero', controls(0), lower, True),
                ('arrival', controls(100, 'keep_arrival'), expected, True),
                ('excluded-arrival', controls(100, 'keep_start'), lower, False),
            ):
                with self.subTest(case=name):
                    folder = Path(temporary) / name
                    receipt = execute(code, bound, request, output, folder, timeout=45, purpose='bend_gesture')
                    audit_path = folder / 'worker/audit.json'
                    audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
                    self.assertEqual(receipt['status'] == 'PASS', accepted, (receipt, audit))
                    self.assertFalse(receipt['parent_expected_staged'])
                    if not accepted:
                        self.assertIsNotNone(audit, receipt)
                        self.assertIn('OUT_OF_COLLECTION', str(audit['error']))
                        self.assertFalse((folder / 'worker/output.json').exists())


if __name__ == '__main__':
    unittest.main()
