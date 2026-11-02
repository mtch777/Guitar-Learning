"""Authored tests of shared octave authority, not style or listening evidence.

Acceptance: selected intervals have one canonical class/shape/register owner;
zero reconstructs the prior backing wrapper exactly; future octave changes use
that same relation after serialization. Unselected authority/guards survive,
and matching current pitches cannot excuse a changed backing relationship.
"""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest

import backing_motion_intervention as motion
import backing_pitch_ownership as backing
import figure_register_ownership as figure
import musical_tier2 as music
from connected_tier2 import realize
from source_fact_tier1 import project_documents
from test_backing_motion_intervention import SOURCE, TARGET, controls
from test_backing_relationship_preservation import EXTRA, INDEPENDENT, fixture


def prepared_fixture(*, owned_time=True, execution=True):
    docs, before, upper = fixture(owned_time=owned_time, execution=execution)
    owned = motion.own_intervals(upper, motion.prepare(upper, controls()))
    return docs, before, owned, deepcopy(owned['musical_relationships'])


def group(model):
    assert len(model['groups']) == 1
    return model['groups'][0]


def decoded_pitch(model, ref):
    normal = backing._normal(backing.expand(figure.expand(model)))
    return F(music.member_pitch(*backing._index(normal)[ref]))


def as_tier1(template, model):
    upper = deepcopy(template)
    upper['musical_relationships'] = figure.expand(model)
    return realize(upper)


