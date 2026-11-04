"""Relative current dynamics never become additional original observations."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import observed_dynamics as dynamic
from source_fact_tier1 import extract_documents
from test_observed_dynamics_projection import fact, event, fixture, split, model, expected_facts


def documents():
    docs = fixture()
    docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['velocity'] = 'f'
    return docs


def set_markings(docs, changes):
    result = deepcopy(docs)
    for ref, value in changes.items():
        document, pointer = ref.split('#')
        row = result[document]
        fields = pointer.strip('/').split('/')
        for field in fields[:-1]:
            row = row[int(field)] if isinstance(row, list) else row[field]
        row[fields[-1]] = value
    return result


class DynamicRelativeChoiceTests(unittest.TestCase):
    def assert_realized(self, owner, docs):
        self.assertEqual(sorted(dynamic.realize(owner), key=lambda r: r['id']), expected_facts(docs))
        dynamic.validate_source(owner, extract_documents(docs))

    def test_same_equation_solves_every_legal_pair_both_directions(self):
        for source in dynamic.LEVELS:
            for target in dynamic.LEVELS:
                result = dynamic.relative_level(source, marking=target)
                self.assertEqual(dynamic.relative_level(source, offset=result['offset']), result)
                self.assertEqual(result['marking'], target)
        for kwargs in ({}, dict(offset=0, marking='f'), dict(offset=True), dict(offset=1.0),
                       dict(offset='1'), dict(offset=-6), dict(offset=3), dict(marking='ffff')):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                dynamic.relative_level('f', **kwargs)

    def test_new_levels_preserve_original_definitions_observations_and_checksum(self):
        docs = documents(); owner = model(docs); before = deepcopy(owner)
        changes = {fact(0): 'mp', fact(2): 'ff'}
        chosen = dynamic.choose_relative(owner, changes)
        self.assertEqual(chosen['schema'], dynamic.RELATIVE_SCHEMA)
        self.assert_realized(chosen, set_markings(docs, changes))
        self.assertEqual(dynamic.evidence(chosen), dynamic.evidence(owner))
        self.assertEqual(chosen['evidence_sha256'], owner['evidence_sha256'])
        self.assertEqual(dynamic.source_view(chosen), dynamic.source_view(owner))
        self.assertEqual(set(chosen['definitions']), {'dynamic-level:f', 'dynamic-level:mf'})
        self.assertTrue(all(set(row) == {'fact_ref', 'structure', 'offset'} for row in chosen['current']))
        self.assertEqual({r['fact_ref']: r['offset'] for r in chosen['current']},
                         {fact(0): -2, fact(2): 2, fact(3): 0})
        self.assertEqual(owner, before)

    def test_upgrade_preserves_prior_current_choices_in_untouched_regions(self):
        docs = documents(); original = model(docs)
        prior = dynamic.choose(original, fact(0), 'mf')
        chosen = dynamic.choose_relative(prior, {fact(2): 'ff'})
        self.assert_realized(chosen, set_markings(docs, {fact(0): 'mf', fact(2): 'ff'}))
        self.assertEqual(next(r['offset'] for r in chosen['current'] if r['fact_ref'] == fact(0)), -1)
        self.assertEqual(dynamic.current_marking(prior, fact(0)), 'mf')
        self.assertEqual(dynamic.current_marking(chosen, fact(0)), 'mf')

    def test_empty_or_same_current_choice_is_exact_and_revert_is_explicit(self):
        owner = model(documents())
        for changes in ({}, {fact(0): 'f'}):
            self.assertEqual(dynamic.choose_relative(owner, changes), owner)
        chosen = dynamic.choose_relative(owner, {fact(0): 'mp'})
        self.assertEqual(dynamic.choose_relative(chosen, {fact(0): 'mp'}), chosen)
        restored = dynamic.choose_relative(chosen, {fact(0): 'f'})
        self.assertEqual(dynamic.realize(restored), dynamic.realize(owner))
        self.assertEqual(dynamic.evidence(restored), dynamic.evidence(owner))

    def test_saved_successive_changes_use_original_anchor_without_accumulating_offsets(self):
        owner = model(documents())
        first = dynamic.choose_relative(owner, {fact(0): 'mp'})
        saved = json.loads(json.dumps(first))
        second = dynamic.choose_relative(saved, {fact(0): 'ff'})
        row = next(r for r in second['current'] if r['fact_ref'] == fact(0))
        self.assertEqual(row['offset'], 1)  # Original f -> ff, not mp -> ff.
        self.assertEqual(dynamic.current_marking(second, row), 'ff')
        self.assertEqual(dynamic.source_view(second), dynamic.source_view(owner))
        self.assertEqual(saved, first)

    def test_projection_then_relative_update_changes_all_children_using_original_identity(self):
        docs = documents(); owner = model(docs); changed, facts, events = split(docs, 0)
        projected = dynamic.project(owner, facts, events)
        chosen = dynamic.choose_relative(json.loads(json.dumps(projected)), {fact(0): 'ff', fact(2): 'mp'})
        self.assert_realized(chosen, set_markings(changed, {fact(0): 'ff', fact(1): 'ff', fact(3): 'mp'}))
        self.assertEqual(chosen['projection'], projected['projection'])
        with self.assertRaisesRegex(ValueError, 'Original dynamic occurrence'):
            dynamic.choose_relative(chosen, {fact(1): 'mf'})
        self.assertEqual(dynamic.project(chosen, {}, {}), chosen)

    def test_relative_update_then_successive_projection_does_not_create_votes(self):
        docs = documents(); chosen = dynamic.choose_relative(model(docs), {fact(0): 'mp'})
        changed_docs = set_markings(docs, {fact(0): 'mp'})
        once, facts, events = split(changed_docs, 0)
        first = dynamic.project(chosen, facts, events)
        twice, more_facts, more_events = split(once, 0)
        second = dynamic.project(json.loads(json.dumps(first)), more_facts, more_events)
        self.assertEqual(second['schema'], dynamic.RELATIVE_SCHEMA)
        self.assert_realized(second, twice)
        self.assertEqual(second['current'], chosen['current'])
        self.assertEqual(len(second['observations']), 3)
        self.assertEqual(len(dynamic.realize(second)), 5)
        self.assertEqual(dynamic.evidence(second), dynamic.evidence(chosen))

    def test_legacy_choose_remains_observed_only_and_relative_current_cannot_become_donor(self):
        import local_dynamics
        docs = documents(); owner = model(docs)
        chosen = dynamic.choose_relative(owner, {fact(0): 'ff'})
        for state in (owner, chosen):
            with self.assertRaisesRegex(ValueError, 'No original observation'):
                dynamic.choose(state, fact(2), 'ff')
        changed = dynamic.choose(chosen, fact(0), 'mf')
        self.assertEqual(dynamic.current_marking(changed, fact(0)), 'mf')
        current = extract_documents(set_markings(docs, {fact(0): 'ff'}))
        options = local_dynamics.options(current, fact(2), observations=dynamic.source_view(chosen))
        self.assertNotIn('ff', [r['marking'] for r in options['options']])

    def test_invalid_late_entry_and_malformed_relative_models_refuse_atomically(self):
        owner = model(documents()); before = deepcopy(owner)
        for changes in ({fact(0): 'ff', fact(99): 'mp'}, {fact(0): 'ff', fact(2): 'ffff'},
                        {fact(0): 'ff', 2: 'mp'}, [], {fact(0): None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                dynamic.choose_relative(owner, changes)
            self.assertEqual(owner, before)
        chosen = dynamic.choose_relative(owner, {fact(0): 'ff'})
        for field, value in (('offset', 99), ('offset', True), ('offset', '1'), ('definition_ref', 'dynamic-level:f')):
            bad = deepcopy(chosen); bad['current'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                dynamic.realize(bad)
        bad = deepcopy(chosen); bad['definitions']['dynamic-level:ff'] = {'symbol': 'ff'}
        with self.assertRaisesRegex(ValueError, 'Original dynamic observations'):
            dynamic.realize(bad)
        fake = deepcopy(chosen['current'][0]); fake['offset'] = 0
        with self.assertRaisesRegex(ValueError, 'Exact owned'):
            dynamic.current_marking(chosen, fake)

    def test_relative_owner_does_not_claim_accent_cancellation_is_a_loudness_change(self):
        # One common-level step down plus one emphasis step up preserves final
        # velocity. The owner exposes base levels; the joint caller must check
        # performed expression rather than treating this owner as that proof.
        owner = model(documents())
        one = dynamic.choose_relative(owner, {fact(0): 'mf'})
        self.assertEqual(dynamic.LEVELS.index(dynamic.current_marking(one, fact(0))) + 1,
                         dynamic.LEVELS.index(dynamic.current_marking(owner, fact(0))))
        two = dynamic.choose_relative(owner, {fact(0): 'mp'})
        self.assertNotEqual(dynamic.LEVELS.index(dynamic.current_marking(two, fact(0))) + 1,
                            dynamic.LEVELS.index(dynamic.current_marking(owner, fact(0))))

    def test_complete_connected_inverse_and_zero_with_no_file_access(self):
        from connected_tier2 import analyze, strip_lower, realize
        import local_dynamics
        docs = documents(); lower = extract_documents(docs)
        upper = strip_lower(analyze(lower, dynamic_evidence=True))
        old = deepcopy(upper)
        upper['owned_parameters']['observed_dynamics'] = dynamic.choose_relative(
            upper['owned_parameters']['observed_dynamics'], {fact(0): 'mp', fact(2): 'ff'})
        saved = json.loads(json.dumps(upper))
        with patch('builtins.open', side_effect=AssertionError('No source read')):
            actual = realize(saved)
            zero, decision = local_dynamics.intervene(saved,
                dict(context_policy=local_dynamics.POLICY, dynamics=0, target_ref=fact(0), seed=0))
        self.assertEqual(actual, extract_documents(set_markings(docs, {fact(0): 'mp', fact(2): 'ff'})))
        self.assertEqual(zero, saved)
        self.assertFalse(decision['changed'])
        self.assertEqual(saved['musical_relationships'], old['musical_relationships'])

    def test_actual_isolated_inverse_uses_saved_relative_choices_only(self):
        from connected_tier2 import analyze, strip_lower
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        docs = documents(); upper = strip_lower(analyze(extract_documents(docs), dynamic_evidence=True))
        upper['owned_parameters']['observed_dynamics'] = dynamic.choose_relative(
            upper['owned_parameters']['observed_dynamics'], {fact(0): 'mp', fact(2): 'ff'})
        expected = extract_documents(set_markings(docs, {fact(0): 'mp', fact(2): 'ff'}))
        code, _ = bundle(Path(__file__).parent)
        code += '\ndef reconstruct(upper,controls):\n    if controls!={"variation":0}:raise ValueError("Zero only")\n    return sys.modules["connected_tier2"].realize(upper)\n'
        with tempfile.TemporaryDirectory() as folder:
            result = execute(code, json.loads(json.dumps(upper)), {'variation': 0}, expected,
                             Path(folder)/'relative', timeout=30)
        self.assertEqual(result['status'], 'PASS', result)


if __name__ == '__main__':
    unittest.main()
