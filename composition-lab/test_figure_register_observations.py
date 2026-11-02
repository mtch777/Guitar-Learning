"""Finite migration checklist: original bins, saved sequence, exact locks/refusals.

Authored fixtures test implementation; they are not fresh-song or listening QA.
"""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
import random
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest, require
import backing_pitch_ownership as backing
import figure_register_ownership as groups
import figure_register_observations as observations
import observed_figure_register as register
from test_observed_figure_register import fixture_documents, fixture as old_fixture, request
from test_backing_motion_intervention import TARGET


def fixture(docs=None, bindings=None):
    docs = fixture_documents() if docs is None else deepcopy(docs)
    # This pitch class is absent from the eventual melody: preparation must not
    # merely retain the bins convenient for its known answer.
    if docs['track-0.json']['measures'][-1]['voices'][0]['beats'][-1]['notes'][0] == dict(string=0, fret=4):
        docs['track-0.json']['measures'][-1]['voices'][0]['beats'][-1]['notes'][0] = dict(string=0, fret=1)
    docs, lower, legacy = old_fixture(docs, bindings=bindings)
    if bindings is None:
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(legacy['musical_relationships'])['relationships']]
    full = analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time',
                   backing_bindings=bindings, figure_register_refs=TARGET,
                   figure_register_evidence=True)
    return docs, lower, strip_lower(full), strip_lower(legacy), full


def standalone(level=100, seed=1, physical=100):
    return dict(context_policy=register.STANDALONE, register=level, seed=seed, physical=physical)


def current_facts_with_shift(current, shift):
    expected = deepcopy(current)
    wanted = {f'track-0.json#/measures/1/voices/0/beats/{i}/notes/0/fret' for i in range(3)}
    for row in expected['facts']:
        if row['id'] in wanted:
            row['value'] += shift
    return expected


