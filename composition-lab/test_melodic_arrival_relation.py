"""Authored arithmetic expectations; no source score or copied model answer cache."""
from copy import deepcopy
import json
import unittest

from melodic_arrival_relation import SCHEMA, fit, realize, validate


MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
LYDIAN = [0, 2, 4, 6, 7, 9, 11]


def reference(identity='C-major', tonic=0, intervals=MAJOR):
    return dict(id=identity, tonic_pc=tonic, intervals=list(intervals))


class MelodicArrivalRelationTests(unittest.TestCase):
    def test_source_and_flipped_approach_use_diatonic_not_equal_semitone_steps(self):
        source = ['68', '70', '71']
        model = fit(source, [reference('Eb-minor', 3, MINOR)])
        self.assertEqual(realize(model), source)
        self.assertEqual(realize(model, 'flip'), ['75', '73', '71'])
        self.assertEqual(model['original_direction'], 1)
        self.assertEqual(realize(model, 'flip')[-1], model['arrival_pitch'])
        self.assertEqual(model['count'], 3)

    def test_descending_source_reverses_to_ascending_with_same_arrival(self):
        model = fit(['67', '65', '64'], [reference()])
        self.assertEqual(model['original_direction'], -1)
        self.assertEqual(realize(model), ['67', '65', '64'])
        self.assertEqual(realize(model, 'flip'), ['60', '62', '64'])

    def test_register_crossings_negative_octaves_and_longer_approaches(self):
        cases = [
            (['59', '60', '62'], ['65', '64', '62'], reference()),
            (['-5', '-3', '-1'], ['2', '0', '-1'], reference()),
            (['-1', '0', '2'], ['5', '4', '2'], reference()),
            (['-1', '1', '3'], ['6', '4', '3'], reference('B-major', 11)),
            (['60', '62', '64', '65'], ['71', '69', '67', '65'], reference()),
        ]
        for source, flipped, interpretation in cases:
            with self.subTest(source=source):
                model = fit(source, [interpretation])
                self.assertEqual(realize(model), source)
                self.assertEqual(realize(model, 'flip'), flipped)

    def test_complete_multiple_interpretations_retained_when_realizations_agree(self):
        contexts = [reference(), reference('A-minor', 9, MINOR)]
        model = fit(['60', '62', '64'], contexts)
        self.assertEqual(model['interpretations'], contexts)
        self.assertEqual(realize(model, 'flip'), ['67', '65', '64'])

    def test_candidate_disagreement_refuses_without_changing_exact_original(self):
        contexts = [reference(), reference('C-lydian', 0, LYDIAN)]
        model = fit(['60', '62', '64'], contexts)
        frozen = deepcopy(model)
        validate(model)
        self.assertEqual(realize(model), ['60', '62', '64'])
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            realize(model, 'flip')
        self.assertEqual(model, frozen)
        # Neither input order nor selecting the other first interpretation may hide ambiguity.
        reversed_contexts = fit(['60', '62', '64'], contexts[::-1])
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            realize(reversed_contexts, 'flip')

    def test_outside_collection_skips_repeats_and_turns_refuse(self):
        for source in (['60', '61', '62'], ['60', '62', '65'],
                       ['60', '60', '62'], ['60', '62', '60'], ['60', '62'],
                       ['60', '62', '129/2']):
            with self.subTest(source=source), self.assertRaises(ValueError):
                fit(source, [reference()])
        # One interpretation accepting is insufficient.
        with self.assertRaises(ValueError):
            fit(['60', '62', '64'], [reference(), reference('C-minor', 0, MINOR)])

    def test_payload_has_no_pitch_sequence_and_survives_reload(self):
        model = fit(['60', '62', '64'], [reference()])
        self.assertEqual(set(model), {'schema', 'count', 'original_direction', 'arrival_pitch', 'interpretations'})
        self.assertEqual(model['schema'], SCHEMA)
        restored = json.loads(json.dumps(model))
        self.assertEqual(realize(restored), ['60', '62', '64'])
        self.assertEqual(realize(restored, 'flip'), ['67', '65', '64'])
        injected = dict(restored, pitches=['60', '62', '64'])
        with self.assertRaises(ValueError):
            validate(injected)

    def test_all_inputs_are_immutable_and_returned_context_has_no_alias(self):
        source = ['60', '62', '64'];contexts = [reference()]
        before = deepcopy((source, contexts))
        model = fit(source, contexts)
        realize(model);realize(model, 'flip');validate(model)
        self.assertEqual((source, contexts), before)
        contexts[0]['intervals'][1] = 1
        self.assertEqual(model['interpretations'][0]['intervals'], MAJOR)
        model['interpretations'][0]['id'] = 'changed-model-id'
        self.assertEqual(contexts[0]['id'], 'C-major')

    def test_malformed_models_contexts_and_modes_refuse(self):
        model = fit(['60', '62', '64'], [reference()])
        for field, value in [('count', True), ('count', 2), ('count', 3.0),
                             ('original_direction', True), ('original_direction', 0),
                             ('arrival_pitch', 64), ('arrival_pitch', '64.0'),
                             ('interpretations', []), ('schema', 'unknown')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate(dict(model, **{field: value}))
        for contexts in ([], [reference(), reference()], [dict(reference(), pitches=['60'])],
                         [reference('', 0)], [reference('bad-tonic', 12)],
                         [reference('bad-scale', 0, [0, 2, 4, 5, 7, 9, 12])]):
            with self.subTest(contexts=contexts), self.assertRaises(ValueError):
                fit(['60', '62', '64'], contexts)
        with self.assertRaises(ValueError):
            realize(model, 'random')
        # An incoming serialized model must agree in original mode too.
        bad = dict(model, arrival_pitch='65', interpretations=[reference(), reference('C-minor', 0, MINOR)])
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            validate(bad)


if __name__ == '__main__':
    unittest.main()
