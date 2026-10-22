"""Geometry ownership, immutable temporal evidence, and shared timed coordinates."""
from copy import deepcopy
import unittest
from test_musical_tier2 import facts
from musical_tier2 import analyze, reconstruct, strip_lower, geometry_relation, immutable_temporal_scores, temporal_note_context, transpose


def timed_facts():
    lower=facts([(0,60,0,1),(0,64,0,1),(0,67,0,1),(0,62,4,1),(0,66,4,1),(0,69,4,1)])
    for row in lower['events']:row['bar']=1 if int(row['onset_q'])<4 else 2
    frames=[dict(id=f'measure:{i}',ordinal=i,label=str(i),start_q=str((i-1)*4),span_q='4',signature=[4,4],meter_source='explicit' if i==1 else 'inherited',meter_source_frame=1) for i in (1,2,3)]
    lower.update(schema='normalized-written-context-facts/3',scope='written_context_facts_geometry_and_optional_source_keys',source_key_declarations=None,source_key_inventory=[dict(part_id=0,measure_count=3,end_q='12')],measure_geometry=dict(source_format='musicxml',source_id='test.xml',frames=frames,parts=[dict(part_id=0,frame_refs=[r['id'] for r in frames],source_pickup_declared=None)],first_notated_span_q='1'))
    return lower


class TemporalTier2Tests(unittest.TestCase):
    def test_same_geometry_inverse_and_key_scope_absence_distinction(self):
        lower=timed_facts();upper=analyze(lower)
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)
        self.assertIsNone(upper['source_keys'])
        lower['source_key_declarations']=[];upper=analyze(lower)
        self.assertEqual(upper['source_keys']['inventory_ref'],'measure_geometry')
        self.assertNotIn('inventory',upper['source_keys'])
        self.assertEqual(reconstruct(strip_lower(upper),{'variation':0}),lower)

    def test_geometry_rejects_invented_meter_and_inconsistent_clock(self):
        geometry=timed_facts()['measure_geometry']
        for field,value in (('start_q','5'),('meter_source_frame',2),('signature',[3,4])):
            bad=deepcopy(geometry);bad['frames'][1][field]=value
            with self.assertRaises(ValueError):geometry_relation(source=bad)
        bad=deepcopy(geometry);bad['source_format']='songsterr_json';bad['frames'][0]['span_q']='1'
        with self.assertRaises(ValueError):geometry_relation(source=bad)

    def test_immutable_smoothing_does_not_reuse_mutated_neighbors(self):
        raw=[[.9,.1],[.2,.8],[.8,.2]];saved=deepcopy(raw)
        result=immutable_temporal_scores(raw,1)
        self.assertAlmostEqual(result[1][0],1.05);self.assertAlmostEqual(result[1][1],.95)
        self.assertEqual(raw,saved);self.assertEqual(immutable_temporal_scores(raw,1),result)
        self.assertEqual(immutable_temporal_scores(list(reversed(raw)),1),list(reversed(result)))
        self.assertIsNone(immutable_temporal_scores([raw[0],None,raw[2]],4)[1])
        with self.assertRaises(ValueError):immutable_temporal_scores([[1],[1,2]],1)

    def test_empty_real_measure_retains_all_unknowns_and_no_fake_key(self):
        upper=analyze(timed_facts());row=upper['temporal_tonal_evidence']['scopes'][0]['measures'][2]
        self.assertEqual(len(row['candidates']),24)
        self.assertEqual(row['raw_scores'],[None]*24);self.assertEqual(row['smoothed_scores'],[None]*24)
        self.assertEqual(row['contributing_frame_refs'],[])

    def test_timed_note_context_uses_existing_relation_and_scope(self):
        upper=analyze(timed_facts());candidate=upper['temporal_tonal_evidence']['scopes'][0]['measures'][0]['candidates'][0]
        context=temporal_note_context(upper,'note-1',candidate['id'])
        self.assertEqual(context['interval_of_note_base_key_candidate']['semitones_mod12'],'4')
        self.assertIsNone(context['established_key'])
        with self.assertRaises(ValueError):temporal_note_context(upper,'note-4',candidate['id'])
        changed=transpose(upper,2)
        self.assertEqual(reconstruct(changed,{'variation':0})['events'][1]['pitch'],'66')
        bad=strip_lower(upper);bad['temporal_tonal_evidence']['scopes'][0]['measures'][0]['raw_scores'][0]=999
        with self.assertRaises(ValueError):reconstruct(bad,{'variation':0})


if __name__=='__main__':unittest.main()
