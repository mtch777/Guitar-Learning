"""Authored controls/ownership tests; no listening or artist claims."""
from copy import deepcopy
import json
import random
import unittest
from unittest.mock import patch
from fractions import Fraction

from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents
import backing_motion_intervention as motion
import backing_pitch_ownership as backing
import figure_register_ownership as groups
import observed_figure_register as register
from check_technique_connections import check
from test_backing_motion_intervention import documents, controls, TARGET


def fixture_documents():
    docs = documents()
    docs['metadata.json']['tracks'][0] = dict(name='Lead guitar', instrumentId=27)
    docs['track-0.json']['instrumentId'] = 27
    docs['track-0.json']['measures'].append(dict(signature=[4, 4], voices=[dict(beats=[
        dict(duration=[1, 4], notes=[dict(string=3, fret=3)]),
        dict(duration=[1, 4], notes=[dict(string=0, fret=4)]),
        dict(duration=[1, 4], notes=[dict(string=0, fret=0)]),
        dict(duration=[1, 4], notes=[dict(string=0, fret=4)]),
    ])]))
    return docs


def fixture(docs=None, *, bindings=None):
    docs = fixture_documents() if docs is None else deepcopy(docs)
    lower = extract_documents(docs)
    if bindings is None:
        upper = strip_lower(analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time'))
        owned = motion.own_intervals(upper, motion.prepare(upper, controls()))
        bindings = [{k: v for k, v in row.items() if k != 'interval_semitones'}
                    for row in owned['musical_relationships']['relationships']]
    full = analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time',
                   backing_bindings=bindings, figure_register_refs=TARGET)
    return docs, lower, full


def request(level=100, melody=100, seed=0, physical=100):
    return dict(context_policy=register.POLICY, register=level, seed=seed,
                melody_controls=dict(controls(melody, physical=physical), allow_note_octave_changes=True))


def seed_for(options, shift, level=100):
    for seed in range(256):
        rng = random.Random('figure-register:' + str(seed))
        if rng.random() < level / 100 and rng.choice(options)['shift_semitones'] == shift:
            return seed
    raise AssertionError('Requested authored outcome was not sampled')


