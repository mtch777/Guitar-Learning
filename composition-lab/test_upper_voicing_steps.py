"""Nonconstant current contours, live reference movements, and exact history."""
from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path

import backing_pitch_ownership as backing
import upper_voicing_motion as motion
from connected_tier2 import analyze, strip_lower, realize, validate
from source_fact_tier1 import extract_documents, project_documents
from test_upper_voicing_motion import fixture, SOURCE, TARGET, PEER, request, stored_body


def stepped_fixture(*, constant_reference=False):
    docs, _, _, _, _ = fixture(coupled=False)
    for part in (0, 1):
        for beat, fret in zip(docs[f'track-{part}.json']['measures'][1]['voices'][0]['beats'], (2, 1, 4)):
            beat['notes'][0]['fret'] = fret
    if constant_reference:
        for beat in docs['track-0.json']['measures'][0]['voices'][0]['beats'][:3]:
            beat['notes'][0]['fret'] = 2
    lower = extract_documents(docs)
    upper = strip_lower(analyze(lower))
    upper['musical_relationships'] = backing.lift(upper['musical_relationships'],
        [dict(occurrence_ref=p, backing_ref=t) for p,t in zip(PEER,TARGET)],
        tier1=lower, member_scope=True, preserve_execution=True)
    before = deepcopy(upper)
    upper['musical_relationships'] = motion.lift(upper['musical_relationships'], lower,
        [dict(source_ref=s, target_ref=t) for s,t in zip(SOURCE,TARGET)],
        source_origin=upper['source_origin'], encoding='signed_steps')
    return docs, lower, upper, before


