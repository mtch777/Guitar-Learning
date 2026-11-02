"""Independent requirements checks for original observations versus edited music.

Expected values come from literal source declarations and raw document edits,
not from the producer's evidence projection or expected-output helper.
"""
from collections import Counter
from copy import deepcopy
import json
import random
import unittest

from connected_tier2 import analyze, strip_lower, realize, reconstruct
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest
import observed_dynamics
import local_dynamics
import dynamic_context
from test_check_local_dynamics import documents as level_documents
from test_dynamic_context import documents as transition_documents


def ref(measure, beat=0, voice=0, note=None):
    value = f'track-0.json#/measures/{measure}/voices/{voice}/beats/{beat}'
    return value + (f'/notes/{note}' if note is not None else '') + '/velocity'


def controls(target, *, policy=local_dynamics.POLICY, strength=100, seed=0):
    return dict(context_policy=policy, dynamics=strength, target_ref=target, seed=seed)


def upper_from(documents, **kwargs):
    return strip_lower(analyze(extract_documents(documents), dynamic_evidence=True, **kwargs))


def raw_edit(documents, measure, value, *, beat=0, voice=0, note=None):
    result = deepcopy(documents)
    owner = result['track-0.json']['measures'][measure]['voices'][voice]['beats'][beat]
    if note is not None:
        owner = owner['notes'][note]
    owner['velocity'] = value
    return result


def votes(result):
    return {row['marking']: tuple(row['donor_refs']) for row in result['options']}


