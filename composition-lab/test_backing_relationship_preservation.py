"""Preserve pre-existing musical authority when adding backing relationships.

Authored fixtures only. A note-by-note round trip alone cannot detect a lost
relationship: later movement of its backing note must still move the dependent.
"""
from copy import deepcopy
from fractions import Fraction as F
import unittest
import json
from pathlib import Path
import tempfile

import backing_motion_intervention as motion
import backing_pitch_ownership as owner
import musical_tier2 as music
from canonical_backing_bindings import canonical_bindings
from connected_tier2 import analyze, strip_lower, realize, validate
from source_fact_tier1 import extract_documents, project_documents
from test_backing_motion_intervention import documents, controls, SOURCE, TARGET

EXTRA = 'event:987:2:1:0:0:0'
INDEPENDENT = 'event:987:1:1:0:0:0'


def fixture(bindings=None, *, owned_time=False, execution=False):
    docs = documents()
    docs['metadata.json']['tracks'].append(dict(name='Unrelated bass', instrumentId=34))
    docs['track-2.json'] = deepcopy(docs['track-0.json'])
    docs['track-2.json']['partId'] = 2
    if execution:
        # This old, unrelated relationship already carries a real execution
        # obligation: B1 -> A1 on one string is a source-written pull-off.
        docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp'] = True
    before = extract_documents(docs)
    upper = strip_lower(analyze(before, rhythm_groups=owned_time,
        rhythm_group_profile='written_time' if owned_time else 'plain_repeat'))
    upper['musical_relationships'] = owner.lift(upper['musical_relationships'],
        [dict(occurrence_ref=EXTRA, backing_ref=INDEPENDENT)] if bindings is None else bindings,
        tier1=before, preserve_execution=execution)
    return docs, before, upper


def expected_edit(docs):
    expected = deepcopy(docs)
    beats = expected['track-0.json']['measures'][1]['voices'][0]['beats']
    beats[1]['notes'][0] = dict(string=3, fret=3)
    beats[2]['notes'][0] = dict(string=3, fret=7)
    return extract_documents(expected)


def rows(upper):
    return {r['occurrence_ref']: r for r in upper['musical_relationships']['relationships']}


def shift_independent(upper, delta):
    changed = deepcopy(upper)
    group, _ = owner._index(owner._body(changed['musical_relationships']['core']))[INDEPENDENT]
    group['bass_register_anchor'] = str(F(group['bass_register_anchor']) + delta)
    return changed


def pitch(upper, ref):
    expanded = owner._normal(owner.expand(upper['musical_relationships']))
    return F(music.member_pitch(*owner._index(expanded)[ref]))


