"""Controlled diagnostic: preserved exposure cannot describe harmonic direction.

These authored counterexamples have NO asserted true key or musical preference.
They are tests, never generation rules or artist training data.
"""
from copy import deepcopy
import unittest
from musical_tier2 import analyze, strip_lower, reconstruct, harmonic_span_evidence


def counterexample(reverse=False):
    chords=[(57,60,64),(52,56,59,62),(48,52,55)]
    if reverse:chords.reverse()
    events=[]
    for beat,pitches in enumerate(chords):
        for note,pitch in enumerate(pitches):
            events.append(dict(id=f'controlled:{beat}:{note}',part_id=0,bar=1,voice=0,beat=beat,note=note,pitch=str(pitch),onset_q=str(beat),duration_q='1'))
    return dict(tier=1,schema='normalized-written-context-facts/3',scope='written_context_facts_geometry_and_optional_source_keys',events=events,source_coverage=dict(expected=len(events),actual=len(events),tracks=1,layout_warnings=[],timing_warnings=[]),source_key_declarations=None,source_key_inventory=[dict(part_id=0,measure_count=1,end_q='3')],measure_geometry=dict(source_format='musicxml',source_id='AUTHORED_ORDER_COUNTEREXAMPLE_NOT_A_SOURCE_SCORE',frames=[dict(id='measure:1',ordinal=1,label='1',start_q='0',span_q='3',signature=[3,4],meter_source='explicit',meter_source_frame=1)],parts=[dict(part_id=0,frame_refs=['measure:1'],source_pickup_declared=None)],first_notated_span_q='3'))


def query(upper):
    scope=upper['tonal_evidence']['scopes'][0]
    temporal=upper['temporal_tonal_evidence']['scopes'][0]['measures'][0]
    harmonic=harmonic_span_evidence(upper,'0','3')
    return dict(histogram=scope['pitch_class_duration_q'],global_scores=[c['score'] for c in scope['candidates']],raw_temporal=temporal['raw_scores'],smoothed_temporal=temporal['smoothed_scores'],harmonic=harmonic)


class TonalOrderBlindspotTests(unittest.TestCase):
    def test_same_exposure_and_key_scores_different_harmonic_trajectory(self):
        results=[]
        for reverse in (False,True):
            lower=counterexample(reverse);upper=analyze(lower);blind=strip_lower(upper)
            self.assertEqual(reconstruct(blind,{'variation':0}),lower)
            results.append(query(blind))
        a,b=results
        for field in ('histogram','global_scores','raw_temporal','smoothed_temporal'):
            self.assertEqual(a[field],b[field],field)
        self.assertNotEqual(a['harmonic']['all_optimal_path_cell_consensus'][0]['candidate_labels'],b['harmonic']['all_optimal_path_cell_consensus'][0]['candidate_labels'])
        self.assertEqual(a['harmonic']['optimal_score'],b['harmonic']['optimal_score'])


if __name__=='__main__':unittest.main()
