"""Authored counterexamples for written octave execution; no listening claims."""
from copy import deepcopy
import json
import unittest

import figure_execution_contract as contract
import figure_register_ownership as groups
from connected_tier2 import analyze, strip_lower, realize
from source_fact_tier1 import extract_documents, project_documents


def ref(beat, *, bar=1, part=0, note=0):
    return f'event:906:{part}:{bar}:0:{beat}:{note}'


def documents():
    curve = dict(tone=100, points=[dict(position=0, tone=0), dict(position=30, tone=100), dict(position=60, tone=100)])
    notes = [dict(string=5, fret=12, leftHandVibrato='slight'),
             dict(string=5, fret=12, tie=True, leftHandVibrato='slight'),
             dict(string=5, fret=12, tie=True, slide='downwards'),
             dict(string=5, fret=15, bend=curve), dict(string=5, fret=17)]
    durations = [[1, 8], [1, 8], [1, 4], [1, 4], [1, 4]]
    part = dict(songId=906, revisionId=1, partId=0, instrumentId=27,
                tuning=[64, 59, 55, 50, 45, 40], frets=36,
                measures=[dict(signature=[4, 4], voices=[dict(beats=[
                    dict(duration=d, notes=[n]) for d, n in zip(durations, notes)])])])
    backing = dict(songId=906, revisionId=1, partId=1, instrumentId=0,
                   tuning=[64, 59, 55, 50, 45, 40], frets=36,
                   measures=[dict(signature=[4, 4], voices=[dict(beats=[dict(
                       duration=[1, 1], notes=[dict(string=5, fret=7), dict(string=4, fret=2)])])])])
    return {'metadata.json': dict(songId=906, revisionId=1, artist='Authored fixture', title='Written closure',
                                 tracks=[dict(name='Guitar', instrumentId=27), dict(name='Backing', instrumentId=0)]),
            'track-0.json': part, 'track-1.json': backing}


def state(docs=None, bar=1):
    docs = documents() if docs is None else deepcopy(docs)
    lower = extract_documents(docs)
    refs = [ref(i, bar=bar) for i in range(5)]
    seeds = refs[2:]
    bindings = [dict(occurrence_ref=r, backing_ref=ref(0, bar=bar, part=1)) for r in refs]
    upper = strip_lower(analyze(lower, rhythm_groups=True, rhythm_group_profile='written_time', backing_bindings=bindings))
    upper['musical_relationships'] = groups.lift(upper['musical_relationships'], refs)
    group = upper['musical_relationships']['groups'][0]
    return docs, lower, upper, seeds, bindings, group


def change(docs, fn):
    output = deepcopy(docs); fn(output); return extract_documents(output)


