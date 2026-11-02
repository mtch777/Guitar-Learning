"""Control capabilities compose; ownership and execution constraints still apply.

Synthetic fixtures reuse existing policy examples. This proves integration and
atomic refusals, not new musical evidence or arbitrary joint-control acceptance.
"""
from copy import deepcopy
from itertools import product
from pathlib import Path
import tempfile
import unittest

from connected_tier2 import analyze, strip_lower, realize, validate
from source_fact_tier1 import extract_documents
from test_local_accents import documents as accent_documents, TARGET as ACCENT
from test_palm_mute_opportunity_census import documents as palm_documents
from test_local_lever_combinations import (
    documents as rhythm_documents, INSIDE, control, changed_seed,
)
import local_accents as accents
import local_palm_mutes as palms


def with_tempo(docs):
    docs = deepcopy(docs)
    for name, part in docs.items():
        if name.startswith('track-'):
            part['automations'] = dict(tempo=[dict(measure=0, position=0, bpm=120, type=4)])
    return docs


def both_documents():
    docs = accent_documents()
    other = palm_documents()
    part = deepcopy(other['track-0.json'])
    part['songId'] = 93
    part['revisionId'] = 1
    part['partId'] = 1
    docs['track-1.json'] = part
    docs['metadata.json']['tracks'].append(deepcopy(other['metadata.json']['tracks'][0]))
    docs['track-0.json']['measures'].append(deepcopy(docs['track-0.json']['measures'][-1]))
    return with_tempo(docs)


def supported_controls(module, key, before, target, amount):
    evidence = module.options(before, target)
    for seed in range(64):
        controls = control(module, key, target, amount, seed)
        choice, decision = module.sample(evidence, controls)
        if amount == 0 or decision['changed']:
            return controls
    raise AssertionError('Existing source fixture has no changed draw')


