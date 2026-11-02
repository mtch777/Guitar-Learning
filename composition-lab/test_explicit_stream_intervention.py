"""Authored integration contracts for the explicit stream mode, not artist QA."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import backing_motion_intervention as motion
import backing_pitch_ownership as owner
from connected_tier2 import realize, reconstruct
from explicit_backing_stream import KIND
from source_fact_tier1 import extract_documents, project_documents
from test_backing_motion_intervention import SOURCE, TARGET
from test_explicit_backing_stream import ANCHOR, BACKING, fixture


def controls(level=100, physical=100, seed=0, **overrides):
    """Explicit caller intent; repeated held anchor IDs are deliberately valid."""
    result = dict(context_policy=motion.POLICY, melody=level, physical=physical,
                  source_refs=list(SOURCE), target_refs=list(TARGET), backing_part=1,
                  seed=seed, backing_mode=KIND, backing_voice=0,
                  source_backing_refs=[ANCHOR] * 3, target_backing_refs=list(BACKING))
    result.update(overrides)
    return result


def changed_truth(before):
    """Literal fixture answer, independent of the producer's chosen values."""
    docs = project_documents(before)
    beats = docs['track-0.json']['measures'][1]['voices'][0]['beats']
    beats[1]['notes'][0] = dict(string=3, fret=3)
    beats[2]['notes'][0] = dict(string=3, fret=7)
    return extract_documents(docs)


def owned_fixture(owned_time=False):
    before, upper = fixture(owned_time=owned_time)
    return before, motion.own_intervals(upper, motion.prepare(upper, controls()))