class FigureRegisterOwnershipTests(unittest.TestCase):
    def test_one_canonical_relation_runs_both_directions_at_octave_boundaries(self):
        cases = [
            (['-3', '-5', '-8'], '9', ['0', '-2', '-5'], -1),
            (['0', '-12', '12'], '0', ['0', '-12', '12'], 0),
            (['12', '0', '24'], '0', ['0', '-12', '12'], 1),
            (['-12', '-24', '0'], '0', ['0', '-12', '12'], -1),
            (['-1/2', '3/2', '-25/2'], '23/2', ['0', '2', '-12'], -1),
        ]
        for intervals, class_, offsets, octave in cases:
            with self.subTest(intervals=intervals):
                expected = dict(interval_class=class_, offsets_semitones=offsets,
                                octave=octave, intervals=intervals)
                self.assertEqual(figure.relation(intervals=intervals), expected)
                self.assertEqual(figure.relation(interval_class=class_,
                    offsets_semitones=offsets, octave=octave), expected)

    def test_noncanonical_or_ambiguous_coordinates_refuse(self):
        invalid = [
            dict(intervals=['01', '2', '3']),
            dict(intervals=['1/1', '2', '3']),
            dict(intervals=[1, '2', '3']),
            dict(intervals=['NaN', '2', '3']),
            dict(interval_class='12', offsets_semitones=['0', '-2', '-5'], octave=-1),
            dict(interval_class='-1', offsets_semitones=['0', '-2', '-5'], octave=-1),
            dict(interval_class='9', offsets_semitones=['1', '-2', '-5'], octave=-1),
            dict(interval_class='9', offsets_semitones=['0', '-2', '-5'], octave=True),
            dict(interval_class='9', offsets_semitones=['0', '-2', '-5'], octave='-1'),
            dict(intervals=['-3', '-5', '-8'], interval_class='9',
                 offsets_semitones=['0', '-2', '-5'], octave=-1),
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(ValueError):
                figure.relation(**request)

    def test_zero_restores_the_entire_prior_wrapper_for_plain_and_owned_time(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                _, before, top, old = prepared_fixture(owned_time=owned_time)
                snapshot = deepcopy(old)
                shared = figure.lift(old, TARGET)
                self.assertEqual(old, snapshot)
                self.assertEqual(figure.expand(shared), old)
                self.assertEqual(figure.validate(shared), old)
                self.assertEqual(as_tier1(top, shared), before)
                self.assertEqual(figure.shift(shared, group(shared)['id'], group(shared)['octave']), shared)

    def test_selected_scalar_authorities_are_replaced_not_copied_beside_a_tag(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        g = group(shared)
        self.assertEqual(shared['schema'], figure.SCHEMA)
        self.assertEqual(set(g), {'id', 'occurrence_refs', 'interval_class', 'offsets_semitones', 'octave'})
        self.assertEqual(g['occurrence_refs'], TARGET)
        self.assertEqual(g['offsets_semitones'][0], '0')
        self.assertEqual(len(g['offsets_semitones']), len(TARGET))
        before_rows = {r['occurrence_ref']:r for r in old['relationships']}
        rows = {r['occurrence_ref']:r for r in shared['core']['relationships']}
        for ref in TARGET:
            self.assertEqual(set(rows[ref]), {'occurrence_ref', 'backing_ref', 'figure_register_ref'})
            self.assertEqual(rows[ref]['backing_ref'], before_rows[ref]['backing_ref'])
            self.assertEqual(rows[ref]['figure_register_ref'], g['id'])
            base, _ = backing._index(backing._body(shared['core']['core']))[ref]
            self.assertNotIn('bass_register_anchor', base)
        for ref in set(before_rows)-set(TARGET):
            self.assertEqual(rows[ref], before_rows[ref])
        self.assertEqual(shared['core']['core'], old['core'])
        self.assertEqual(shared['core']['written_tie_constraints'], old['written_tie_constraints'])
        self.assertEqual(shared['core']['execution_constraints'], old['execution_constraints'])

    def test_serialized_future_register_shift_moves_exactly_the_selected_figure(self):
        docs, _, top, old = prepared_fixture()
        shared = json.loads(json.dumps(figure.lift(old, TARGET)))
        snapshot = deepcopy(shared)
        g = group(shared)
        moved = figure.shift(shared, g['id'], g['octave']+1)
        self.assertEqual(shared, snapshot)
        for ref in TARGET:
            self.assertEqual(decoded_pitch(moved, ref), decoded_pitch(shared, ref)+12)
        for ref in SOURCE+[EXTRA]:
            self.assertEqual(decoded_pitch(moved, ref), decoded_pitch(shared, ref))
        old_pitches = [decoded_pitch(shared, ref) for ref in TARGET]
        new_pitches = [decoded_pitch(moved, ref) for ref in TARGET]
        self.assertEqual([old_pitches[i+1]-old_pitches[i] for i in range(2)],
                         [new_pitches[i+1]-new_pitches[i] for i in range(2)])
        expected = deepcopy(docs)
        for beat in expected['track-0.json']['measures'][1]['voices'][0]['beats'][:3]:
            beat['notes'][0]['fret'] += 12
        self.assertEqual(project_documents(as_tier1(top, moved)), expected)
        self.assertEqual(figure.shift(moved, g['id'], g['octave']), shared)

    def test_only_explicit_shared_register_change_is_authorized_by_history_check(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        g = group(shared)
        moved = figure.shift(shared, g['id'], g['octave']+1)
        with self.assertRaises(ValueError):
            figure.assert_preserved(shared, moved)
        figure.assert_preserved(shared, moved, mutable_groups=[g['id']])
        for field, value in [('interval_class', str((F(g['interval_class'])+1)%12)),
                             ('offsets_semitones', ['0', '1', '2'])]:
            corrupt = deepcopy(shared)
            group(corrupt)[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                figure.assert_preserved(shared, corrupt, mutable_groups=[g['id']])

    def test_unrelated_dependent_still_responds_to_its_backing(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        moved = deepcopy(shared)
        chord, _ = backing._index(backing._body(moved['core']['core']))[INDEPENDENT]
        chord['bass_register_anchor'] = str(F(chord['bass_register_anchor'])+2)
        self.assertEqual(decoded_pitch(moved, EXTRA), decoded_pitch(shared, EXTRA)+2)
        for ref in TARGET:
            self.assertEqual(decoded_pitch(moved, ref), decoded_pitch(shared, ref))
        # This is a real dependency response, but a register-only transaction
        # has no authority to alter that separate backing input.
        with self.assertRaises(ValueError):
            figure.assert_preserved(shared, moved, mutable_groups=[group(shared)['id']])

    def test_compensated_unrelated_rebind_refuses_even_when_current_notes_match(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        rebound = deepcopy(shared)
        row = next(r for r in rebound['core']['relationships'] if r['occurrence_ref'] == EXTRA)
        alternative = 'event:987:1:1:0:0:1'
        normal = backing._normal(backing.expand(old))
        index = backing._index(normal)
        dependent = F(music.member_pitch(*index[EXTRA]))
        anchor = F(music.member_pitch(*index[alternative]))
        row.update(backing_ref=alternative, interval_semitones=str(dependent-anchor))
        self.assertEqual(decoded_pitch(rebound, EXTRA), decoded_pitch(shared, EXTRA))
        for ref in SOURCE+TARGET:
            self.assertEqual(decoded_pitch(rebound, ref), decoded_pitch(shared, ref))
        with self.assertRaises(ValueError):
            figure.assert_preserved(shared, rebound, mutable_groups=[group(shared)['id']])

    def test_invalid_selection_is_not_silently_sorted_deduplicated_or_guessed(self):
        _, _, _, old = prepared_fixture()
        selections = [list(reversed(TARGET)), [TARGET[0], TARGET[0], TARGET[2]],
                      [TARGET[0], TARGET[1], EXTRA], [TARGET[0], TARGET[1], 'event:987:0:999:0:0:0']]
        original = deepcopy(old)
        for refs in selections:
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                figure.lift(old, refs)
            self.assertEqual(old, original)

    def test_missing_or_duplicate_scalar_owner_is_rejected_before_lifting(self):
        _, _, _, old = prepared_fixture()
        for kind in ('missing', 'duplicate'):
            altered = deepcopy(old)
            selected = next(r for r in altered['relationships'] if r['occurrence_ref'] == TARGET[1])
            if kind == 'missing':
                altered['relationships'].remove(selected)
            else:
                altered['relationships'].append(deepcopy(selected))
            snapshot = deepcopy(altered)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                figure.lift(altered, TARGET)
            self.assertEqual(altered, snapshot)

    def test_stale_missing_duplicate_and_overlapping_group_authorities_refuse(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        corruptions = []
        c = deepcopy(shared); group(c)['id'] += '-stale'; corruptions.append(c)
        c = deepcopy(shared); group(c)['offsets_semitones'].pop(); corruptions.append(c)
        c = deepcopy(shared); group(c)['occurrence_refs'][1] = TARGET[0]; corruptions.append(c)
        c = deepcopy(shared); c['groups'].append(deepcopy(group(c))); corruptions.append(c)
        c = deepcopy(shared); c['groups'] = []; corruptions.append(c)
        c = deepcopy(shared); group(c)['old_intervals'] = ['1', '2', '3']; corruptions.append(c)
        c = deepcopy(shared)
        row = next(r for r in c['core']['relationships'] if r['occurrence_ref'] == TARGET[1])
        row['interval_semitones'] = '-19'; corruptions.append(c)
        c = deepcopy(shared)
        row = next(r for r in c['core']['relationships'] if r['occurrence_ref'] == TARGET[1])
        row['figure_register_ref'] = 'figure-register:missing'; corruptions.append(c)
        for number, malformed in enumerate(corruptions):
            with self.subTest(corruption=number), self.assertRaises(ValueError):
                figure.expand(malformed)

    def test_unsupported_chains_and_self_anchors_are_not_hidden_by_grouping(self):
        _, _, _, old = prepared_fixture()
        for which in ('self', 'chain'):
            altered = deepcopy(old)
            ref = TARGET[0] if which == 'self' else EXTRA
            row = next(r for r in altered['relationships'] if r['occurrence_ref'] == ref)
            row['backing_ref'] = TARGET[0]
            row['interval_semitones'] = '0'
            with self.subTest(which=which), self.assertRaises(ValueError):
                figure.lift(altered, TARGET)

    def test_shift_requires_existing_identity_and_integer_octave_parameter(self):
        _, _, _, old = prepared_fixture()
        shared = figure.lift(old, TARGET)
        original = deepcopy(shared)
        for value in (True, 0.5, '0', None, float('nan')):
            with self.subTest(octave=value), self.assertRaises(ValueError):
                figure.shift(shared, group(shared)['id'], value)
        with self.assertRaises(ValueError):
            figure.shift(shared, 'figure-register:missing', 0)
        self.assertEqual(shared, original)


if __name__ == '__main__':
    unittest.main()