class ControlOwnerCompatibilityTests(unittest.TestCase):
    def test_accent_control_works_with_every_supported_additional_owner(self):
        before = extract_documents(with_tempo(accent_documents()))
        for palm, tempo, amount in product((False, True), (False, True), (0, 50, 100)):
            with self.subTest(palm=palm, tempo=tempo, amount=amount):
                upper = strip_lower(analyze(before, note_accent_slots=True,
                                            palm_mute_slots=palm, step_tempos=tempo))
                original = deepcopy(upper)
                controls = supported_controls(accents, 'accents', before, ACCENT, amount)
                edited, decision = accents.intervene(upper, controls)
                after = validate(edited)
                self.assertEqual(upper, original)
                expected = deepcopy(upper)
                expected['owned_parameters']['optional_note_accents'] = deepcopy(
                    edited['owned_parameters']['optional_note_accents'])
                self.assertEqual(edited, expected)
                if amount:
                    self.assertTrue(decision['changed'])
                    accents.verify_effect(before, after, decision['evidence']['target']['note_ref'],
                                          decision['chosen']['state'])
                else:
                    self.assertEqual(edited, upper)
                    self.assertEqual(after, before)

    def test_palm_control_works_with_tempo_accent_and_written_time_owners(self):
        before = extract_documents(with_tempo(palm_documents()))
        for accent, tempo, amount in product((False, True), (False, True), (0, 50, 100)):
            with self.subTest(accent=accent, tempo=tempo, amount=amount):
                upper = strip_lower(analyze(before, note_accent_slots=accent,
                    palm_mute_slots=True, step_tempos=tempo,
                    rhythm_groups=True, rhythm_group_profile='written_time'))
                original = deepcopy(upper)
                controls = supported_controls(palms, 'palm_mute', before, 'coattack:0:1', amount)
                edited, decision = palms.intervene(upper, controls)
                after = validate(edited)
                self.assertEqual(upper, original)
                expected = deepcopy(upper)
                expected['owned_parameters']['optional_beat_palm_mutes'] = deepcopy(
                    edited['owned_parameters']['optional_beat_palm_mutes'])
                self.assertEqual(edited, expected)
                if amount:
                    self.assertTrue(decision['changed'])
                    palms.verify_effect(before, after, decision['evidence']['target']['beat_refs'],
                                        decision['chosen']['states'])
                else:
                    self.assertEqual(edited, upper)
                    self.assertEqual(after, before)

    def test_unmigrated_accent_palm_chains_refuse_atomically_in_both_orders(self):
        before = extract_documents(both_documents())
        upper = strip_lower(analyze(before, note_accent_slots=True, palm_mute_slots=True,
            step_tempos=True, rhythm_groups=True, rhythm_group_profile='written_time'))
        original = deepcopy(upper)
        for a, p in product((0, 50, 100), repeat=2):
            with self.subTest(accents=a, palm_mute=p):
                ac = supported_controls(accents, 'accents', before, ACCENT, a)
                pc = supported_controls(palms, 'palm_mute', before, 'coattack:1:1', p)
                accented, ad = accents.intervene(upper, ac)
                muted, pd2 = palms.intervene(upper, pc)
                if a and p:
                    # Coexisting owners are valid, but neither policy yet owns
                    # immutable original observations for an edited score.
                    for module, first, controls in ((palms, accented, pc), (accents, muted, ac)):
                        snapshot = deepcopy(first)
                        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
                            module.intervene(first, controls)
                        self.assertEqual(first, snapshot)
                    self.assertTrue(ad['changed'] and pd2['changed'])
                    self.assertEqual(upper, original)
                    continue
                ap, pd = palms.intervene(accented, pc)
                pa, ad2 = accents.intervene(muted, ac)
                self.assertEqual(ap, pa)
                self.assertEqual(validate(ap), validate(pa))
                self.assertEqual((ad['changed'], pd['changed']), (bool(a), bool(p)))
                self.assertEqual((ad['changed'], pd['changed']), (ad2['changed'], pd2['changed']))
                self.assertEqual(upper, original)

    def test_absent_owner_is_refused_at_nonzero_without_partial_mutation(self):
        for module, key, docs, target, owner in (
            (accents, 'accents', accent_documents(), ACCENT, 'optional_note_accents'),
            (palms, 'palm_mute', palm_documents(), 'coattack:0:1', 'optional_beat_palm_mutes'),
        ):
            before = extract_documents(with_tempo(docs))
            upper = strip_lower(analyze(before, step_tempos=True))
            original = deepcopy(upper)
            self.assertNotIn(owner, upper['owned_parameters'])
            for amount in (50, 100):
                with self.subTest(owner=owner, amount=amount):
                    controls = supported_controls(module, key, before, target, amount)
                    with self.assertRaisesRegex(ValueError, 'ownership required'):
                        module.intervene(upper, controls)
                    self.assertEqual(upper, original)
            out, _ = module.intervene(upper, control(module, key, target, 0))
            self.assertEqual(out, upper)

    def test_owner_presence_cannot_bypass_the_connected_contract(self):
        before = extract_documents(both_documents())
        upper = strip_lower(analyze(before, note_accent_slots=True, palm_mute_slots=True,
                                    step_tempos=True))
        accent_note = accents.options(before, ACCENT)['target']['note_ref']
        palm_beat = palms.options(before, 'coattack:1:1')['target']['beat_refs'][0]
        for kind in ('unknown_schema', 'duplicate_owner', 'missing_rule', 'overlap', 'extra_payload'):
            for module, owner in ((accents, 'optional_note_accents'), (palms, 'optional_beat_palm_mutes')):
                with self.subTest(kind=kind, owner=owner):
                    bad = deepcopy(upper)
                    model = bad['owned_parameters'][owner]
                    if kind == 'unknown_schema':
                        bad['schema'] = 'connected-source-musical-relations/999'
                    elif kind == 'duplicate_owner':
                        model['groups'].append(deepcopy(model['groups'][0]))
                    elif kind == 'missing_rule':
                        bad['coverage']['rules'].remove(dict(relation=model['groups'][0]['id']))
                    elif kind == 'overlap':
                        field = 'note_structure' if module is accents else 'beat_structure'
                        bad['source_structure']['facts'].append(deepcopy(model['groups'][0][field]))
                    else:
                        bad['owned_parameters']['unregistered_owner'] = {}
                    preserved = deepcopy(bad)
                    with self.assertRaises(ValueError):
                        if module is accents:
                            accents.apply(bad, accent_note, dict(kind='explicit', value=1))
                        else:
                            palms.apply(bad, [palm_beat], [dict(kind='explicit', value=True)])
                    self.assertEqual(bad, preserved)

    def test_plain_rhythm_dependency_still_refuses_new_accents_with_all_owners(self):
        before = extract_documents(with_tempo(rhythm_documents()))
        upper = strip_lower(analyze(before, rhythm_groups=True, note_accent_slots=True,
                                    palm_mute_slots=True, step_tempos=True))
        evidence = accents.options(before, INSIDE)
        seed = changed_seed(accents, evidence, 'accents', INSIDE,
                            predicate=lambda choice: choice['sound_level'] == 1)
        original = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, 'Rhythm group not supported by reconstructed source'):
            accents.intervene(upper, control(accents, 'accents', INSIDE, seed=seed))
        self.assertEqual(upper, original)
        self.assertEqual(realize(upper), before)

    def test_late_invalid_multibeat_state_cannot_partially_mutate_input(self):
        before = extract_documents(with_tempo(palm_documents()))
        upper = strip_lower(analyze(before, palm_mute_slots=True, step_tempos=True))
        refs = [g['beat_structure']['id'] for g in upper['owned_parameters']['optional_beat_palm_mutes']['groups'][:2]]
        original = deepcopy(upper)
        with self.assertRaises(ValueError):
            palms.apply(upper, refs, [dict(kind='explicit', value=True), dict(kind='explicit', value=1)])
        self.assertEqual(upper, original)

    def test_combined_owner_controls_run_in_the_actual_source_denied_worker(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before = extract_documents(both_documents())
        upper = strip_lower(analyze(before, note_accent_slots=True, palm_mute_slots=True,
            step_tempos=True, rhythm_groups=True, rhythm_group_profile='written_time',
            dynamic_evidence=True))
        self.assertEqual(upper['schema'], 'connected-source-musical-relations/5')
        code, _ = bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as folder:
            for module, key, target, purpose in (
                (accents, 'accents', ACCENT, 'local_accents_intervention'),
                (palms, 'palm_mute', 'coattack:1:1', 'local_palm_mute_intervention'),
            ):
                for amount in (0, 50, 100):
                    with self.subTest(control=key, amount=amount):
                        controls = supported_controls(module, key, before, target, amount)
                        edited, _ = module.intervene(upper, controls)
                        self.assertEqual(validate(edited), realize(edited))
                        result = execute(code, upper, controls, realize(edited),
                            Path(folder) / f'{key}-{amount}', timeout=45, purpose=purpose)
                        self.assertEqual(result['status'], 'PASS', result)


if __name__ == '__main__':
    unittest.main()
