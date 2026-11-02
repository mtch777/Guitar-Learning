"""Independent boundary checks on authored fixtures, not musical-style evidence."""
from copy import deepcopy
from unittest.mock import patch
import unittest

import backing_motion_intervention as motion
from connected_tier2 import realize
from source_fact_tier1 import extract_documents
from test_backing_motion_intervention import documents, model, controls


class BackingMotionAuditTests(unittest.TestCase):
    def assert_refused_without_mutation(self, docs, supplied=None):
        original = deepcopy(docs)
        _, upper = model(docs)
        snapshot = deepcopy(upper)
        with self.assertRaises(ValueError):
            motion.intervene(upper, controls() if supplied is None else supplied)
        self.assertEqual(upper, snapshot)
        self.assertEqual(docs, original)

    def test_complete_source_output_matches_literal_expected_facts(self):
        docs=documents(); before,upper=model(docs)
        changed,decision=motion.intervene(upper,controls())
        expected=deepcopy(docs)
        beats=expected['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[1]['notes'][0]['string']=3
        beats[1]['notes'][0]['fret']=3
        beats[2]['notes'][0]['fret']=7
        self.assertEqual(realize(changed),extract_documents(expected))
        self.assertEqual(realize(upper),before)
        self.assertEqual(decision['physical']['minimum_changes'],1)

    def test_percussion_and_unknown_domains_cannot_supply_melodic_evidence(self):
        for pid in (0,1):
            for program in (1024,999):
                with self.subTest(part=pid,program=program):
                    docs=documents()
                    docs[f'track-{pid}.json']['instrumentId']=program
                    docs['metadata.json']['tracks'][pid]['instrumentId']=program
                    self.assert_refused_without_mutation(docs)

    def test_invalid_original_contacts_cannot_be_silently_repaired(self):
        for bar,string,fret in ((0,0,-1),(1,2,-1),(0,3,25),(1,2,25)):
            with self.subTest(bar=bar,string=string,fret=fret):
                docs=documents()
                docs['track-0.json']['measures'][bar]['voices'][0]['beats'][0]['notes'][0]=dict(string=string,fret=fret)
                self.assert_refused_without_mutation(docs)

    def test_malformed_reference_values_fail_with_typed_value_error(self):
        for values in ((['a'],['b']), ({'x':1},{'y':2})):
            with self.subTest(values=values), self.assertRaises(ValueError):
                motion.validate_controls(dict(controls(),source_refs=list(values)))

    def test_ambiguous_backing_stops_before_pitch_application(self):
        docs=documents()
        beat=docs['track-1.json']['measures'][1]['voices'][0]['beats'][0]
        beat['notes'].append(dict(string=0,fret=2)) # F#4 allows competing equal-size shifts.
        _,upper=model(docs);snapshot=deepcopy(upper)
        with patch.object(motion,'apply',side_effect=AssertionError('Applied ambiguous evidence')):
            with self.assertRaisesRegex(ValueError,'AMBIGUOUS_OR_INSUFFICIENT'):
                motion.intervene(upper,controls())
        self.assertEqual(upper,snapshot)

    def test_repeated_backing_occurrences_do_not_supply_two_distinct_pitches(self):
        docs=documents()
        beat=docs['track-1.json']['measures'][1]['voices'][0]['beats'][0]
        beat['notes']=[dict(string=3,fret=4),dict(string=3,fret=4),dict(string=3,fret=4)]
        self.assert_refused_without_mutation(docs)

    def test_missing_current_backing_does_not_fall_forward_to_next_attack(self):
        docs=documents()
        docs['track-1.json']['measures'][1]['voices'][0]['beats'][0]['notes']=[dict(rest=True)]
        self.assert_refused_without_mutation(docs)

    def test_backing_execution_qualification_is_carried_not_called_sounding_truth(self):
        docs=documents()
        notes=docs['track-1.json']['measures'][1]['voices'][0]['beats'][2]['notes']
        for n in notes:n['slide']='legato'
        _,upper=model(docs);changed,decision=motion.intervene(upper,controls())
        match=decision['correspondences'][2]['match']
        self.assertEqual(match['selected_delta'],0)
        self.assertEqual(match['pitch_domain'],'written_base_not_sounding')
        self.assertEqual(sum('unresolved_sounding_pitch_slide' in q
            for q in match['target_context']['qualifications']),2)
        expected=deepcopy(docs)
        target=expected['track-0.json']['measures'][1]['voices'][0]['beats']
        target[1]['notes'][0]=dict(string=3,fret=3);target[2]['notes'][0]=dict(string=3,fret=7)
        self.assertEqual(realize(changed),extract_documents(expected))

    def test_original_target_answers_cannot_change_the_computed_pitch_vector(self):
        _,first=model();baseline=motion.prepare(first,dict(controls(),allow_note_octave_changes=True))
        docs=documents()
        beats=docs['track-0.json']['measures'][1]['voices'][0]['beats']
        for beat in beats[:3]:beat['notes'][0]['fret']=12
        _,altered=model(docs);result=motion.prepare(altered,dict(controls(),allow_note_octave_changes=True))
        self.assertEqual(result['correspondences'],baseline['correspondences'])
        self.assertEqual([r['pitches']for r in result['options']],[r['pitches']for r in baseline['options']])

    def test_physical_lock_refuses_before_application_and_is_atomic(self):
        _,upper=model();snapshot=deepcopy(upper)
        with patch.object(motion,'apply',side_effect=AssertionError('Applied through physical lock')):
            with self.assertRaisesRegex(ValueError,'PHYSICAL_LOCK_CONFLICT'):
                motion.intervene(upper,controls(100,0))
        self.assertEqual(upper,snapshot)

    def test_changed_or_missing_original_evidence_refuses_before_backing_query(self):
        _,upper=model();changed,_=motion.intervene(upper,controls())
        no_origin=deepcopy(upper);no_origin.pop('source_origin')
        for candidate in (changed,no_origin):
            snapshot=deepcopy(candidate)
            with patch.object(motion,'backing',side_effect=AssertionError('Queried untrusted current notes')):
                with self.assertRaisesRegex(ValueError,'ORIGINAL_OBSERVATIONS|UNSUPPORTED_CHAINED_EVIDENCE'):
                    motion.intervene(candidate,controls())
                with self.assertRaisesRegex(ValueError,'ORIGINAL_OBSERVATIONS|UNSUPPORTED_CHAINED_EVIDENCE'):
                    motion.prepare(candidate,controls())
            self.assertEqual(candidate,snapshot)

    def test_zero_with_physical_permission_stays_literal_without_a_query(self):
        _,upper=model();changed,_=motion.intervene(upper,controls())
        for candidate in (upper,changed):
            with patch.object(motion,'prepare',side_effect=AssertionError('Zero made a choice')):
                after,decision=motion.intervene(candidate,controls(0,100))
            self.assertEqual(after,candidate);self.assertFalse(decision['released'])
        invalid=deepcopy(upper);invalid['source_origin']['facts_sha256']='invalid'
        with self.assertRaises(ValueError):motion.intervene(invalid,controls(0,100))

    def test_full_fact_verifier_rejects_unrelated_changes_and_reordering(self):
        _,upper=model();prepared=motion.prepare(upper,controls());option=prepared['options'][0]
        owned=motion.own_intervals(upper,prepared)
        after=realize(motion.apply(owned,prepared['source'],prepared['target'],option))
        changed=deepcopy(after)
        row=next(r for r in changed['facts']if r['id']=='metadata.json#/title')
        row['value']='unrelated edit'
        with self.assertRaises(ValueError):motion.verify(prepared,changed,option)
        changed=deepcopy(after);changed['facts'].reverse()
        with self.assertRaises(ValueError):motion.verify(prepared,changed,option)

    def test_full_release_allows_relation_coincidence_without_forcing_a_change(self):
        docs=documents();beats=docs['track-0.json']['measures'][1]['voices'][0]['beats']
        beats[1]['notes'][0]=dict(string=3,fret=3);beats[2]['notes'][0]=dict(string=3,fret=7)
        before,upper=model(docs);after,decision=motion.intervene(upper,controls())
        self.assertTrue(decision['released']);self.assertFalse(decision['changed'])
        self.assertEqual(realize(after),before)


if __name__=='__main__':unittest.main()
