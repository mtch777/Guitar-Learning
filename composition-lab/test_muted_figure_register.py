"""Authored PM/register contract tests; not source or acoustic acceptance."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from connected_tier2 import analyze, strip_lower, realize, reconstruct, validate
from source_fact_tier1 import extract_documents, project_documents
from source_observation_evidence import digest, require
import backing_pitch_ownership as backing
import figure_register_ownership as groups
import figure_register_observations as observations
import observed_figure_register as register

SONG = 986544
REFS = [f'event:{SONG}:0:1:0:{i}:0' for i in range(4)]


def documents():
    def beat(string, fret, duration=(1, 4), **flags):
        return dict(duration=list(duration), notes=[dict(string=string, fret=fret, **flags)])
    def bar(beats):
        return dict(signature=[4, 4], voices=[dict(beats=beats)])
    first = [beat(s, f, (1, 8)) for s, f in [(3, 11), (3, 9), (4, 9), (3, 11)]]
    for row in first:
        row['palmMute'] = True
    first[0].update(beamStart=True, velocity='f'); first[-1]['beamStop'] = True
    first.append(dict(duration=[1, 2], notes=[dict(rest=True)]))
    guitar = [bar(first), bar([beat(3, 11), beat(3, 9), beat(4, 9), beat(1, 7)]),
              bar([beat(1, 12), beat(1, 12, slide='shift'), beat(1, 14), beat(1, 14, slide='shift')]),
              bar([beat(1, 17), dict(duration=[3, 4], notes=[dict(rest=True)])])]
    bass = [bar([beat(0, 0, (1, 1))]) for _ in guitar]
    return {'metadata.json': dict(songId=SONG, revisionId=1, artist='Authored fixture', title='Muted register',
                    tracks=[dict(name='Guitar', instrumentId=30), dict(name='Bass', instrumentId=34)]),
            'track-0.json': dict(songId=SONG, revisionId=1, partId=0, instrumentId=30,
                                tuning=[64, 59, 55, 50, 45, 40], frets=24, measures=guitar),
            'track-1.json': dict(songId=SONG, revisionId=1, partId=1, instrumentId=34,
                                tuning=[35, 30, 25, 20], frets=24, measures=bass)}


def fixture(docs=None, *, evidence=True, extra_owner=False):
    docs = documents() if docs is None else deepcopy(docs)
    bindings = [dict(occurrence_ref=r, backing_ref=f'event:{SONG}:1:1:0:0:0') for r in REFS]
    if extra_owner:
        docs['metadata.json']['tracks'].append(dict(name='Independent', instrumentId=0))
        docs['track-2.json'] = dict(songId=SONG, revisionId=1, partId=2, instrumentId=0,
            tuning=[60], frets=24, measures=[dict(signature=[4, 4], voices=[dict(beats=[
                dict(duration=[1, 1], notes=[dict(rest=True)] if i < 3 else [dict(string=0, fret=0)])])]) for i in range(4)])
        bindings.append(dict(occurrence_ref=f'event:{SONG}:2:4:0:0:0', backing_ref=f'event:{SONG}:1:4:0:0:0'))
    before = extract_documents(docs)
    full = analyze(before, rhythm_groups=True, rhythm_group_profile='written_time',
        backing_bindings=bindings, muted_figure_register_refs=REFS,
        figure_register_evidence=evidence,
        figure_register_observation_profile=observations.WRITTEN_PROFILE if evidence else None)
    return docs, before, strip_lower(full), full


def controls(level=100, seed=1, physical=100):
    return dict(context_policy=register.MUTED, register=level, seed=seed, physical=physical)


def shifted(before, delta):
    expected = deepcopy(before)
    wanted = {f'track-0.json#/measures/0/voices/0/beats/{i}/notes/0/fret' for i in range(4)}
    for row in expected['facts']:
        if row['id'] in wanted:
            row['value'] += delta
    return expected


class MutedFigureRegisterTests(unittest.TestCase):
    def refuse(self, upper, request, error=None):
        original = deepcopy(upper)
        with self.assertRaisesRegex(ValueError, error or '.'):
            register.intervene(upper, request)
        self.assertEqual(upper, original)

    def test_forward_same_owners_and_exact_source_no_scalar_note_backup(self):
        docs, before, upper, full = fixture()
        self.assertEqual(validate(full), before)
        self.assertEqual(project_documents(realize(upper)), docs)
        wrapper = upper['musical_relationships']
        self.assertEqual(wrapper['schema'], groups.MUTED_SCHEMA)
        self.assertEqual(wrapper['core']['schema'], backing.EXECUTION_SCHEMA)
        self.assertIn('execution_constraints', wrapper['core'])
        self.assertIn('written_tie_constraints', wrapper['core'])
        self.assertEqual(wrapper['groups'][0]['occurrence_refs'], REFS)
        self.assertEqual([r['value'] for r in wrapper['execution_contract']['palm_mute_declarations']], [True]*4)
        for link in wrapper['core']['relationships']:
            self.assertNotIn('interval_semitones', link)
            self.assertIn('figure_register_ref', link)
        table = upper['owned_parameters'][observations.SLOT]
        self.assertEqual(table['schema'], observations.MUTED_SCHEMA)
        self.assertEqual(table['qualification'], observations.WRITTEN_PROFILE)
        for key in ('facts', 'events', 'documents', 'donor_refs', 'original'):
            self.assertNotIn('"' + key + '"', json.dumps(table))

    def test_observation_and_editability_are_distinct_without_own_effect_bypass(self):
        docs, before, upper, _ = fixture()
        table = upper['owned_parameters'][observations.SLOT]
        self.assertEqual(table['counts'], [dict(pitch_class=pc, octave=octave, count=n)
            for (pc, octave), n in sorted(Counter((p % 12, p // 12-1) for p in [61,59,54,66,71,73,76]).items())])
        # Plain incoming slide endpoint73 counts once; outgoing own-slide73 does not.
        self.assertEqual(next(r['count'] for r in table['counts'] if (r['pitch_class'],r['octave'])==(1,5)), 1)
        original_plain = deepcopy(docs)
        for beat in original_plain['track-0.json']['measures'][0]['voices'][0]['beats'][:4]:
            del beat['palmMute']
        old_before = extract_documents(original_plain)
        bindings = groups.bindings(upper['musical_relationships'])
        old = analyze(old_before, backing_bindings=bindings, figure_register_refs=REFS, figure_register_evidence=True)
        old_table = old['owned_parameters'][observations.SLOT]
        self.assertEqual(old_table['schema'], observations.SCHEMA)
        self.assertNotIn((1,5), {(r['pitch_class'],r['octave']) for r in old_table['counts']})
        # Same target cannot receive a new expression or execution dependency.
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['slide'] = 'shift'
        with self.assertRaises(ValueError):
            fixture(docs)

    def test_original_own_harmonic_bend_dead_and_unknown_fields_do_not_add_votes(self):
        docs = documents()
        docs['track-0.json']['measures'][-1]['voices'][0]['beats'] = [
            dict(duration=[1,4],notes=[dict(string=1,fret=17)]),
            dict(duration=[1,4],notes=[dict(string=1,fret=14,harmonic='natural')]),
            dict(duration=[1,4],notes=[dict(string=1,fret=14,bend=dict(tone=100,points=[dict(position=0,tone=0),dict(position=60,tone=100)]))]),
            dict(duration=[1,4],notes=[dict(string=1,fret=14,dead=True)])]
        _, _, upper, _ = fixture(docs)
        self.assertEqual(next(r['count'] for r in upper['owned_parameters'][observations.SLOT]['counts']
                              if (r['pitch_class'],r['octave'])==(1,5)), 1)

    def test_zero_fifty_hundred_literal_facts_and_only_group_octave_changes(self):
        _, before, upper, _ = fixture(); snapshot = deepcopy(upper)
        releases = set()
        for level in (0,50,100):
            for seed in (0,1,4):
                out, decision = register.intervene(upper, controls(level,seed))
                rng = random.Random('figure-register:'+str(seed)); released = rng.random() < level/100
                delta = rng.choice([0,12]) if released else 0
                self.assertEqual(realize(out), shifted(before,delta))
                self.assertEqual(decision['released'],released)
                expected = deepcopy(upper); expected['musical_relationships']['groups'][0]['octave'] += delta//12
                self.assertEqual(out,expected)
                self.assertEqual(reconstruct(upper, controls(level,seed)), shifted(before,delta))
                if level==50:releases.add(released)
                if level:
                    self.assertEqual([r['shift_semitones'] for r in decision['options']],[0,12])
                    self.assertNotIn('donor_refs',decision['options'][0])
        self.assertEqual(releases,{False,True});self.assertEqual(upper,snapshot)

    def test_saved_second_register_uses_current_pitch_fixed_absolute_bins(self):
        _, before, upper, _ = fixture()
        high, decision = register.intervene(upper,controls())
        self.assertTrue(decision['changed']); self.assertEqual(realize(high),shifted(before,12))
        saved = json.loads(json.dumps(high)); evidence = deepcopy(saved['owned_parameters'][observations.SLOT])
        self.assertEqual(register.intervene(saved,controls(0))[0],saved)
        with patch.object(register,'prepare_original',side_effect=AssertionError('Relearned edited source')):
            for level in (50,100):
                for seed in (0,1,4):
                    out,d = register.intervene(saved,controls(level,seed))
                    self.assertEqual([r['shift_semitones'] for r in d['options']],[-12,0])
                    rng=random.Random('figure-register:'+str(seed));released=rng.random()<level/100
                    delta=rng.choice([-12,0])if released else 0
                    self.assertEqual(realize(out),shifted(before,12+delta))
                    self.assertEqual(out['owned_parameters'][observations.SLOT],evidence)
                    self.assertEqual(register.intervene(out,controls(0))[0],out)
        self.assertEqual(saved,high)

    def test_absent_false_true_stay_distinct_and_nonboolean_pm_refuses(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        del beats[0]['palmMute'];beats[1]['palmMute']=False
        _,before,upper,_=fixture(docs)
        rows=upper['musical_relationships']['execution_contract']['palm_mute_declarations']
        self.assertFalse(rows[0]['present']);self.assertNotIn('value',rows[0])
        self.assertIs(rows[1]['value'],False);self.assertIs(rows[2]['value'],True)
        self.assertEqual(reconstruct(upper,controls(0)),before)
        for value in (None,0,1,'true',[]):
            invalid=documents();invalid['track-0.json']['measures'][0]['voices'][0]['beats'][0]['palmMute']=value
            with self.assertRaises(ValueError):fixture(invalid)

    def test_profile_and_wrapper_require_explicit_separate_optins(self):
        docs,before,upper,_=fixture();bindings=groups.bindings(upper['musical_relationships'])
        for kwargs in (dict(figure_register_refs=REFS),dict(expressive_figure_seed_refs=REFS)):
            with self.assertRaises(ValueError):
                analyze(before,backing_bindings=bindings,figure_register_evidence=True,**kwargs)
        with self.assertRaisesRegex(ValueError,'PROFILE'):
            analyze(before,backing_bindings=bindings,muted_figure_register_refs=REFS,figure_register_evidence=True)
        with self.assertRaises(ValueError):
            analyze(before,backing_bindings=bindings,figure_register_refs=REFS,
                    figure_register_evidence=True,figure_register_observation_profile=observations.WRITTEN_PROFILE)
        _,before,without,_=fixture(evidence=False)
        self.assertEqual(reconstruct(without,controls(0)),before)
        self.refuse(without,controls(),'ORIGINAL_MUTED_REGISTER_OBSERVATIONS_REQUIRED')

    def test_mutable_axis_is_only_common_octave_not_shape_strings_flags_or_backing(self):
        _,_,upper,_=fixture();table=upper['owned_parameters'][observations.SLOT]
        projection=observations.protected_state(upper,table['scope'])
        high,_=register.intervene(upper,controls())
        self.assertEqual(observations.protected_state(high,table['scope']),projection)
        for change in ('class','offset','string','backing','contract'):
            bad=deepcopy(high);w=bad['musical_relationships']
            if change=='class':w['groups'][0]['interval_class']='3'
            elif change=='offset':w['groups'][0]['offsets_semitones'][1]='-1'
            elif change=='string':
                row=next(r for r in bad['owned_parameters']['source_choices']if r['fact_ref']=='track-0.json#/measures/0/voices/0/beats/0/notes/0/string');row['parameter']['normalized']='2'
            elif change=='backing':w['core']['relationships'][0]['backing_ref']=f'event:{SONG}:1:2:0:0:0'
            else:w['execution_contract']['palm_mute_declarations'][0]['value']=False
            self.refuse(bad,controls())

    def test_unrelated_authority_survives_and_future_dependency_still_works(self):
        _,_,upper,_=fixture(extra_owner=True);high,_=register.intervene(upper,controls())
        self.assertEqual(high['musical_relationships']['core'],upper['musical_relationships']['core'])
        later=deepcopy(high);body=backing._body(later['musical_relationships']['core']['core'])
        anchor=f'event:{SONG}:1:4:0:0:0';owner,_=backing._index(body)[anchor]
        owner['bass_register_anchor']=str(F(owner['bass_register_anchor'])+1)
        before=project_documents(realize(high));after=project_documents(realize(later))
        self.assertEqual(after['track-2.json']['measures'][3]['voices'][0]['beats'][0]['notes'][0]['fret'],
                         before['track-2.json']['measures'][3]['voices'][0]['beats'][0]['notes'][0]['fret']+1)
        with patch.object(register,'choices',side_effect=AssertionError('Queried choices outside protected scope')):
            self.refuse(later,controls(),'PROTECTED_STATE_CHANGED')

    def test_typed_counts_integrity_no_recursive_source_validation(self):
        _,_,upper,_=fixture();model=upper['owned_parameters'][observations.SLOT]
        with patch('connected_tier2.realize',side_effect=AssertionError('Recursive inverse')):
            observations.validate(model,upper['source_origin'])
        for key,value in [('count',True),('count',0),('pitch_class',12)]:
            bad=deepcopy(upper);table=bad['owned_parameters'][observations.SLOT];table['counts'][0][key]=value
            table['evidence_sha256']=digest(observations.evidence(table))
            with self.assertRaises(ValueError):realize(bad)
        bad=deepcopy(upper);bad['owned_parameters'][observations.SLOT]['counts'][0]['count']+=1
        self.refuse(bad,controls(0),'CHECKSUM')

    def test_strict_controls_physical_lock_and_other_policies_refuse_atomically(self):
        _,_,upper,_=fixture()
        for request in (controls(physical=0),dict(controls(),placement_policy='minimum_string_changes'),
                        controls(True),controls(float('nan')),controls(seed=True)):
            self.refuse(upper,request)
        high,_=register.intervene(upper,controls())
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_CHAINED_EVIDENCE'):
            require(high,dict(context_policy='source_local_note_accent',accents=100))
        missing=deepcopy(high);del missing['owned_parameters'][observations.SLOT]
        self.refuse(missing,controls(),'ORIGINAL_MUTED_REGISTER_OBSERVATIONS_REQUIRED')

    def test_actual_bundled_source_denied_zero_change_and_saved_second_register(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        _,before,upper,_=fixture();high,_=register.intervene(upper,controls())
        code,_=bundle(Path(__file__).resolve().parent)
        with tempfile.TemporaryDirectory()as directory:
            for name,model,request,expected in (
                ('zero',upper,controls(0),before),
                ('changed',upper,controls(),shifted(before,12)),
                ('saved-zero',json.loads(json.dumps(high)),controls(0),shifted(before,12)),
                ('saved-return',json.loads(json.dumps(high)),controls(100,0),before)):
                target=Path(directory)/name
                receipt=execute(code,model,request,expected,target,timeout=120,purpose='guitar_figure_register')
                self.assertEqual(receipt['status'],'PASS',receipt)
                self.assertEqual(json.loads((target/'worker/output.json').read_text()),expected)


if __name__=='__main__':unittest.main()
