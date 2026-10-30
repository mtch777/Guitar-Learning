import json,tempfile,unittest
from unittest.mock import patch
from copy import deepcopy
from pathlib import Path
from tempo_source_census import raw_fields,global_inventory,global_inventory_documents,component_inventory,component_inventory_documents,tempo_opportunities,independent
from test_palm_mute_opportunity_census import documents


def tempo_documents():
    docs=documents();part=docs['track-0.json'];bar=deepcopy(part['measures'][0]);part['measures']=[deepcopy(bar)for _ in range(24)]
    part['automations']=dict(tempo=[dict(measure=2*i,position=0,bpm=100 if i%2==0 else 110+i*10,type=4)for i in range(12)])
    return docs


def inspect(docs):
    with tempfile.TemporaryDirectory()as folder:
        path=Path(folder)
        for name,value in docs.items():(path/name).write_text(json.dumps(value),encoding='utf-8')
        clock=global_inventory(path);components=component_inventory(path,clock)
        return clock,components,tempo_opportunities(components)


class TempoRawInventoryTests(unittest.TestCase):
    def test_data_only_adapters_preserve_capture_observations_without_file_access(self):
        docs=tempo_documents();original=deepcopy(docs)
        clock,view,choices=inspect(docs)
        from reversible_temporal import extract_documents,encode,decode
        with patch('builtins.open',side_effect=AssertionError('No source file access')),patch.object(Path,'read_bytes',side_effect=AssertionError('No source file access')),patch.object(Path,'read_text',side_effect=AssertionError('No source file access')),patch.object(Path,'glob',side_effect=AssertionError('No source lookup')):
            records=extract_documents(docs);self.assertEqual(decode(encode(records)),records)
            data_clock=global_inventory_documents(docs)
            self.assertEqual({k:v for k,v in data_clock.items()if k!='temporal_record_inverse'},{k:v for k,v in clock.items()if k!='temporal_record_inverse'})
            data_view=component_inventory_documents(docs,data_clock)
            self.assertEqual(data_view,view);self.assertEqual(tempo_opportunities(data_view),choices)
        self.assertEqual(docs,original)

    def test_every_location_type_and_nested_tempo_field_is_retained(self):
        docs={'metadata.json':{'tempo':123,'unknown':{'BPM':None}},'track-0.json':{'automations':{'gradualTempo':False,'tempo':[{'bpm':123,'type':4,'linear':False}]},'a/b':{'tempo~raw':'unknown'}}}
        rows=raw_fields(docs);index={r['source_ref']:r for r in rows}
        self.assertEqual(len(rows),6)
        self.assertEqual(index['metadata.json#/unknown/BPM']['value_type'],'null')
        self.assertEqual(index['track-0.json#/a~1b/tempo~0raw']['value'],'unknown')
        self.assertIs(index['track-0.json#/automations/gradualTempo']['value'],False)
        self.assertEqual(index['track-0.json#/automations/tempo']['value'],docs['track-0.json']['automations']['tempo'])

    def test_aliases_remain_exact_but_each_global_event_counts_once(self):
        docs=tempo_documents();docs['track-1.json']=deepcopy(docs['track-0.json']);docs['track-1.json']['partId']=1
        docs['metadata.json']['tracks'].append(deepcopy(docs['metadata.json']['tracks'][0]))
        clock,view,counts=inspect(docs)
        self.assertEqual(clock['counts']['declarations'],24);self.assertEqual(clock['counts']['global_events'],12)
        self.assertEqual(clock['counts']['extra_track_aliases'],12)
        self.assertTrue(all(len(e['alias_refs'])==2 for e in clock['global_events']))
        self.assertEqual(clock['temporal_record_inverse']['status'],'pass')

    def test_both_strata_keep_full_independent_source_denominators(self):
        clock,view,choices=inspect(tempo_documents());byid={e['event_id']:e for e in view['events']}
        for key,result in choices.items():
            self.assertEqual(result['component_denominator'],12)
            supported=[r for r in result['components']if r['independent_contrast']]
            self.assertTrue(supported,key)
            for row in supported:
                a,b=(byid[r]for r in row['independent_contrast']);target=byid[row['event_id']]
                self.assertNotEqual(a['bpm'],b['bpm'])
                self.assertTrue(independent(a,b)and independent(a,target)and independent(b,target))
                if key=='B_transition':self.assertEqual(a['incoming_bpm'],target['incoming_bpm']);self.assertEqual(b['incoming_bpm'],target['incoming_bpm'])
        self.assertEqual(choices['B_transition']['counts']['UNKNOWN_INCOMING_BPM'],1)

    def test_inactive_components_are_not_positive_rhythmic_evidence(self):
        docs=tempo_documents()
        for m in docs['track-0.json']['measures']:
            for b in m['voices'][0]['beats']:
                for n in b['notes']:n['rest']=True
        _,_,choices=inspect(docs)
        for result in choices.values():
            self.assertEqual(result['counts']['NO_RHYTHMIC_ATTACK_EVIDENCE'],12)
            self.assertFalse(any(r['supported_bpms']for r in result['components']))
            self.assertEqual(result['complete_ensemble_choice_targets'],0)

    def test_missing_dynamics_stays_unknown_without_default(self):
        docs=tempo_documents()
        for m in docs['track-0.json']['measures']:
            for b in m['voices'][0]['beats']:b.pop('velocity',None)
        _,view,choices=inspect(docs)
        self.assertTrue(all('UNKNOWN_WRITTEN_DYNAMICS'in e['components'][0]['reasons']for e in view['events']))
        self.assertEqual(choices['A_passage_speed']['counts']['UNKNOWN_OR_PARTIAL'],12)

    def test_ramps_units_and_conflicting_aliases_are_retained(self):
        docs=tempo_documents();docs['track-0.json']['automations']['tempo'][2]['linear']=True
        docs['track-0.json']['automations']['tempo'][3]['type']=8
        docs['track-1.json']=deepcopy(docs['track-0.json']);docs['track-1.json']['partId']=1
        docs['track-1.json']['automations']['tempo'][0]['bpm']=101
        docs['metadata.json']['tracks'].append(deepcopy(docs['metadata.json']['tracks'][0]))
        clock,_,_=inspect(docs)
        self.assertIn('CONFLICTING_GLOBAL_BPM_DECLARATIONS',clock['global_events'][0]['reasons'])
        self.assertIn('ramp_execution_unresolved',clock['global_events'][2]['reasons'])
        self.assertIn('unverified_or_missing_tempo_unit',clock['global_events'][3]['reasons'])


if __name__=='__main__':unittest.main()
