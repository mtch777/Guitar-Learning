"""Authored member choices, not evidence of an artist's preferred voicing."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import backing_pitch_ownership as backing
import connected_tier2 as connected
import material_degree_paths as degree
import musical_support_material as material
import musical_tier2 as music
import written_tie_pitch_ownership as ties
from source_fact_tier1 import extract_documents, project_documents
from test_material_degree_paths import C, G, authored, lift, pitches
from test_written_tie_pitch_ownership import beat, documents, note, ref


def saved(value):
    return json.loads(json.dumps(value))


def tied_fixture(*, signed=False):
    docs = documents([[beat(note(fret=12)),
                       beat(note(fret=12, tie=True), note(1, 13), note(2, 5)),
                       beat(note(fret=12, tie=True), note(1, 13), note(2, 2 if signed else 5)),
                       beat(note(fret=15))]])
    lower = extract_documents(docs)
    top = connected.strip_lower(connected.analyze(lower))
    top['musical_relationships'] = ties.lift(top['musical_relationships'], tier1=lower)
    plain = material.fit(top, parts=[0], first_bar=1, last_bar=1, lower=lower)
    return docs, lower, top, plain, lift(plain)


def restore(top, plain):
    return material._restore(material._remove(top, [plain['scope']]), [plain])


def group_ref(owned, member):
    return next(row['coattack_ref'] for row in owned['degree_paths']['bindings']
                if member in row['member_refs'])


def realized_pitches(top):
    core = top['musical_relationships']
    if core.get('schema') == ties.SCHEMA:
        core = ties.expand(core)
    return {ref: music.member_pitch(*pair) for ref, pair in backing._index(core).items()}


class DegreeMemberChoiceTests(unittest.TestCase):
    def test_held_lower_and_two_unison_uppers_spread_without_moving_the_hold(self):
        docs, lower, top, plain, owned = tied_fixture()
        before = deepcopy(owned)
        self.assertEqual(degree.expand(saved(owned), member_steps={}), plain)
        self.assertEqual(degree.expand(owned, member_steps={ref(1, 1): 0, ref(1, 2): 0}), plain)
        self.assertEqual(connected.realize(restore(top, degree.expand(owned))), lower)
        changed = degree.expand(owned, member_steps={ref(1, 2): 2})
        current = restore(top, changed)
        actual = realized_pitches(current)
        self.assertEqual([actual[ref(1, i)] for i in range(3)], ['52', '60', '64'])
        self.assertEqual(current['musical_relationships']['relationships'],
                         top['musical_relationships']['relationships'])
        self.assertEqual(current['musical_relationships']['groups'], top['musical_relationships']['groups'])
        self.assertEqual(changed['external_pitch_refs'], plain['external_pitch_refs'])
        expected = deepcopy(docs)
        expected['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][2]['fret'] = 9
        self.assertEqual(project_documents(connected.realize(current)), expected)
        self.assertEqual(owned, before)

    def test_saved_member_choice_and_later_basis_change_use_same_equations_without_files(self):
        _, _, top, _, owned = tied_fixture()
        request = saved(dict(definition=owned, member_steps={ref(1, 2): 2}))
        group = group_ref(owned, ref(1, 1))
        with patch.object(Path, 'read_text', side_effect=AssertionError('hidden source access')), \
             patch('builtins.open', side_effect=AssertionError('hidden source access')):
            first = degree.expand(request['definition'], member_steps=request['member_steps'])
            after = degree.expand(request['definition'], {group: 1},
                                  member_steps=request['member_steps'])
            self.assertEqual(realized_pitches(restore(top, first))[ref(1, 2)], '64')
            current = restore(top, after)
            actual = realized_pitches(current)
            self.assertEqual([actual[ref(1, i)] for i in range(3)], ['52', '62', '65'])
            connected.realize(current)  # existing full physical/contact validator

    def test_signed_free_shape_and_crossing_keep_original_basis_identity(self):
        _, _, top, plain, owned = tied_fixture(signed=True)
        self.assertIn([None, 0, -2], owned['degree_paths']['shapes'])
        self.assertEqual(degree.expand(owned), plain)
        group = group_ref(owned, ref(1, 1))
        changed = degree.expand(owned, member_steps={ref(1, 2): -2})
        actual = realized_pitches(restore(top, changed))
        self.assertEqual([actual[ref(1, i)] for i in range(3)], ['52', '60', '57'])
        again = degree.expand(saved(owned), {group: 1}, member_steps={ref(1, 2): -2})
        actual = realized_pitches(restore(top, again))
        self.assertEqual([actual[ref(1, i)] for i in range(3)], ['52', '62', '59'])
        with self.assertRaisesRegex(ValueError, 'stable free basis'):
            degree.expand(owned, member_steps={ref(1, 1): 1})

    def test_ordinary_member_crossing_canonicalizes_output_not_choice_identity(self):
        plain = authored(); owned = lift(plain)
        row = owned['degree_paths']['bindings'][0]
        group = row['coattack_ref']; upper = row['member_refs'][1]
        changed = degree.expand(owned, member_steps={upper: -2})
        self.assertEqual(pitches(changed)[group], [59, 57])
        expanded = material.expand(changed)
        actual = next(g for g in expanded['coattacks'] if g['id'] == group)
        self.assertEqual(actual['bass_register_anchor'], '57')
        self.assertEqual([m['voicing_interval'] for m in actual['members']], ['2', '0'])
        later = degree.expand(saved(owned), {group: 1}, member_steps={upper: -2})
        self.assertEqual(pitches(later)[group], [60, 59])

    def test_tied_unknown_unselected_and_noninteger_requests_refuse_atomically(self):
        _, _, _, _, tied = tied_fixture()
        dead = lift(authored(dead=True))
        dead_ref = dead['degree_paths']['bindings'][0]['member_refs'][-1]
        requests = [(tied, {ref(1): 0}), (tied, {ref(1): 1}),
                    (tied, {'missing': 1}), (tied, {ref(1, 2): True}),
                    (tied, {ref(1, 2): 1.0}), (tied, []), (dead, {dead_ref: 0})]
        for owned, request in requests:
            before = deepcopy(owned)
            with self.subTest(request=request), self.assertRaises(ValueError):
                degree.expand(owned, member_steps=request)
            self.assertEqual(owned, before)

    def test_hypothesis_disagreement_about_member_choice_is_not_silently_selected(self):
        plain = authored(ambiguous=True); owned = lift(plain, [C, G])
        upper = owned['degree_paths']['bindings'][0]['member_refs'][1]
        before = deepcopy(owned)
        with self.assertRaisesRegex(ValueError, 'interpretations disagree'):
            degree.expand(owned, member_steps={upper: 1})  # E -> F versus F-sharp
        self.assertEqual(owned, before)
        self.assertEqual(degree.expand(owned), plain)

    def test_foreign_owner_and_duplicate_tied_authority_stay_forbidden(self):
        _, _, _, plain, owned = tied_fixture()
        for kind in ('upper_member', 'singleton'):
            bad = deepcopy(plain)
            bad['external_pitch_refs'][0]['kind'] = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                lift(bad)
        bad = deepcopy(owned)
        row = next(r for r in bad['degree_paths']['bindings'] if ref(1) in r['member_refs'])
        bad['degree_paths']['shapes'][row['shape_refs'][0]][0] = 0
        with self.assertRaisesRegex(ValueError, 'external pitch owner'):
            degree.expand(bad)

    def test_execution_guard_survives_exactly_and_keeps_its_existing_validation(self):
        docs = documents([[beat(note(fret=12, slide='downwards')), beat(note(fret=13)),
                           beat(note(fret=15)), beat(note(fret=17))]])
        lower = extract_documents(docs)
        top = connected.strip_lower(connected.analyze(lower))
        plain = material.fit(top, parts=[0], first_bar=1, last_bar=1, lower=lower)
        guard = deepcopy(plain['unresolved_execution_locks'])
        owned = lift(plain)
        self.assertEqual(degree.expand(saved(owned)), plain)
        self.assertEqual(owned['unresolved_execution_locks'], guard)
        group = group_ref(owned, ref(3))
        changed = degree.expand(owned, {group: 1})
        self.assertEqual(changed['unresolved_execution_locks'], guard)
        current = connected.realize(restore(top, changed))
        material.validate_execution(changed, current)
        protected = degree.expand(owned, {group_ref(owned, ref(0)): 1})
        with self.assertRaisesRegex(ValueError, 'context changed'):
            material.validate_execution(protected, connected.realize(restore(top, protected)))


if __name__ == '__main__':
    unittest.main()
