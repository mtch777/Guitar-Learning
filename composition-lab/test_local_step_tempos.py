import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from source_fact_tier1 import extract_documents
from test_tempo_source_census import tempo_documents
import local_step_tempos as tempo


def setup_case():
    docs=tempo_documents();facts=extract_documents(docs);view=tempo.inventory(facts)
    row=next(r for r in view['choices']['A_passage_speed']['components']if r['independent_contrast'])
    controls=dict(context_policy=tempo.POLICY,tempo=100,target_ref=row['event_id'],component_ref=tempo.component_id(row['part_id'],row['voice']),seed=0)
    evidence=tempo.options(facts,controls['target_ref'],controls['component_ref'],view)
    return docs,facts,view,evidence,controls


class LocalStepTempoTests(unittest.TestCase):
    def test_same_owner_intervention_keeps_written_time_and_all_other_facts_exact(self):
        from connected_tier2 import analyze,strip_lower,realize
        docs,facts,view,evidence,controls=setup_case()
        upper=strip_lower(analyze(facts,step_tempos=True,rhythm_groups=True,rhythm_group_profile='written_time',note_accent_slots=True,palm_mute_slots=True))
        locked,decision=tempo.intervene(upper,dict(controls,tempo=0))
        self.assertEqual(locked,upper);self.assertEqual(realize(locked),facts);self.assertFalse(decision['changed'])
        changed_seed=next(i for i in range(32)if tempo.sample(evidence,dict(controls,seed=i))[1]['changed'])
        edited,decision=tempo.intervene(upper,dict(controls,seed=changed_seed))
        self.assertTrue(decision['changed']);self.assertEqual(decision['evidence_label'],'PARTIAL')
        self.assertEqual(realize(upper),facts)
        chosen,_=tempo.sample(evidence,dict(controls,seed=changed_seed))
        self.assertEqual(tempo.verify_effect(facts,realize(edited),evidence['target'],chosen['quarter_bpm'])['status'],'EXACT_GLOBAL_BPM_ALIAS_SCOPE')
        expected=deepcopy(upper);expected['owned_parameters']['global_step_tempos']=edited['owned_parameters']['global_step_tempos']
        self.assertEqual(edited,expected)

    def test_intervention_recomputes_changed_donor_relationships(self):
        from connected_tier2 import analyze,strip_lower,realize
        from step_tempo_relations import set_bpm
        _,facts,_,_,controls=setup_case();upper=strip_lower(analyze(facts,step_tempos=True))
        for group in upper['owned_parameters']['global_step_tempos']['groups']:
            upper['owned_parameters']['global_step_tempos']=set_bpm(upper['owned_parameters']['global_step_tempos'],group['id'],'120')
        before=realize(upper);out,decision=tempo.intervene(upper,controls)
        self.assertEqual(realize(out),before);self.assertFalse(decision['changed']);self.assertFalse(decision['evidence']['options'])

    def test_data_only_evidence_uses_unique_global_events_and_preserves_partial_scope(self):
        docs,facts,view,evidence,controls=setup_case()
        original=deepcopy(facts)
        with patch('builtins.open',side_effect=AssertionError('No source file')),patch.object(Path,'read_bytes',side_effect=AssertionError('No source file')),patch.object(Path,'read_text',side_effect=AssertionError('No source file')):
            fresh=tempo.options(facts,controls['target_ref'],controls['component_ref'])
        self.assertEqual(fresh,evidence);self.assertEqual(facts,original)
        self.assertEqual(evidence['evidence_label'],'PARTIAL')
        self.assertTrue(evidence['options'])
        refs=[r for o in evidence['options']for r in o['donor_refs']]
        self.assertEqual(len(refs),len(set(refs)));self.assertNotIn(controls['target_ref'],refs)
        self.assertEqual({o['quarter_bpm']for o in evidence['options']},set(evidence['target']['component_evidence']['supported_bpms']))
        self.assertEqual(evidence['target']['full_influence_musical_suitability'],'NOT_ESTABLISHED_BY_ENTRY_BAR')

    def test_release_is_probability_and_100_does_not_force_difference(self):
        _,_,_,evidence,controls=setup_case()
        outcomes={s:[tempo.sample(evidence,dict(controls,tempo=s,seed=i))[1]for i in range(1024)]for s in(0,50,100)}
        self.assertFalse(any(r['released']or r['changed']for r in outcomes[0]))
        self.assertTrue(all(r['released']for r in outcomes[100]))
        self.assertTrue(any(r['changed']for r in outcomes[100]))
        self.assertTrue(any(not r['changed']for r in outcomes[100]))
        self.assertGreater(sum(r['released']for r in outcomes[50]),400)
        self.assertLess(sum(r['released']for r in outcomes[50]),624)

    def test_donor_change_recomputes_support_without_original_cache(self):
        docs,facts,_,evidence,controls=setup_case()
        self.assertTrue(evidence['options'])
        for entry in docs['track-0.json']['automations']['tempo']:entry['bpm']=120
        changed=tempo.options(extract_documents(docs),controls['target_ref'],controls['component_ref'])
        self.assertFalse(changed['options']);self.assertIsNone(changed['witness_pair'])

    def test_native_unknown_extra_and_ramp_are_not_silently_ignored(self):
        for edit in('metadata','ramp','local_missing_unit','other_track_conflict'):
            docs,_,_,_,controls=setup_case()
            if edit=='metadata':docs['metadata.json']['tempo']=999
            elif edit=='ramp':docs['track-0.json']['automations']['tempo'][-1]['linear']=True
            elif edit=='local_missing_unit':docs['track-0.json']['measures'][-1]['voices'][0]['beats'][0]['tempo']={'bpm':80}
            else:
                docs['track-1.json']=deepcopy(docs['track-0.json']);docs['track-1.json']['partId']=1
                docs['track-1.json']['automations']['tempo'][-1]['bpm']=999
                docs['metadata.json']['tracks'].append(deepcopy(docs['metadata.json']['tracks'][0]))
            result=tempo.options(extract_documents(docs),controls['target_ref'],controls['component_ref'])
            self.assertEqual(result['status'],'REFUSED_NATIVE_TEMPO_MAP',edit);self.assertFalse(result['options'],edit)

    def test_typed_controls_and_unknown_targets_are_refused(self):
        _,facts,view,_,controls=setup_case()
        for field,value in(('tempo',True),('tempo',float('nan')),('tempo',101),('seed',True),('component_ref','part:0'),('target_ref','global-tempo:-1'),('context_policy','whole_song_palette')):
            with self.assertRaises(ValueError):tempo.validate_controls(dict(controls,**{field:value}))
        with self.assertRaises(ValueError):tempo.validate_controls(dict(controls,bpm=120))
        with self.assertRaises(ValueError):tempo.options(facts,'global-tempo:9999',controls['component_ref'],view)
        with self.assertRaises(ValueError):tempo.options(facts,controls['target_ref'],'part:99:voice:0',view)

    def test_alias_only_fact_comparison_includes_exact_occurrence_order(self):
        _,facts,_,evidence,_=setup_case();target=evidence['target'];bpm=next(o['quarter_bpm']for o in evidence['options']if o['changed'])
        edited=deepcopy(facts)
        for r in edited['facts']:
            if r['id']in target['bpm_refs']:r['value']=int(bpm)
        self.assertEqual(tempo.verify_effect(facts,edited,target,bpm)['status'],'EXACT_GLOBAL_BPM_ALIAS_SCOPE')
        corrupted=deepcopy(edited);next(r for r in corrupted['facts']if r['id'].endswith('/fret'))['value']+=1
        with self.assertRaises(ValueError):tempo.verify_effect(facts,corrupted,target,bpm)
        with self.assertRaises(ValueError):tempo.verify_effect(facts,facts,target,bpm)
        reordered=deepcopy(edited);reordered['facts'][0],reordered['facts'][1]=reordered['facts'][1],reordered['facts'][0]
        with self.assertRaisesRegex(ValueError,'occurrence order'):tempo.verify_effect(facts,reordered,target,bpm)


if __name__=='__main__':unittest.main()