class ExplicitStreamInterventionTests(unittest.TestCase):
    def assert_six_interval_owners(self, upper):
        self.assertNotIn('input', upper)
        self.assertNotIn('derived_views', upper)
        wrapper = upper['musical_relationships']
        self.assertEqual(wrapper['schema'], owner.EXECUTION_SCHEMA)
        self.assertEqual(set(wrapper), {'schema', 'core', 'relationships',
                                        'written_tie_constraints', 'execution_constraints'})
        rows = wrapper['relationships']
        self.assertEqual({r['occurrence_ref'] for r in rows}, set(SOURCE + TARGET))
        self.assertEqual(len(rows), 6)
        refs = sorted(SOURCE + TARGET, key=owner.address)
        # This authored fixture has no incident execution declarations. The
        # complete saved contracts contain identities and predicates, not a
        # hidden backup of the six original pitches, frets or note objects.
        self.assertEqual(wrapper['execution_constraints'], dict(
            schema='backing-execution-constraints/1', owned_refs=refs, part_ids=[0],
            obligations=[], unresolved_outside_neighborhood=[],
            written_string_occupancy=dict(kind='owned_written_string_exclusivity',
                clock='half_open_written_intervals', all_voices=True,
                sounding_ring_end='not_inferred')))
        self.assertEqual(wrapper['written_tie_constraints'], dict(
            schema='backing-written-tie-constraints/1', relations=[],
            incidence=[dict(occurrence_ref=ref, relation_refs=[]) for ref in refs]))
        body = owner._body(wrapper['core']); index = owner._index(body)
        for ref in SOURCE + TARGET:
            group, member = index[ref]
            self.assertNotIn('bass_register_anchor', group)
            self.assertNotIn('interpretation', group)
            self.assertNotIn('pitch', member)
            self.assertNotIn('fret', member)
            self.assertEqual(member['voicing_interval'], '0')
            _, part, bar, voice, beat, note = owner.address(ref)
            fret = f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}/fret'
            self.assertFalse(any(r['fact_ref'] == fret for r in upper['owned_parameters']['source_choices']))
        self.assertTrue(all('value' not in r for r in upper['source_structure']['facts']))

    def test_default_sonority_mode_still_refuses_singletons(self):
        _, upper = fixture(); old = controls()
        for key in ('backing_mode', 'backing_voice', 'source_backing_refs', 'target_backing_refs'):
            old.pop(key)
        snapshot = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, 'INSUFFICIENT_DISTINCT_PITCH_MATCHES'):
            motion.intervene(upper, old)
        self.assertEqual(upper, snapshot)

    def test_explicit_mode_changes_only_literal_expected_source_fields(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                before, upper = fixture(owned_time=owned_time); snapshot = deepcopy(upper)
                with patch('melodic_contour_intervention.apply_pitch',
                           side_effect=AssertionError('Separate absolute pitch writer used')):
                    changed, decision = motion.intervene(upper, controls())
                self.assertEqual(decision['chosen']['pitches'], ['35', '31', '35'])
                self.assertEqual([r['match']['selected_delta'] for r in decision['correspondences']], [0, -2, 0])
                self.assertTrue(all(r['match']['kind'] == KIND for r in decision['correspondences']))
                self.assertTrue(decision['released']); self.assertTrue(decision['changed'])
                self.assertEqual(realize(changed), changed_truth(before))
                self.assertEqual(reconstruct(upper, controls()), changed_truth(before))
                self.assertEqual(realize(upper), before)
                self.assertEqual(upper, snapshot)
                self.assertEqual(changed['source_origin'], upper['source_origin'])
                self.assert_six_interval_owners(changed)

    def test_zero_literal_half_deterministic_branches_and_full_release(self):
        before, upper = owned_fixture(); snapshot = deepcopy(upper)
        self.assert_six_interval_owners(upper)
        zero, decision = motion.intervene(upper, controls(0, physical=0))
        self.assertEqual(zero, upper); self.assertEqual(realize(zero), before)
        self.assertFalse(decision['released']); self.assertFalse(decision['changed'])
        # Fixed authored sampler contrasts: seed0 retains, seed1 releases at50%.
        for seed, released in ((0, False), (1, True)):
            request = controls(50, seed=seed)
            half, decision = motion.intervene(upper, request)
            again, repeated = motion.intervene(upper, request)
            self.assertEqual((half, decision), (again, repeated))
            self.assertEqual(decision['released'], released)
            self.assertEqual(decision['changed'], released)
            self.assertEqual(realize(half), changed_truth(before) if released else before)
            if not released: self.assertEqual(half, upper)
        full, decision = motion.intervene(upper, controls(100))
        self.assertTrue(decision['released']); self.assertTrue(decision['changed'])
        self.assertEqual(realize(full), changed_truth(before))
        self.assertEqual(upper, snapshot)

    def test_physical_lock_refuses_without_partial_edit(self):
        _, upper = fixture(); snapshot = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, 'PHYSICAL_LOCK_CONFLICT'):
            motion.intervene(upper, controls(physical=0))
        self.assertEqual(upper, snapshot)

    def test_octave_permission_required_before_derived_register_change(self):
        def higher_target(docs):
            beats = docs['track-0.json']['measures'][1]['voices'][0]['beats']
            for beat, (string, fret) in zip(beats, [(0, 4), (0, 2), (1, 4)]):
                beat['notes'][0] = dict(string=string, fret=fret)
        before, upper = fixture(higher_target); snapshot = deepcopy(upper)
        for permission in (None, False):
            request = controls()
            if permission is not None: request['allow_note_octave_changes'] = permission
            with self.subTest(permission=permission), self.assertRaisesRegex(ValueError, 'NOTE_OCTAVE_PERMISSION_REQUIRED'):
                motion.intervene(upper, request)
            self.assertEqual(upper, snapshot)
        changed, decision = motion.intervene(upper, controls(allow_note_octave_changes=True))
        self.assertEqual(decision['chosen']['pitches'], ['35', '31', '35'])
        self.assertNotEqual(realize(changed), before)
        self.assertEqual(upper, snapshot)

    def test_malformed_or_mixed_controls_refuse_before_stream_choice(self):
        _, upper = fixture(); snapshot = deepcopy(upper); cases = []
        for value in (None, False, 'sonority_fallback', 'invented'):
            cases.append(controls(backing_mode=value))
        for value in (None, True, -1, 0.0, '0'):
            cases.append(controls(backing_voice=value))
        for key in ('backing_mode', 'backing_voice', 'source_backing_refs', 'target_backing_refs'):
            request = controls(); request.pop(key); cases.append(request)
        cases.extend([controls(source_backing_refs=None), controls(source_backing_refs=ANCHOR),
                      controls(source_backing_refs=[ANCHOR]), controls(target_backing_refs=BACKING + [BACKING[0]]),
                      controls(source_backing_refs=[False, ANCHOR, ANCHOR]),
                      controls(target_backing_refs=[None] + BACKING[1:]),
                      controls(melody=True), controls(melody=float('nan')), controls(seed=None)])
        for request in cases:
            for level in (0, 100):
                trial = deepcopy(request)
                if request['melody'] == 100: trial['melody'] = level
                with self.subTest(request=trial), patch('backing_motion_intervention.prepare',
                        side_effect=AssertionError('Malformed request reached choice preparation')), self.assertRaises(ValueError):
                    motion.intervene(upper, trial)
                self.assertEqual(upper, snapshot)

    def test_wrong_voice_future_expired_and_missing_identities_refuse(self):
        _, upper = fixture(); snapshot = deepcopy(upper)
        cases = [controls(backing_voice=1),
                 controls(target_backing_refs=[BACKING[1], BACKING[1], BACKING[2]]),
                 controls(target_backing_refs=[BACKING[0], BACKING[0], BACKING[2]]),
                 controls(target_backing_refs=['event:987:1:99:0:0:0'] + BACKING[1:]),
                 controls(source_backing_refs=['event:987:1:1:1:0:0'] * 3),
                 controls(source_backing_refs=[SOURCE[0]] * 3)]
        for request in cases:
            with self.subTest(request=request), self.assertRaises(ValueError):
                motion.intervene(upper, request)
            self.assertEqual(upper, snapshot)

    def test_duplicate_unisons_are_two_occurrences_not_a_single_line(self):
        def duplicate(docs):
            notes = docs['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']
            notes.append(deepcopy(notes[0]))
        _, upper = fixture(duplicate); snapshot = deepcopy(upper)
        with self.assertRaises(ValueError): motion.intervene(upper, controls())
        self.assertEqual(upper, snapshot)

    def test_target_pitch_does_not_choose_different_backing_identity(self):
        _, plain = fixture()
        a = motion.own_intervals(plain, motion.prepare(plain, controls(allow_note_octave_changes=True)))
        def other_target(docs):
            for beat in docs['track-0.json']['measures'][1]['voices'][0]['beats'][:3]:
                beat['notes'][0]['fret'] += 5
        _, changed_source = fixture(other_target)
        b = motion.own_intervals(changed_source, motion.prepare(changed_source, controls(allow_note_octave_changes=True)))
        identities = lambda upper: [(r['occurrence_ref'], r['backing_ref'])
                                    for r in upper['musical_relationships']['relationships']]
        self.assertEqual(identities(a), identities(b))
        self.assertEqual([r['backing_ref'] for r in a['musical_relationships']['relationships']
                          if r['occurrence_ref'] in SOURCE], [ANCHOR] * 3)

    def test_original_observations_stay_immutable_and_nonzero_chain_refuses(self):
        before, upper = fixture(); snapshot = deepcopy(upper)
        changed, _ = motion.intervene(upper, controls()); generated = deepcopy(changed)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
            motion.intervene(changed, controls(100))
        self.assertEqual(changed, generated)
        self.assertEqual(changed['source_origin'], upper['source_origin'])
        zero, decision = motion.intervene(changed, controls(0))
        self.assertEqual(zero, changed); self.assertFalse(decision['released'])
        self.assertEqual(realize(zero), changed_truth(before))
        self.assertEqual(upper, snapshot)

    def test_actual_isolated_zero_and_full_release_have_no_source_or_selected_answer(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code, modules = bundle(Path(__file__).parent)
        self.assertIn('explicit_backing_stream', modules)
        before, upper = owned_fixture(owned_time=True)
        self.assert_six_interval_owners(upper)
        with tempfile.TemporaryDirectory() as temp:
            for level, expected in ((0, before), (100, changed_truth(before))):
                with self.subTest(level=level):
                    out = Path(temp) / str(level)
                    result = execute(code, upper, controls(level), expected, out,
                                     timeout=45, purpose='observed_backing_motion')
                    audit_path = out / 'worker/audit.json'
                    audit = json.loads(audit_path.read_text(encoding='utf-8')) if audit_path.exists() else None
                    self.assertEqual(result['status'], 'PASS', dict(result=result, audit_error=audit and audit['error']))
                    self.assertFalse(result['parent_expected_staged'])
                    self.assertEqual(set(result['frozen_files']), {'input.json', 'relationships.py', 'worker.py'})
                    staged = json.loads((out / 'worker/input.json').read_text(encoding='utf-8'))
                    self.assertEqual(set(staged), {'upper', 'controls', 'purpose'})
                    self.assert_six_interval_owners(staged['upper'])
                    actual = json.loads((out / 'worker/output.json').read_text(encoding='utf-8'))
                    self.assertEqual(actual, expected)
                    self.assertIsNotNone(audit)
                    self.assertIsNone(audit['error'])
                    self.assertFalse(any(e['denied'] for e in audit['events']))


if __name__ == '__main__':
    unittest.main()