class ObservedFigureRegisterTests(unittest.TestCase):
    def test_standalone_zero_fifty_hundred_never_requests_a_melody_reference(self):
        docs = fixture_documents()
        docs['track-0.json']['measures'].append(dict(signature=[4, 4], voices=[dict(beats=[
            dict(duration=[1, 4], notes=[dict(string=0, fret=2)]),
            dict(duration=[1, 4], notes=[dict(string=1, fret=4)]),
            dict(duration=[1, 4], notes=[dict(string=0, fret=4)]),
            dict(duration=[1, 4], notes=[dict(string=3, fret=2)]),
        ])]))
        _, before, full = fixture(docs); upper = strip_lower(full)
        prepared = register.prepare_original(upper, TARGET)
        options, _ = register.choices(prepared, before, TARGET)
        self.assertEqual({row['shift_semitones'] for row in options}, {0, 12})
        original = deepcopy(upper)
        with patch.object(motion, 'prepare', side_effect=AssertionError('Unused melody reference requested')), \
             patch.object(motion, 'intervene', side_effect=AssertionError('Melody operation called')):
            for level in (0, 50, 100):
                seed = 0 if level == 0 else seed_for(options, 12, level)
                control = dict(context_policy=register.STANDALONE, register=level, physical=100, seed=seed)
                edited, result = register.intervene(upper, control)
                if level == 0:
                    self.assertEqual(edited, upper)
                else:
                    self.assertEqual(result['choice']['shift_semitones'], 12)
                    old_group = upper['musical_relationships']['groups'][0]
                    new_group = edited['musical_relationships']['groups'][0]
                    self.assertEqual(new_group['octave'], old_group['octave'] + 1)
                    self.assertEqual(new_group['offsets_semitones'], old_group['offsets_semitones'])
                    self.assertEqual(new_group['interval_class'], old_group['interval_class'])
                    groups.assert_preserved(upper['musical_relationships'], edited['musical_relationships'],
                                            mutable_groups=[old_group['id']])
                    self.assertEqual(reconstruct(upper, control), realize(edited))
            coincident = dict(context_policy=register.STANDALONE, register=100, physical=0,
                              seed=seed_for(options, 0))
            self.assertEqual(register.intervene(upper, coincident)[0], upper)
            conflict = dict(coincident, seed=seed_for(options, 12))
            self.assert_atomic_refusal(upper, conflict, 'PHYSICAL_CONTACT_LOCK')
        self.assertEqual(upper, original)

    def test_standalone_does_not_accept_extra_reference_or_answer_fields(self):
        _, _, full = fixture(); upper = strip_lower(full)
        control = dict(context_policy=register.STANDALONE, register=100, physical=100, seed=0)
        for extra in ({'melody_controls': controls()}, {'shift_semitones': 12}, {'octave': 1}):
            self.assert_atomic_refusal(upper, dict(control, **extra), 'EXPLICIT_FIGURE_REGISTER_CONTROLS')

    def assert_atomic_refusal(self, upper, controls, reason):
        snapshot = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, reason):
            register.intervene(upper, controls)
        self.assertEqual(upper, snapshot)

    def test_forward_owns_group_and_zero_keeps_original_destination(self):
        docs, lower, full = fixture()
        self.assertEqual(full['musical_relationships']['core']['schema'], backing.EXECUTION_SCHEMA)
        self.assertIn('execution_constraints', full['musical_relationships']['core'])
        self.assertEqual(validate(full), lower)
        self.assertEqual(check(docs, full)['status'], 'PASS_SOURCE_BACKED_RELATIONSHIPS')
        upper = strip_lower(full)
        self.assertEqual(reconstruct(upper, request(0, 0)), lower)
        self.assertEqual(register.intervene(upper, request(0, 0))[0], upper)

    def test_compound_uses_immutable_evidence_and_one_persisted_parameter(self):
        docs, before, full = fixture()
        upper = strip_lower(full); snapshot = deepcopy(upper)
        prepared = register.prepare_original(upper, TARGET)
        plain = deepcopy(upper); plain['musical_relationships'] = groups.expand(upper['musical_relationships'])
        melody, _ = motion.intervene(plain, request()['melody_controls'])
        current = realize(melody)
        options, _ = register.choices(prepared, current, TARGET)
        self.assertEqual({row['shift_semitones'] for row in options}, {0, 12})
        for level in (50, 100):
            with self.subTest(level=level):
                changed, decision = register.intervene(upper, request(level, seed=seed_for(options, 12, level)))
                self.assertEqual(decision['choice']['shift_semitones'], 12)
                self.assertEqual(changed['source_origin'], upper['source_origin'])
                old = {r['id']: r for r in current['facts']}
                new = {r['id']: r for r in realize(changed)['facts']}
                wanted = {motion.pointer(prepared['events'][ref]) + '/fret' for ref in TARGET}
                self.assertEqual({key for key in old if old[key] != new[key]}, wanted)
                for key in wanted:
                    self.assertEqual(new[key]['value'] - old[key]['value'], 12)
                self.assertEqual(changed['musical_relationships']['core'], upper['musical_relationships']['core'])
                expanded = groups.expand(changed['musical_relationships'])
                backing.assert_preserved(plain['musical_relationships'], expanded, mutable_refs=TARGET)
                saved = json.loads(json.dumps(changed))
                self.assertEqual(realize(saved), realize(changed))
                self.assertEqual(register.intervene(saved, request(0, 0))[0], saved)
                with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
                    register.intervene(saved, request())
        self.assertEqual(upper, snapshot)
        self.assertEqual(realize(upper), before)

    def test_unlock_can_keep_current_register(self):
        _, _, full = fixture(); upper = strip_lower(full)
        prepared = register.prepare_original(upper, TARGET)
        plain = deepcopy(upper); plain['musical_relationships'] = groups.expand(upper['musical_relationships'])
        melody, _ = motion.intervene(plain, request()['melody_controls'])
        options, _ = register.choices(prepared, realize(melody), TARGET)
        changed, decision = register.intervene(upper, request(seed=seed_for(options, 0)))
        self.assertTrue(decision['released']); self.assertTrue(decision['changed'])
        self.assertTrue(decision['melody_changed']); self.assertFalse(decision['register_changed'])
        self.assertEqual(realize(changed), realize(melody))

    def test_wrong_group_or_instrument_refuses_without_mutation(self):
        _, _, full = fixture(); upper = strip_lower(full); snapshot = deepcopy(upper)
        wrong = request(); wrong['melody_controls']['target_refs'] = list(reversed(TARGET))
        with self.assertRaises(ValueError): register.intervene(upper, wrong)
        self.assertEqual(upper, snapshot)
        wrong = request(); wrong['register'] = True
        self.assert_atomic_refusal(upper, wrong, 'FINITE_REGISTER_RELEASE_AND_INTEGER_SEED_REQUIRED')
        docs = fixture_documents()
        docs['track-0.json']['instrumentId'] = 34
        _, before, full = fixture(docs); upper = strip_lower(full)
        self.assertEqual(reconstruct(upper, request(0, 0)), before)
        self.assert_atomic_refusal(upper, request(), 'OUTSIDE_DECLARED_GUITAR_PROGRAM_SCOPE')

    def test_register_cannot_bypass_the_physical_lock_when_melody_is_locked(self):
        docs = fixture_documents()
        # Each ORIGINAL destination pitch has an independent +12 observation.
        # This isolates the register permission from the melody permission.
        docs['track-0.json']['measures'].append(dict(signature=[4, 4], voices=[dict(beats=[
            dict(duration=[1, 4], notes=[dict(string=0, fret=4)]),  # B2
            dict(duration=[1, 4], notes=[dict(string=0, fret=2)]),  # A2
            dict(duration=[1, 4], notes=[dict(string=1, fret=4)]),  # F#2
            dict(duration=[1, 4], notes=[dict(rest=True)]),
        ])]))
        _, before, full = fixture(docs); upper = strip_lower(full)
        options, _ = register.choices(register.prepare_original(upper, TARGET), before, TARGET)
        self.assertEqual({row['shift_semitones'] for row in options}, {12})
        for level in (50, 100):
            seed = seed_for(options, 12, level)
            self.assert_atomic_refusal(upper, request(level, melody=0, physical=0, seed=seed),
                                       'FIGURE_REGISTER_PHYSICAL_CONTACT_LOCK')
            changed, decision = register.intervene(upper, request(level, melody=0, seed=seed))
            self.assertTrue(decision['changed'])
            expected = deepcopy(docs)
            for beat in expected['track-0.json']['measures'][1]['voices'][0]['beats'][:3]:
                beat['notes'][0]['fret'] += 12
            self.assertEqual(project_documents(realize(changed)), expected)
        self.assertEqual(register.intervene(upper, request(0, melody=0, physical=0))[0], upper)

    def test_group_must_exist_before_zero_or_release_and_have_the_exact_scope(self):
        _, _, full = fixture(); upper = strip_lower(full)
        ungrouped = deepcopy(upper)
        ungrouped['musical_relationships'] = groups.expand(upper['musical_relationships'])
        for level in (0, 50, 100):
            self.assert_atomic_refusal(ungrouped, request(level, melody=0), 'PREOWNED_FIGURE_GROUP_REQUIRED')
            wrong = request(level, melody=0)
            wrong['melody_controls']['target_refs'] = [f'event:987:0:3:0:{i}:0' for i in range(3)]
            self.assert_atomic_refusal(upper, wrong, 'EXACT_EXISTING_FIGURE_SCOPE_REQUIRED')

    def test_no_register_donor_does_not_invent_one_or_cancel_the_melody_result(self):
        docs = fixture_documents()
        # No G in this part outside the selected destination after melody moves.
        for beat in docs['track-0.json']['measures'][2]['voices'][0]['beats']:
            beat['notes'][0] = dict(string=0, fret=6)
        _, _, full = fixture(docs); upper = strip_lower(full)
        plain = deepcopy(upper); plain['musical_relationships'] = groups.expand(upper['musical_relationships'])
        melody, _ = motion.intervene(plain, request()['melody_controls'])
        changed, decision = register.intervene(upper, request())
        self.assertTrue(decision['released'])
        self.assertTrue(decision['changed'])
        self.assertFalse(decision['register_changed'])
        self.assertEqual(decision['options'], [])
        self.assertIsNone(decision['choice'])
        self.assertEqual(realize(changed), realize(melody))
        self.assertEqual(changed['source_origin'], upper['source_origin'])

    def test_only_current_register_is_a_valid_100_percent_result(self):
        docs = fixture_documents()
        for beat in docs['track-0.json']['measures'][2]['voices'][0]['beats']:
            beat['notes'][0] = dict(string=3, fret=3)
        _, _, full = fixture(docs); upper = strip_lower(full)
        changed, decision = register.intervene(upper, request())
        self.assertEqual([row['shift_semitones'] for row in decision['options']], [0])
        self.assertTrue(decision['released']); self.assertTrue(decision['changed'])
        self.assertFalse(decision['register_changed'])
        self.assertEqual(decision['choice']['shift_semitones'], 0)
        self.assertNotEqual(realize(changed), realize(upper))  # Melody did change.

    def test_forged_original_observation_hash_refuses_atomically(self):
        _, _, full = fixture(); upper = strip_lower(full)
        for fingerprint in ('0' * 64, 'not-a-hash'):
            corrupt = deepcopy(upper)
            corrupt['source_origin']['facts_sha256'] = fingerprint
            self.assert_atomic_refusal(corrupt, request(),
                                       'UNSUPPORTED_CHAINED_EVIDENCE|Typed original-observation origin required')

    def test_execution_linked_donors_are_not_source_votes(self):
        docs = fixture_documents()
        beats = docs['track-0.json']['measures'][2]['voices'][0]['beats']
        # The apparent G2 observation is an incoming pull-off endpoint. Its
        # notation looks plain, but it is not an independent donor occurrence.
        beats[1]['notes'][0]['hp'] = True
        _, _, full = fixture(docs); upper = strip_lower(full)
        prepared = register.prepare_original(upper, TARGET)
        excluded = {row['ref']: row['reason'] for row in prepared['excluded']}
        self.assertIn('event:987:0:3:0:2:0', excluded)
        self.assertNotIn(43, prepared['donors'])
        _, decision = register.intervene(upper, request())
        self.assertEqual([row['shift_semitones'] for row in decision['options']], [0])

    def test_dependency_target_is_refused_even_if_group_has_exact_zero(self):
        _, _, baseline = fixture()
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(baseline['musical_relationships'])['relationships']]
        docs = fixture_documents()
        # Written pull-off between the first two destination notes on string2.
        docs['track-0.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['hp'] = True
        _, before, full = fixture(docs, bindings=bindings); upper = strip_lower(full)
        self.assertEqual(reconstruct(upper, request(0, 0)), before)
        self.assert_atomic_refusal(upper, request(100, melody=0), 'FIGURE_EXECUTION_DEPENDENCY')

    def test_written_tie_origin_is_not_a_plain_donor_or_mutable_target(self):
        _, _, baseline = fixture()
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(baseline['musical_relationships'])['relationships']]
        docs = fixture_documents()
        beats = docs['track-0.json']['measures'][2]['voices'][0]['beats']
        beats[1]['notes'][0] = dict(string=0, fret=0)
        beats[2]['notes'][0] = dict(string=0, fret=0, tie=True)
        _, _, full = fixture(docs, bindings=bindings); upper = strip_lower(full)
        prepared = register.prepare_original(upper, TARGET)
        excluded = {row['ref'] for row in prepared['excluded']}
        self.assertTrue({'event:987:0:3:0:1:0', 'event:987:0:3:0:2:0'} <= excluded)
        self.assertNotIn(43, prepared['donors'])
        _, decision = register.intervene(upper, request())
        self.assertEqual([row['shift_semitones'] for row in decision['options']], [0])

        docs = fixture_documents()
        beats = docs['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[1]['notes'][0] = dict(string=2, fret=2, tie=True)
        _, before, full = fixture(docs, bindings=bindings); upper = strip_lower(full)
        self.assertEqual(reconstruct(upper, request(0, 0)), before)
        self.assert_atomic_refusal(upper, request(100, melody=0), 'FIGURE_EXECUTION_DEPENDENCY')

    def test_unrelated_owner_and_execution_guard_survive_and_remain_effective(self):
        from test_backing_relationship_preservation import EXTRA, INDEPENDENT
        docs = fixture_documents()
        docs['metadata.json']['tracks'].append(dict(name='Independent bass', instrumentId=34))
        docs['track-2.json'] = deepcopy(docs['track-0.json'])
        docs['track-2.json'].update(partId=2, instrumentId=34)
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp'] = True
        _, _, baseline = fixture()
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(baseline['musical_relationships'])['relationships']]
        bindings.append(dict(occurrence_ref=EXTRA, backing_ref=INDEPENDENT))
        _, before, full = fixture(docs, bindings=bindings); upper = strip_lower(full)
        stronger = backing.extend_bindings(groups.expand(upper['musical_relationships']),
                                           bindings, tier1=before, preserve_execution=True)
        upper['musical_relationships'] = groups.lift(stronger, TARGET)
        original = deepcopy(upper)
        old_row = next(row for row in stronger['relationships'] if row['occurrence_ref'] == EXTRA)
        prepared = register.prepare_original(upper, TARGET)
        plain = deepcopy(upper); plain['musical_relationships'] = stronger
        melody, _ = motion.intervene(plain, request()['melody_controls'])
        options, _ = register.choices(prepared, realize(melody), TARGET)
        changed, _ = register.intervene(upper, request(seed=seed_for(options, 12)))
        expanded = groups.expand(changed['musical_relationships'])
        self.assertEqual(next(row for row in expanded['relationships'] if row['occurrence_ref'] == EXTRA), old_row)
        self.assertEqual(changed['musical_relationships']['core'], upper['musical_relationships']['core'])
        self.assertEqual(upper, original)
        # Behavioral proof: this old owner still follows its independent
        # backing pitch after the new register change, rather than a snapshot.
        moved = deepcopy(changed)
        body = backing._body(moved['musical_relationships']['core']['core'])
        group, _ = backing._index(body)[INDEPENDENT]
        group['bass_register_anchor'] = str(Fraction(group['bass_register_anchor']) + 1)
        before_docs = project_documents(realize(changed)); after_docs = project_documents(realize(moved))
        old_note = before_docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        new_note = after_docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(new_note, dict(old_note, fret=old_note['fret'] + 1))


if __name__ == '__main__':
    unittest.main()
