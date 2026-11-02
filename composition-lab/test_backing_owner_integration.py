"""Independent integration checks for the one persisted backing relation.

All scores here are authored fixtures. Worker expectations stay in the parent;
tests do not claim artist fit or broad combined-control support.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import backing_motion_intervention as motion
import backing_pitch_ownership as owner
from canonical_backing_bindings import canonical_bindings
from connected_tier2 import analyze, strip_lower, realize, validate, reconstruct
from source_fact_tier1 import extract_documents, project_documents
from test_backing_pitch_ownership import setup
from test_backing_motion_intervention import controls, SOURCE, TARGET


def package(owned_time):
    lower, plain, _ = setup(owned_time)
    evidence = motion.prepare(plain, controls())
    bindings = canonical_bindings(plain['musical_relationships'], evidence['correspondences'])
    upper = strip_lower(analyze(lower, backing_bindings=bindings,
        rhythm_groups=owned_time, rhythm_group_profile='written_time' if owned_time else 'plain_repeat'))
    return lower, upper


def changed_truth(before, complete=True):
    docs = project_documents(before)
    notes = docs['track-0.json']['measures'][1]['voices'][0]['beats']
    notes[1]['notes'][0] = dict(string=3, fret=3)
    if complete: notes[2]['notes'][0] = dict(string=3, fret=7)
    return extract_documents(docs)


def string_owner(upper, ref):
    _, part, bar, voice, beat, note = owner.address(ref)
    pointer = f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}/string'
    return next(row for row in upper['owned_parameters']['source_choices'] if row['fact_ref']==pointer)


class BackingOwnerIntegrationTests(unittest.TestCase):
    def assert_no_old_pitch_owner(self, upper):
        self.assertNotIn('input', upper); self.assertNotIn('derived_views', upper)
        wrapper = upper['musical_relationships']; body = owner._body(wrapper['core'])
        self.assertEqual(wrapper['schema'], owner.SCHEMA)
        self.assertEqual(set(body), owner.BASE_FIELDS)
        index = owner._index(body)
        self.assertEqual({r['occurrence_ref'] for r in wrapper['relationships']}, set(SOURCE+TARGET))
        for ref in SOURCE+TARGET:
            group, member = index[ref]
            self.assertNotIn('bass_register_anchor', group)
            self.assertNotIn('interpretation', group)
            self.assertNotIn('pitch', member)
            self.assertNotIn('fret', member)
            self.assertEqual(member['voicing_interval'], '0')
            string_ref = string_owner(upper, ref)['fact_ref']
            self.assertFalse(any(row['fact_ref']==string_ref.removesuffix('/string')+'/fret'
                                 for row in upper['owned_parameters']['source_choices']))
        self.assertTrue(all('value' not in row for row in upper['source_structure']['facts']))

    def test_zero_and_released_edit_are_exact_in_both_time_representations(self):
        for owned_time in (False, True):
            with self.subTest(owned_time=owned_time):
                before, upper = package(owned_time); frozen = deepcopy(upper)
                self.assert_no_old_pitch_owner(upper)
                self.assertEqual(validate(upper), before)
                self.assertEqual(reconstruct(upper, controls(0)), before)
                with patch('melodic_contour_intervention.apply_pitch', side_effect=AssertionError('Absolute pitch writer used')):
                    changed, decision = motion.intervene(upper, controls(100))
                self.assertEqual(decision['chosen']['pitches'], ['35','31','35'])
                self.assertEqual(realize(changed), changed_truth(before))
                self.assert_no_old_pitch_owner(changed)
                self.assertEqual(upper, frozen)
                self.assertEqual(changed['source_origin'], upper['source_origin'])
                for seed, released in ((0,False),(1,True)):
                    half, half_decision = motion.intervene(upper,controls(50,seed=seed))
                    self.assertEqual(half_decision['released'],released)
                    self.assertEqual(realize(half),changed_truth(before) if released else before)
                    self.assertEqual(half['source_origin'],upper['source_origin'])
                old = {r['occurrence_ref']:r for r in upper['musical_relationships']['relationships']}
                new = {r['occurrence_ref']:r for r in changed['musical_relationships']['relationships']}
                for a,b in zip(SOURCE,TARGET):
                    self.assertEqual(new[a], old[a])
                    self.assertEqual(new[b]['interval_semitones'], old[a]['interval_semitones'])

    def test_actual_isolated_zero_and_release_receive_no_source_or_decision(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code, hashes = bundle(Path(__file__).parent)
        self.assertIn('backing_pitch_ownership', hashes)
        self.assertIn('canonical_backing_bindings', hashes)
        with tempfile.TemporaryDirectory() as temp:
            for owned_time in (False, True):
                before, upper = package(owned_time)
                for level, expected in ((0,before),(100,changed_truth(before))):
                    with self.subTest(owned_time=owned_time,level=level):
                        out = Path(temp)/f'time-{owned_time}-level-{level}'
                        result = execute(code,upper,controls(level),expected,out,timeout=40,purpose='observed_backing_motion')
                        self.assertEqual(result['status'],'PASS',result)
                        self.assertFalse(result['parent_expected_staged'])
                        self.assertEqual(set(result['frozen_files']),{'input.json','relationships.py','worker.py'})
                        staged = json.loads((out/'worker/input.json').read_text())
                        self.assertEqual(set(staged),{'upper','controls','purpose'})
                        self.assert_no_old_pitch_owner(staged['upper'])
                        audit = json.loads((out/'worker/audit.json').read_text())
                        self.assertIsNone(audit['error'])
                        self.assertFalse(any(event['denied'] for event in audit['events']))
                        actual = json.loads((out/'worker/output.json').read_text())
                        self.assertEqual(actual,expected)

    def test_missing_duplicate_or_hidden_owner_refuses_without_mutation(self):
        for owned_time in (False, True):
            _, original = package(owned_time)
            def missing(model): model['relationships'].pop()
            def duplicate(model): model['relationships'].append(deepcopy(model['relationships'][0]))
            def old_anchor(model): owner._index(owner._body(model['core']))[TARGET[0]][0]['bass_register_anchor']='35'
            def cached(model): owner._body(model['core'])['input']={'events':[]}
            for corruption in (missing,duplicate,old_anchor,cached):
                with self.subTest(owned_time=owned_time,corruption=corruption.__name__):
                    bad = deepcopy(original); corruption(bad['musical_relationships']); snapshot=deepcopy(bad)
                    with self.assertRaises(ValueError): reconstruct(bad,controls(0))
                    with self.assertRaises(ValueError): reconstruct(bad,controls(100))
                    self.assertEqual(bad,snapshot)

    def test_below_open_string_interval_needs_valid_coupled_contact(self):
        from fractions import Fraction as F
        for owned_time in (False,True):
            with self.subTest(owned_time=owned_time):
                before, upper=package(owned_time)
                row=next(r for r in upper['musical_relationships']['relationships'] if r['occurrence_ref']==TARGET[1])
                row['interval_semitones']=str(F(row['interval_semitones'])-2)
                snapshot=deepcopy(upper)
                with self.assertRaisesRegex(ValueError,'string/fret/tuning'): realize(upper)
                self.assertEqual(upper,snapshot)
                string_owner(upper,TARGET[1])['parameter']=dict(normalized='3',negative_zero=False)
                self.assertEqual(realize(upper),changed_truth(before,complete=False))
                self.assertEqual(validate(upper),changed_truth(before,complete=False))

    def test_declared_fret_limit_and_fractional_contact_refuse(self):
        from fractions import Fraction as F
        for change in ('100','1/2'):
            before, upper=package(False)
            row=next(r for r in upper['musical_relationships']['relationships'] if r['occurrence_ref']==TARGET[0])
            row['interval_semitones']=str(F(row['interval_semitones'])+F(change))
            snapshot=deepcopy(upper)
            with self.subTest(change=change),self.assertRaises(ValueError): realize(upper)
            self.assertEqual(upper,snapshot)

    def test_successive_nonzero_refuses_but_zero_preserves_actual_current_state(self):
        for owned_time in (False,True):
            with self.subTest(owned_time=owned_time):
                before, upper=package(owned_time)
                changed,_=motion.intervene(upper,controls(100));snapshot=deepcopy(changed)
                with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CHAINED_EVIDENCE'):
                    motion.intervene(changed,controls(100))
                self.assertEqual(changed,snapshot)
                self.assertEqual(reconstruct(changed,controls(0)),changed_truth(before))

    def test_nonzero_backing_register_policy_cannot_move_a_locked_dependent_melody(self):
        import voicing_register
        from test_voicing_register import documents as register_documents
        docs=register_documents()
        docs['metadata.json']['tracks'].append(dict(name='Dependent bass',instrumentId=34))
        docs['track-1.json']=dict(songId=77,revisionId=3,partId=1,instrumentId=34,tuning=[28],frets=24,
            measures=[dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=0,fret=7)])])])
                      for _ in range(4)])
        lower=extract_documents(docs); plain=strip_lower(analyze(lower))
        catalog=voicing_register.inventory(lower)
        unit=next(u for u in catalog['units'] if u['part_id']==0 and u['bar']==1)
        request=dict(voicing=0,register=100,target_ref=unit['id'],seed=9427)
        baseline,decision=voicing_register.intervene(plain,request)
        self.assertTrue(decision['changed'])  # This must exercise a real backing-edit option.
        dependent='event:77:1:1:0:0:0'
        upper=strip_lower(analyze(lower,backing_bindings=[dict(occurrence_ref=dependent,backing_ref='event:77:0:1:0:0:0')]))
        snapshot=deepcopy(upper)
        self.assertEqual(reconstruct(upper,dict(request,register=0)),lower)
        with self.assertRaises(ValueError): voicing_register.intervene(upper,request)
        self.assertEqual(upper,snapshot)
        self.assertEqual(realize(upper),lower)


if __name__=='__main__': unittest.main()