class FigureExecutionContractTests(unittest.TestCase):
    def test_complete_tie_closure_and_unknown_slide_endpoint(self):
        docs, lower, upper, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        self.assertEqual(scope['closure']['member_refs'], [ref(i) for i in range(5)])
        self.assertEqual(scope['closure']['attack_root_refs'], [ref(i) for i in (0, 3, 4)])
        self.assertEqual(len(scope['closure']['tie_relations']), 2)
        self.assertEqual(scope['source_exit_endpoint'], 'unknown')
        exit_row = next(r for r in scope['effects'] if r['kind'] == 'symbolic_downward_exit')
        self.assertIsNone(exit_row['endpoint']); self.assertIsNone(exit_row['extent'])
        self.assertEqual(realize(upper), lower)
        self.assertIsNone(contract.validate(scope, realize(upper), group, bindings))
        self.assertNotIn('points', json.dumps(scope))
        self.assertNotIn('original_pitch', json.dumps(scope))

    def test_same_equation_shifts_all_five_fragments_and_preserves_every_other_source_fact(self):
        docs, lower, upper, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        saved = deepcopy((lower, upper, scope))
        for delta in (-1, 0, 1):
            moved = deepcopy(upper)
            moved['musical_relationships'] = groups.shift(upper['musical_relationships'], group['id'], group['octave'] + delta)
            result = realize(moved)
            expected = deepcopy(docs)
            for beat in expected['track-0.json']['measures'][0]['voices'][0]['beats']:
                beat['notes'][0]['fret'] += 12 * delta
            self.assertEqual(project_documents(result), expected)
            moved_group = moved['musical_relationships']['groups'][0]
            contract.validate(json.loads(json.dumps(scope)), result, moved_group, bindings)
            self.assertEqual(contract.build(result, seeds, moved_group, bindings), scope)
        self.assertEqual((lower, upper, scope), saved)

    def test_missing_tie_member_and_partial_tie_change_refuse(self):
        docs, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        partial = change(docs, lambda d: d['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0].update(fret=0))
        with self.assertRaises(ValueError): contract.validate(scope, partial, group, bindings)
        shortened = deepcopy(group); shortened['occurrence_refs'].pop(0); shortened['offsets_semitones'].pop(0)
        shortened['id'] = groups.identifier(shortened['occurrence_refs'])
        with self.assertRaises(ValueError): contract.build(lower, seeds, shortened, bindings[1:])
        no_tie = change(docs, lambda d: d['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0].pop('tie'))
        with self.assertRaises(ValueError): contract.validate(scope, no_tie, group, bindings)

    def test_nonuniform_geometry_even_with_consistent_new_interval_equation_refuses(self):
        docs, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        altered = change(docs, lambda d: d['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0].update(fret=16))
        changed_group = deepcopy(group); changed_group['offsets_semitones'][3] = '4'
        with self.assertRaisesRegex(ValueError, 'FIGURE_EXECUTION_CONTRACT_CONFLICT'):
            contract.validate(scope, altered, changed_group, bindings)

    def test_compensated_string_change_and_equal_pitch_backing_rebind_refuse(self):
        docs, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        altered = change(docs, lambda d: d['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0].update(string=4, fret=10))
        with self.assertRaisesRegex(ValueError, 'FIGURE_EXECUTION_CONTRACT_CONFLICT'):
            contract.validate(scope, altered, group, bindings)
        alternate = deepcopy(bindings); alternate[3]['backing_ref'] = ref(0, part=1, note=1)
        with self.assertRaisesRegex(ValueError, 'FIGURE_EXECUTION_CONTRACT_CONFLICT'):
            contract.validate(scope, lower, group, alternate)

    def test_bend_midpoint_vibrato_and_typed_literal_changes_refuse(self):
        docs, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        def midpoint(d): d['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['bend']['points'][1]['position'] = 20
        def typed_peak(d): d['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['bend']['points'][1]['tone'] = 100.0
        def vibrato(d): d['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0].pop('leftHandVibrato')
        def dynamic(d): d['track-0.json']['measures'][0]['voices'][0]['beats'][3]['velocity'] = 80
        for edit in (midpoint, typed_peak, vibrato, dynamic):
            with self.assertRaises(ValueError): contract.validate(scope, change(docs, edit), group, bindings)
        unchanged = deepcopy(scope)
        self.assertEqual(scope, unchanged)

    def test_missing_contract_hash_closure_or_invented_endpoint_refuses(self):
        _, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        for field in ('effects', 'fingerprints', 'closure'):
            bad = deepcopy(scope); del bad[field]
            with self.assertRaises(ValueError): contract.validate(bad, lower, group, bindings)
        bad = deepcopy(scope); next(r for r in bad['effects'] if r['kind'] == 'symbolic_downward_exit')['endpoint'] = '68'
        with self.assertRaises(ValueError): contract.validate(bad, lower, group, bindings)
        bad = deepcopy(scope); bad['closure']['member_refs'].pop(0)
        with self.assertRaises(ValueError): contract.validate(bad, lower, group, bindings)
        bad = deepcopy(scope); del bad['fingerprints']['relative_geometry']
        with self.assertRaises(ValueError): contract.validate(bad, lower, group, bindings)

    def test_physical_bounds_program_and_collision_remain_required(self):
        docs, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        for delta in (-24, 24):
            modified = deepcopy(docs)
            for beat in modified['track-0.json']['measures'][0]['voices'][0]['beats']:
                beat['notes'][0]['fret'] += delta
            changed_group = deepcopy(group); changed_group['octave'] += delta // 12
            with self.assertRaises(ValueError): contract.validate(scope, extract_documents(modified), changed_group, bindings)
        collision = deepcopy(docs)
        collision['track-0.json']['measures'][0]['voices'].append(dict(beats=[dict(duration=[1, 1], notes=[dict(string=5, fret=1)])]))
        with self.assertRaisesRegex(ValueError, 'WRITTEN_STRING_COLLISION'):
            contract.build(extract_documents(collision), seeds, group, bindings)
        piano = deepcopy(docs); piano['track-0.json']['instrumentId'] = 0
        with self.assertRaisesRegex(ValueError, 'GUITAR_PROGRAM'):
            contract.build(extract_documents(piano), seeds, group, bindings)

    def test_tied_bends_hopo_other_slides_and_unknown_expression_are_not_admitted(self):
        docs, _, _, seeds, bindings, group = state()
        for field, value in [('bend', deepcopy(docs['track-0.json']['measures'][0]['voices'][0]['beats'][3]['notes'][0]['bend'])),
                             ('hp', True), ('leftHandVibrato', 'wide'), ('slide', 'shift'), ('madeUpExpression', True)]:
            modified = deepcopy(docs); modified['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0][field] = value
            with self.assertRaises(ValueError): contract.build(extract_documents(modified), seeds, group, bindings)

    def test_incoming_unselected_hopo_dependency_refuses(self):
        docs = documents()
        prefix = dict(signature=[4, 4], voices=[dict(beats=[dict(duration=[1, 4], notes=[dict(string=5, fret=10, **({'hp': True} if i == 3 else {}))]) for i in range(4)])])
        docs['track-0.json']['measures'].insert(0, prefix)
        docs['track-1.json']['measures'].insert(0, deepcopy(docs['track-1.json']['measures'][0]))
        _, lower, _, seeds, bindings, group = state(docs, bar=2)
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_AFFECTED_FIGURE_EXECUTION'):
            contract.build(lower, seeds, group, bindings)

    def test_input_is_unchanged_on_success_and_all_failure_paths(self):
        _, lower, _, seeds, bindings, group = state()
        scope = contract.build(lower, seeds, group, bindings)
        inputs = deepcopy((lower, seeds, bindings, group, scope))
        contract.validate(scope, lower, group, bindings)
        wrong = deepcopy(group); wrong['octave'] += 1
        with self.assertRaises(ValueError): contract.validate(scope, lower, wrong, bindings)
        self.assertEqual((lower, seeds, bindings, group, scope), inputs)


if __name__ == '__main__':
    unittest.main()