class BackingRelationshipPreservationTests(unittest.TestCase):
    def test_reported_unrelated_relationship_survives_exact_normal_edit(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                docs, before, upper = fixture(owned_time=owned_time)
                self.assertEqual(validate(upper), before)
                snapshot = deepcopy(upper); old = deepcopy(rows(upper)[EXTRA])
                changed, decision = motion.intervene(upper, controls(100))
                self.assertTrue(decision['changed'])
                self.assertEqual(realize(changed), expected_edit(docs))
                self.assertEqual(validate(changed), realize(changed))
                self.assertEqual(upper, snapshot)
                self.assertEqual(changed['source_origin'], upper['source_origin'])
                self.assertEqual(rows(changed).get(EXTRA), old)
                self.assertEqual(set(rows(changed)), set(SOURCE + TARGET + [EXTRA]))
                group, _ = owner._index(owner._body(changed['musical_relationships']['core']))[EXTRA]
                self.assertNotIn('bass_register_anchor', group)

    def test_unrelated_dependent_still_follows_backing_after_the_normal_edit(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                _, _, upper = fixture(owned_time=owned_time)
                changed, _ = motion.intervene(upper, controls(100))
                snapshot = deepcopy(changed)
                moved = shift_independent(changed, 2)
                self.assertEqual(pitch(moved, EXTRA), pitch(changed, EXTRA) + 2)
                actual = project_documents(realize(moved))
                expected = project_documents(realize(changed))
                # The independent chord moves; its three existing reference
                # dependents and the unrelated dependent must follow it.
                for note in expected['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']:
                    note['fret'] += 2
                for beat in expected['track-0.json']['measures'][0]['voices'][0]['beats'][:3]:
                    beat['notes'][0]['fret'] += 2
                expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 2
                self.assertEqual(actual, expected)
                self.assertEqual(validate(moved), realize(moved))
                self.assertEqual(changed, snapshot)

    def test_existing_selected_compatible_binding_is_idempotent(self):
        for selected in (SOURCE[0], TARGET[1]):
            with self.subTest(selected=selected):
                _, before, initial = fixture()
                evidence = motion.prepare(initial, controls())
                plain = owner.expand(initial['musical_relationships'])
                compatible = next(b for b in canonical_bindings(plain, evidence['correspondences'])
                                  if b['occurrence_ref'] == selected)
                _, _, upper = fixture([dict(occurrence_ref=EXTRA, backing_ref=INDEPENDENT), compatible])
                snapshot = deepcopy(upper); old_rows = deepcopy(rows(upper))
                owned = motion.own_intervals(upper, motion.prepare(upper, controls()))
                self.assertEqual(realize(owned), before)
                self.assertEqual(rows(owned)[selected], old_rows[selected])
                self.assertEqual(rows(owned).get(EXTRA), old_rows[EXTRA])
                self.assertEqual(len(rows(owned)), len(owned['musical_relationships']['relationships']))
                self.assertEqual(upper, snapshot)

    def assert_extension_refused_atomically(self, upper):
        snapshot = deepcopy(upper)
        self.assertEqual(validate(upper), realize(upper))
        prepared = motion.prepare(upper, controls()); prepared_snapshot = deepcopy(prepared)
        with self.assertRaises(ValueError): motion.own_intervals(upper, prepared)
        self.assertEqual(upper, snapshot)
        self.assertEqual(prepared, prepared_snapshot)
        with self.assertRaises(ValueError): motion.intervene(upper, controls(100))
        self.assertEqual(upper, snapshot)
        self.assertEqual(realize(motion.intervene(upper, controls(0))[0]), realize(upper))

    def test_conflicting_existing_selected_binding_is_not_silently_replaced(self):
        # This anchor is active and valid, but differs from the canonical anchor
        # selected by the current operation. Equal initial notes do not justify
        # overwriting an already authoritative relationship.
        _, _, upper = fixture([dict(occurrence_ref=SOURCE[0], backing_ref=INDEPENDENT)])
        self.assert_extension_refused_atomically(upper)

    def test_combined_old_and_new_dependency_chain_is_not_silently_flattened(self):
        # Existing EXTRA -> SOURCE[0] is valid by itself. Owning SOURCE[0]
        # through another backing creates a chain the current owner forbids.
        _, _, upper = fixture([dict(occurrence_ref=EXTRA, backing_ref=SOURCE[0])])
        self.assert_extension_refused_atomically(upper)

    def test_legacy_v1_read_and_zero_survive_but_extension_is_explicitly_refused(self):
        _, before, upper = fixture()
        existing = upper['musical_relationships']
        bindings = [{k: v for k, v in row.items() if k != 'interval_semitones'}
                    for row in existing['relationships']]
        upper['musical_relationships'] = owner.legacy_relift(owner.expand(existing), bindings)
        self.assertEqual(realize(upper), before)
        self.assert_extension_refused_atomically(upper)

    def test_existing_v3_guard_survives_old_mode_extension_and_still_enforces(self):
        docs, before, upper = fixture(execution=True)
        self.assertEqual(validate(upper), before)
        snapshot = deepcopy(upper)
        old_scope = deepcopy(upper['musical_relationships']['execution_constraints'])
        self.assertTrue(old_scope['obligations'])
        changed, _ = motion.intervene(upper, controls(100))  # matched-sonorities mode
        self.assertEqual(upper, snapshot)
        self.assertEqual(realize(changed), expected_edit(docs))
        model = changed['musical_relationships']
        self.assertEqual(model['schema'], owner.EXECUTION_SCHEMA)
        self.assertIn(EXTRA, model['execution_constraints']['owned_refs'])
        for obligation in old_scope['obligations']:
            self.assertIn(obligation, model['execution_constraints']['obligations'])
        self.assertEqual(pitch(shift_independent(changed, 1), EXTRA), pitch(changed, EXTRA) + 1)
        self.assertEqual(validate(shift_independent(changed, 1)), realize(shift_independent(changed, 1)))
        # The physical contact stays valid, but B1->A1 would become G1->A1:
        # changing a pull-off into a hammer-on must still be rejected.
        invalid = shift_independent(changed, -4); untouched = deepcopy(invalid)
        with self.assertRaises(ValueError): realize(invalid)
        self.assertEqual(invalid, untouched)


    def test_disjoint_extensions_commute_and_share_one_independent_anchor(self):
        for owned_time in (False, True):
            for execution in (False, True):
                with self.subTest(owned_time=owned_time, execution=execution):
                    _, before, upper = fixture(owned_time=owned_time, execution=execution)
                    base = upper['musical_relationships']; snapshot = deepcopy(base)
                    a = [dict(occurrence_ref=SOURCE[0], backing_ref=INDEPENDENT)]
                    b = [dict(occurrence_ref=SOURCE[1], backing_ref=INDEPENDENT)]
                    ab = owner.extend_bindings(owner.extend_bindings(base, a, tier1=before), b, tier1=before)
                    ba = owner.extend_bindings(owner.extend_bindings(base, b, tier1=before), a, tier1=before)
                    self.assertEqual(ab, ba)
                    self.assertEqual(base, snapshot)
                    enlarged = deepcopy(upper); enlarged['musical_relationships'] = ab
                    self.assertEqual(validate(enlarged), before)
                    self.assertEqual({r['backing_ref'] for r in ab['relationships']}, {INDEPENDENT})
                    moved = shift_independent(enlarged, 1)
                    for ref in (EXTRA, SOURCE[0], SOURCE[1]):
                        self.assertEqual(pitch(moved, ref), pitch(enlarged, ref) + 1)
                    self.assertEqual(pitch(moved, SOURCE[2]), pitch(enlarged, SOURCE[2]))
                    self.assertEqual(validate(moved), realize(moved))

    def test_self_cycle_and_missing_reference_extensions_refuse_atomically(self):
        _, before, upper = fixture(); base = upper['musical_relationships']
        # The two cycle endpoints are simultaneous, monophonic and initially
        # independent: refusal is not explained by expired/future notes.
        other = 'event:987:2:1:0:2:0'
        absent = 'event:987:9:1:0:0:0'
        cases = [
            [dict(occurrence_ref=SOURCE[0], backing_ref=SOURCE[0])],
            [dict(occurrence_ref=SOURCE[2], backing_ref=other),
             dict(occurrence_ref=other, backing_ref=SOURCE[2])],
            [dict(occurrence_ref=absent, backing_ref=INDEPENDENT)],
            [dict(occurrence_ref=SOURCE[0], backing_ref=absent)],
        ]
        for additions in cases:
            with self.subTest(additions=additions):
                snapshot = deepcopy(base); original_additions = deepcopy(additions); original_source = deepcopy(before)
                with self.assertRaises(ValueError): owner.extend_bindings(base, additions, tier1=before)
                self.assertEqual(base, snapshot)
                self.assertEqual(additions, original_additions)
                self.assertEqual(before, original_source)
                self.assertEqual(validate(upper), before)

    def test_existing_written_tie_records_and_incidence_survive_and_enforce(self):
        docs, _, _ = fixture()
        beats = docs['track-2.json']['measures'][0]['voices'][0]['beats']
        beats[1]['notes'][0] = dict(string=3, fret=7, tie=True)
        before = extract_documents(docs)
        upper = strip_lower(analyze(before, backing_bindings=[dict(occurrence_ref=EXTRA, backing_ref=INDEPENDENT)]))
        old = deepcopy(upper['musical_relationships']['written_tie_constraints'])
        self.assertEqual(len(old['relations']), 1)
        changed, _ = motion.intervene(upper, controls(100))
        actual = changed['musical_relationships']['written_tie_constraints']
        self.assertEqual(actual['relations'], old['relations'])
        for incidence in old['incidence']:
            self.assertIn(incidence, actual['incidence'])
        self.assertEqual(realize(changed), expected_edit(docs))
        # A later independent-anchor move cannot break that retained tie.
        corrupted = shift_independent(changed, 1); snapshot = deepcopy(corrupted)
        with self.assertRaises(ValueError): realize(corrupted)
        self.assertEqual(corrupted, snapshot)

    def test_source_denied_workers_preserve_old_and_new_relationship_behavior(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        docs, before, upper = fixture(owned_time=True, execution=True)
        owned = motion.own_intervals(upper, motion.prepare(upper, controls()))
        self.assertEqual(len(rows(owned)), 7)
        changed, _ = motion.intervene(owned, controls(100))
        shifted = shift_independent(changed, 1)
        expected_shifted = project_documents(expected_edit(docs))
        for note in expected_shifted['track-1.json']['measures'][0]['voices'][0]['beats'][0]['notes']:
            note['fret'] += 1
        for beat in expected_shifted['track-0.json']['measures'][0]['voices'][0]['beats'][:3]:
            beat['notes'][0]['fret'] += 1
        expected_shifted['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['fret'] += 1
        code, _ = bundle(Path(__file__).resolve().parent)
        jobs = [('zero', owned, controls(0), before),
                ('released', owned, controls(100), expected_edit(docs)),
                ('later_backing_move', shifted, controls(0), extract_documents(expected_shifted))]
        with tempfile.TemporaryDirectory() as tmp:
            for name, packet, request, expected in jobs:
                with self.subTest(worker=name):
                    out = Path(tmp)/name
                    receipt = execute(code, packet, request, expected, out, timeout=40,
                                      purpose='observed_backing_motion')
                    self.assertEqual(receipt['status'], 'PASS', receipt)
                    self.assertFalse(receipt['parent_expected_staged'])
                    self.assertEqual(set(receipt['frozen_files']), {'input.json', 'relationships.py', 'worker.py'})
                    staged = json.loads((out/'worker/input.json').read_text())['upper']
                    self.assertNotIn('input', staged); self.assertNotIn('derived_views', staged)
                    group, _ = owner._index(owner._body(staged['musical_relationships']['core']))[EXTRA]
                    self.assertNotIn('bass_register_anchor', group)
                    self.assertEqual(set(rows(staged)), set(SOURCE + TARGET + [EXTRA]))
                    self.assertEqual(staged['source_origin'], upper['source_origin'])
                    self.assertEqual(json.loads((out/'worker/output.json').read_text()), expected)
                    audit = json.loads((out/'worker/audit.json').read_text())
                    self.assertIsNone(audit['error'])
                    self.assertFalse(any(event['denied'] for event in audit['events']))


if __name__ == '__main__':
    unittest.main()
