"""Public and source-denied acceptance for fixed-span note/rest release."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, realize, reconstruct, strip_lower
from source_fact_tier1 import extract_documents, project_documents
import local_note_rest_timing as local
import note_rest_timing as timing
from test_note_rest_timing import binding, documents, ref


def fixture(**kwargs):
    lower = extract_documents(documents())
    original = strip_lower(analyze(lower, **kwargs))
    return lower, original, local.attach(original, [binding()])


def controls(amount=100, seed=1):
    return dict(context_policy=local.POLICY, rhythm=amount, seed=seed,
                target_ref=timing.pair_id(ref(0, 1), ref(0, 2)))


def expected_changed():
    expected = documents(); beats = expected['track-0.json']['measures'][0]['voices'][0]['beats']
    beats[1].update(dots=0, duration=[1, 4])
    beats[2].update(type=4, duration=[1, 4])
    return extract_documents(expected)


class NoteRestControlsTests(unittest.TestCase):
    def test_control_packet_requires_exact_typed_fields(self):
        local.validate_controls(controls(0)); local.validate_controls(controls(50)); local.validate_controls(controls(100))
        for field, value in [('rhythm', True), ('rhythm', 50.0), ('rhythm', -1), ('rhythm', 101),
                             ('seed', True), ('seed', 1.0), ('context_policy', 'source_complete_group_rhythm'),
                             ('target_ref', 'event:77:0:1:0:1:0'), ('target_ref', timing.pair_id(ref(0, 1), ref(1, 2)))]:
            request = controls(); request[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                local.validate_controls(request)
        for request in (dict(controls(), pitch=40), {k: v for k, v in controls().items() if k != 'seed'}):
            with self.assertRaises(ValueError): local.validate_controls(request)


class LocalNoteRestTimingTests(unittest.TestCase):
    def test_attach_transfers_exact_existing_owners_and_zero_is_complete(self):
        before, original, upper = fixture()
        self.assertEqual(realize(upper), before)
        self.assertNotIn('input', upper); self.assertNotIn('derived_views', upper)
        _, values = timing.expand(upper['musical_relationships'])
        selected = set(values)
        self.assertTrue(selected.isdisjoint(row['fact_ref'] for row in upper['owned_parameters']['source_choices']))
        self.assertEqual({row['fact_ref'] for row in upper['coverage'] if row['owner'] == local.OWNER}, selected)
        self.assertEqual([row for row in upper['owned_parameters']['source_choices']],
                         [row for row in original['owned_parameters']['source_choices'] if row['fact_ref'] not in selected])
        edited, report = local.intervene(upper, controls(0))
        self.assertEqual(edited, upper); self.assertEqual(realize(edited), before)
        self.assertEqual(report['status'], 'EXACT_ZERO_LOCK'); self.assertFalse(report['released'])
        self.assertEqual(reconstruct(upper, controls(0)), before)

    def test_probability_at_fifty_has_both_outcomes_and_hundred_uses_source_ratio(self):
        before, _, upper = fixture(); snapshot = deepcopy(upper)
        retained, no = local.intervene(upper, controls(50, seed=0))
        edited, yes = local.intervene(upper, controls(50, seed=1))
        full, hundred = local.intervene(upper, controls(100, seed=0))
        self.assertEqual(retained, upper); self.assertEqual(realize(retained), before)
        self.assertFalse(no['released']); self.assertTrue(yes['released']); self.assertTrue(hundred['released'])
        self.assertEqual(edited, full); self.assertEqual(realize(full), expected_changed())
        self.assertEqual(upper, snapshot)
        self.assertEqual(reconstruct(upper, controls(100)), expected_changed())
        self.assertEqual(len(hundred['influence_check']['changed_fact_refs']), 5)

    def test_saved_edit_retains_evidence_and_zero_does_not_restore_original(self):
        _, _, upper = fixture()
        edited, _ = local.intervene(upper, controls())
        saved = json.loads(json.dumps(edited)); origin = deepcopy(saved['source_origin'])
        observed = deepcopy(saved['musical_relationships']['pairs'][0]['observations'])
        zero, report = local.intervene(saved, controls(0))
        again, coincidence = local.intervene(saved, controls(100))
        self.assertEqual(zero, saved); self.assertEqual(again, saved)
        self.assertFalse(report['changed']); self.assertEqual(coincidence['status'], 'OBSERVED_COINCIDENCE')
        self.assertTrue(coincidence['released']); self.assertFalse(coincidence['changed'])
        self.assertEqual(again['source_origin'], origin)
        self.assertEqual(again['musical_relationships']['pairs'][0]['observations'], observed)
        self.assertEqual(realize(again), expected_changed())
        with self.assertRaisesRegex(ValueError, 'never relearned'):
            local.attach(saved, [binding()])

    def test_missing_duplicate_or_changed_owners_refuse_atomically(self):
        lower = extract_documents(documents()); original = strip_lower(analyze(lower))
        for corruption in ('missing_choice', 'duplicate_choice', 'missing_coverage', 'duplicate_coverage', 'wrong_owner'):
            bad = deepcopy(original); choices = bad['owned_parameters']['source_choices']; coverage = bad['coverage']
            choice = next(row for row in choices if row['fact_ref'] == ref(0, 1) + '/type')
            ledger = next(row for row in coverage if row['fact_ref'] == choice['fact_ref'])
            if corruption == 'missing_choice': choices.remove(choice)
            elif corruption == 'duplicate_choice': choices.append(deepcopy(choice))
            elif corruption == 'missing_coverage': coverage.remove(ledger)
            elif corruption == 'duplicate_coverage': coverage.append(deepcopy(ledger))
            else: ledger['owner'] = 'written_pitch_relationship'
            frozen = deepcopy(bad)
            with self.subTest(corruption=corruption), self.assertRaises((ValueError, KeyError)):
                local.attach(bad, [binding()])
            self.assertEqual(bad, frozen)

    def test_attachment_requires_original_observations_and_strips_lower_caches(self):
        lower = extract_documents(documents()); raw = analyze(lower)
        upper = local.attach(raw, [binding()])
        self.assertNotIn('input', upper); self.assertNotIn('derived_views', upper)
        before = strip_lower(raw)
        before['source_origin']['facts_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'relabel'):
            local.attach(before, [binding()])
        missing = strip_lower(raw); del missing['source_origin']
        with self.assertRaises(ValueError): local.attach(missing, [binding()])

    def test_held_preference_survives_shortening_without_invented_key(self):
        import stable_pitch_policy as stable
        before = extract_documents(documents()); original = strip_lower(analyze(before))
        original = stable.attach(original, context=None, held_refs=['event:77:0:1:0:1:0'])
        upper = local.attach(original, [binding()]); policy = deepcopy(upper[stable.SLOT])
        edited, decision = local.intervene(upper, controls())
        self.assertEqual(edited[stable.SLOT], policy)
        self.assertEqual(decision['stable_pitch_check']['status'], 'UNCHANGED_STABLE_PITCHES')
        self.assertEqual(decision['stable_pitch_check']['new_stable_spans'], [])
        self.assertEqual(realize(edited), expected_changed())
        self.assertEqual(reconstruct(upper, controls()), expected_changed())

    def test_whole_upper_write_allowlist_rejects_unrelated_mutation(self):
        _, _, upper = fixture(); saved = deepcopy(upper); real_apply = timing.apply
        def corrupt(model, target):
            result = real_apply(model, target)
            result['pitch_relationships']['theory']['unexpected'] = 'changed'
            return result
        with patch.object(timing, 'apply', side_effect=corrupt), self.assertRaisesRegex(ValueError, 'PROTECTED_STATE'):
            local.intervene(upper, controls())
        self.assertEqual(upper, saved)

    def test_all_current_guards_run_at_zero_and_nonzero(self):
        _, _, upper = fixture()
        for amount in (0, 100):
            for kind in ('bad_origin', 'unknown_pair', 'donor_tamper'):
                bad = deepcopy(upper); request = controls(amount)
                if kind == 'bad_origin': bad['source_origin']['facts_sha256'] = 'f' * 64
                elif kind == 'unknown_pair': request['target_ref'] = timing.pair_id(ref(1, 1), ref(1, 2))
                else: bad['musical_relationships']['pairs'][0]['observations']['donor']['shares'] = ['1/4', '3/4']
                snapshot = deepcopy(bad)
                with self.subTest(amount=amount, kind=kind), self.assertRaises(ValueError):
                    local.intervene(bad, request)
                self.assertEqual(bad, snapshot)

    def test_conditional_coverage_owner_composes_without_altering_slot_rules(self):
        before, original, upper = fixture(note_accent_slots=True, palm_mute_slots=True)
        self.assertEqual(upper['coverage']['rules'], original['coverage']['rules'])
        self.assertEqual(realize(upper), before)
        edited, _ = local.intervene(upper, controls())
        self.assertEqual(realize(edited), expected_changed())

    def test_actual_source_denied_workers_zero_fifty_and_hundred(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before, _, upper = fixture(); code, _ = bundle(Path(__file__).parent)
        cases = [('zero', controls(0), before), ('half-retained', controls(50, seed=0), before),
                 ('half-released', controls(50, seed=1), expected_changed()),
                 ('full', controls(100), expected_changed())]
        with tempfile.TemporaryDirectory() as directory:
            for name, request, expected in cases:
                result = execute(code, upper, request, expected, Path(directory) / name,
                                 timeout=45, purpose='note_rest_timing')
                self.assertEqual(result['status'], 'PASS', result)
                self.assertFalse(result['parent_expected_staged'])


if __name__ == '__main__':
    unittest.main()