class UpperVoicingStepsTests(unittest.TestCase):
    def test_same_difference_prefix_sum_preserves_arbitrary_contour(self):
        solved = motion.step_relation(source_intervals=['7','8','10'], target_intervals=['7','6','9'])
        self.assertEqual(solved['steps'], ['-1','3'])
        self.assertEqual(motion.step_relation(source_intervals=['7','8','10'],
            base_interval=solved['base_interval'], steps=solved['steps']), solved)
        # Constant reference is legitimate: no binary-identifiability restriction.
        self.assertEqual(motion.step_relation(source_intervals=['7','7','7'],
            base_interval='9', steps=['reference_step']*2)['target_intervals'], ['9']*3)

    def test_zero_removes_duplicate_owners_and_exactly_recovers_nonconstant_source(self):
        _, lower, upper, before = stepped_fixture()
        model = upper['musical_relationships']
        self.assertEqual(model['schema'], motion.STEP_SCHEMA)
        self.assertEqual(model['parameters'], dict(base_interval='7', steps=['-1','3']))
        for ref in TARGET:
            self.assertNotIn('voicing_interval',backing._index(stored_body(upper))[ref][1])
        self.assertEqual(model['core']['relationships'],before['musical_relationships']['relationships'])
        self.assertEqual(validate(upper), lower)
        self.assertEqual(motion.intervene(upper, request(0))[0], upper)

    def test_follow_changes_shape_not_just_octave_and_keeps_complete_score(self):
        docs, _, upper, _ = stepped_fixture()
        snapshot = deepcopy(upper)
        final, decision = motion.intervene(upper, request())
        expected = deepcopy(docs)
        for part in (0,1):
            for beat,fret in zip(expected[f'track-{part}.json']['measures'][1]['voices'][0]['beats'],(2,3,5)):
                beat['notes'][0]['fret']=fret
        self.assertEqual(project_documents(realize(final)),expected)
        self.assertTrue(decision['changed'])
        self.assertEqual(final['musical_relationships']['parameters']['steps'],['reference_step']*2)
        self.assertEqual(final['musical_relationships']['observations'],upper['musical_relationships']['observations'])
        self.assertEqual(final['musical_relationships']['core'],upper['musical_relationships']['core'])
        self.assertEqual(upper,snapshot)

    def test_saved_live_dependency_survives_and_original_observations_do_not_change(self):
        _, _, upper, _ = stepped_fixture()
        followed,_=motion.intervene(upper,request())
        saved=json.loads(json.dumps(followed));before=project_documents(realize(saved))
        evidence=deepcopy(saved['musical_relationships']['observations'])
        backing._index(stored_body(saved))[SOURCE[1]][1]['voicing_interval']='9'
        # Both adjacent signed steps update; the last target stays unchanged.
        before['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret']+=1
        for part in(0,1):before[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][1]['notes'][0]['fret']+=1
        self.assertEqual(project_documents(realize(saved)),before)
        self.assertEqual(saved['musical_relationships']['observations'],evidence)

    def test_mixed_owned_and_reference_steps_remain_distinct_after_save(self):
        _, _, upper, _ = stepped_fixture()
        upper['musical_relationships']['parameters']['steps']=['reference_step','-2']
        saved=json.loads(json.dumps(upper));before=project_documents(realize(saved))
        backing._index(stored_body(saved))[SOURCE[1]][1]['voicing_interval']='9'
        before['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret']+=1
        for part in(0,1):
            for i in(1,2):before[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][i]['notes'][0]['fret']+=1
        self.assertEqual(project_documents(realize(saved)),before)

    def test_repeat_is_an_intention_not_secret_original_restore(self):
        docs, lower, upper, _=stepped_fixture()
        followed,_=motion.intervene(upper,request())
        current_zero,_=motion.intervene(json.loads(json.dumps(followed)),request(0))
        self.assertEqual(current_zero,followed)
        repeat,_=motion.intervene(followed,request(intent='repeat_upper_interval'))
        self.assertNotEqual(realize(repeat),lower)
        for part in(0,1):
            for beat in docs[f'track-{part}.json']['measures'][1]['voices'][0]['beats'][:3]:beat['notes'][0]['fret']=2
        self.assertEqual(project_documents(realize(repeat)),docs)
        self.assertEqual(repeat['musical_relationships']['parameters']['steps'],['0','0'])

    def test_half_can_lock_or_release_and_full_can_coincide(self):
        _, lower, upper, _=stepped_fixture()
        states=set()
        for seed in range(8):
            final,decision=motion.intervene(upper,request(50,seed=seed));states.add(decision['released'])
            self.assertEqual(realize(final)!=lower,decision['released'])
        self.assertEqual(states,{True,False})
        once,_=motion.intervene(upper,request());twice,d=motion.intervene(once,request())
        self.assertEqual(twice,once);self.assertFalse(d['changed'])

    def test_invalid_or_physically_unrealizable_steps_fail_without_mutation(self):
        _, _, upper, _=stepped_fixture()
        for steps in (['0'],['reference_step','oops'],[True,'0'],['1/2','0'],['-8','0'],['100','0']):
            bad=deepcopy(upper);bad['musical_relationships']['parameters']['steps']=steps
            snapshot=deepcopy(bad)
            with self.assertRaises(ValueError):realize(bad)
            self.assertEqual(bad,snapshot)

    def test_reference_clock_mismatch_and_duplicate_owner_refuse(self):
        _, _, upper, _=stepped_fixture()
        bad=deepcopy(upper);backing._index(stored_body(bad))[SOURCE[1]][0]['onset_q']='3/2'
        with self.assertRaisesRegex(ValueError,'clock'):realize(bad)
        bad=deepcopy(upper);backing._index(stored_body(bad))[TARGET[1]][1]['voicing_interval']='6'
        with self.assertRaisesRegex(ValueError,'Duplicate'):realize(bad)

    def test_real_isolated_zero_follow_and_corruption(self):
        from qa_isolation_harness import execute
        from run_connected_tier2_qa import bundle
        _, lower, upper, _=stepped_fixture();code,_=bundle(Path(__file__).parent)
        followed,_=motion.intervene(upper,request());expected=realize(followed)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,controls,wanted in(('zero',request(0),lower),('follow',request(),expected)):
                self.assertEqual(execute(code,upper,controls,wanted,root/name,purpose='upper_voicing_motion')['status'],'PASS')
            corrupt=deepcopy(upper);corrupt['musical_relationships']['parameters']['steps']=['reference_step']
            self.assertNotEqual(execute(code,corrupt,request(0),lower,root/'corrupt',purpose='upper_voicing_motion')['status'],'PASS')

if __name__=='__main__':unittest.main()