class FigureRegisterObservationTests(unittest.TestCase):
    def assert_refuses(self, upper, controls, error):
        snapshot = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, error):
            register.intervene(upper, controls)
        self.assertEqual(upper, snapshot)

    def test_forward_all_original_bins_match_raw_fixture_and_not_only_answer_pcs(self):
        docs, before, upper, legacy, full = fixture()
        raw_counts = Counter()
        part = docs['track-0.json']
        for bar, measure in enumerate(part['measures'], 1):
            for voice, row in enumerate(measure['voices']):
                for beat, event in enumerate(row['beats']):
                    for note, contact in enumerate(event['notes']):
                        ref = f'event:987:0:{bar}:{voice}:{beat}:{note}'
                        if ref in TARGET or set(contact) != {'string', 'fret'}:
                            continue
                        pitch = part['tuning'][contact['string']] + contact['fret']
                        raw_counts[pitch % 12, pitch // 12 - 1] += 1
        table = upper['owned_parameters'][observations.SLOT]
        self.assertEqual(table['counts'], [dict(pitch_class=pc, octave=octave, count=count)
            for (pc, octave), count in sorted(raw_counts.items())])
        self.assertIn(8, {row['pitch_class'] for row in table['counts']})
        self.assertEqual(table['scope']['excluded_member_refs'], TARGET)
        self.assertEqual(realize(upper), before)
        self.assertEqual(validate(full), before)
        self.assertEqual(upper['musical_relationships'], legacy['musical_relationships'])
        encoded = json.dumps(table)
        for key in ('donor_refs', 'original', 'facts', 'events', 'documents', 'pitches'):
            self.assertNotIn('"' + key + '"', encoded)

    def test_all_zero_and_melody_only_zero_prepare_no_new_observations(self):
        _, before, upper, legacy, _ = fixture()
        table = deepcopy(upper['owned_parameters'][observations.SLOT])
        with patch.object(register, 'prepare_original', side_effect=AssertionError('Relearned source')):
            self.assertEqual(register.intervene(upper, request(0, 0))[0], upper)
            edited, _ = register.intervene(upper, request(0))
        old_edit, _ = register.intervene(legacy, request(0))
        self.assertEqual(realize(edited), realize(old_edit))
        self.assertNotEqual(realize(edited), before)
        self.assertEqual(edited['owned_parameters'][observations.SLOT], table)
        saved = json.loads(json.dumps(edited))
        self.assertEqual(register.intervene(saved, standalone(0))[0], saved)

    def test_saved_sequence_zero_fifty_hundred_equals_atomic_and_literal_raw_changes(self):
        _, _, upper, legacy, _ = fixture()
        snapshot = deepcopy(upper)
        edited, _ = register.intervene(upper, request(0))
        saved = json.loads(json.dumps(edited))
        current = realize(saved)
        releases = {0: [], 50: [], 100: []}
        for level in (0, 50, 100):
            for seed in (0, 1, 4):
                with self.subTest(level=level, seed=seed):
                    out, decision = register.intervene(saved, standalone(level, seed))
                    atomic, atomic_decision = register.intervene(upper, request(level, seed=seed))
                    old_atomic, _ = register.intervene(legacy, request(level, seed=seed))
                    self.assertEqual(out, atomic)
                    self.assertEqual(realize(out), realize(old_atomic))
                    rng = random.Random('figure-register:' + str(seed))
                    released = rng.random() < level / 100
                    shift = rng.choice([0, 12]) if released else 0
                    self.assertEqual(decision['released'], released)
                    self.assertEqual(realize(out), current_facts_with_shift(current, shift))
                    self.assertEqual(out['owned_parameters'][observations.SLOT],
                                     snapshot['owned_parameters'][observations.SLOT])
                    self.assertEqual(out['musical_relationships']['core'], saved['musical_relationships']['core'])
                    self.assertEqual(register.intervene(out, standalone(0))[0], out)
                    if level:
                        self.assertEqual([o['shift_semitones'] for o in decision['options']], [0, 12])
                        self.assertNotIn('donor_refs', decision['options'][0])
                        self.assertIn('observation_support', decision['options'][0])
                    releases[level].append(released)
        self.assertFalse(any(releases[0]))
        self.assertEqual(set(releases[50]), {False, True})
        self.assertTrue(all(releases[100]))
        self.assertEqual(upper, snapshot)
        self.assertEqual(saved, edited)

    def test_current_pitch_and_contact_context_not_original_target_contacts(self):
        _, _, upper, _, _ = fixture()
        edited, _ = register.intervene(upper, request(0))
        before_table = deepcopy(edited['owned_parameters'][observations.SLOT])
        # Same current B1 can occupy another valid declared string. This is a
        # synthetic current-state boundary check, not a new source observation.
        string_ref = 'track-0.json#/measures/1/voices/0/beats/0/notes/0/string'
        moved = deepcopy(edited)
        row = next(r for r in moved['owned_parameters']['source_choices'] if r['fact_ref'] == string_ref)
        row['parameter']['normalized'] = '3'
        current = realize(moved)
        with patch.object(register, 'prepare_original', side_effect=AssertionError('Relearned source')):
            higher, decision = register.intervene(moved, standalone())
        self.assertEqual(decision['choice']['contacts'][TARGET[0]], dict(string=3, fret=19))
        self.assertEqual(realize(higher), current_facts_with_shift(current, 12))
        self.assertEqual(higher['owned_parameters'][observations.SLOT], before_table)
        prepared = observations.prepare_current(higher, realize(higher), TARGET)
        options, _ = register.choices(prepared, realize(higher), TARGET)
        self.assertEqual([row['shift_semitones'] for row in options], [-12, 0])
        self.assertEqual(higher['owned_parameters'][observations.SLOT], before_table)

    def test_current_melody_changes_eligible_options_with_the_same_original_table(self):
        _, _, upper, _, _ = fixture()
        table = deepcopy(upper['owned_parameters'][observations.SLOT])
        before = realize(upper)
        original_options, _ = register.choices(observations.prepare_current(upper, before, TARGET), before, TARGET)
        edited, _ = register.intervene(upper, request(0))
        current = realize(edited)
        current_options, _ = register.choices(observations.prepare_current(edited, current, TARGET), current, TARGET)
        self.assertEqual(original_options, [])  # No independent source F#1 bin.
        self.assertEqual([row['shift_semitones'] for row in current_options], [0, 12])
        self.assertEqual(upper['owned_parameters'][observations.SLOT], table)
        self.assertEqual(edited['owned_parameters'][observations.SLOT], table)

    def test_legacy_edited_packet_still_refuses_and_zero_keeps_current(self):
        _, _, _, legacy, _ = fixture()
        edited, _ = register.intervene(legacy, request(0))
        self.assertEqual(register.intervene(edited, standalone(0))[0], edited)
        self.assert_refuses(edited, standalone(), 'UNSUPPORTED_CHAINED_EVIDENCE')

    def test_actual_source_denied_saved_zero_and_changed_register_workers(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        _, _, upper, _, _ = fixture()
        edited, _ = register.intervene(upper, request(0))
        saved = json.loads(json.dumps(edited))
        current = realize(saved)
        code, _ = bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as directory:
            for level, shift in ((0, 0), (100, 12)):
                expected = current_facts_with_shift(current, shift)
                receipt = execute(code, saved, standalone(level), expected,
                                  Path(directory) / str(level), timeout=120,
                                  purpose='guitar_figure_register')
                self.assertEqual(receipt['status'], 'PASS', receipt)
                actual = json.loads((Path(directory) / str(level) / 'worker/output.json').read_text())
                self.assertEqual(actual, expected)

    def test_current_physical_lock_and_other_nonzero_routes_refuse_atomically(self):
        _, _, upper, _, _ = fixture()
        edited, _ = register.intervene(upper, request(0))
        self.assert_refuses(edited, standalone(physical=0), 'PHYSICAL_CONTACT_LOCK')
        self.assert_refuses(edited, dict(standalone(), placement_policy='minimum_string_changes'),
                            'UNSUPPORTED_POLICY_SCOPE')
        self.assert_refuses(edited, request(), 'UNSUPPORTED_CHAINED_EVIDENCE')
        self.assert_refuses(edited, dict(standalone(), context_policy=register.EXPRESSIVE),
                            'UNSUPPORTED_POLICY_SCOPE')
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
            require(edited, dict(context_policy='source_local_note_accent', accents=100))

    def test_nonselected_parameter_change_refuses_before_choice_query(self):
        _, _, upper, _, _ = fixture()
        edited, _ = register.intervene(upper, request(0))
        corrupt = deepcopy(edited)
        row = next(r for r in corrupt['owned_parameters']['source_choices'] if r['fact_ref'] == 'track-0.json#/frets')
        row['parameter']['normalized'] = '25'
        realize(corrupt)  # Valid current source, but outside this retained scope.
        with patch.object(register, 'choices', side_effect=AssertionError('Choices queried before boundary')):
            self.assert_refuses(corrupt, standalone(), 'PROTECTED_STATE_CHANGED')

    def test_typed_table_and_integrity_refuse_without_recursive_inverse(self):
        _, _, upper, _, _ = fixture()
        model = upper['owned_parameters'][observations.SLOT]
        with patch('connected_tier2.realize', side_effect=AssertionError('Recursive validation')):
            observations.validate(model, upper['source_origin'])
        for mutation, rehash in (
                (lambda m: m['counts'][0].update(count=True), True),
                (lambda m: m['counts'][0].update(count=0), True),
                (lambda m: m['counts'][0].update(pitch_class=12), True),
                (lambda m: m['counts'].append(deepcopy(m['counts'][0])), True),
                (lambda m: m['scope'].update(part_id=1), True),
                (lambda m: m['counts'][0].update(count=999), False),
                (lambda m: m.update(original=[]), True)):
            corrupt = deepcopy(upper)
            table = corrupt['owned_parameters'][observations.SLOT]
            mutation(table)
            if rehash:
                table['evidence_sha256'] = digest(observations.evidence(table))
            with self.assertRaises(ValueError):
                realize(corrupt)
        # Coordinated malicious rehashing of a plausible table is not an
        # authenticity claim made by this integrity contract.

    def test_normalization_keeps_group_identity_links_and_unrelated_authorities(self):
        _, _, upper, _, _ = fixture()
        table = upper['owned_parameters'][observations.SLOT]
        plain = deepcopy(upper)
        plain['musical_relationships'] = groups.expand(plain['musical_relationships'])
        self.assertEqual(observations.protected_state(plain, table['scope']),
                         observations.protected_state(upper, table['scope']))
        for ref in [TARGET[0], upper['musical_relationships']['core']['relationships'][0]['occurrence_ref']]:
            corrupt = deepcopy(upper)
            link = next(r for r in corrupt['musical_relationships']['core']['relationships'] if r['occurrence_ref'] == ref)
            other = next(candidate for candidate in ('event:987:1:1:0:0:0', 'event:987:1:1:0:0:1')
                         if candidate != link['backing_ref'])
            link['backing_ref'] = other
            with self.assertRaises(ValueError):
                observations.validate_current(corrupt)
        corrupt = deepcopy(upper)
        corrupt['musical_relationships']['groups'][0]['id'] = 'figure-register:' + '0' * 64
        with self.assertRaises(ValueError):
            observations.validate_current(corrupt)

    def test_unrelated_link_survives_and_still_propagates_after_the_sequence(self):
        from test_backing_relationship_preservation import EXTRA, INDEPENDENT
        docs = fixture_documents()
        docs['metadata.json']['tracks'].append(dict(name='Independent bass', instrumentId=34))
        docs['track-2.json'] = deepcopy(docs['track-0.json'])
        docs['track-2.json'].update(partId=2, instrumentId=34)
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp'] = True
        _, _, baseline = old_fixture(docs)
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(baseline['musical_relationships'])['relationships']]
        bindings.append(dict(occurrence_ref=EXTRA, backing_ref=INDEPENDENT))
        _, _, upper, _, _ = fixture(docs, bindings)
        original_link = next(r for r in groups.expand(upper['musical_relationships'])['relationships']
                             if r['occurrence_ref'] == EXTRA)
        melody, _ = register.intervene(upper, request(0))
        saved = json.loads(json.dumps(melody))
        higher, _ = register.intervene(saved, standalone())
        expanded = groups.expand(higher['musical_relationships'])
        self.assertEqual(next(r for r in expanded['relationships'] if r['occurrence_ref'] == EXTRA), original_link)
        self.assertEqual(higher['musical_relationships']['core'], upper['musical_relationships']['core'])
        moved = deepcopy(higher)
        body = backing._body(moved['musical_relationships']['core']['core'])
        group, _ = backing._index(body)[INDEPENDENT]
        group['bass_register_anchor'] = str(F(group['bass_register_anchor']) + 1)
        before_docs, after_docs = project_documents(realize(higher)), project_documents(realize(moved))
        old_note = before_docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        new_note = after_docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(new_note, dict(old_note, fret=old_note['fret'] + 1))
        self.assertEqual(moved['owned_parameters'][observations.SLOT], higher['owned_parameters'][observations.SLOT])
        self.assert_refuses(moved, standalone(), 'PROTECTED_STATE_CHANGED')

    def test_original_execution_linked_donor_endpoints_stay_excluded(self):
        docs = fixture_documents()
        docs['track-0.json']['measures'][2]['voices'][0]['beats'][1]['notes'][0]['hp'] = True
        _, _, upper, _, _ = fixture(docs)
        keys = {(r['pitch_class'], r['octave']) for r in upper['owned_parameters'][observations.SLOT]['counts']}
        self.assertNotIn((7, 2), keys)  # Plain-looking incoming HP endpoint G2.

    def test_forward_flag_requires_typed_explicit_plain_group(self):
        lower = extract_documents(fixture_documents())
        for value in (None, 1, True):
            with self.assertRaisesRegex(ValueError, 'Original register observations'):
                analyze(lower, figure_register_evidence=value)


if __name__ == '__main__':
    unittest.main()
