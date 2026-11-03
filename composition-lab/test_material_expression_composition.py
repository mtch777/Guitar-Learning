"""Existing expression owners survive shared-material timing operations.

The authored score uses complete coattacks, optional note/beat containers,
original dynamic observations, and an unrelated live backing relationship.
Expected score changes are specified independently of the material inverse.
"""
from copy import deepcopy
import json
import unittest

import connected_tier2 as connected
import local_accents as accents
import local_dynamics as dynamics
import material_rhythm_control as rhythm
import melodic_movement_ownership as movement
import musical_support_material as material
import observed_dynamics
import support_material_uses as uses
import test_direct_support_material as direct
import test_musical_cell_development as fixture
from source_fact_tier1 import extract_documents, project_documents


USE = 'material-use:0'
SPEC = dict(parts=[2, 3], first_bar=1, last_bar=1)
DYNAMIC = 'track-2.json#/measures/0/voices/0/beats/0/velocity'
ACCENT = 'track-2.json#/measures/0/voices/0/beats/1/notes/0'


def reload(value):
    return json.loads(json.dumps(value))


def authored_documents(*, tied=False):
    docs = direct.authored_documents()
    for part in (2, 3):
        track = docs[f'track-{part}.json']
        for bar in (1, 2, 4):
            beats = []
            for index, pitch in enumerate((50, 52, 50, 53)):
                notes = [dict(string=string, fret=pitch+interval-track['tuning'][string])
                         for string, interval in ((0, 0), (1, 7))]
                if index == (1 if bar == 1 else 2):
                    notes[0]['accentuated'] = 1
                beat = dict(type=4, duration=[1, 4], notes=notes)
                if index == 0:
                    beat['velocity'] = 'f' if bar != 4 else 'pp'
                    beat['palmMute'] = True
                if index == 2:
                    beat['velocity'] = 'pp'
                beats.append(beat)
            track['measures'][bar-1]['voices'][0]['beats'] = beats
        if tied:
            origin = track['measures'][0]['voices'][0]['beats'][3]['notes']
            destination = track['measures'][1]['voices'][0]['beats'][0]['notes']
            for before, after in zip(origin, destination):
                after['fret'] = before['fret']
                after['tie'] = True
    return docs


def build(*, optional=True, dynamic=True, tied=False):
    docs = authored_documents(tied=tied)
    lower = extract_documents(docs)
    t2 = connected.strip_lower(connected.analyze(lower,
        note_accent_slots=optional, palm_mute_slots=optional,
        dynamic_evidence=dynamic, backing_bindings=[direct.FOREIGN]))
    return docs, lower, t2


def expected_later(docs, bars=(1,)):
    result = deepcopy(docs)
    for part in (2, 3):
        for bar in bars:
            beats = result[f'track-{part}.json']['measures'][bar-1]['voices'][0]['beats']
            beats[0].update(duration=[3, 8], dots=1)
            beats[-1].update(duration=[1, 8], type=8)
    return result


def expression(t2):
    # Explicit intentions use the existing sole-owner update APIs. No raw
    # source facts or copied lower payloads are patched into the output.
    result = dynamics.apply(t2, DYNAMIC, 'pp')
    return accents.apply(result, ACCENT, dict(kind='absent'))


def expression_documents(docs):
    result = deepcopy(docs)
    beats = result['track-2.json']['measures'][0]['voices'][0]['beats']
    beats[0]['velocity'] = 'pp'
    del beats[1]['notes'][0]['accentuated']
    return result


