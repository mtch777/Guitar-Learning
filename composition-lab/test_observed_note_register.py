"""Authored behavioral contrasts for an octave control, not style/listening evidence.

Acceptance: one source-observed register changes one literal fret; all other
score fields and existing relationships stay exact. Original observations do
not become generated observations. Linked execution and physical limits remain
binding, including when this operation follows melody inside one transaction.
"""
from copy import deepcopy
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, realize, strip_lower
from source_fact_tier1 import extract_documents, project_documents
import backing_pitch_ownership as owners
import observed_note_register as register
from test_backing_motion_intervention import (
    SOURCE, TARGET, controls as melody_controls, documents as melody_documents,
)


NOTE = 'event:987:2:1:0:0:1'
LOW_DONOR = 'event:987:2:2:0:0:0'
HIGH_DONOR = 'event:987:2:3:0:0:0'


def measure(beats):
    return dict(signature=[4, 4], voices=[dict(beats=beats)])


def attack(string, fret, duration=(1, 8), **flags):
    return dict(duration=list(duration), notes=[dict(string=string, fret=fret, **flags)])


def rest(duration):
    return dict(duration=list(duration), notes=[dict(rest=True)])


def documents():
    docs = melody_documents()
    docs['metadata.json']['tracks'].append(dict(name='Keyboard fixture', instrumentId=5))
    docs['track-2.json'] = dict(
        songId=987, revisionId=1, partId=2, instrumentId=5,
        tuning=[64, 59, 55, 50, 45, 40], frets=24,
        measures=[
            measure([dict(duration=[1, 1], chord=dict(text='Am7'), notes=[
                dict(string=1, fret=5), dict(string=2, fret=5),
                dict(string=3, fret=5), dict(string=4, fret=7),
            ])]),
            measure([attack(2, 5), rest((7, 8))]),
            measure([attack(1, 13), rest((7, 8))]),
        ],
    )
    return docs


def model(docs=None, **kwargs):
    before = extract_documents(documents() if docs is None else docs)
    return before, strip_lower(analyze(before, **kwargs))


def controls(level=100, seed=0, target=NOTE):
    return dict(context_policy=register.POLICY, register=level, target_ref=target, seed=seed)


def compound(level=100, seed=0):
    return dict(controls(level, seed), context_policy=register.COMPOUND,
                melody_controls=melody_controls())


def seed_for(prepared, pitch, level=100):
    # Authored fixture seed discovery only: no source selection or music claim.
    for seed in range(128):
        choice, decision = register.sample(prepared, level, seed)
        if choice is not None and choice['pitch'] == pitch:
            return seed
    raise AssertionError(f'The fixture did not sample its observed pitch {pitch}')