class DynamicEvidenceTests(unittest.TestCase):
    def test_original_known_declarations_have_one_vote_each_and_one_current_owner(self):
        documents = level_documents()
        before = extract_documents(documents)
        upper = upper_from(documents)
        self.assertEqual(upper['schema'], 'connected-source-musical-relations/5')
        model = upper['owned_parameters']['observed_dynamics']
        original = {
            ref(0): 'f', ref(1): 'mf', ref(2): 'f', ref(0, voice=1): 'fff',
            ref(0, 1, note=0): 'pp', ref(1, 1, note=0): 'p',
        }
        self.assertEqual(len(model['observations']), len(original))
        self.assertEqual(len(model['current']), len(original))
        actual = {
            row['fact_ref']: model['definitions'][row['definition_ref']]['symbol']
            for row in model['observations']
        }
        self.assertEqual(actual, original)
        self.assertEqual(Counter(actual.values()), Counter(original.values()))
        self.assertEqual(len(model['definitions']), len(set(original.values())))
        technique_refs = {
            group['source_fact_ref']
            for group in upper['owned_parameters']['technique_declarations']['groups']
        }
        self.assertFalse(set(original) & technique_refs)
        self.assertEqual(realize(upper), before)
        self.assertNotIn('input', upper)

    def test_successive_edits_preserve_original_f_mf_f_votes_and_exact_raw_output(self):
        documents = level_documents()
        upper = upper_from(documents)
        frozen_upper = deepcopy(upper)
        original_evidence = observed_dynamics.evidence(upper['owned_parameters']['observed_dynamics'])
        wanted = {'f': (ref(0),), 'mf': (ref(1),)}
        self.assertEqual(votes(local_dynamics.package_options(upper, ref(2))), wanted)

        first, decision = local_dynamics.intervene(upper, controls(ref(0), seed=0))
        self.assertEqual(decision['chosen']['marking'], 'mf')
        current_documents = raw_edit(documents, 0, 'mf')
        self.assertEqual(realize(first), extract_documents(current_documents))
        self.assertEqual(upper, frozen_upper)
        self.assertEqual(votes(local_dynamics.package_options(first, ref(2))), wanted)

        second, decision = local_dynamics.intervene(first, controls(ref(2), seed=0))
        self.assertEqual(decision['chosen']['marking'], 'mf')
        current_documents = raw_edit(current_documents, 2, 'mf')
        self.assertEqual(realize(second), extract_documents(current_documents))
        self.assertEqual(observed_dynamics.evidence(second['owned_parameters']['observed_dynamics']), original_evidence)
        # Both original f slots now sound mf, but the first target still has one
        # original f donor (the third marking) and one mf donor (the second).
        last = local_dynamics.package_options(second, ref(0))
        self.assertEqual(votes(last), {'f': (ref(2),), 'mf': (ref(1),)})
        self.assertEqual({row['marking']: row['changed'] for row in last['options']}, {'f': True, 'mf': False})
        # Explicit note overrides and the other voice must remain literal.
        self.assertEqual(project_documents(realize(second)), current_documents)

    def test_release_draws_use_original_multiplicity_after_an_edit(self):
        upper = upper_from(level_documents())
        edited, _ = local_dynamics.intervene(upper, controls(ref(0), seed=0))
        snapshot = deepcopy(edited)
        for strength in (0, 50, 100):
            for seed in range(12):
                with self.subTest(strength=strength, seed=seed):
                    result, decision = local_dynamics.intervene(edited, controls(ref(2), strength=strength, seed=seed))
                    rng = random.Random(seed)
                    released = rng.random() < strength / 100
                    selected = rng.choice(('f', 'mf')) if released else 'f'
                    expected = raw_edit(raw_edit(level_documents(), 0, 'mf'), 2, selected)
                    self.assertEqual(realize(result), extract_documents(expected))
                    self.assertIs(decision['released'], released)
                    self.assertIs(decision['changed'], selected != 'f')
                    if released:
                        self.assertEqual(decision['chosen']['donor_refs'], [ref(0) if selected == 'f' else ref(1)])
        self.assertEqual(edited, snapshot)

    def test_current_incoming_context_changes_without_rewriting_original_transitions(self):
        documents = transition_documents()
        upper = upper_from(documents)
        frozen = observed_dynamics.evidence(upper['owned_parameters']['observed_dynamics'])
        target = ref(0, 1)
        initial = dynamic_context.package_options(upper, target)
        self.assertEqual(initial['context']['context_key'], [0, 0, 'beat', 'f', 4, '1', '1'])
        self.assertEqual(votes(initial), {
            'mf': (ref(3, 1), ref(4, 1)), 'mp': (ref(2, 1), ref(5, 1)),
        })
        changed, first = local_dynamics.intervene(upper, controls(ref(0), seed=3))
        self.assertEqual(first['chosen']['marking'], 'mp')
        expected = extract_documents(raw_edit(documents, 0, 'mp'))
        self.assertEqual(realize(changed), expected)
        available = dynamic_context.package_options(changed, target)
        self.assertEqual(available['context']['context_key'], [0, 0, 'beat', 'mp', 4, '1', '1'])
        self.assertEqual(available['options'], [])
        self.assertEqual(observed_dynamics.evidence(changed['owned_parameters']['observed_dynamics']), frozen)
        result, decision = dynamic_context.intervene(changed, controls(target, policy=dynamic_context.POLICY))
        self.assertTrue(decision['released'])
        self.assertFalse(decision['changed'])
        self.assertEqual(result, changed)
        self.assertEqual(realize(result), expected)

    def test_contextual_selection_and_level_selection_share_the_current_owner(self):
        documents = transition_documents()
        upper = upper_from(documents)
        original = observed_dynamics.evidence(upper['owned_parameters']['observed_dynamics'])
        changed, decision = dynamic_context.intervene(upper, controls(ref(0, 1), policy=dynamic_context.POLICY, seed=1))
        self.assertEqual(decision['chosen']['marking'], 'mf')
        expected = raw_edit(documents, 0, 'mf', beat=1)
        self.assertEqual(realize(changed), extract_documents(expected))
        self.assertEqual(observed_dynamics.evidence(changed['owned_parameters']['observed_dynamics']), original)
        self.assertEqual(votes(local_dynamics.package_options(changed, ref(2, 1)))['mp'], (ref(0, 1), ref(5, 1)))

    def test_both_nonzero_edits_change_in_every_supported_ordered_policy_pair(self):
        # Fixed synthetic cases: both targets begin mp, at bars 1 and 3 beat 2.
        # Release=100, seed=1 selects f for level and mf for transition. These
        # literal expectations are source-fixture checks, not fresh-song QA.
        cases = (
            (local_dynamics, local_dynamics, 'f', 'f'),
            (local_dynamics, dynamic_context, 'f', 'mf'),
            (dynamic_context, local_dynamics, 'mf', 'f'),
            (dynamic_context, dynamic_context, 'mf', 'mf'),
        )
        for first, second, first_mark, second_mark in cases:
            with self.subTest(first=first.POLICY, second=second.POLICY):
                expected_documents = transition_documents()
                score = upper_from(expected_documents)
                original_evidence = observed_dynamics.evidence(score['owned_parameters']['observed_dynamics'])
                for measure, policy, expected_mark in ((0, first, first_mark), (2, second, second_mark)):
                    snapshot = deepcopy(score)
                    previous = realize(score)
                    changed, decision = policy.intervene(score, controls(ref(measure, 1), policy=policy.POLICY, strength=100, seed=1))
                    self.assertIs(decision['released'], True)
                    self.assertIs(decision['changed'], True)
                    self.assertEqual(decision['chosen']['marking'], expected_mark)
                    expected_documents = raw_edit(expected_documents, measure, expected_mark, beat=1)
                    actual = realize(changed)
                    self.assertEqual(actual, extract_documents(expected_documents))
                    self.assertEqual([before['id'] for before, after in zip(previous['facts'], actual['facts']) if before != after], [ref(measure, 1)])
                    self.assertEqual(observed_dynamics.evidence(changed['owned_parameters']['observed_dynamics']), original_evidence)
                    self.assertEqual(score, snapshot)
                    score = changed

    def test_editing_a_donor_context_does_not_rewrite_its_original_transition(self):
        documents = transition_documents()
        upper = upper_from(documents)
        target = ref(0, 1)
        wanted = {'mf': (ref(3, 1), ref(4, 1)), 'mp': (ref(2, 1), ref(5, 1))}
        original = observed_dynamics.evidence(upper['owned_parameters']['observed_dynamics'])
        edited, decision = local_dynamics.intervene(upper, controls(ref(3), seed=3))
        self.assertEqual(decision['chosen']['marking'], 'mp')
        self.assertEqual(realize(edited), extract_documents(raw_edit(documents, 3, 'mp')))
        # The donor now has incoming mp; its original f -> mf transition is
        # still one source observation for the unchanged f-conditioned target.
        self.assertEqual(votes(dynamic_context.package_options(edited, target)), wanted)
        self.assertEqual(observed_dynamics.evidence(edited['owned_parameters']['observed_dynamics']), original)

    def test_unknown_declarations_remain_exact_without_becoming_original_votes(self):
        for raw in (None, False, 0, 'unknown'):
            with self.subTest(raw=raw):
                documents = raw_edit(level_documents(), 1, raw)
                before = extract_documents(documents)
                upper = upper_from(documents)
                observations = upper['owned_parameters']['observed_dynamics']['observations']
                self.assertNotIn(ref(1), [r['fact_ref'] for r in observations])
                self.assertEqual(realize(upper), before)
                self.assertEqual(local_dynamics.package_options(upper, ref(1))['options'], [])

    def test_serialized_stripped_package_recovers_current_score_and_original_votes(self):
        documents = level_documents()
        upper = upper_from(documents)
        edited, _ = local_dynamics.intervene(upper, controls(ref(0), seed=0))
        loaded = json.loads(json.dumps(edited))
        self.assertNotIn('input', loaded)
        self.assertEqual(reconstruct(loaded, {'variation': 0}), extract_documents(raw_edit(documents, 0, 'mf')))
        self.assertEqual(votes(local_dynamics.package_options(loaded, ref(2))), {'f': (ref(0),), 'mf': (ref(1),)})
        self.assertEqual(observed_dynamics.evidence(loaded['owned_parameters']['observed_dynamics']), observed_dynamics.evidence(upper['owned_parameters']['observed_dynamics']))

    def test_stale_observation_definition_context_or_origin_is_refused_even_at_zero(self):
        original = upper_from(transition_documents())
        def value(model): model['observations'][0]['definition_ref'] = 'dynamic-level:mf'
        def context(model): model['observations'][1]['transition']['incoming_fact_ref'] = ref(2)
        def definition(model): model['definitions']['dynamic-level:f']['symbol'] = 'mf'
        def missing(model): model['observations'].pop()
        def duplicate(model): model['observations'].append(deepcopy(model['observations'][0]))
        def origin(model): model['origin']['facts_sha256'] = '0' * 64
        for mutation in (value, context, definition, missing, duplicate, origin):
            with self.subTest(mutation=mutation.__name__):
                broken = deepcopy(original)
                mutation(broken['owned_parameters']['observed_dynamics'])
                snapshot = deepcopy(broken)
                with self.assertRaises(ValueError):
                    reconstruct(broken, {'variation': 0})
                self.assertEqual(broken, snapshot)

    def test_structurally_forged_observations_fail_even_with_updated_local_digest(self):
        original = upper_from(level_documents())
        def duplicate(model): model['observations'].append(deepcopy(model['observations'][0]))
        def address(model): model['observations'][0]['declaration']['bar'] = 400
        def remove_pair(model):
            removed = model['observations'].pop()['fact_ref']
            model['current'] = [r for r in model['current'] if r['fact_ref'] != removed]
        for mutation in (duplicate, address, remove_pair):
            with self.subTest(mutation=mutation.__name__):
                broken = deepcopy(original)
                model = broken['owned_parameters']['observed_dynamics']
                mutation(model)
                model['evidence_sha256'] = digest(observed_dynamics.evidence(model))
                with self.assertRaises(ValueError):
                    realize(broken)

    def test_direct_contextual_zero_validates_original_evidence(self):
        broken = upper_from(transition_documents())
        broken['owned_parameters']['observed_dynamics']['observations'][0]['definition_ref'] = 'dynamic-level:mf'
        snapshot = deepcopy(broken)
        with self.assertRaises(ValueError):
            dynamic_context.intervene(broken, controls(ref(0, 1), policy=dynamic_context.POLICY, strength=0))
        self.assertEqual(broken, snapshot)

    def test_original_transition_meter_and_lists_reject_resealed_malformed_structure(self):
        original = upper_from(transition_documents())

        def mutate(upper, name):
            model = upper['owned_parameters']['observed_dynamics']
            row = next(r for r in model['observations'] if r['fact_ref'] == ref(0, 1))
            transition = row['transition']
            if name == 'boolean_beats': transition['source_meter']['beats'] = True
            elif name == 'zero_beats': transition['source_meter']['beats'] = 0
            elif name == 'noncanonical_unit': transition['source_meter']['beat_unit_q'] = '2/2'
            elif name == 'zero_denominator': transition['source_meter']['beat_unit_q'] = '1/0'
            elif name == 'missing_unit': del transition['source_meter']['beat_unit_q']
            elif name == 'bad_meter_ref': transition['meter_source_refs'] = ['track-0.json#/tuning']
            elif name == 'duplicate_meter_ref': transition['meter_source_refs'] *= 2
            elif name == 'missing_dependency': transition['dependency_refs'].remove(ref(0))
            elif name == 'duplicate_dependency': transition['dependency_refs'].append(ref(0))
            elif name == 'extra_dependency': transition['dependency_refs'] = sorted(transition['dependency_refs'] + [ref(5, 1)])
            elif name == 'unordered_dependencies': transition['dependency_refs'].reverse()
            elif name == 'wrong_influence_type': transition['influence_refs'] = False
            elif name == 'different_influence': transition['influence_refs'] = []
            elif name == 'duplicate_influence': transition['influence_refs'] *= 2
            elif name == 'forged_influence_namespace':
                row['declaration']['influence_refs'] = ['not-an-occurrence']
                transition['influence_refs'] = ['not-an-occurrence']
                transition['dependency_refs'] = sorted({ref(0, 1), ref(0), ref(1), 'not-an-occurrence'})
            elif name == 'cross_voice_boundary':
                transition['incoming_fact_ref'] = ref(0, voice=1)
                transition['dependency_refs'] = sorted(set(transition['dependency_refs']) - {ref(0)} | {ref(0, voice=1)})
            else: raise AssertionError(name)
            model['evidence_sha256'] = digest(observed_dynamics.evidence(model))

        cases = ('boolean_beats', 'zero_beats', 'noncanonical_unit', 'zero_denominator', 'missing_unit',
                 'bad_meter_ref', 'duplicate_meter_ref', 'missing_dependency', 'duplicate_dependency',
                 'extra_dependency', 'unordered_dependencies', 'wrong_influence_type', 'different_influence',
                 'duplicate_influence', 'forged_influence_namespace', 'cross_voice_boundary')
        for name in cases:
            with self.subTest(case=name):
                broken = deepcopy(original)
                mutate(broken, name)
                snapshot = deepcopy(broken)
                with self.assertRaises(ValueError):
                    realize(broken)
                self.assertEqual(broken, snapshot)

    def test_current_owner_unknown_choice_duplicate_and_source_pointer_are_refused(self):
        original = upper_from(level_documents())
        def unknown(model): model['current'][0]['definition_ref'] = 'dynamic-level:invented'
        def duplicate(model): model['current'].append(deepcopy(model['current'][0]))
        def pointer(model): model['current'][0]['structure']['pointer'] += '/forged'
        for mutation in (unknown, duplicate, pointer):
            with self.subTest(mutation=mutation.__name__):
                broken = deepcopy(original)
                mutation(broken['owned_parameters']['observed_dynamics'])
                with self.assertRaises(ValueError):
                    realize(broken)

    def test_influence_binds_actual_song_part_voice_and_declaration_occurrences(self):
        documents = level_documents()
        original = upper_from(documents)
        observed_dynamics.validate_source(original['owned_parameters']['observed_dynamics'], extract_documents(documents))
        cases = {
            'missing_bar': 'event:93:0:999:0:0:0',
            'missing_note': 'event:93:0:1:0:0:99',
            'wrong_song': 'event:94:0:1:0:0:0',
            'wrong_part': 'event:93:1:1:0:0:0',
            'existing_other_voice': 'event:93:0:1:1:0:0',
            'existing_other_declaration': 'event:93:0:2:0:0:0',
        }
        for label, occurrence in cases.items():
            with self.subTest(case=label):
                broken = deepcopy(original)
                model = broken['owned_parameters']['observed_dynamics']
                row = next(r for r in model['observations'] if r['fact_ref'] == ref(0))
                row['declaration']['influence_refs'] = [occurrence]
                transition = row['transition']
                transition['influence_refs'] = [occurrence]
                transition['dependency_refs'] = sorted({ref(0), occurrence, *(
                    r for r in (transition['incoming_fact_ref'], transition['following_boundary_fact_ref']) if r is not None)})
                model['evidence_sha256'] = digest(observed_dynamics.evidence(model))
                with self.assertRaises(ValueError):
                    observed_dynamics.validate_source(model, extract_documents(documents))
                with self.assertRaises(ValueError):
                    realize(broken)

    def test_unmigrated_nonzero_policy_refuses_edited_package_without_partial_changes(self):
        import local_accents
        upper = upper_from(level_documents(), note_accent_slots=True)
        edited, _ = local_dynamics.intervene(upper, controls(ref(0), seed=0))
        snapshot = deepcopy(edited)
        request = dict(context_policy=local_accents.POLICY, accents=100, target_ref='event:93:0:1:0:1:0', seed=0)
        for call in (lambda: reconstruct(edited, request), lambda: local_accents.intervene(edited, request)):
            with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
                call()
            self.assertEqual(edited, snapshot)
        self.assertEqual(reconstruct(edited, dict(request, accents=0)), realize(edited))

    def test_legacy_missing_origin_remains_exact_at_zero_but_refuses_new_choices(self):
        before = extract_documents(level_documents())
        legacy = strip_lower(analyze(before))
        legacy.pop('source_origin', None)
        snapshot = deepcopy(legacy)
        self.assertEqual(reconstruct(legacy, {'variation': 0}), before)
        self.assertEqual(reconstruct(legacy, controls(ref(0), strength=0)), before)
        for call in (
            lambda: reconstruct(legacy, controls(ref(0))),
            lambda: local_dynamics.intervene(legacy, controls(ref(0))),
        ):
            with self.assertRaisesRegex(ValueError, 'MISSING_ORIGINAL_OBSERVATIONS'):
                call()
            self.assertEqual(legacy, snapshot)


if __name__ == '__main__':
    unittest.main()
