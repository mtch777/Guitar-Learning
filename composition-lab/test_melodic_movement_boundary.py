"""Exercise the actual shared inverse/worker and saved tonal-policy boundary."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import connected_tier2 as connected
import melodic_movement_ownership as movement
import stable_pitch_policy as preference
from qa_isolation_harness import execute, validate_request
from run_connected_tier2_qa import bundle
from test_melodic_movement_ownership import build, controls, documents, TARGET, REFERENCE, set_pitches
from source_fact_tier1 import extract_documents


class MovementBoundaryTests(unittest.TestCase):
    def test_v2_four_states_and_saved_current_zero_in_actual_worker(self):
        runtime = dict(implementation=sys.implementation.name, version=list(sys.version_info[:3]),
                       executable=str(Path(sys.executable).resolve()))
        code, _ = bundle(Path(__file__).parent)
        checksum = hashlib.sha256(code.encode()).hexdigest()
        for coattack in (False, True):
            docs = documents()
            if coattack:
                for beat in docs['track-0.json']['measures'][1]['voices'][0]['beats'][:3]:
                    beat['notes'] += [dict(string=5, fret=25), dict(string=1, fret=19)]
            original = extract_documents(docs)
            plain = connected.strip_lower(connected.analyze(original))
            owned = movement.lift(plain, TARGET, reference_attack_refs=REFERENCE, register_controls=True)
            before = deepcopy(owned)
            with tempfile.TemporaryDirectory() as folder:
                for m, r, pitches in [(0,0,[60,61,62]), (100,0,[60,67,58]),
                                      (0,100,[72,73,74]), (100,100,[72,79,70])]:
                    request = dict(controls(m, 'follow_reference_motion', 0), register=r, register_direction='up')
                    expected_docs = set_pitches(docs, pitches)
                    if coattack and m:
                        # Written58 on string0 would span17 frets against the
                        # retained25/19 contacts, above this source's15. String1
                        # is occupied; string2/fret18 is the nearest feasible
                        # alternative. The later octave release can retain that
                        # string at fret30. Identity remains the SAME note0.
                        note = expected_docs['track-0.json']['measures'][1]['voices'][0]['beats'][2]['notes'][0]
                        note.update(string=2, fret=pitches[2]-40)
                    expected = extract_documents(expected_docs)
                    edited, decision = movement.intervene(owned, request)
                    self.assertEqual(connected.realize(edited), expected)
                    self.assertEqual(owned, before)
                    self.assertEqual(decision['changed'], bool(m or r))
                    self.assertEqual(edited['owned_parameters'][movement.SLOT]['observations'],
                                     owned['owned_parameters'][movement.SLOT]['observations'])
                    receipt = execute(code, owned, request, expected, Path(folder)/f'{m}-{r}', timeout=30,
                        purpose='melodic_movement', expected_runtime=runtime, expected_operator_sha256=checksum)
                    self.assertEqual(receipt['status'], 'PASS', receipt)
                    if m and r:
                        saved = json.loads(json.dumps(edited))
                        receipt = execute(code, saved, dict(variation=0), expected, Path(folder)/'saved-zero',
                            timeout=30, expected_runtime=runtime, expected_operator_sha256=checksum)
                        self.assertEqual(receipt['status'], 'PASS', receipt)

    def test_same_shared_inverse_zero_nonzero_saved_and_isolated(self):
        _, original, _, owned = build(references=REFERENCE, unrelated=True)
        self.assertEqual(connected.validate(owned), original)
        self.assertNotIn('input', owned)
        before = deepcopy(owned)
        runtime = dict(implementation=sys.implementation.name, version=list(sys.version_info[:3]),
                       executable=str(Path(sys.executable).resolve()))
        code, _ = bundle(Path(__file__).parent)
        checksum = hashlib.sha256(code.encode()).hexdigest()
        for level in (0, 50, 100):
            request = controls(level, 'follow_reference_motion')
            edited, decision = movement.intervene(owned, request)
            lower = connected.reconstruct(owned, request)
            self.assertEqual(connected.realize(edited), lower)
            self.assertEqual(owned, before)
            self.assertEqual(edited['source_origin'], owned['source_origin'])
            saved = json.loads(json.dumps(edited))
            self.assertEqual(connected.reconstruct(saved, dict(variation=0)), lower)
            with tempfile.TemporaryDirectory() as folder:
                actual = execute(code, owned, request, lower, Path(folder)/'worker-run', timeout=30,
                                 purpose='melodic_movement', expected_runtime=runtime,
                                 expected_operator_sha256=checksum)
                self.assertEqual(actual['status'], 'PASS', actual)
            if level == 0:
                self.assertFalse(decision['changed'])
                self.assertEqual(lower, original)
            if level == 100:
                self.assertTrue(decision['changed'])

    def test_unresolved_saved_pitch_preference_cannot_be_bypassed(self):
        _, original, _, owned = build(references=REFERENCE)
        owned = preference.attach(owned, held_refs=TARGET)
        before = deepcopy(owned)
        self.assertEqual(connected.reconstruct(owned, controls(0)), original)
        for operation in (movement.intervene, connected.reconstruct):
            with self.assertRaises(ValueError):
                operation(owned, controls(100, 'follow_reference_motion'))
            self.assertEqual(owned, before)

    def test_worker_rejects_bad_controls_before_loading_code(self):
        good = controls()
        validate_request('melodic_movement', good)
        for key, value in [('melody', True), ('melody', -1), ('melody', 101),
                           ('seed', '1'), ('intent', 'desired_pitch')]:
            bad = dict(good, **{key: value})
            with self.assertRaises(ValueError):
                validate_request('melodic_movement', bad)
        with self.assertRaises(ValueError):
            validate_request('melodic_movement', dict(good, pitch=60))

    def test_worker_register_packet_keeps_values_out_and_validates_both_releases(self):
        good = dict(controls(), register=100, register_direction='up')
        validate_request('melodic_movement', good)
        validate_request('melodic_movement', dict(good, melody=0, register=0))
        for field, value in [('register', True), ('register', -1), ('register', 101),
                             ('register', 50.0), ('register_direction', 'octave4'),
                             ('melody', True), ('seed', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_request('melodic_movement', dict(good, **{field:value}))
        for extra in ('pitch', 'octave', 'contacts', 'source_path'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_request('melodic_movement', dict(good, **{extra:12}))
        for missing in ('register', 'register_direction'):
            bad = dict(good); bad.pop(missing)
            with self.assertRaises(ValueError):
                validate_request('melodic_movement', bad)


if __name__ == '__main__':
    unittest.main()
