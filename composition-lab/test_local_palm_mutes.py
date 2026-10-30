"""Source-predicate policy and exact source locks; no artist judgment."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,realize
from test_palm_mute_opportunity_census import documents
import local_palm_mutes as mute

TARGET='coattack:0:1'


def model(docs=None,**kwargs):
    before=extract_documents(documents()if docs is None else docs)
    return before,strip_lower(analyze(before,palm_mute_slots=True,**kwargs))


class LocalPalmMuteTests(unittest.TestCase):
    def test_source_options_preserve_false_absent_and_on_off_independence(self):
        before,_=model();ev=mute.options(before,TARGET)
        self.assertEqual(ev['status'],'SOURCE_SUPPORTED_PALM_MUTE_CHOICES')
        self.assertEqual({str(o['states'])for o in ev['options']},{str([dict(kind='absent')]),str([dict(kind='explicit',value=False)]),str([dict(kind='explicit',value=True)])})
        self.assertEqual(len(ev['witness_pair']),2)

    def test_whole_chord_changes_one_beat_flag_with_every_other_fact_locked(self):
        before,upper=model();ev=mute.options(before,TARGET);chosen=next(o for o in ev['options']if o['mute_changed'])
        out=mute.apply(upper,ev['target']['beat_refs'],chosen['states']);after=realize(out)
        proof=mute.verify_effect(before,after,ev['target']['beat_refs'],chosen['states'])
        self.assertEqual(proof['status'],'EXACT_COMPLETE_COATTACK_PALM_MUTE_SCOPE')
        docs=project_documents(after);self.assertTrue(docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['palmMute'])
        self.assertEqual(docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'],documents()['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'])
        self.assertEqual(out['musical_relationships'],upper['musical_relationships'])

    def test_zero_is_exact_and_percentage_release_not_forced_change(self):
        before,upper=model();controls=dict(context_policy=mute.POLICY,palm_mute=0,target_ref=TARGET,seed=0)
        out,decision=mute.intervene(upper,controls);self.assertEqual(out,upper);self.assertEqual(realize(out),before)
        ev=mute.options(before,TARGET)
        for amount in(0,50,100):
            draws=[mute.sample(ev,dict(controls,palm_mute=amount,seed=s))[1]for s in range(256)]
            if amount==0:self.assertFalse(any(d['released']or d['changed']for d in draws))
            elif amount==50:self.assertTrue(100<sum(d['released']for d in draws)<156)
            else:
                self.assertTrue(all(d['released']for d in draws))
                self.assertTrue(any(d['mute_changed']for d in draws))
                self.assertTrue(any(not d['changed']for d in draws))
        false=next(o for o in ev['options']if o['states']==[dict(kind='explicit',value=False)])
        self.assertTrue(false['changed']);self.assertFalse(false['mute_changed'])

    def test_no_choice_and_other_execution_remain_refused(self):
        docs=documents()
        for m in docs['track-0.json']['measures']:
            for b in m['voices'][0]['beats']:b['palmMute']=True
        before,upper=model(docs);self.assertEqual(mute.options(before,TARGET)['options'],[])
        out,decision=mute.intervene(upper,dict(context_policy=mute.POLICY,palm_mute=100,target_ref=TARGET,seed=0))
        self.assertEqual(out,upper);self.assertFalse(decision['changed'])
        docs=documents();docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['letRing']=True
        before,_=model(docs);self.assertEqual(mute.options(before,TARGET)['status'],'REFUSED_PALM_MUTE_CONTEXT')

    def test_optional_accents_and_structural_time_owner_compose(self):
        before,upper=model(note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time')
        self.assertEqual(realize(upper),before);ev=mute.options(before,TARGET);choice=next(o for o in ev['options']if o['mute_changed'])
        out=mute.apply(upper,ev['target']['beat_refs'],choice['states'])
        self.assertEqual(out['owned_parameters']['optional_note_accents'],upper['owned_parameters']['optional_note_accents'])
        self.assertEqual(out['musical_relationships'],upper['musical_relationships'])
        mute.verify_effect(before,realize(out),ev['target']['beat_refs'],choice['states'])

    def test_locked_pitch_duration_and_other_marking_cannot_change(self):
        before,upper=model();ev=mute.options(before,TARGET);choice=next(o for o in ev['options']if o['mute_changed'])
        after=realize(mute.apply(upper,ev['target']['beat_refs'],choice['states']))
        for suffix in('/notes/0/fret','/duration/1','/velocity'):
            wrong=deepcopy(after);row=next(r for r in wrong['facts']if r['id']==ev['target']['beat_refs'][0]+suffix)
            row['value']='p'if suffix=='/velocity'else row['value']+1
            with self.assertRaises(ValueError):mute.verify_effect(before,wrong,ev['target']['beat_refs'],choice['states'])

    def test_actual_palm_flag_inside_owned_time_group_keeps_same_time_owner(self):
        from test_group_rhythm_relations import documents as rhythm_documents
        docs=rhythm_documents();before,upper=model(docs,rhythm_groups=True,rhythm_group_profile='written_time',note_accent_slots=True)
        self.assertTrue(upper['musical_relationships']['groups'])
        beat=upper['musical_relationships']['groups'][0]['members'][1]['beat_ref']
        original=deepcopy(upper['musical_relationships'])
        changed=mute.apply(upper,[beat],[dict(kind='explicit',value=True)])
        self.assertEqual(changed['musical_relationships'],original)
        mute.verify_effect(before,realize(changed),[beat],[dict(kind='explicit',value=True)])
        from local_group_rhythm import options as rhythm_options
        self.assertFalse(rhythm_options(realize(changed),original['groups'][0]['id'])['options'])

    def test_duplicate_or_stale_optional_ownership_fails_inverse(self):
        _,upper=model(note_accent_slots=True)
        for kind in('duplicate_group','structure_overlap','stale_flag','unknown_state','wrong_coverage'):
            bad=deepcopy(upper);g=bad['owned_parameters']['optional_beat_palm_mutes']['groups'][0]
            if kind=='duplicate_group':bad['owned_parameters']['optional_beat_palm_mutes']['groups'].append(deepcopy(g))
            elif kind=='structure_overlap':bad['source_structure']['facts'].append(deepcopy(g['beat_structure']))
            elif kind=='stale_flag':g['beat_structure']['children'].append(g['beat_structure']['id']+'/palmMute')
            elif kind=='unknown_state':g['state']=dict(kind='explicit',value=1,child_index=0)
            else:bad['coverage']['rules'].pop()
            with self.assertRaises((ValueError,KeyError)):realize(bad)

    def test_every_beat_of_one_multivoice_coattack_changes_together(self):
        docs=documents();docs['track-0.json']['tuning'].append(60)
        for m in docs['track-0.json']['measures']:
            second=deepcopy(m['voices'][0])
            for b in second['beats']:b['notes']=[dict(string=2,fret=2)]
            m['voices'].append(second)
        before,upper=model(docs);ev=mute.options(before,TARGET)
        chosen=next(o for o in ev['options']if o['mute_changed'])
        self.assertEqual(len(ev['target']['beat_refs']),2)
        after=realize(mute.apply(upper,ev['target']['beat_refs'],chosen['states']))
        for voice in project_documents(after)['track-0.json']['measures'][0]['voices']:
            self.assertTrue(voice['beats'][1]['palmMute'])
        mute.verify_effect(before,after,ev['target']['beat_refs'],chosen['states'])
        docs['track-0.json']['measures'][0]['voices'][1]['beats'][1]['palmMute']=True
        before,_=model(docs);ev=mute.options(before,TARGET)
        self.assertEqual(ev['options'],[]);self.assertIn('MIXED_MUTED_AND_UNMUTED_COATTACK',ev['target']['reasons'])

    def test_missing_group_with_rule_old_owner_and_forged_child_fail_full_inverse(self):
        before,upper=model();legacy=analyze(before)['owned_parameters']['technique_declarations']
        for kind in('missing_group_and_rule','former_technique_owner','forged_immediate_child'):
            bad=deepcopy(upper);model_=bad['owned_parameters']['optional_beat_palm_mutes'];group=model_['groups'][0]
            if kind=='missing_group_and_rule':
                model_['groups'].remove(group);bad['coverage']['rules'].remove(dict(relation=group['id']))
            elif kind=='former_technique_owner':
                old=next(g for g in legacy['groups']if g['field']=='palmMute')
                bad['owned_parameters']['technique_declarations']['groups'].append(deepcopy(old))
                bad['coverage']['fixed'].append(dict(fact_ref=old['source_fact_ref'],owner='technique_declaration'))
            else:group['beat_structure']['children'].append(group['beat_structure']['id']+'/forged')
            with self.assertRaises((ValueError,KeyError),msg=kind):realize(bad)

    def test_actual_source_denied_percentage_policy(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        before,upper=model(note_accent_slots=True,rhythm_groups=True,rhythm_group_profile='written_time')
        expected=documents();expected['track-0.json']['measures'][0]['voices'][0]['beats'][1]['palmMute']=True
        expected=extract_documents(expected);code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as folder:
            for amount in(0,50,100):
                c=dict(context_policy=mute.POLICY,palm_mute=amount,target_ref=TARGET,seed=3)
                result=execute(code,upper,c,before if amount==0 else expected,Path(folder)/str(amount),timeout=45,purpose='local_palm_mute_intervention')
                self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
