"""Exact explicit-reference degrees are not authored spelling or inferred keys."""
from copy import deepcopy
from fractions import Fraction as F
import unittest
from test_musical_tier2 import facts
from test_temporal_tier2 import timed_facts
from musical_tier2 import analyze,collection_degree_relation,collection_motion_context,tonal_note_context,temporal_note_context,strip_lower,reconstruct,same

MAJOR=[0,2,4,5,7,9,11]
MINOR=[0,2,3,5,7,8,10]


def candidate(upper,quality,tonic=0):
    return next(c['id'] for s in upper['tonal_evidence']['scopes'] if s['id']=='song-pooled' for c in s['candidates'] if c['family']=='KrumhanslSchmuckler' and c['quality']==quality and c['tonic_pc']==tonic)


class CollectionDegreeTests(unittest.TestCase):
    def test_every_degree_register_and_tonic_solves_same_equation_both_ways(self):
        for tonic in range(12):
            for intervals in (MAJOR,MINOR):
                for octave in range(-2,9):
                    for degree,interval in enumerate(intervals,1):
                        inverse=collection_degree_relation(tonic,intervals,degree=degree,relative_octaves=octave)
                        self.assertEqual(inverse['pitch'],str(tonic+12*octave+interval))
                        self.assertEqual(collection_degree_relation(tonic,intervals,pitch=inverse['pitch']),inverse)

    def test_same_notes_under_parallel_references_do_not_force_chromatic_degrees(self):
        lower=facts([(0,60,0,1),(0,63,1,1),(0,65,2,1)]);upper=analyze(lower)
        major=collection_motion_context(upper,['note-0','note-1','note-2'],candidate(upper,'major'))
        minor=collection_motion_context(upper,['note-0','note-1','note-2'],candidate(upper,'minor'))
        self.assertEqual([c['interval_of_note_base_key_candidate']['reference_collection_degree'] for c in major['note_contexts']],[1,None,4])
        self.assertEqual([c['interval_of_note_base_key_candidate']['reference_collection_degree'] for c in minor['note_contexts']],[1,3,4])
        self.assertIsNone(major['pairs'][0]['signed_diatonic_displacement'])
        self.assertEqual([r['signed_diatonic_displacement'] for r in minor['pairs']],[2,1])
        self.assertEqual([r['chromatic_distance_semitones'] for r in minor['pairs']],['3','2'])
        self.assertEqual([r['adjacent_degree_movement'] for r in minor['pairs']],[False,True])
        self.assertIsNone(minor['passing_tone']);self.assertIsNone(minor['established_key'])
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        self.assertTrue(same(minor,collection_motion_context(strip_lower(upper),['note-0','note-1','note-2'],candidate(upper,'minor'))))

    def test_octave_crossing_adjacent_degree_and_large_leap_not_adjacent(self):
        for pitches,expected in (([59,60,62],[1,1]),([62,60,59],[-1,-1]),([60,74,88],[8,8])):
            upper=analyze(facts([(0,p,i,1) for i,p in enumerate(pitches)]));result=collection_motion_context(upper,['note-0','note-1','note-2'],candidate(upper,'major'))
            self.assertEqual([p['signed_diatonic_displacement'] for p in result['pairs']],expected)
            self.assertEqual([p['adjacent_degree_movement'] for p in result['pairs']],[abs(x)==1 for x in expected])

    def test_unknown_fractional_and_source_ambiguity_preserve_limits(self):
        upper=analyze(facts([(0,None,0,1),(0,F(121,2),1,1),(0,62,2,1)]));result=collection_motion_context(upper,['note-0','note-1','note-2'],candidate(upper,'major'))
        self.assertIsNone(result['note_contexts'][0]['interval_of_note_base_key_candidate'])
        self.assertIsNone(result['note_contexts'][1]['interval_of_note_base_key_candidate']['reference_collection_degree'])
        self.assertEqual(result['pairs'][1]['chromatic_distance_semitones'],'3/2')
        upper=analyze(facts([(0,60,0,1),(0,62,0,1),(0,64,1,1)]));result=collection_motion_context(upper,['note-0','note-1','note-2'],candidate(upper,'major'))
        self.assertEqual(result['pairs'][0]['status'],'source_sequence_interpretation_refused')
        self.assertIsNone(result['pairs'][0]['adjacent_degree_movement'])

    def test_global_and_temporal_coordinates_share_the_same_degree_relation(self):
        upper=analyze(timed_facts());global_context=tonal_note_context(upper,'note-1',candidate(upper,'major'))
        timed=next(c for s in upper['temporal_tonal_evidence']['scopes'] if s['id']=='song-pooled' for m in s['measures'] if m['frame_ref']=='measure:1' for c in m['candidates'] if c['tonic_pc']==0 and c['quality']=='major')
        temporal=temporal_note_context(upper,'note-1',timed['id'])
        self.assertEqual(global_context['interval_of_note_base_key_candidate'],temporal['interval_of_note_base_key_candidate'])
        self.assertEqual(global_context['interval_of_note_base_key_candidate']['reference_collection_degree'],3)

    def test_malformed_coordinates_and_stale_candidate_refused(self):
        for kwargs in (dict(degree=True,relative_octaves=5),dict(degree=0,relative_octaves=5),dict(degree=8,relative_octaves=5),dict(degree=1,relative_octaves=False),dict(degree=1,relative_octaves=5.0),dict(pitch='60',degree=2),dict(pitch='60',relative_octaves=4),dict(pitch='61'),dict(degree=1)):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):collection_degree_relation(0,MAJOR,**kwargs)
        for tonic,intervals in ((True,MAJOR),(12,MAJOR),(0,[0,2,2,5,7,9,11]),(0,[0,2,4,5,7,9,12]),(0,[0,2,4,5,7,9,True])):
            with self.assertRaises(ValueError):collection_degree_relation(tonic,intervals,pitch='60')
        upper=analyze(facts([(0,60,0,1),(0,62,1,1),(0,64,2,1)]));bad=deepcopy(upper);bad['tonal_evidence']['scopes'][0]['candidates'][0]['reference_intervals'][0]=1
        with self.assertRaises(ValueError):collection_motion_context(bad,['note-0','note-1','note-2'],candidate(upper,'major'))

    def test_query_reference_retains_tied_or_undefined_models_without_arbitrary_key(self):
        from run_collection_degree_qa import study
        symmetric=analyze(facts([(0,p,i,1) for i,p in enumerate((60,64,68))]))
        result=study(strip_lower(symmetric),1e-12)
        self.assertIsNone(result['query_reference']);self.assertGreater(len(result['numerically_tied_maxima']),1)
        self.assertTrue(all(r['contexts']==[] for r in result['sequences']))
        uniform=analyze(facts([(0,60+i,i,1) for i in range(12)]));result=study(strip_lower(uniform),1e-12)
        self.assertIsNone(result['query_reference']);self.assertEqual(result['numerically_tied_maxima'],[])

    def test_independent_reference_selector_rejects_wrong_winner_and_parallel_set(self):
        from run_collection_degree_qa import study,reference_selection_issues
        upper=analyze(facts([(0,p,i,1) for i,p in enumerate((60,62,64))]));result=study(strip_lower(upper),1e-12)
        scope=next(s for s in upper['tonal_evidence']['scopes'] if s['id']=='song-pooled')
        self.assertIsNotNone(result['query_reference']);self.assertEqual(reference_selection_issues(scope,result,1e-12),[])
        for mutate in ('id','parallel','tolerance','ties'):
            wrong=deepcopy(result)
            if mutate=='id':wrong['query_reference']['candidate_ref']='wrong-model-reference'
            elif mutate=='parallel':wrong['query_reference']['parallel_candidates'].pop()
            elif mutate=='tolerance':wrong['tolerance']=1e-3
            else:wrong['numerically_tied_maxima']=[]
            self.assertTrue(reference_selection_issues(scope,wrong,1e-12))


if __name__=='__main__':unittest.main()