class ObservedNoteRegisterTests(unittest.TestCase):
    def test_one_observed_octave_changes_only_one_literal_fret(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                kwargs = dict(rhythm_groups=True, rhythm_group_profile='written_time') if owned_time else {}
                before, upper = model(**kwargs)
                snapshot = deepcopy(upper)
                prepared = register.prepare(upper, NOTE)
                evidence = deepcopy(prepared)
                edited, decision = register.intervene(upper, controls(seed=seed_for(prepared, 72)))
                expected = documents()
                expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][1]['fret'] = 17
                self.assertEqual(project_documents(realize(edited)), expected)
                self.assertTrue(decision['changed'])
                self.assertEqual(edited['source_origin'], upper['source_origin'])
                self.assertEqual(upper, snapshot)
                self.assertEqual(realize(upper), before)
                self.assertEqual(prepared, evidence)

    def test_zero_is_literal_even_without_an_alternative(self):
        docs = documents()
        docs['track-2.json']['measures'] = docs['track-2.json']['measures'][:1]
        _, upper = model(docs)
        with patch.object(register, 'prepare', side_effect=AssertionError('Zero queried donors')):
            self.assertEqual(register.intervene(upper, controls(0))[0], upper)
            both_zero = dict(compound(0), melody_controls=melody_controls(0))
            self.assertEqual(register.intervene(upper, both_zero)[0], upper)

    def test_percentages_release_choices_without_forcing_a_different_register(self):
        _, upper = model()
        prepared = register.prepare(upper, NOTE)
        before = deepcopy(prepared)
        runs = {level: [register.sample(prepared, level, seed) for seed in range(128)]
                for level in (0, 50, 100)}
        self.assertTrue(all(choice is None and not d['released'] for choice, d in runs[0]))
        self.assertTrue(all(d['released'] for _, d in runs[100]))
        self.assertEqual({choice['pitch'] for choice, _ in runs[100]}, {60, 72})
        self.assertEqual({d['released'] for _, d in runs[50]}, {False, True})
        self.assertTrue(any(d['released'] and not d['changed'] for _, d in runs[100]))
        self.assertEqual(runs[50], [register.sample(prepared, 50, seed) for seed in range(128)])
        self.assertEqual(prepared, before)

    def test_only_original_same_part_same_pitch_class_attacks_supply_votes(self):
        docs = documents()
        other = deepcopy(docs['track-2.json'])
        other['partId'] = 3
        other['measures'] = [measure([attack(0, 20, (1, 1))])]
        docs['track-3.json'] = other
        docs['metadata.json']['tracks'].append(dict(name='Other keyboard', instrumentId=5))
        _, upper = model(docs)
        prepared = register.prepare(upper, NOTE)
        self.assertEqual({o['pitch']: o['donor_refs'] for o in prepared['options']},
                         {60: [LOW_DONOR], 72: [HIGH_DONOR]})
        self.assertNotIn(NOTE, [r for o in prepared['options'] for r in o['donor_refs']])

    def test_fixed_string_limits_do_not_clamp_or_invent_an_octave(self):
        for case in ('declared_upper_bound', 'negative_fret'):
            with self.subTest(case=case):
                docs = documents()
                if case == 'declared_upper_bound':
                    docs['track-2.json']['frets'] = 16  # C5 donor f13 valid; target f17 invalid.
                    rejected_pitch = 72
                else:
                    docs['track-2.json']['measures'][2] = measure([attack(5, 8), rest((7, 8))])
                    rejected_pitch = 48  # C3 exists, but is below the selected notation string.
                _, upper = model(docs)
                prepared = register.prepare(upper, NOTE)
                self.assertEqual([o['pitch'] for o in prepared['options']], [60])
                self.assertIn(rejected_pitch, [o['pitch'] for o in prepared['rejected']])
                self.assertEqual(register.intervene(upper, controls())[0], upper)

    def test_controls_fail_before_source_choices(self):
        _, upper = model()
        bad = [dict(controls(), register=value) for value in
               (None, True, '50', float('nan'), float('inf'), -1, 101)]
        bad += [dict(controls(), seed=value) for value in (None, True, 1.5, '0')]
        bad += [dict(controls(), extra=True), dict(controls(), context_policy='unknown')]
        snapshot = deepcopy(upper)
        with patch.object(register, 'prepare', side_effect=AssertionError('Invalid controls queried evidence')):
            for request in bad:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    register.intervene(upper, request)
        self.assertEqual(upper, snapshot)

    def test_nonkeyboard_and_nonplain_target_are_not_silently_admitted(self):
        for kind in ('guitar', 'dead', 'tie_destination'):
            with self.subTest(kind=kind):
                docs = documents()
                if kind == 'guitar':
                    docs['track-2.json']['instrumentId'] = 27
                    docs['metadata.json']['tracks'][2]['instrumentId'] = 27
                else:
                    note = docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][1]
                    note['dead' if kind == 'dead' else 'tie'] = True
                _, upper = model(docs)
                with self.assertRaises(ValueError):
                    register.prepare(upper, NOTE)

    def test_plain_origin_of_a_written_tie_is_still_linked(self):
        docs = documents()
        docs['track-2.json']['measures'][1]['voices'][0]['beats'][0]['notes'][0]['tie'] = True
        _, upper = model(docs)
        original = deepcopy(upper)
        with self.assertRaises(ValueError):
            register.prepare(upper, NOTE)
        self.assertEqual(upper, original)

        # A tied origin is excluded as a donor too, even though only its
        # continuation carries the literal tie flag.
        docs = documents()
        docs['track-2.json']['measures'][2] = measure([
            attack(1, 13), attack(1, 13, tie=True), rest((3, 4)),
        ])
        _, upper = model(docs)
        prepared = register.prepare(upper, NOTE)
        self.assertEqual([o['pitch'] for o in prepared['options']], [60])
        self.assertTrue({HIGH_DONOR, 'event:987:2:3:0:1:0'} <=
                        {row['ref'] for row in prepared['excluded_donors']})

    def test_keyboard_hopo_with_unverified_destination_does_not_supply_plain_votes(self):
        docs = documents()
        docs['track-2.json']['measures'][2] = measure([
            attack(1, 12, hp=True), attack(1, 13), rest((3, 4)),
        ])
        _, upper = model(docs)
        # The approved HP detector excludes keyboard programs. We must not
        # invent its endpoint merely because this authored line looks obvious.
        # The declared narrow policy refuses that unknown part-level scope.
        with self.assertRaises(ValueError):
            register.prepare(upper, NOTE)

    def test_both_sides_of_an_existing_pitch_link_lock_changed_register_only(self):
        for side in ('anchor', 'dependent'):
            with self.subTest(side=side):
                before, upper = model()
                target = NOTE if side == 'anchor' else LOW_DONOR
                binding = (dict(occurrence_ref=SOURCE[0], backing_ref=NOTE) if side == 'anchor' else
                           dict(occurrence_ref=LOW_DONOR, backing_ref='event:987:1:2:0:0:0'))
                upper['musical_relationships'] = owners.lift(
                    upper['musical_relationships'], [binding], tier1=before, preserve_execution=True)
                self.assertEqual(realize(upper), before)
                snapshot = deepcopy(upper)
                prepared = register.prepare(upper, target)
                keep = controls(seed=seed_for(prepared, 60), target=target)
                self.assertEqual(register.intervene(upper, keep)[0], upper)
                change = controls(seed=seed_for(prepared, 72), target=target)
                with self.assertRaisesRegex(ValueError, 'REGISTER_BACKING_DEPENDENCY_LOCK'):
                    register.intervene(upper, change)
                self.assertEqual(upper, snapshot)

    def test_lowest_note_can_move_up_without_moving_the_other_chord_notes(self):
        docs = documents()
        notes = docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes']
        notes[:] = [dict(string=1, fret=5), dict(string=2, fret=5), dict(string=0, fret=3)]
        before, upper = model(docs)
        prepared = register.prepare(upper, NOTE)
        expected = deepcopy(docs)
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][1]['fret'] = 17
        edited, _ = register.intervene(upper, controls(seed=seed_for(prepared, 72)))
        self.assertEqual(project_documents(realize(edited)), expected)
        self.assertEqual(realize(upper), before)

    def test_generated_score_and_forged_choices_never_replace_original_evidence(self):
        _, upper = model()
        prepared = register.prepare(upper, NOTE)
        seed = seed_for(prepared, 72)
        edited, _ = register.intervene(upper, controls(seed=seed))
        snapshot = deepcopy(edited)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
            register.intervene(edited, controls(seed=seed))
        self.assertEqual(register.intervene(edited, controls(0))[0], edited)
        forged = deepcopy(prepared['options'][-1]); forged['pitch'] += 12; forged['fret'] += 12
        with self.assertRaises(ValueError):
            register.apply(upper, prepared, forged)
        corrupt = deepcopy(prepared)
        corrupt['before']['facts'][0]['value'] = 'different original observation'
        with self.assertRaises(ValueError):
            register.apply(upper, corrupt, prepared['options'][-1])
        self.assertEqual(edited, snapshot)

    def test_forging_both_the_option_and_choice_cannot_invent_source_evidence(self):
        docs = documents()
        # Both forged contacts below are geometrically valid. The refusal must
        # therefore come from their lack of original musical evidence, not a
        # coincidental fret-limit failure.
        docs['track-2.json']['frets'] = 36
        _, upper = model(docs)
        prepared = register.prepare(upper, NOTE)
        snapshot = deepcopy(upper)
        for pitch in (73, 84):  # Different pitch class; unwitnessed C6 octave.
            with self.subTest(forged_pitch=pitch):
                forged = deepcopy(prepared)
                index = next(i for i, row in enumerate(forged['options']) if row['pitch'] == 72)
                choice = forged['options'][index]
                choice.update(pitch=pitch, register=pitch // 12, fret=pitch - 55)
                self.assertIn(choice, forged['options'])
                self.assertLessEqual(choice['fret'], 36)
                with self.assertRaises(ValueError):
                    register.apply(upper, forged, deepcopy(choice))
                self.assertEqual(upper, snapshot)

    def test_forged_target_timing_metadata_cannot_relabel_the_original_observation(self):
        _, upper = model()
        prepared = register.prepare(upper, NOTE)
        choice = next(row for row in prepared['options'] if row['pitch'] == 72)
        snapshot = deepcopy(upper)
        for field, value in (('onset_q', '99'), ('duration_q', '1/8')):
            with self.subTest(field=field):
                forged = deepcopy(prepared)
                forged['target'][field] = value
                with self.assertRaises(ValueError):
                    register.apply(upper, forged, choice)
                self.assertEqual(upper, snapshot)

    def test_preedited_score_requires_explicit_compound_authorization(self):
        _, upper = model()
        prepared = register.prepare(upper, NOTE)
        choice = next(row for row in prepared['options'] if row['pitch'] == 72)
        preedited, _ = register.motion.intervene(upper, melody_controls())
        self.assertNotEqual(realize(preedited), realize(upper))
        snapshot = deepcopy(preedited)
        # A legitimate prior edit is still unauthorized at apply's default
        # boundary. Only the explicit compound route may declare its edit refs.
        with self.assertRaises(ValueError):
            register.apply(preedited, prepared, choice)
        self.assertEqual(preedited, snapshot)

    def test_compound_uses_original_evidence_and_retains_melody_relationships(self):
        before, upper = model()
        snapshot = deepcopy(upper)
        prepared = register.prepare(upper, NOTE)
        request = compound(seed=seed_for(prepared, 72))
        with patch.object(register, 'prepare', wraps=register.prepare) as watched:
            edited, decision = register.intervene(upper, request)
        self.assertEqual(watched.call_count, 1)
        self.assertEqual(watched.call_args.args[0], snapshot)
        expected = documents()
        beats = expected['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[1]['notes'][0] = dict(string=3, fret=3)
        beats[2]['notes'][0] = dict(string=3, fret=7)
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][1]['fret'] = 17
        self.assertEqual(project_documents(realize(edited)), expected)
        links = edited['musical_relationships']['relationships']
        self.assertEqual({r['occurrence_ref'] for r in links}, set(SOURCE + TARGET))
        melody_only, _ = register.motion.intervene(upper, request['melody_controls'])
        for field in ('relationships', 'written_tie_constraints', 'execution_constraints'):
            self.assertEqual(edited['musical_relationships'].get(field),
                             melody_only['musical_relationships'].get(field))
        self.assertEqual(decision['chosen']['donor_refs'], [HIGH_DONOR])
        self.assertEqual(upper, snapshot)
        self.assertEqual(realize(upper), before)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
            register.intervene(edited, request)

    def test_prepared_apply_rejects_unauthorized_source_structure(self):
        before, upper = model()
        prepared = register.prepare(upper, NOTE)
        choice = next(row for row in prepared['options'] if row['pitch'] == 72)
        snapshot = deepcopy(upper)
        reordered = deepcopy(before)
        reordered['facts'].reverse()
        # Exact fact values alone do not authorize a changed ordered source.
        with patch('connected_tier2.realize', return_value=reordered):
            with self.assertRaisesRegex(ValueError, 'UNAUTHORIZED_PRIOR_REGISTER_STRUCTURE'):
                register.apply(upper, prepared, choice)
        self.assertEqual(upper, snapshot)

    def test_compound_failure_after_melody_is_atomic(self):
        _, upper = model()
        snapshot = deepcopy(upper)
        prepared = register.prepare(upper, NOTE)
        request = compound(seed=seed_for(prepared, 72))
        with patch.object(register.motion, 'intervene', wraps=register.motion.intervene) as melody:
            with patch.object(register, 'apply', side_effect=ValueError('Authored second-operation refusal')):
                with self.assertRaisesRegex(ValueError, 'second-operation refusal'):
                    register.intervene(upper, request)
            self.assertEqual(melody.call_count, 1)
        self.assertEqual(upper, snapshot)


if __name__ == '__main__':
    unittest.main()
