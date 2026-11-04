"""Authored quota/ownership counterexamples; no musical-quality assertions."""
from copy import deepcopy
from fractions import Fraction as F
import json
import unittest
from unittest.mock import patch

import backing_pitch_ownership as backing
import melodic_movement_ownership as movement
import movement_output_control as control
from connected_tier2 import realize
from test_melodic_movement_ownership import (
    build_v2, v2_documents, documents, output, selected_pitches,
    set_pitches, TARGET, REFERENCE, BACKING, DEPENDENT,
)


def request(melody=0, register=0, *, intent='follow_reference_motion', direction='up', seed=0):
    return dict(melody=melody, register=register, intent=intent,
                register_direction=direction, seed=seed)


def positive(docs=None, **options):
    # Reference steps3,-1 alter movement without an incidental octave crossing.
    docs=set_pitches(v2_documents() if docs is None else docs,[67,70,69],measure=0)
    return build_v2(docs,**options)


class MovementOutputControlTests(unittest.TestCase):
    def test_zero_and_saved_zero_use_complete_existing_inverse(self):
        _, lower, _, owned = positive()
        frozen = deepcopy(owned)
        zero, report = control.intervene(owned, request())
        self.assertEqual(zero, owned)
        self.assertEqual(realize(zero), lower)
        self.assertTrue(report['satisfied']); self.assertFalse(report['changed'])
        changed, _ = control.intervene(owned, request(100, 100))
        saved = json.loads(json.dumps(changed))
        zero, report = control.intervene(saved, request())
        self.assertEqual(zero, saved)
        self.assertEqual(realize(zero), realize(changed))
        self.assertTrue(report['satisfied'])
        self.assertEqual(owned, frozen)

    def test_fifty_changes_exactly_one_of_two_signed_steps_for_every_seed(self):
        _, _, _, owned = positive()
        snapshot = deepcopy(owned)
        for seed in (0, 1, 9):
            changed, report = control.intervene(owned, request(50, seed=seed))
            self.assertTrue(report['satisfied'], report)
            pitches = selected_pitches(output(changed))
            steps = [b-a for a,b in zip(pitches,pitches[1:])]
            self.assertEqual(sum(a != b for a,b in zip(steps, [1,1])), 1)
            self.assertIn(steps, ([3,1], [1,-1]))
            row = report['final_output']['features']['melody']
            self.assertEqual((row['total_count'],row['changed_count'],row['target_count']), (2,1,1))
            self.assertEqual(report['final_output']['features']['register']['changed_count'], 0)
            repeated, repeated_report = control.intervene(owned, request(50, seed=seed))
            self.assertEqual((changed,report),(repeated,repeated_report))
        self.assertEqual(owned, snapshot)

    def test_all_steps_and_common_octave_are_measured_independently(self):
        _, _, _, owned = positive()
        for m,r in ((100,0),(0,100),(100,100)):
            changed, report = control.intervene(owned,request(m,r))
            self.assertTrue(report['satisfied'], report)
            pitches = selected_pitches(output(changed))
            steps = [b-a for a,b in zip(pitches,pitches[1:])]
            self.assertEqual(steps, [3,-1] if m else [1,1])
            shift = pitches[0]-60
            if r:self.assertIn(shift,(12,24))
            else:self.assertEqual(shift,0)
            self.assertEqual(report['final_output']['features']['melody']['changed_count'], 2 if m else 0)
            self.assertEqual(report['final_output']['features']['register']['changed_count'], 3 if r else 0)
            measured = control.measurements(changed, baseline_upper=owned, lower=realize(changed))
            self.assertEqual(control.evaluate_targets(report['contract'],measured),report['final_output'])
            if not r:self.assertEqual(pitches,[60,63,62])

    def test_common_register_half_is_atomic_unsatisfied_with_full_denominator(self):
        _, _, _, owned = positive(); frozen=deepcopy(owned)
        unchanged, report = control.intervene(owned, request(0,50))
        self.assertEqual(unchanged,frozen); self.assertEqual(owned,frozen)
        self.assertEqual(report['status'],'TARGET_UNSATISFIED')
        self.assertFalse(report['satisfied'])
        row=report['baseline']['features']['register']
        self.assertEqual((row['total_count'],row['target_count']), (3,2))
        self.assertEqual(report['algebraic_register_counts'],[0,3])

    def test_equal_zero_and_reference_steps_cannot_earn_change_credit(self):
        for intent in ('repeat_start','follow_reference_motion'):
            docs=v2_documents()
            if intent=='repeat_start':docs=set_pitches(docs,[60,60,62])
            else:docs=set_pitches(docs,[67,68,70],measure=0)
            _,_,_,owned=build_v2(docs)
            unchanged,report=control.intervene(owned,request(100,intent=intent))
            self.assertEqual(unchanged,owned)
            self.assertEqual(report['status'],'TARGET_UNSATISFIED')
            self.assertEqual(report['algebraic_melody_max_changed'],1)
            self.assertEqual(report['baseline']['features']['melody']['total_count'],2)
            changed,report=control.intervene(owned,request(50,intent=intent))
            self.assertTrue(report['satisfied'],report)
            self.assertEqual(report['final_output']['features']['melody']['changed_count'],1)

    def test_joint_placement_can_work_when_movement_only_is_impossible(self):
        docs=documents();part=docs['track-0.json'];old=part['tuning']
        for measure in part['measures']:
            for beat in measure['voices'][0]['beats']:
                for note in beat['notes']:
                    if 'fret' in note:
                        pitch=old[note['string']]+note['fret']
                        note.update(string=0,fret=pitch-60)
        # +12 leaves the final attack in its original octave. +24 is needed
        # to change ALL actual octaves, and declared36-fret geometry permits it.
        part.update(tuning=[60,60,60,60,60,60],frets=36)
        _,lower,_,owned=build_v2(docs)
        parameters=deepcopy(owned['owned_parameters'][movement.SLOT]['parameters'])
        parameters['steps']=[movement.REFERENCE_STEP]*2
        with self.assertRaisesRegex(ValueError,'NO_CONTACT'):
            movement._placed_candidate(owned,parameters,lower)
        changed,report=control.intervene(owned,request(100,100))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(selected_pitches(output(changed)),[84,91,82])

    def test_complete_coattacks_ties_and_unrelated_live_owner_survive(self):
        docs=v2_documents(coattack=True,tied=True)
        _,_,_,owned=positive(docs,unrelated=True)
        prior=deepcopy(owned);links=deepcopy(owned['musical_relationships']['relationships'])
        changed,report=control.intervene(owned,request(100,100))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(changed['musical_relationships']['relationships'],links)
        self.assertEqual(changed['owned_parameters'][movement.SLOT]['attacks'],
                         owned['owned_parameters'][movement.SLOT]['attacks'])
        self.assertEqual(changed['owned_parameters'][movement.SLOT]['observations'],
                         owned['owned_parameters'][movement.SLOT]['observations'])
        actual=output(changed);pitches=selected_pitches(actual,tied=True)
        self.assertEqual(pitches[2],pitches[3])
        self.assertEqual(report['final_output']['features']['register']['total_count'],3)
        for i in range(4):
            self.assertEqual(actual['track-0.json']['measures'][1]['voices'][0]['beats'][i]['notes'][1:],
                             docs['track-0.json']['measures'][1]['voices'][0]['beats'][i]['notes'][1:])
        saved=json.loads(json.dumps(changed))
        index=backing._index(movement._body(saved['musical_relationships']))
        index[BACKING][0]['bass_register_anchor']='41'
        later=output(saved)
        dependent=later['track-0.json']['measures'][2]['voices'][0]['beats'][0]['notes'][0]
        self.assertEqual(later['track-0.json']['tuning'][dependent['string']]+dependent['fret'],73)
        self.assertEqual(saved['musical_relationships']['relationships'],links)
        self.assertEqual(owned,prior)

    def test_saved_next_edit_uses_current_steps_and_retains_observations(self):
        _,_,_,owned=positive()
        changed,first=control.intervene(owned,request(100))
        self.assertTrue(first['satisfied'])
        saved=json.loads(json.dumps(changed));old_observations=deepcopy(saved['owned_parameters'][movement.SLOT]['observations'])
        second,report=control.intervene(saved,request(100,intent='repeat_start'))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(selected_pitches(output(second)),[60,60,60])
        self.assertEqual(second['owned_parameters'][movement.SLOT]['observations'],old_observations)
        again,failed=control.intervene(second,request(100,intent='repeat_start'))
        self.assertEqual(again,second);self.assertFalse(failed['satisfied'])

    def test_search_limit_is_not_exhaustive_failure_or_partial_mutation(self):
        _,_,_,owned=positive();snapshot=deepcopy(owned)
        with patch.object(movement,'_placed_candidate',side_effect=ValueError('Authored unsupported placement')) as placed:
            unchanged,report=control.intervene(owned,request(50),max_candidates=1)
        self.assertEqual(placed.call_count,1)
        self.assertEqual(report['status'],'SEARCH_LIMIT')
        self.assertFalse(report['search_exhausted']);self.assertFalse(report['satisfied'])
        self.assertEqual(unchanged,snapshot);self.assertEqual(owned,snapshot)
        changed,report=control.intervene(owned,request(50),max_candidates=1)
        self.assertTrue(report['satisfied']);self.assertFalse(report['search_exhausted'])
        self.assertEqual(report['final_output']['features']['melody']['changed_count'],1)

    def test_preference_runs_once_per_complete_admitted_candidate(self):
        _,_,_,owned=positive()
        with patch.object(control.halfsteps,'evaluate',wraps=control.halfsteps.evaluate) as evaluate:
            _,report=control.intervene(owned,request(50,100))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(evaluate.call_count,report['admitted_candidates'])
        self.assertTrue(all(d['halfstep_preference']['discount_count']<=1 for d in report['candidates']))
        with patch.object(control.halfsteps,'evaluate',wraps=control.halfsteps.evaluate) as evaluate:
            deferred,report=control.candidates(owned,request(50,100),defer_preference=True)
        self.assertEqual(evaluate.call_count,0)
        self.assertTrue(deferred)
        self.assertTrue(all(d['halfstep_preference'] is None for _,d in deferred))

    def test_bad_controls_and_missing_reference_refuse_without_mutation(self):
        _,_,_,owned=positive(references=None);snapshot=deepcopy(owned)
        for bad in (dict(request(),melody=True),dict(request(),register=101),
                    dict(request(),seed=False),dict(request(),intent='invent_notes')):
            with self.assertRaises(ValueError):control.intervene(owned,bad)
        unchanged,report=control.intervene(owned,request(100))
        self.assertEqual(unchanged,owned);self.assertFalse(report['satisfied'])
        self.assertEqual(owned,snapshot)

    def test_joint_movement_can_change_half_the_actual_octaves_and_cannot_hide_cancellation(self):
        docs=documents();docs=set_pitches(docs,[67,70,65],measure=0)
        docs=set_pitches(docs,[60,72,62]);track=docs['track-0.json'];old=track['tuning']
        for measure in track['measures']:
            for beat in measure['voices'][0]['beats']:
                for note in beat['notes']:
                    if 'fret' in note:
                        pitch=old[note['string']]+note['fret'];note.update(string=0,fret=pitch-60)
        track.update(tuning=[60]*6,frets=12)
        from source_fact_tier1 import extract_documents
        from connected_tier2 import analyze,strip_lower
        lower=extract_documents(docs);plain=strip_lower(analyze(lower))
        owned=movement.lift(plain,TARGET[:2],register_controls=True)
        changed,report=control.intervene(owned,request(100,50,intent='repeat_start'))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(selected_pitches(output(changed))[:2],[72,72])
        self.assertEqual(report['final_output']['features']['register']['changed_ids'],[TARGET[0]])
        self.assertEqual(report['changed_attack_refs'],[TARGET[0]])
        self.assertEqual(report['final_output']['features']['melody']['changed_count'],1)
        unchanged,report=control.intervene(owned,request(100,100,intent='repeat_start'))
        self.assertEqual(unchanged,owned);self.assertFalse(report['satisfied'])
        self.assertEqual(report['status'],'TARGET_UNSATISFIED')

    def test_final_register_zero_rejects_a_movement_induced_octave_crossing(self):
        _,_,_,owned=build_v2()  # [60,61,62] -> [60,67,58]
        unchanged,report=control.intervene(owned,request(100,0))
        self.assertEqual(unchanged,owned);self.assertFalse(report['satisfied'])
        changed,report=control.intervene(owned,request(100,50))
        self.assertTrue(report['satisfied'],report)
        self.assertEqual(selected_pitches(output(changed)),[72,79,70])
        self.assertEqual(report['final_output']['features']['register']['changed_count'],2)


if __name__=='__main__':unittest.main()
