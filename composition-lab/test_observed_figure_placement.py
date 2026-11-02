"""Authored geometry and ownership counterexamples, not artist-fit evidence."""
from copy import deepcopy
from fractions import Fraction as F
import json
import random
import unittest

import backing_pitch_ownership as backing
import figure_register_ownership as groups
import observed_figure_register as register
from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents


SONG = 90217


def beat(string, fret, duration=(1, 8), **flags):
    return dict(duration=list(duration), notes=[dict(string=string, fret=fret, **flags)])


def rest(duration):
    return dict(duration=list(duration), notes=[dict(rest=True)])


def bar(beats, extra_voice=None):
    voices = [dict(beats=beats)]
    if extra_voice is not None:
        voices.append(dict(beats=extra_voice))
    return dict(signature=[4, 4], voices=voices)


def fixture(*, occupied=(), incoming=False, donors=True, donor_hopo=False):
    # Three plain attacks with a lower source-supported register. Two D notes
    # fit their current string open; the C requires one of two lower strings.
    target = bar([beat(3, 12), beat(3, 12), beat(3, 10), rest((5, 8))],
        [rest((1, 16)), dict(duration=[15, 16], notes=[dict(string=s, fret=0) for s in occupied])] if occupied else None)
    donor_notes = [beat(5, 10, (1, 4)), beat(4, 3, (1, 4)),
                   beat(3, 12, (1, 4)), beat(3, 10, (1, 4))] if donors else [rest((1, 1))]
    if donor_hopo:
        donor_notes[1]['notes'][0]['hp'] = True
        # Same-string descending successor establishes a written pull-off.
        donor_notes[2] = beat(4, 1, (1, 4))
    measures = [target, bar(donor_notes)]
    if incoming:
        measures.insert(0, bar([rest((7, 8)), beat(3, 13, hp=True)]))
    target_bar = 2 if incoming else 1
    count = len(measures)
    docs = {'metadata.json': dict(songId=SONG, revisionId=1, title='Authored placement',
        artist='Test fixture', tracks=[dict(name='Guitar', instrumentId=27),
            dict(name='Backing', instrumentId=34), dict(name='Independent dependent', instrumentId=34)]),
        'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=27,
            tuning=[64, 59, 55, 50, 45, 40], frets=24, measures=measures),
        'track-1.json': dict(songId=SONG, revisionId=1, partId=1, instrumentId=34,
            tuning=[40], frets=36, measures=[bar([beat(0, 8 if i != count-1 else 10, (1, 1))]) for i in range(count)]),
        'track-2.json': dict(songId=SONG, revisionId=1, partId=2, instrumentId=34,
            tuning=[40], frets=36, measures=[bar([rest((1, 1))]) for _ in range(count-1)] + [bar([beat(0, 20, (1, 1))])])}
    refs = [f'event:{SONG}:0:{target_bar}:0:{i}:0' for i in range(3)]
    anchor = f'event:{SONG}:1:{target_bar}:0:0:0'
    extra = f'event:{SONG}:2:{count}:0:0:0'
    independent = f'event:{SONG}:1:{count}:0:0:0'
    bindings = [dict(occurrence_ref=ref, backing_ref=anchor) for ref in refs]
    bindings.append(dict(occurrence_ref=extra, backing_ref=independent))
    lower = extract_documents(docs)
    full = analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time',
        backing_bindings=bindings, figure_register_refs=refs)
    return docs, lower, strip_lower(full), refs, independent, extra


def control(level=100, seed=0, physical=100, placement=register.MINIMUM_STRING_CHANGES):
    return dict(context_policy=register.STANDALONE, register=level, seed=seed,
        physical=physical, placement_policy=placement)


def options_for(upper, refs):
    return register.choices(register.prepare_original(upper, refs), realize(upper), refs,
        placement_policy=register.MINIMUM_STRING_CHANGES)


def seed_for(options, shift, last_string=None, level=100):
    for seed in range(256):
        rng = random.Random('figure-register:' + str(seed))
        if rng.random() >= level / 100:
            continue
        chosen = rng.choice(options)
        contacts = rng.choice(chosen['contact_options'])
        if chosen['shift_semitones'] == shift and (last_string is None or list(contacts.values())[-1]['string'] == last_string):
            return seed
    raise AssertionError('Declared authored alternative was not sampled')


