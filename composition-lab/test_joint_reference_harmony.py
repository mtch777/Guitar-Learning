"""Outside an explicit collection can still be inside a supported chord."""
from copy import deepcopy
import hashlib
import json
import unittest
from test_musical_tier2 import facts
from test_temporal_tier2 import timed_facts
from musical_tier2 import analyze,harmonic_span_evidence,joint_reference_harmonic_context,_chord_membership,strip_lower,reconstruct,same


def reference(upper,tonic,quality,scope='song-pooled'):
    return next(c['id'] for s in upper['tonal_evidence']['scopes'] if s['id']==scope for c in s['candidates'] if c['family']=='KrumhanslSchmuckler' and c['tonic_pc']==tonic and c['quality']==quality)


class JointReferenceHarmonyTests(unittest.TestCase):
    def test_outside_natural_minor_but_inside_supported_major_chord(self):
        lower=facts([(0,70,0,1)]+[(1,p,0,1) for p in (42,46,49)]);upper=analyze(lower);evidence=harmonic_span_evidence(upper,'0','1')
        query=[dict(occurrence_ref='note-0',at_q='1/2')];candidate=reference(upper,11,'minor')
        result=joint_reference_harmonic_context(upper,evidence,query,candidate)
        self.assertEqual(result['queries'][0]['reference_membership'],'outside_reference_collection')
        self.assertIsNone(result['queries'][0]['reference_coordinates']['reference_collection_degree'])
        labels=result['queries'][0]['marginal_harmonic_context']['labels']
        self.assertTrue(any(c['root_pc']==6 and c['kind']=='major' and c['note_membership']=='chord_member' for c in labels))
        self.assertTrue(any(v[0]['chord_membership']=='chord_member' for v in result['combined_membership_vectors']))
        self.assertIsNone(result['harmonic_function']);self.assertIsNone(result['chord_mode']);self.assertIsNone(result['established_key'])
        self.assertTrue(same(result,joint_reference_harmonic_context(strip_lower(upper),evidence,query,candidate)))
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_explicit_minor_theory_is_distinct_from_winning_source_hypotheses(self):
        # A# is NOT a member of an explicitly supplied F#minor hypothesis.
        self.assertEqual(_chord_membership('70',dict(root_pc=6,formula=[0,3,7])),'nonmember')
        upper=analyze(facts([(0,70,0,1)]+[(1,p,0,1) for p in (42,45,49)]));evidence=harmonic_span_evidence(upper,'0','1')
        result=joint_reference_harmonic_context(upper,evidence,[dict(occurrence_ref='note-0',at_q='0')],reference(upper,11,'minor'))
        for label in result['queries'][0]['marginal_harmonic_context']['labels']:
            expected='chord_member' if (70-label['root_pc'])%12 in label['formula'] else 'nonmember'
            self.assertEqual(label['note_membership'],expected)
        # Do not force F#minor to win after the queried A# changes the evidence.
        self.assertEqual(result['joint_membership']['feasible_membership_vectors'][0]['memberships'][0],result['combined_membership_vectors'][0][0]['chord_membership'])

    def test_marginal_label_inventory_never_becomes_incompatible_joint_vectors(self):
        upper=analyze(facts([(0,p,0,1) for p in (60,64,67,69)]));evidence=harmonic_span_evidence(upper,'0','1');before=deepcopy(evidence)
        queries=[dict(occurrence_ref=i,at_q='0') for i in ('note-2','note-3')]
        result=joint_reference_harmonic_context(upper,evidence,queries,reference(upper,0,'major'))
        vectors={tuple(r['chord_membership'] for r in v) for v in result['combined_membership_vectors']}
        self.assertEqual(vectors,{('chord_member','nonmember'),('nonmember','chord_member')})
        for row in result['queries']:
            self.assertEqual(len(row['marginal_harmonic_context']['labels']),len(evidence['all_optimal_path_cell_consensus'][0]['candidate_labels']))
        self.assertEqual(evidence,before)
        digest=hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        self.assertEqual(result['harmonic_evidence_ref']['sha256'],digest)
        from check_harmonic_span_source import check
        lower=upper['input'];owned={r['id']:r for r in lower['events']};raw=[tuple(r[k] for k in ('part_id','bar','pitch','onset_q','duration_q')) for r in lower['events']]
        self.assertEqual(check(raw,evidence,result['joint_membership'],owned)['status'],'PASS')
        missing=deepcopy(result['joint_membership']);missing['feasible_membership_vectors'].pop()
        self.assertEqual(check(raw,evidence,missing,owned)['status'],'FAIL')

    def test_temporal_and_part_candidate_scope_are_not_silently_extended(self):
        upper=analyze(timed_facts());evidence=harmonic_span_evidence(upper,'0','8')
        c=upper['temporal_tonal_evidence']['scopes'][0]['measures'][0]['candidates'][0]
        result=joint_reference_harmonic_context(upper,evidence,[dict(occurrence_ref='note-0',at_q='1/2')],c['id'])
        self.assertEqual(result['reference']['time_span_q'],['0','4'])
        with self.assertRaises(ValueError):joint_reference_harmonic_context(upper,evidence,[dict(occurrence_ref='note-3',at_q='9/2')],c['id'])
        upper=analyze(facts([(0,60,0,1),(1,64,0,1)]));evidence=harmonic_span_evidence(upper,'0','1')
        with self.assertRaises(ValueError):joint_reference_harmonic_context(upper,evidence,[dict(occurrence_ref='note-1',at_q='0')],reference(upper,0,'major','part:0'))

    def test_unknown_domain_resource_and_stale_outcomes_remain_explicit(self):
        upper=analyze(facts([(0,None,0,1),(0,'121/2',1,1)]));evidence=harmonic_span_evidence(upper,'0','2')
        queries=[dict(occurrence_ref='note-0',at_q='0'),dict(occurrence_ref='note-1',at_q='1')]
        result=joint_reference_harmonic_context(upper,evidence,queries,reference(upper,0,'major'))
        self.assertEqual([q['reference_membership'] for q in result['queries']],['unknown','unknown'])
        resource=harmonic_span_evidence(upper,'0','2',max_edges=1)
        # Unknown intervals do not split the scoring grid, so use known notes
        # to exercise an actual resource refusal rather than manufacture one.
        known=analyze(facts([(0,60,0,1),(0,62,1,1)]));resource=harmonic_span_evidence(known,'0','2',max_edges=1)
        result=joint_reference_harmonic_context(known,resource,[dict(occurrence_ref='note-0',at_q='0')],reference(known,0,'major'))
        self.assertEqual(result['status'],'HARMONIC_ANALYSIS_NOT_RUN');self.assertIsNone(result['joint_membership'])
        stale=deepcopy(evidence);stale['optimal_score']=999
        with self.assertRaises(ValueError):joint_reference_harmonic_context(upper,stale,queries,reference(upper,0,'major'))


if __name__=='__main__':unittest.main()
