"""Frozen musical contrasts; shape is not a validated note-function label."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
import unittest
from test_musical_tier2 import facts
from test_harmonic_spans import brute_paths
from musical_tier2 import analyze, harmonic_span_evidence, harmonic_membership_evidence, note_motion_evidence, strip_lower, reconstruct
from run_note_context_qa import study, independent_queries

MELODY=[(0,60,0,1),(0,62,1,1),(0,64,2,1)]
CONTEXTS={'C':[(1,p,0,3) for p in (48,52,55)],'G':[(1,p,0,3) for p in (43,47,50)]}


class NoteContextEvidenceTests(unittest.TestCase):
    def test_independent_source_checker_rejects_missing_and_nonoptimal_witnesses(self):
        lower=facts([(0,60,0,1),(0,62,1,1),(0,64,2,1)]+[(1,p,0,3) for p in (48,52,55)])
        # Give synthetic occurrences the same public address grammar as source.
        raw={}
        for e in lower['events']:
            e['id']=f"event:1:{e['part_id']}:1:0:{e['beat']}:0";raw[e['id']]={k:e[k] for k in ('id','pitch','onset_q','duration_q')}
        sequences=[dict(part_id=0,voice=0,first_three_refs=[e['id'] for e in lower['events'][:3]])]
        result=study(analyze(lower),dict(start_q='0',end_q='3'),sequences)
        self.assertEqual(independent_queries(raw,sequences,result)['status'],'PASS')
        empty=deepcopy(result);empty['sequences'][0]['membership']['feasible_membership_vectors']=[]
        self.assertEqual(independent_queries(raw,sequences,empty)['status'],'FAIL')
        omitted=deepcopy(result);omitted['sequences'][0]['membership']=None
        self.assertEqual(independent_queries(raw,sequences,omitted)['status'],'FAIL')
        duplicate=deepcopy(result);rows=duplicate['sequences'][0]['membership']['feasible_membership_vectors'];rows.append(deepcopy(rows[0]))
        self.assertEqual(independent_queries(raw,sequences,duplicate)['status'],'FAIL')
        wrong=deepcopy(result);wrong['sequences'][0]['membership']['queries'][0]['at_q']='1/2'
        self.assertEqual(independent_queries(raw,sequences,wrong)['status'],'FAIL')
        nonoptimal=deepcopy(result);edge=nonoptimal['sequences'][0]['membership']['feasible_membership_vectors'][0]['one_valid_path_and_label_witness'][0]
        nonoptimal['harmonic']['optimal_predecessors'][edge['stop']].remove(edge['begin'])
        self.assertEqual(independent_queries(raw,sequences,nonoptimal)['status'],'FAIL')

    def test_storage_order_does_not_override_original_source_addresses(self):
        lower=facts([(0,60,0,0),(0,62,0,1),(0,64,1,1)])
        lower['events']=lower['events'][1:]+lower['events'][:1]
        upper=analyze(lower)
        result=note_motion_evidence(upper,['note-0','note-1','note-2'])
        self.assertNotIn('not_consecutive_owned_occurrences',result['refusal_reasons'])
        self.assertIn('zero_duration_or_grace_occurrence',result['refusal_reasons'])
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_joint_memberships_match_exhaustive_paths_and_label_assignments(self):
        notes=[(0,p,0,1) for p in (60,64,67,69)]+[(0,p,1,1) for p in (62,65,69)]
        upper=analyze(facts(notes));evidence=harmonic_span_evidence(upper,'0','2')
        queries=[dict(occurrence_ref=i,at_q=t) for i,t in (('note-2','0'),('note-3','1/2'),('note-4','1'))]
        actual=harmonic_membership_evidence(upper,evidence,queries)
        _,paths=brute_paths(notes,0,2);points=list(map(F,evidence['partition_points_q']))
        forms=((0,4,7),(0,4,7,10),(0,3,7),(0,3,6,9),(0,3,6,10),(0,3,6))
        expected=set()
        for path in paths:
            choices=[]
            for begin,stop in zip(path,path[1:]):
                weights=[0]*12
                for _,pitch,start,duration in notes:
                    for t in points[begin:stop]:
                        if start<=t<start+duration:weights[pitch%12]+=1
                rows=[]
                for root in range(12):
                    for formula in forms:
                        pcs={(root+x)%12 for x in formula};score=sum(w if pc in pcs else -w for pc,w in enumerate(weights))-sum(weights[pc]==0 for pc in pcs)
                        rows.append((score,pcs))
                best=max(s for s,_ in rows);choices.append([pcs for s,pcs in rows if s==best])
            for labels in product(*choices):
                vector=[]
                for query in queries:
                    slot=int(query['occurrence_ref'].split('-')[1]);at=F(query['at_q'])
                    edge=next(j for j,(a,b) in enumerate(zip(path,path[1:])) if points[a]<=at<points[b])
                    vector.append('chord_member' if notes[slot][1]%12 in labels[edge] else 'nonmember')
                expected.add(tuple(vector))
        self.assertEqual({tuple(r['memberships']) for r in actual['feasible_membership_vectors']},expected)
        for row in actual['feasible_membership_vectors']:
            witness=row['one_valid_path_and_label_witness'];self.assertEqual(witness[0]['begin'],0);self.assertEqual(witness[-1]['stop'],len(points)-1)
            self.assertTrue(all(a['stop']==b['begin'] for a,b in zip(witness,witness[1:])))
            for edge in witness:self.assertIn(edge['begin'],evidence['optimal_predecessors'][edge['stop']])

    def test_same_motion_different_harmony_changes_membership(self):
        vectors={}
        for context,accompaniment in CONTEXTS.items():
            lower=facts(MELODY+accompaniment);upper=analyze(lower)
            motion=note_motion_evidence(upper,['note-0','note-1','note-2'])
            self.assertEqual(motion['eligibility'],'eligible_owned_written_sequence')
            self.assertEqual(motion['motion']['shape'],'strictly_monotonic')
            self.assertIsNone(motion['passing_tone'])
            evidence=harmonic_span_evidence(upper,'0','3')
            result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref=f'note-{i}',at_q=str(i)) for i in range(3)])
            vectors[context]={tuple(r['memberships']) for r in result['feasible_membership_vectors']}
            self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        self.assertEqual(vectors['C'],{('chord_member','nonmember','chord_member')})
        # The final E may support an E-minor alternative; do not erase it to
        # enforce the accompaniment's intended label. D is a member in BOTH.
        self.assertEqual(vectors['G'],{('nonmember','chord_member','nonmember'),('nonmember','chord_member','chord_member')})

    def test_one_held_occurrence_changes_membership_without_new_attack(self):
        lower=facts([(0,60,0,2)]+[(1,p,0,1) for p in (48,52,55)]+[(1,p,1,1) for p in (43,47,50)])
        upper=analyze(lower);evidence=harmonic_span_evidence(upper,'0','2')
        result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='note-0',at_q=t) for t in ('1/2','3/2')])
        self.assertEqual({tuple(r['memberships']) for r in result['feasible_membership_vectors']},{('chord_member','nonmember')})
        self.assertEqual(upper['input']['events'][0]['onset_q'],'0')
        with self.assertRaises(ValueError):harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='note-0',at_q='2')])

    def test_same_edge_cannot_choose_incompatible_labels_per_note(self):
        upper=analyze(facts([(0,p,0,1) for p in (60,64,67,69)]));evidence=harmonic_span_evidence(upper,'0','1')
        result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref=i,at_q='0') for i in ('note-2','note-3')])
        self.assertEqual({tuple(r['memberships']) for r in result['feasible_membership_vectors']},{('chord_member','nonmember'),('nonmember','chord_member')})
        for row in result['feasible_membership_vectors']:self.assertEqual(len(row['one_valid_path_and_label_witness']),1)

    def test_octave_leaps_never_become_a_passing_tone_claim(self):
        upper=analyze(facts([(0,60,0,1),(0,74,1,1),(0,88,2,1)]))
        result=note_motion_evidence(upper,['note-0','note-1','note-2'])
        self.assertEqual(result['motion']['approach_semitones'],'14')
        self.assertEqual(result['motion']['shape'],'strictly_monotonic')
        self.assertIsNone(result['passing_tone']);self.assertIsNone(result['motion']['diatonic_step'])

    def test_polyphony_grace_unknown_gaps_and_skipped_occurrences_refused(self):
        cases=[[(0,60,0,1),(0,64,0,1),(0,65,1,1)],[(0,60,0,1),(0,None,1,1),(0,64,2,1)],[(0,60,0,1),(0,62,2,1),(0,64,3,1)],[(0,60,0,1),(0,62,1,0),(0,64,1,1)]]
        for notes in cases:
            result=note_motion_evidence(analyze(facts(notes)),['note-0','note-1','note-2'])
            self.assertEqual(result['eligibility'],'refused_unique_melodic_interpretation')
        upper=analyze(facts([(0,60,0,1),(0,None,1,1),(0,62,2,1),(0,64,3,1)]))
        self.assertIn('not_consecutive_owned_occurrences',note_motion_evidence(upper,['note-0','note-2','note-3'])['refusal_reasons'])
        upper=analyze(facts([(0,48,0,5),(0,60,1,1),(0,62,2,1),(0,64,3,1)]))
        self.assertIn('ambiguous_same_voice_overlap',note_motion_evidence(upper,['note-1','note-2','note-3'])['refusal_reasons'])

    def test_unknown_membership_is_retained_and_stale_context_rejected(self):
        upper=analyze(facts([(0,None,0,1)]));evidence=harmonic_span_evidence(upper,'0','1')
        result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='note-0',at_q='0')])
        self.assertEqual(result['feasible_membership_vectors'][0]['memberships'],['unknown'])
        self.assertTrue(result['query_has_partial_known_pitch_evidence'][0])
        stale=deepcopy(evidence);stale['optimal_score']=999
        with self.assertRaises(ValueError):harmonic_membership_evidence(upper,stale,[dict(occurrence_ref='note-0',at_q='0')])

    def test_fractional_pitch_unknown_and_partial_support_scope_distinct(self):
        upper=analyze(facts([(0,p,0,1) for p in (60,64,67,F(121,2))]));evidence=harmonic_span_evidence(upper,'0','1')
        result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='note-3',at_q='0')])
        self.assertEqual(result['query_pitch_domain'],['outside_supported_12_pitch_class_domain'])
        self.assertEqual(result['feasible_membership_vectors'][0]['memberships'],['unknown'])
        upper=analyze(facts([(0,p,0,2) for p in (60,64,67)]+[(0,None,1,1)]));evidence=harmonic_span_evidence(upper,'0','2')
        result=harmonic_membership_evidence(upper,evidence,[dict(occurrence_ref='note-0',at_q='0')])
        self.assertEqual(result['query_has_partial_known_pitch_evidence'],[False])
        self.assertEqual(result['feasible_membership_vectors'][0]['witness_supporting_edge_has_partial_evidence'],[True])


if __name__=='__main__':unittest.main()
