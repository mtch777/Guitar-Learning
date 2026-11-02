"""Final-versus-stage reporting on existing owners and real operations.

Authored pre-owned fixtures, not source portability or listening evidence.
No mocked musical outputs: every reported expectation uses the shared inverse.
"""
from copy import deepcopy
import json
import random
import unittest

from connected_tier2 import realize, strip_lower
import backing_motion_intervention as motion
import figure_register_ownership as groups
import observed_figure_register as figure
import observed_note_register as note
from test_observed_figure_register import fixture, fixture_documents, request, seed_for
from test_observed_note_register import model, compound, NOTE, seed_for as note_seed
from test_figure_register_observations import fixture as retained_fixture, standalone


class CompoundChangeReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, _, full = fixture()
        cls.figure_upper = strip_lower(full)
        _, cls.note_upper = model(rhythm_groups=True, rhythm_group_profile='written_time')

    def assert_report(self, initial, after_melody, final, report):
        a, b, c = map(realize, (initial, after_melody, final))
        expected = dict(changed=c != a, melody_changed=b != a,
                        register_changed=c != b,
                        relationships_changed=final['musical_relationships'] != initial['musical_relationships'])
        self.assertEqual({key: report.get(key) for key in expected}, expected)
        self.assertEqual(final['source_origin'], initial['source_origin'])

    def figure_melody(self, upper, control):
        plain = deepcopy(upper)
        plain['musical_relationships'] = groups.expand(upper['musical_relationships'])
        return motion.intervene(plain, control['melody_controls'])[0]

    def exercise_figure(self, control):
        upper = deepcopy(self.figure_upper)
        snapshot = deepcopy(upper)
        middle = self.figure_melody(upper, control)
        final, report = figure.intervene(upper, control)
        self.assertNotEqual(realize(middle), realize(upper))
        self.assert_report(upper, middle, final, report)
        self.assertEqual(upper, snapshot)
        self.assertEqual(final['musical_relationships']['core'], upper['musical_relationships']['core'])
        return final

    def test_figure_melody_changed_register_zero(self):
        self.exercise_figure(request(0))

    def test_figure_register_unreleased_half_still_reports_melody(self):
        seed = next(s for s in range(32)
                    if random.Random('figure-register:' + str(s)).random() >= .5)
        self.exercise_figure(request(50, seed=seed))

    def test_figure_register_hundred_coincides_but_melody_changed(self):
        upper = deepcopy(self.figure_upper)
        middle = self.figure_melody(upper, request())
        prepared = figure.prepare_original(upper, request()['melody_controls']['target_refs'])
        options, _ = figure.choices(prepared, realize(middle), request()['melody_controls']['target_refs'])
        self.exercise_figure(request(100, seed=seed_for(options, 0)))

    def exercise_note(self, control):
        upper = deepcopy(self.note_upper)
        snapshot = deepcopy(upper)
        middle, _ = motion.intervene(upper, control['melody_controls'])
        final, report = note.intervene(upper, control)
        self.assertNotEqual(realize(middle), realize(upper))
        self.assert_report(upper, middle, final, report)
        self.assertEqual(upper, snapshot)
        return final

    def test_note_melody_changed_register_zero(self):
        self.exercise_note(compound(0))

    def test_note_register_unreleased_half_still_reports_melody(self):
        seed = next(s for s in range(32) if random.Random(s).random() >= .5)
        self.exercise_note(compound(50, seed=seed))

    def test_note_register_hundred_coincides_but_melody_changed(self):
        prepared = note.prepare(self.note_upper, NOTE)
        self.exercise_note(compound(100, seed=note_seed(prepared, 60)))

    def test_json_saved_current_zero_and_exact_unsupported_later_edit(self):
        for upper, operation, control in (
                (self.figure_upper, figure.intervene, request(0)),
                (self.note_upper, note.intervene, compound(0))):
            with self.subTest(policy=control['context_policy']):
                original = deepcopy(upper)
                edited, _ = operation(upper, control)
                saved = json.loads(json.dumps(edited))
                snapshot = deepcopy(saved)
                zero = deepcopy(control)
                zero['register'] = 0
                zero['melody_controls']['melody'] = 0
                current, report = operation(saved, zero)
                self.assertEqual(current, saved)
                self.assert_report(saved, saved, current, report)
                with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_CHAINED_EVIDENCE'):
                    operation(saved, control)
                self.assertEqual(saved, snapshot)
                self.assertEqual(upper, original)

    def test_retained_saved_sequence_remains_supported_and_observations_fixed(self):
        _, _, upper, _, _ = retained_fixture()
        snapshot = deepcopy(upper)
        melody, report = figure.intervene(upper, request(0))
        self.assert_report(upper, self.figure_melody(upper, request(0)), melody, report)
        saved = json.loads(json.dumps(melody))
        edited, report = figure.intervene(saved, standalone(100, seed=1))
        self.assert_report(saved, saved, edited, report)
        self.assertEqual(edited['owned_parameters'], saved['owned_parameters'])
        self.assertEqual(edited['musical_relationships']['core'], saved['musical_relationships']['core'])
        self.assertEqual(upper, snapshot)

    def test_real_compound_cancellation_distinguishes_stage_changes_from_final(self):
        docs = fixture_documents()
        target = docs['track-0.json']['measures'][1]['voices'][0]['beats']
        # Existing backing motion derives35/31/35; these47/43/47 source
        # contacts remain legal on the SAME strings throughout both stages.
        for beat, contact in zip(target, ((2, 14), (3, 15), (2, 14))):
            beat['notes'][0] = dict(string=contact[0], fret=contact[1])
        docs['track-0.json']['measures'].append(dict(signature=[4, 4], voices=[dict(beats=[
            dict(duration=[1, 4], notes=[dict(string=2, fret=14)]),
            dict(duration=[1, 4], notes=[dict(string=3, fret=15)]),
            dict(duration=[1, 4], notes=[dict(string=2, fret=14)]),
            dict(duration=[1, 4], notes=[dict(string=3, fret=3)]),
        ])]))
        # Reuse existing explicit bindings, avoiding the fixture convenience
        # selector's default octave-lock admission. The real request below
        # explicitly grants octave changes; no production guard is bypassed.
        bindings = [{key: row[key] for key in ('occurrence_ref', 'backing_ref')}
                    for row in groups.expand(self.figure_upper['musical_relationships'])['relationships']]
        _, _, full = fixture(docs, bindings=bindings)
        upper = strip_lower(full)
        snapshot = deepcopy(upper)
        middle = self.figure_melody(upper, request())
        prepared = figure.prepare_original(upper, request()['melody_controls']['target_refs'])
        options, _ = figure.choices(prepared, realize(middle), request()['melody_controls']['target_refs'])
        final, report = figure.intervene(upper, request(seed=seed_for(options, 12)))
        self.assertNotEqual(realize(middle), realize(upper))
        self.assertEqual(realize(final), realize(upper))
        self.assert_report(upper, middle, final, report)
        self.assertTrue(report['melody_changed'])
        self.assertTrue(report['register_changed'])
        self.assertFalse(report['changed'])
        self.assertEqual(upper, snapshot)


if __name__ == '__main__':
    unittest.main()
