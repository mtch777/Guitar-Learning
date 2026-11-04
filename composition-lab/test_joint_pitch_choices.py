"""Authored joint constraints; these tests make no listening-quality claim."""
from copy import deepcopy
from itertools import product
import json
import random
import unittest

from joint_pitch_choices import solve


def c(pitch, string=0, fret=0):
    return dict(pitch=pitch, string=string, fret=fret)


def step(left, right, baseline, change=True, **fields):
    return dict(from_ref=left, to_ref=right, baseline_step=baseline, change=change, **fields)


class JointPitchChoiceTests(unittest.TestCase):
    def test_individually_valid_contacts_can_be_jointly_impossible(self):
        options = {'held': [c(36, 5, 2)], 'fresh': [c(34, 5, 0)]}
        result = solve(options, simultaneous_groups=[['held', 'fresh']])
        self.assertEqual(result['status'], 'INFEASIBLE')
        self.assertTrue(result['exhaustive_contradiction'])
        self.assertIsNone(result['assignment'])
        options['fresh'].append(c(39, 4, 9))
        result = solve(options, simultaneous_groups=[['held', 'fresh']])
        self.assertEqual(result['assignment'], {'held': c(36, 5, 2), 'fresh': c(39, 4, 9)})

    def test_one_sustain_choice_must_fit_all_overlapping_groups(self):
        options = {'hold': [c(60, 0), c(60, 1)], 'first': [c(62, 0)], 'later': [c(64, 1)]}
        for group in (['hold', 'first'], ['hold', 'later']):
            self.assertEqual(solve(options, simultaneous_groups=[group])['status'], 'FEASIBLE')
        result = solve(options, simultaneous_groups=[['hold', 'first'], ['hold', 'later']])
        self.assertEqual(result['status'], 'INFEASIBLE')
        options['hold'].append(c(60, 2))
        result = solve(options, simultaneous_groups=[['hold', 'first'], ['hold', 'later']])
        self.assertEqual(result['assignment']['hold'], c(60, 2))

    def test_eight_sustain_occurrences_share_one_choice_with_seven_fresh_notes(self):
        options = {'hold': [c(36, 5, 2), c(48, 4, 7)]}
        options.update({f'fresh:{i}': [c(34, 5, 0)] for i in range(7)})
        groups = [['hold']] + [['hold', f'fresh:{i}'] for i in range(7)]
        result = solve(options, simultaneous_groups=groups)
        self.assertEqual(result['status'], 'FEASIBLE')
        self.assertEqual(result['assignment']['hold'], c(48, 4, 7))
        self.assertEqual(len(result['assignment']), 8)  # one hold, seven fresh variables

    def test_gesture_endpoints_share_string_without_collapsing_distinct_pitches(self):
        options = {'origin': [c(48, 2, 7), c(48, 3, 12)],
                   'destination': [c(43, 3, 7), c(43, 2, 2)]}
        result = solve(options, same_string_groups=[['origin', 'destination']])
        self.assertEqual(result['assignment'], {'origin': c(48, 2, 7), 'destination': c(43, 2, 2)})
        self.assertNotEqual(result['assignment']['origin']['pitch'], result['assignment']['destination']['pitch'])
        impossible = solve(options, same_string_groups=[['origin', 'destination']],
                           simultaneous_groups=[['origin', 'destination']])
        self.assertEqual(impossible['status'], 'INFEASIBLE')
        self.assertIsNone(impossible['assignment'])

    def test_retained_gesture_fret_direction_excludes_unison_and_wrong_direction(self):
        options = {'origin': [c(48, 2, 7)],
                   'destination': [c(48, 2, 7), c(50, 2, 9), c(43, 2, 2)]}
        common = dict(same_string_groups=[['origin', 'destination']])
        descending = dict(from_ref='origin', to_ref='destination', direction='descending')
        result = solve(options, fret_directions=[descending], **common)
        self.assertEqual(result['assignment']['destination'], c(43, 2, 2))
        ascending = dict(descending, direction='ascending')
        self.assertEqual(solve(options, fret_directions=[ascending], **common)['assignment']['destination'], c(50, 2, 9))
        reverse = dict(from_ref='destination', to_ref='origin', direction='ascending')
        self.assertEqual(solve(options, fret_directions=[reverse], **common)['assignment']['destination'], c(43, 2, 2))
        self.assertEqual(solve(options, fret_directions=[ascending, descending], **common)['status'], 'INFEASIBLE')

    def test_open_context_remains_explicit_candidate_admission(self):
        options = {'origin': [c(48, 2, 7)], 'destination': [c(41, 2, 0)]}
        result = solve(options, same_string_groups=[['origin', 'destination']],
            fret_directions=[dict(from_ref='origin', to_ref='destination', direction='descending')])
        self.assertEqual(result['assignment']['destination']['fret'], 0)
        with self.assertRaisesRegex(ValueError, 'known physical fret'):
            solve({'a': [c(None, 1, None)], 'b': [c(41, 1, 0)]},
                fret_directions=[dict(from_ref='a', to_ref='b', direction='ascending')])
        self.assertEqual(solve({'a': [c(48, 2, 7)]},
            fret_directions=[dict(from_ref='a', to_ref='a', direction='ascending')])['status'], 'INFEASIBLE')

    def test_protected_choice_survives_and_inputs_are_never_mutated(self):
        options = {'protected': [c(60, 0), c(62, 1)], 'moving': [c(64, 1), c(65, 0)]}
        fixed = {'protected': c(62, 1)}
        before = deepcopy((options, fixed))
        result = solve(options, simultaneous_groups=[['protected', 'moving']], fixed=fixed)
        self.assertEqual(result['assignment'], {'protected': c(62, 1), 'moving': c(65, 0)})
        self.assertEqual((options, fixed), before)
        result['assignment']['protected']['pitch'] = 99
        self.assertEqual((options, fixed), before)

    def test_changed_and_unchanged_signed_steps_are_final_output_predicates(self):
        options = {'a': [c(60)], 'b': [c(62), c(64), c(58)]}
        self.assertEqual(solve(options, step_constraints=[step('a', 'b', 2)])['assignment']['b']['pitch'], 64)
        self.assertEqual(solve(options, step_constraints=[step('a', 'b', 2, False)])['assignment']['b']['pitch'], 62)
        self.assertEqual(solve(options, step_constraints=[step('b', 'a', -2, False)])['assignment']['b']['pitch'], 62)
        # No extra rule requires changing string: changed pitch changes contact
        # under fixed tuning/capo, even when the chosen string stays the same.
        self.assertEqual(solve({'a': [c(65, 0, 5)]})['assignment']['a']['string'], 0)

    def test_explicit_opposite_direction_and_unresolved_repeat_intention(self):
        options = {'a': [c(60)], 'b': [c(62), c(64), c(58)]}
        result = solve(options, step_constraints=[step('a', 'b', 2, intention='opposite_direction')])
        self.assertEqual(result['assignment']['b']['pitch'], 58)
        with self.assertRaisesRegex(ValueError, 'no opposite direction'):
            solve(options, step_constraints=[step('a', 'b', 0, intention='opposite_direction')])
        self.assertEqual(solve({'a': [c(60)], 'b': [c(60), c(62)]},
            step_constraints=[step('a', 'b', 0)])['assignment']['b']['pitch'], 62)

    def test_contradictory_step_requests_and_repeated_variable_are_proved_impossible(self):
        options = {'a': [c(60)], 'b': [c(62), c(64)]}; before = deepcopy(options)
        result = solve(options, step_constraints=[step('a', 'b', 2), step('a', 'b', 2, False)])
        self.assertEqual(result['status'], 'INFEASIBLE')
        self.assertIsNone(result['assignment']); self.assertEqual(options, before)
        result = solve({'a': [c(60), c(62)]}, step_constraints=[step('a', 'a', 0)])
        self.assertEqual(result['status'], 'INFEASIBLE')
        self.assertEqual(result['examined_choices'], 0)

    def test_budget_exhaustion_is_not_a_musical_impossibility_claim(self):
        options = {'a': [c(60, 0), c(61, 1)], 'b': [c(62, 0)]}
        result = solve(options, simultaneous_groups=[['a', 'b']], max_nodes=1)
        self.assertEqual(result['status'], 'SEARCH_BUDGET_EXHAUSTED')
        self.assertFalse(result['decision_complete']); self.assertFalse(result['exhaustive_contradiction'])
        self.assertIsNone(result['assignment'])
        self.assertEqual(solve(options, simultaneous_groups=[['a', 'b']], max_nodes=2)['status'], 'FEASIBLE')
        result = solve({'a': [c(60)], 'b': [c(62)]}, simultaneous_groups=[['a', 'b']], max_nodes=1)
        self.assertEqual(result['status'], 'INFEASIBLE')  # all one-choice branches exhausted

    def test_components_preserve_budget_counts_and_no_partial_failed_assignment(self):
        result = solve({'a': [c(60)], 'b': [c(62)], 'c': [c(64)]}, max_nodes=1)
        self.assertEqual(result['status'], 'SEARCH_BUDGET_EXHAUSTED')
        self.assertEqual([r['examined_choices'] for r in result['components']], [1, 0])
        self.assertEqual(result['pending_components'], 1)
        self.assertIsNone(result['assignment'])
        self.assertEqual(solve({})['assignment'], {})

    def test_more_than_python_recursion_limit_in_one_connected_component(self):
        count = 1200
        options = {str(i): [c(2*i)] for i in range(count)}
        constraints = [step(str(i), str(i+1), 1) for i in range(count-1)]
        result = solve(options, step_constraints=constraints, max_nodes=count)
        self.assertEqual(result['status'], 'FEASIBLE')
        self.assertEqual(result['examined_choices'], count)
        self.assertEqual(len(result['components']), 1)

    def test_dead_pitch_can_reserve_string_without_inventing_a_pitch(self):
        options = {'dead': [c(None, 1, None)], 'pitched': [c(60, 1), c(60, 0)]}
        result = solve(options, simultaneous_groups=[['dead', 'pitched']])
        self.assertIsNone(result['assignment']['dead']['pitch'])
        self.assertEqual(result['assignment']['pitched']['string'], 0)
        with self.assertRaisesRegex(ValueError, 'known pitched'):
            solve(options, step_constraints=[step('dead', 'pitched', 0)])

    def test_saved_inputs_are_deterministic_and_caller_candidate_rank_is_retained(self):
        options = {'a': [c(65, 1), c(60, 0)], 'b': [c(64, 0), c(62, 1)]}
        result = solve(options, simultaneous_groups=[['a', 'b']])
        self.assertEqual(result, solve(json.loads(json.dumps(options)), simultaneous_groups=[['a', 'b']]))
        self.assertEqual(result['assignment'], {'a': c(65, 1), 'b': c(64, 0)})

    def test_small_authored_domains_match_independent_exhaustive_oracle(self):
        rng = random.Random(7319)
        for case in range(100):
            options = {}
            for ref in ('a', 'b', 'c', 'd'):
                candidates = []
                for _ in range(rng.randrange(1, 4)):
                    pitch = rng.randrange(48, 56); value = c(pitch, rng.randrange(3), pitch-40)
                    if value not in candidates: candidates.append(value)
                options[ref] = candidates
            groups = [list(pair) for pair in (('a','b'), ('b','c'), ('a','c','d')) if rng.randrange(2)]
            constraints = [step(a, b, rng.randrange(-3,4), bool(rng.randrange(2)))
                for a,b in (('a','b'), ('c','b'), ('b','d')) if rng.randrange(2)]
            same_string = [['a', 'd']] if rng.randrange(2) else []
            directions = [dict(from_ref='b', to_ref='c', direction=rng.choice(['ascending','descending']))] if rng.randrange(2) else []
            fixed = {'b': options['b'][-1]} if rng.randrange(2) else {}
            admissible = []
            for values in product(*options.values()):
                assignment = dict(zip(options, values))
                if any(assignment[ref] != value for ref,value in fixed.items()): continue
                if any(len({assignment[ref]['string'] for ref in group}) != len(group) for group in groups): continue
                if any(len({assignment[ref]['string'] for ref in group}) != 1 for group in same_string): continue
                if any((assignment[row['to_ref']]['fret'] <= assignment[row['from_ref']]['fret'])
                    if row['direction']=='ascending' else
                    (assignment[row['to_ref']]['fret'] >= assignment[row['from_ref']]['fret']) for row in directions): continue
                if any(((assignment[row['to_ref']]['pitch']-assignment[row['from_ref']]['pitch'])
                    != row['baseline_step']) != row['change'] for row in constraints): continue
                admissible.append(assignment)
            before = deepcopy((options, groups, constraints, fixed))
            result = solve(options, simultaneous_groups=groups, same_string_groups=same_string,
                fret_directions=directions, step_constraints=constraints, fixed=fixed)
            with self.subTest(case=case):
                self.assertEqual(result['status'], 'FEASIBLE' if admissible else 'INFEASIBLE')
                if admissible: self.assertIn(result['assignment'], admissible)
                self.assertEqual((options, groups, constraints, fixed), before)

    def test_invalid_late_constraints_and_choices_refuse_without_mutation(self):
        options = {'a': [c(60)], 'b': [c(62)]}; before = deepcopy(options)
        for kwargs in (dict(fixed={'a': c(65)}), dict(simultaneous_groups=[['a', 'a']]),
                       dict(step_constraints=[step('a', 'b', 2), step('a', 'missing', 2)]),
                       dict(max_nodes=True)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): solve(options, **kwargs)
            self.assertEqual(options, before)
        with self.assertRaisesRegex(ValueError, 'Duplicate candidate'):
            solve({'a': [c(60), c(60)]})
        with self.assertRaises(ValueError): solve({'a': [dict(c(60), degree_delta=1)]})
        self.assertEqual(solve({'a': []})['status'], 'INFEASIBLE')


if __name__ == '__main__':
    unittest.main()