class MaterialExpressionCompositionTests(unittest.TestCase):
    def test_material_fit_accepts_conditional_coverage_without_flattening_it(self):
        _, lower, t2 = build(dynamic=False)
        frozen = deepcopy(t2)
        definition = material.fit(t2, lower=lower, **SPEC)
        restored = material.restore_fragments(
            material._remove(t2, [definition['scope']]), [material.expand(definition)])
        self.assertEqual(connected.realize(restored), lower)
        self.assertEqual(restored, t2)
        self.assertEqual(t2, frozen)

    def test_original_observed_dynamics_roundtrips_without_duplicate_authority(self):
        docs, lower, t2 = build(optional=False)
        frozen = deepcopy(t2)
        model = uses.from_tier2(t2, [SPEC])
        self.assertEqual(uses.expand(reload(model)), t2)
        actual = uses.reconstruct(reload(model), {'variation': 0})
        self.assertEqual(actual, lower)
        self.assertEqual(project_documents(actual), docs)
        self.assertEqual(t2, frozen)

    def test_optional_accent_and_palm_mute_containers_survive_added_dots(self):
        docs, lower, t2 = build(dynamic=False)
        frozen = deepcopy(t2)
        model = uses.from_tier2(t2, [SPEC])
        self.assertEqual(uses.reconstruct(reload(model), {'variation': 0}), lower)
        changed = rhythm.candidate(rhythm.lift(model, USE), USE, '1/2')
        self.assertEqual(project_documents(uses.reconstruct(reload(changed), {'variation': 0})),
                         expected_later(docs))
        self.assertEqual(t2, frozen)

    def test_saved_expression_then_rhythm_preserves_evidence_and_later_dependency(self):
        docs, original_lower, t2 = build()
        frozen = deepcopy(t2)
        edited = expression(t2)
        expected = expression_documents(docs)
        self.assertEqual(project_documents(connected.realize(edited)), expected)
        model = uses.from_tier2(reload(edited), [SPEC])
        zero = rhythm.lift(model, USE)
        changed = rhythm.candidate(reload(zero), USE, '1/2')
        saved = reload(changed)
        self.assertEqual(project_documents(uses.reconstruct(saved, {'variation': 0})),
                         expected_later(expected))
        restored_t2 = uses.expand(saved)
        self.assertEqual(restored_t2['source_origin'], t2['source_origin'])
        self.assertEqual(observed_dynamics.evidence(restored_t2['owned_parameters']['observed_dynamics']),
                         observed_dynamics.evidence(t2['owned_parameters']['observed_dynamics']))
        self.assertEqual(restored_t2['musical_relationships']['relationships'],
                         t2['musical_relationships']['relationships'])
        self.assertEqual(restored_t2['owned_parameters']['optional_note_accents'],
                         edited['owned_parameters']['optional_note_accents'])
        # This pre-existing unrelated relationship must still respond after a
        # save/reload. Correct notes immediately after the edit are insufficient.
        core = movement._body(saved['lower_tier']['musical_relationships'])
        group = next(g for g in core['coattacks']
                     if any(m['id'] == fixture.FOREIGN_BACKING for m in g['members']))
        group['bass_register_anchor'] = '41'
        propagated = expected_later(expected)
        for part, pitch in ((2, 66), (3, 41)):
            track = propagated[f'track-{part}.json']
            note = track['measures'][8]['voices'][0]['beats'][0]['notes'][0]
            note['fret'] = pitch-track['tuning'][note['string']]
        self.assertEqual(project_documents(uses.reconstruct(saved, {'variation': 0})), propagated)
        # Original reconstruction is a separate state; current zero preserves
        # the expression edit and is deliberately not an original-score reset.
        self.assertEqual(connected.realize(t2), original_lower)
        reverted = rhythm.candidate(reload(changed), USE, '0')
        self.assertEqual(reverted, zero)
        self.assertEqual(project_documents(uses.reconstruct(reverted, {'variation': 0})), expected)
        self.assertEqual(t2, frozen)

    def test_current_zero_and_unsupported_nonzero_are_atomic(self):
        _, _, t2 = build()
        model = rhythm.lift(uses.from_tier2(expression(t2), [SPEC]), USE)
        changed = rhythm.candidate(model, USE, '1/2')
        frozen = deepcopy(changed)
        locked, report = rhythm.intervene(reload(changed), USE,
            dict(release=0, intention='earlier', seed=0))
        self.assertEqual(locked, changed)
        self.assertFalse(report['changed'])
        for offset in ('1', '-1', '0.5'):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                rhythm.candidate(changed, USE, offset)
            self.assertEqual(changed, frozen)

    def test_tied_coattacks_roundtrip_and_unsupported_shift_is_atomic(self):
        docs, lower, t2 = build(tied=True)
        model = uses.from_tier2(t2, [dict(parts=[2, 3], first_bar=1, last_bar=2)])
        zero = rhythm.lift(model, USE)
        actual = uses.reconstruct(reload(zero), {'variation': 0})
        self.assertEqual(actual, lower)
        self.assertEqual(project_documents(actual), docs)
        refs = [row for row in actual['facts'] if row['slot'] == 'tie']
        self.assertEqual(len(refs), 4)
        self.assertTrue(all(row['value'] is True for row in refs))
        frozen = deepcopy(zero)
        with self.assertRaisesRegex(ValueError, 'Tied clock displacement'):
            rhythm.candidate(zero, USE, '1/2')
        self.assertEqual(zero, frozen)
        self.assertEqual(uses.reconstruct(zero, {'variation': 0}), lower)

    def test_outgoing_tie_keeps_destination_and_full_sounding_endpoint(self):
        docs, _, t2 = build(tied=True)
        model = uses.from_tier2(t2, [SPEC])
        changed = rhythm.candidate(rhythm.lift(model, USE), USE, '1/2')
        actual = project_documents(uses.reconstruct(reload(changed), {'variation': 0}))
        self.assertEqual(actual, expected_later(docs))
        # The selected origin moves from beat 4 to beat 4-and; its continuation
        # stays at the next bar's first beat. The sounding endpoint remains q=5.
        from fractions import Fraction
        for part in (2, 3):
            beats = actual[f'track-{part}.json']['measures'][0]['voices'][0]['beats']
            destination = actual[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][0]
            onset = sum((4*Fraction(*b['duration']) for b in beats[:-1]), Fraction())
            end = onset+4*Fraction(*beats[-1]['duration'])+4*Fraction(*destination['duration'])
            self.assertEqual(onset, Fraction(7, 2))
            self.assertEqual(end, 5)
            self.assertEqual(destination, docs[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][0])

    def test_stored_material_cannot_duplicate_an_optional_beat_owner(self):
        _, lower, t2 = build()
        model = uses.from_tier2(t2, [SPEC])
        corrupt = reload(model)
        beat_ref = 'track-2.json#/measures/0/voices/0/beats/0'
        original_container = next(row for row in lower['facts'] if row['id'] == beat_ref)
        corrupt['materials'][0]['lower_tier']['source_structure'].append(deepcopy(original_container))
        frozen = deepcopy(corrupt)
        with self.assertRaises(ValueError):
            uses.reconstruct(corrupt, {'variation': 0})
        self.assertEqual(corrupt, frozen)
        definition = corrupt['materials'][0]
        before_definition = deepcopy(definition)
        with self.assertRaises(ValueError):
            uses.place(definition, corrupt['slots'][0], corrupt['uses'][0], parent=corrupt['lower_tier'])
        self.assertEqual(definition, before_definition)
        self.assertEqual(corrupt, frozen)

    def test_public_subsequent_dynamic_edit_packs_without_losing_saved_rhythm(self):
        docs, _, t2 = build()
        model = uses.from_tier2(expression(t2), [SPEC])
        changed = rhythm.candidate(rhythm.lift(model, USE), USE, '1/2')
        frozen = deepcopy(changed)
        current = uses.expand(reload(changed))
        following, decision = dynamics.intervene(current, dict(
            context_policy=dynamics.POLICY, dynamics=100, target_ref=DYNAMIC, seed=1))
        self.assertTrue(decision['changed'])
        packed = uses.pack_expression(changed, following)
        self.assertEqual(uses.expand(reload(packed)), following)
        expected = expected_later(expression_documents(docs))
        expected['track-2.json']['measures'][0]['voices'][0]['beats'][0]['velocity'] = 'f'
        self.assertEqual(project_documents(uses.reconstruct(reload(packed), {'variation': 0})), expected)
        self.assertEqual(packed['materials'], changed['materials'])
        self.assertEqual(packed['uses'], changed['uses'])
        self.assertEqual(observed_dynamics.evidence(following['owned_parameters']['observed_dynamics']),
                         observed_dynamics.evidence(t2['owned_parameters']['observed_dynamics']))
        self.assertEqual(changed, frozen)
        for level in (0, 50, 100):
            with self.subTest(level=level):
                next_t2, report = dynamics.intervene(uses.expand(packed), dict(
                    context_policy=dynamics.POLICY, dynamics=level, target_ref=DYNAMIC, seed=1))
                next_model = uses.pack_expression(packed, next_t2)
                self.assertEqual(uses.expand(next_model), next_t2)
                self.assertEqual(next_model['uses'], packed['uses'])
                self.assertEqual(report['changed'], next_t2 != uses.expand(packed))
                if level == 0:
                    self.assertEqual(next_model, packed)

    def test_expression_packing_refuses_other_valid_changes_atomically(self):
        _, _, t2 = build()
        model = rhythm.candidate(rhythm.lift(uses.from_tier2(expression(t2), [SPEC]), USE), USE, '1/2')
        current = uses.expand(model)
        # This is a valid, separate backing edit. The expression packer must
        # refuse it, not silently discard it or acquire another responsibility.
        core = movement._body(current['musical_relationships'])
        group = next(g for g in core['coattacks']
                     if any(m['id'] == fixture.FOREIGN_BACKING for m in g['members']))
        group['bass_register_anchor'] = '41'
        connected.realize(current)
        before, proposed = deepcopy(model), deepcopy(current)
        with self.assertRaises(ValueError):
            uses.pack_expression(model, current)
        self.assertEqual(model, before)
        self.assertEqual(current, proposed)

    def test_fixed_batch_equals_successive_operations_without_relearning_expression(self):
        docs, _, t2 = build()
        second = dict(parts=[2, 3], first_bar=4, last_bar=4)
        model = uses.from_tier2(expression(t2), [SPEC, second])
        requests = [dict(use_id=f'material-use:{i}', scope=dict(parts=spec['parts'],
            first_bar=spec['first_bar'], last_bar=spec['last_bar']), offset_q='1/2')
            for i, spec in enumerate((SPEC, second))]
        frozen = deepcopy(model)
        actual = rhythm.candidate_many(model, requests)
        successive = deepcopy(model)
        for request in requests:
            successive = rhythm.candidate(rhythm.lift(successive, request['use_id']),
                                          request['use_id'], request['offset_q'])
        self.assertEqual(actual, successive)
        self.assertEqual(project_documents(uses.reconstruct(reload(actual), {'variation': 0})),
                         expected_later(expression_documents(docs), bars=(1, 4)))
        self.assertEqual(model, frozen)
        self.assertEqual(uses.expand(actual)['source_origin'], t2['source_origin'])

    def test_batch_rejects_bad_identity_scope_and_offset_without_partial_edit(self):
        _, _, t2 = build()
        model = uses.from_tier2(expression(t2), [SPEC])
        request = dict(use_id=USE, scope=dict(parts=[2, 3], first_bar=1, last_bar=1), offset_q='1/2')
        invalid = [
            [request, deepcopy(request)],
            [dict(request, use_id='material-use:missing')],
            [dict(request, scope=dict(parts=[2, 3], first_bar=2, last_bar=2))],
            [dict(request, offset_q='0.5')],
            [dict(request, offset_q='1')],
        ]
        for requests in invalid:
            frozen_model, frozen_requests = deepcopy(model), deepcopy(requests)
            with self.subTest(requests=requests), self.assertRaises(ValueError):
                rhythm.candidate_many(model, requests)
            self.assertEqual(model, frozen_model)
            self.assertEqual(requests, frozen_requests)

    def test_relocation_cannot_silently_steal_destination_expression_owners(self):
        _, _, t2 = build()
        model = uses.from_tier2(t2, [SPEC, dict(parts=[2, 3], first_bar=4, last_bar=4)])
        original = deepcopy(model)
        proposal = reload(model)
        proposal['uses'][1]['material_ref'] = 0
        frozen = deepcopy(proposal)
        # This operation has no admitted policy for reassigning occurrence-bound
        # optional/dynamic owners. A valid-looking score cannot excuse lost links.
        with self.assertRaises(ValueError):
            uses.reconstruct(proposal, {'variation': 0})
        self.assertEqual(proposal, frozen)
        self.assertEqual(model, original)


if __name__ == '__main__':
    unittest.main()