def string_parameter(upper, ref):
    _, _, part, measure, voice, note_beat, note = ref.split(':')
    pointer = f'track-{part}.json#/measures/{int(measure)-1}/voices/{voice}/beats/{note_beat}/notes/{note}/string'
    return next(row for row in upper['owned_parameters']['source_choices'] if row['fact_ref'] == pointer)


class FigurePlacementTests(unittest.TestCase):
    def assert_atomic_refusal(self, upper, request, reason):
        original = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, reason):
            register.intervene(upper, request)
        self.assertEqual(upper, original)

    def test_fresh_owner_and_exact_zero_remain_byte_equivalent(self):
        _, lower, upper, refs, _, _ = fixture()
        self.assertEqual(validate(upper), lower)
        self.assertEqual(upper['musical_relationships']['schema'], groups.SCHEMA)
        self.assertEqual(upper['musical_relationships']['core']['schema'], backing.EXECUTION_SCHEMA)
        raw = json.dumps(upper)
        result, decision = register.intervene(upper, control(0, physical=0))
        self.assertEqual(json.dumps(result), raw)
        self.assertFalse(decision['changed'])
        self.assertEqual(reconstruct(upper, control(0, physical=0)), lower)
        selected = {row['occurrence_ref']: row for row in upper['musical_relationships']['core']['relationships']}
        self.assertTrue(all('interval_semitones' not in selected[ref] for ref in refs))

    def test_both_minimum_contacts_reconstruct_only_the_declared_changes(self):
        docs, _, upper, refs, _, _ = fixture()
        options, refused = options_for(upper, refs)
        self.assertEqual([row['shift_semitones'] for row in options], [-12, 0])
        self.assertEqual(refused, [])
        self.assertEqual([len(row['contact_options']) for row in options], [2, 1])
        snapshot = deepcopy(upper)
        for last_string, last_fret in ((4, 3), (5, 8)):
            with self.subTest(last_string=last_string):
                changed, decision = register.intervene(upper, control(seed=seed_for(options, -12, last_string)))
                expected = deepcopy(docs)
                beats = expected['track-0.json']['measures'][0]['voices'][0]['beats']
                beats[0]['notes'][0]['fret'] = beats[1]['notes'][0]['fret'] = 0
                beats[2]['notes'][0] = dict(string=last_string, fret=last_fret)
                self.assertEqual(project_documents(realize(changed)), expected)
                self.assertEqual(decision['choice']['minimum_string_changes'], 1)
                self.assertEqual(decision['choice']['contact_option_count'], 2)
                self.assertEqual(changed['musical_relationships']['core'], upper['musical_relationships']['core'])
                self.assertEqual(changed['owned_parameters']['physical_positions'], upper['owned_parameters']['physical_positions'])
                self.assertEqual(changed['source_origin'], upper['source_origin'])
                old_choices = {r['fact_ref']: r for r in upper['owned_parameters']['source_choices']}
                changed_choices = {r['fact_ref']: r for r in changed['owned_parameters']['source_choices']}
                wanted = string_parameter(upper, refs[-1])['fact_ref']
                self.assertEqual({r for r in old_choices if old_choices[r] != changed_choices[r]}, {wanted})
                reloaded = json.loads(json.dumps(changed))
                self.assertEqual(realize(reloaded), realize(changed))
                self.assertEqual(register.intervene(reloaded, control(0))[0], reloaded)
        self.assertEqual(upper, snapshot)

    def test_register_is_sampled_before_contact_multiplicity(self):
        _, _, upper, refs, _, _ = fixture()
        options, _ = options_for(upper, refs)
        # Two contacts for -12 do not create two octave lottery entries.
        for level, seed in ((50, 0), (50, 1), (100, 0), (100, 1), (100, 5), (100, 9)):
            rng = random.Random('figure-register:' + str(seed))
            released = rng.random() < level / 100
            octave = rng.choice([-12, 0]) if released else None
            row = next((row for row in options if row['shift_semitones'] == octave), None)
            contacts = rng.choice(row['contact_options']) if row else None
            _, decision = register.intervene(upper, control(level, seed))
            self.assertEqual(decision['released'], released)
            self.assertEqual(decision['choice']['shift_semitones'] if decision['choice'] else None, octave)
            self.assertEqual(decision['choice']['contacts'] if decision['choice'] else None, contacts)

    def test_physical_lock_is_atomic_but_zero_register_choice_is_allowed(self):
        _, _, upper, refs, _, _ = fixture()
        options, _ = options_for(upper, refs)
        self.assert_atomic_refusal(upper, control(seed=seed_for(options, -12), physical=0), 'PHYSICAL_CONTACT_LOCK')
        unchanged, decision = register.intervene(upper, control(seed=seed_for(options, 0), physical=0))
        self.assertEqual(unchanged, upper)
        self.assertFalse(decision['changed'])

    def test_occupied_string_filters_each_contact_without_expanding_search(self):
        _, _, upper, refs, _, _ = fixture(occupied=(4,))
        options, refused = options_for(upper, refs)
        lower = next(row for row in options if row['shift_semitones'] == -12)
        self.assertEqual([row[refs[-1]] for row in lower['contact_options']], [dict(string=5, fret=8)])
        self.assertTrue(any(row['shift_semitones'] == -12 and row['contacts'][refs[-1]]['string'] == 4 for row in refused))
        changed, _ = register.intervene(upper, control(seed=seed_for(options, -12)))
        corrupt = deepcopy(changed)
        string_parameter(corrupt, refs[-1])['parameter'] = dict(normalized='4', negative_zero=False)
        with self.assertRaisesRegex(ValueError, 'OCCUPANCY|COLLISION'):
            realize(corrupt)
        _, _, upper, refs, _, _ = fixture(occupied=(4, 5))
        options, refused = options_for(upper, refs)
        self.assertEqual([row['shift_semitones'] for row in options], [0])
        self.assertEqual(sum(row['shift_semitones'] == -12 for row in refused), 2)

    def test_direct_invalid_contact_and_out_of_range_octave_refuse_in_inverse(self):
        _, _, upper, refs, _, _ = fixture()
        options, _ = options_for(upper, refs)
        changed, _ = register.intervene(upper, control(seed=seed_for(options, -12, 4)))
        for invalid in ('0', '6'):
            corrupt = deepcopy(changed)
            string_parameter(corrupt, refs[-1])['parameter'] = dict(normalized=invalid, negative_zero=False)
            with self.assertRaises(ValueError):
                realize(corrupt)
        corrupt = deepcopy(changed)
        corrupt['musical_relationships']['groups'][0]['octave'] += 8
        with self.assertRaises(ValueError):
            realize(corrupt)
        # A different physically valid free contact is representable. The
        # inverse enforces validity, not this selector's minimum-count taste.
        valid = deepcopy(changed)
        string_parameter(valid, refs[0])['parameter'] = dict(normalized='5', negative_zero=False)
        self.assertEqual(project_documents(realize(valid))['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0], dict(string=5, fret=10))

    def test_incoming_execution_and_linked_donors_are_not_plain_evidence(self):
        _, lower, upper, _, _, _ = fixture(incoming=True)
        self.assertEqual(realize(register.intervene(upper, control(0))[0]), lower)
        self.assert_atomic_refusal(upper, control(), 'FIGURE_EXECUTION_DEPENDENCY')
        _, _, upper, refs, _, _ = fixture(donor_hopo=True)
        prepared = register.prepare_original(upper, refs)
        options, _ = register.choices(prepared, realize(upper), refs, placement_policy=register.MINIMUM_STRING_CHANGES)
        self.assertFalse(any(row['shift_semitones'] == -12 for row in options))
        self.assertTrue(any(row['reason'] == 'SOURCE_EXECUTION_DEPENDENCY' for row in prepared['excluded']))

    def test_unrelated_dependent_retains_future_backing_behavior(self):
        _, _, upper, refs, independent, extra = fixture()
        options, _ = options_for(upper, refs)
        changed, _ = register.intervene(upper, control(seed=seed_for(options, -12)))
        old = next(row for row in upper['musical_relationships']['core']['relationships'] if row['occurrence_ref'] == extra)
        self.assertEqual(next(row for row in changed['musical_relationships']['core']['relationships'] if row['occurrence_ref'] == extra), old)
        moved = deepcopy(changed)
        core = moved['musical_relationships']['core']['core']
        independent_group, _ = backing._index(backing._body(core))[independent]
        independent_group['bass_register_anchor'] = str(F(independent_group['bass_register_anchor']) + 2)
        expected = project_documents(realize(changed))
        expected['track-1.json']['measures'][-1]['voices'][0]['beats'][0]['notes'][0]['fret'] += 2
        expected['track-2.json']['measures'][-1]['voices'][0]['beats'][0]['notes'][0]['fret'] += 2
        self.assertEqual(project_documents(realize(moved)), expected)

    def test_no_donors_generated_evidence_and_stale_origin_do_not_create_choices(self):
        _, _, upper, refs, _, _ = fixture(donors=False)
        self.assertEqual(options_for(upper, refs), ([], []))
        unchanged, decision = register.intervene(upper, control())
        self.assertEqual(unchanged, upper)
        self.assertIsNone(decision['choice'])
        _, _, upper, refs, _, _ = fixture()
        options, _ = options_for(upper, refs)
        changed, _ = register.intervene(upper, control(seed=seed_for(options, -12)))
        self.assert_atomic_refusal(changed, control(), 'UNSUPPORTED_CHAINED_EVIDENCE')
        forged = deepcopy(upper)
        forged['source_origin']['facts_sha256'] = '0' * 64
        self.assert_atomic_refusal(forged, control(), 'UNSUPPORTED_CHAINED_EVIDENCE')

    def test_old_fixed_string_and_expressive_scopes_remain_explicit(self):
        _, _, upper, refs, _, _ = fixture()
        prepared = register.prepare_original(upper, refs)
        options, refused = register.choices(prepared, realize(upper), refs)
        self.assertEqual([row['shift_semitones'] for row in options], [0])
        self.assertEqual(refused[0]['reason'], 'CURRENT_STRING_CONTACT_LIMIT')
        for policy in (register.POLICY, register.EXPRESSIVE):
            self.assert_atomic_refusal(upper, dict(control(), context_policy=policy), 'EXPLICIT_FIGURE_REGISTER_CONTROLS_REQUIRED')
        for invalid in (None, True, 'best_fingering', []):
            self.assert_atomic_refusal(upper, dict(control(), placement_policy=invalid), 'EXPLICIT_SUPPORTED_FIGURE_PLACEMENT_REQUIRED')
        old = deepcopy(upper)
        old['musical_relationships']['core']['schema'] = backing.SCHEMA
        old['musical_relationships']['core'].pop('execution_constraints')
        self.assert_atomic_refusal(old, control(), 'PLAIN_FIGURE_WITH_SHARED_EXECUTION_REQUIRED')

    def test_actual_source_denied_worker_accepts_placement_and_rejects_wrong_policy(self):
        from pathlib import Path
        import tempfile
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute

        docs, before, upper, refs, _, _ = fixture()
        options, _ = options_for(upper, refs)
        seed = seed_for(options, -12, 4)
        expected = deepcopy(docs)
        beats = expected['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[0]['notes'][0]['fret'] = beats[1]['notes'][0]['fret'] = 0
        beats[2]['notes'][0] = dict(string=4, fret=3)
        code, _ = bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temporary:
            for name, request, wanted, accepted in (
                ('zero', control(0, physical=0), before, True),
                ('changed', control(seed=seed), extract_documents(expected), True),
                ('wrong-policy', dict(control(seed=seed), context_policy=register.EXPRESSIVE), before, False),
            ):
                upper_before, wanted_before = deepcopy(upper), deepcopy(wanted)
                destination = Path(temporary)/name
                receipt = execute(code, upper, request, wanted, Path(temporary)/name,
                    timeout=40, purpose='guitar_figure_register')
                self.assertEqual(receipt['status'] == 'PASS', accepted, receipt)
                self.assertEqual(upper, upper_before)
                self.assertEqual(wanted, wanted_before)
                if accepted:
                    self.assertFalse(receipt['parent_expected_staged'])
                else:
                    self.assertEqual(receipt['failure_stage'], 'preflight')
                    self.assertFalse(receipt['reconstruction_started'])
                    self.assertTrue(any('Explicit plain-figure placement scope required' in issue
                                        for issue in receipt['issues']), receipt)
                    # No input, expected answer, executable code, or execution
                    # output exists in the worker that preflight rejected.
                    self.assertEqual(list((destination/'worker').iterdir()), [])
                    self.assertEqual({p.name for p in destination.iterdir()}, {'worker', 'result.json'})


if __name__ == '__main__':
    unittest.main()
