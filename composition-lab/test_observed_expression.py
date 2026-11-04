"""Original evidence survives address changes without gaining generated votes."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from source_fact_tier1 import extract_documents
from source_observation_evidence import digest, origin
from test_local_accents import documents
import observed_expression as saved


class ObservedExpressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tier1 = extract_documents(documents())
        cls.owner = saved.capture(cls.tier1)

    def test_three_domains_contain_semantic_evidence_not_a_hidden_score(self):
        saved.validate(self.owner, origin(self.tier1))
        self.assertEqual(set(self.owner['observations']), saved.POLICIES)
        serialized = json.dumps(self.owner)
        for forbidden in ('"facts":', '"documents":', '"note_notation":', '"pattern":', '"context_key":'):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(saved.source_view(self.owner), self.owner)
        self.assertEqual(saved.project(self.owner, {}, {}), self.owner)

    def test_shift_and_subdivision_retain_original_counts_and_identity(self):
        first = 'event:93:0:1:0:1:0'
        later = 'event:93:0:1:0:2:0'
        first_beat = 'track-0.json#/measures/0/voices/0/beats/1'
        later_beat = 'track-0.json#/measures/0/voices/0/beats/2'
        event_map = {first:[first,later], later:['event:93:0:1:0:3:0']}
        fact_map = {first_beat:[first_beat,later_beat], later_beat:['track-0.json#/measures/0/voices/0/beats/3']}
        # Shift the remaining source addresses too: collisions are forbidden.
        for source in saved._domains(self.owner)['event_map']:
            fields = source.split(':')
            if fields[3:5] == ['1','0'] and int(fields[5]) >= 3:
                event_map[source] = [':'.join(fields[:5]+[str(int(fields[5])+1),fields[6]])]
        for source in saved._domains(self.owner)['fact_map']:
            prefix='track-0.json#/measures/0/voices/0/beats/'
            if source.startswith(prefix) and source[len(prefix):].isdigit() and int(source[len(prefix):])>=3:
                fact_map[source]=[prefix+str(int(source[len(prefix):])+1)]
        projected = saved.project(self.owner, fact_map, event_map)
        self.assertEqual(saved.evidence(projected), saved.evidence(self.owner))
        self.assertEqual(projected['evidence_sha256'], self.owner['evidence_sha256'])
        self.assertEqual(saved.original_refs(projected, [first,later], require_all=True), {first})
        self.assertEqual(saved.original_refs(projected, ['event:93:0:1:0:3:0'], require_all=True), {later})
        restored = json.loads(json.dumps(projected))
        self.assertEqual(saved.project(restored, {}, {}), projected)
        self.assertEqual(len(saved.observations(restored, saved.ACCENT)), len(self.owner['observations'][saved.ACCENT]))

    def test_conflicting_lineage_refuses_atomically(self):
        old = deepcopy(self.owner)
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            saved.project(self.owner, {}, {'event:93:0:1:0:1:0':['event:93:0:1:0:2:0']})
        self.assertEqual(self.owner, old)
        with self.assertRaisesRegex(ValueError, 'crossed'):
            saved.project(self.owner, {}, {'event:93:0:1:0:1:0':['event:93:1:1:0:1:0']})

    def test_unpitched_rest_identity_moves_with_complete_beat_map(self):
        docs=documents();beats=docs['track-0.json']['measures'][0]['voices'][0]['beats']
        beats[2]['notes']=[dict(rest=True)];beats[2]['rest']=True
        owner=saved.capture(extract_documents(docs));unchanged=deepcopy(owner)
        prefix='track-0.json#/measures/0/voices/0/beats/'
        fact_map={prefix+'1':[prefix+'1',prefix+'2'],
                  **{prefix+str(i):[prefix+str(i+1)]for i in range(2,len(beats))}}
        # Deliberately provide only the pitched split member: the rest has no
        # normalized pitched event, exactly as in the retained Cloud failure.
        events={'event:93:0:1:0:1:0':['event:93:0:1:0:1:0','event:93:0:1:0:2:0']}
        projected=saved.project(owner,fact_map,events)
        self.assertEqual(saved.evidence(projected),saved.evidence(owner))
        self.assertEqual(projected['evidence_sha256'],owner['evidence_sha256'])
        self.assertEqual(saved.original_refs(projected,['event:93:0:1:0:3:0'],require_all=True),{'event:93:0:1:0:2:0'})
        self.assertEqual(saved.original_refs(projected,['event:93:0:1:0:2:0'],require_all=True),{'event:93:0:1:0:1:0'})
        wrong=dict(events,**{'event:93:0:1:0:2:0':['event:93:0:1:0:99:0']})
        with self.assertRaisesRegex(ValueError,'conflicts with enclosing beat'):
            saved.project(owner,fact_map,wrong)
        self.assertEqual(owner,unchanged)

    def test_observation_and_origin_tampering_are_detected(self):
        changed = deepcopy(self.owner)
        changed['observations'][saved.ACCENT][0]['sound_level']=2
        with self.assertRaisesRegex(ValueError, 'observations changed'):
            saved.validate(changed)
        wrong = deepcopy(self.owner['origin']);wrong['facts_sha256']='a'*64
        with self.assertRaisesRegex(ValueError, 'origin disagrees'):
            saved.validate(self.owner, wrong)

    def test_saved_evidence_does_not_query_original_source_or_current_score(self):
        with patch('builtins.open',side_effect=AssertionError('Source lookup forbidden')), \
                patch('local_accents.inventory',side_effect=AssertionError('No new votes')):
            clone = saved.source_view(json.loads(json.dumps(self.owner)))
            self.assertEqual(digest(clone), digest(self.owner))
        with self.assertRaisesRegex(ValueError,'no original lineage'):
            saved.original_refs(clone,['event:93:0:99:0:0:0'],require_all=True)

    def test_ephemeral_preparation_is_a_snapshot_and_does_not_change_saved_evidence(self):
        import local_accents as policy
        from test_local_accents import TARGET
        owner=deepcopy(self.owner);prepared=saved.prepare(owner)
        baseline=policy.options(self.tier1,TARGET,observations=owner)
        self.assertEqual(baseline,policy.options(self.tier1,TARGET,observations=prepared))
        owner['observations'][saved.ACCENT].clear()
        self.assertEqual(baseline,policy.options(self.tier1,TARGET,observations=prepared))


class RetainedPolicyEvidenceTests(unittest.TestCase):
    def test_unchanged_accent_options_are_identical(self):
        import local_accents as policy
        from test_local_accents import TARGET
        facts=extract_documents(documents());owner=saved.capture(facts)
        self.assertEqual(policy.options(facts,TARGET),policy.options(facts,TARGET,observations=owner))

    def test_edited_donor_accents_cannot_manufacture_original_votes(self):
        import local_accents as policy
        from test_local_accents import TARGET
        original=documents();facts=extract_documents(original);owner=saved.capture(facts)
        baseline=policy.options(facts,TARGET,observations=owner)
        for measure in original['track-0.json']['measures'][1:]:
            measure['voices'][0]['beats'][1]['notes'][0]['accentuated']=2
        current=extract_documents(original)
        after=policy.options(current,TARGET,observations=json.loads(json.dumps(owner)))
        self.assertEqual(after['options'],baseline['options'])
        self.assertEqual(after['witness_pair'],baseline['witness_pair'])
        self.assertNotEqual(policy.options(current,TARGET)['options'],baseline['options'])
        original['track-0.json']['measures'][0]['voices'][0]['beats'][1]['duration']=[1,8]
        self.assertFalse(policy.options(extract_documents(original),TARGET,observations=owner)['options'])

    def test_unchanged_complete_mute_options_are_identical(self):
        import local_palm_mutes as policy
        from test_local_palm_mutes import TARGET
        from test_palm_mute_opportunity_census import documents as mute_documents
        facts=extract_documents(mute_documents());owner=saved.capture(facts)
        self.assertEqual(policy.options(facts,TARGET),policy.options(facts,TARGET,observations=owner))

    def test_edited_mute_donors_are_not_relearned_and_current_pitch_changes_eligibility(self):
        import local_palm_mutes as policy
        from test_local_palm_mutes import TARGET
        from test_palm_mute_opportunity_census import documents as mute_documents
        docs=mute_documents();facts=extract_documents(docs);owner=saved.capture(facts)
        baseline=policy.options(facts,TARGET,observations=owner)
        for measure in docs['track-0.json']['measures'][1:]:
            for beat in measure['voices'][0]['beats']:beat['palmMute']=True
        current=extract_documents(docs)
        self.assertEqual(policy.options(current,TARGET,observations=owner)['options'],baseline['options'])
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret']+=1
        self.assertFalse(policy.options(extract_documents(docs),TARGET,observations=owner)['options'])

    def test_original_tempo_options_match_then_survive_changed_all_source_speeds(self):
        import local_step_tempos as policy
        from test_local_step_tempos import setup_case
        docs,facts,view,baseline,controls=setup_case();owner=saved.capture(facts)
        self.assertEqual(baseline,policy.options(facts,controls['target_ref'],controls['component_ref'],observations=owner))
        for entry in docs['track-0.json']['automations']['tempo']:entry['bpm']=120
        current=extract_documents(docs)
        after=policy.options(current,controls['target_ref'],controls['component_ref'],observations=owner)
        self.assertEqual(after['witness_pair'],baseline['witness_pair'])
        self.assertEqual([(r['quarter_bpm'],r['donor_refs'])for r in after['options']],
                         [(r['quarter_bpm'],r['donor_refs'])for r in baseline['options']])
        self.assertFalse(policy.options(current,controls['target_ref'],controls['component_ref'])['options'])
        changed=next(row for row in policy.inventory(current)['clock']['global_events']if row['id']==controls['target_ref'])
        beat=docs['track-0.json']['measures'][changed['bar']-1]['voices'][0]['beats'][0]
        beat['notes'][0]['accentuated']=2
        self.assertFalse(policy.options(extract_documents(docs),controls['target_ref'],controls['component_ref'],observations=owner)['options'])


class RetainedOwnerIntegrationTests(unittest.TestCase):
    def test_batch_accent_equals_sequential_preserves_owners_and_is_atomic(self):
        from connected_tier2 import analyze,strip_lower,realize
        import local_accents as policy
        facts=extract_documents(documents())
        upper=strip_lower(analyze(facts,note_accent_slots=True,expression_evidence=True))
        refs=[group['note_structure']['id']for group in upper['owned_parameters']['optional_note_accents']['groups']]
        changes={refs[0]:dict(kind='explicit',value=1),refs[-1]:dict(kind='explicit',value=2)}
        sequential=upper
        for ref,state in changes.items():sequential=policy.apply(sequential,ref,state)
        with patch('connected_tier2.realize',wraps=realize)as realization:
            batch=policy.apply_many(upper,changes)
            self.assertEqual(realization.call_count,2)
        self.assertEqual(batch,sequential)
        expected=deepcopy(upper)
        expected['owned_parameters']['optional_note_accents']=batch['owned_parameters']['optional_note_accents']
        self.assertEqual(batch,expected)
        untouched=deepcopy(upper)
        with self.assertRaises(ValueError):
            policy.apply_many(upper,dict(changes,missing_note=dict(kind='explicit',value=2)))
        self.assertEqual(upper,untouched)
        with self.assertRaises(ValueError):
            policy.apply_many(upper,{refs[0]:changes[refs[0]],refs[-1]:dict(kind='explicit',value=99)})
        self.assertEqual(upper,untouched)

    def _successive(self, policy, facts, controls, **flags):
        from connected_tier2 import analyze, strip_lower, realize
        upper=strip_lower(analyze(facts,expression_evidence=True,**flags))
        evidence=deepcopy(upper['owned_parameters']['observed_expression'])
        control=next(key for key in ('accents','palm_mute','tempo')if key in controls)
        self.assertEqual(realize(upper),facts)
        for iteration in range(2):
            upper=json.loads(json.dumps(upper))
            before=deepcopy(upper)
            if control=='tempo':
                available=policy.options(realize(upper),controls['target_ref'],controls['component_ref'],observations=evidence)
            else:
                available=policy.options(realize(upper),controls['target_ref'],observations=evidence)
            seed=next(seed for seed in range(32)if policy.sample(available,dict(controls,seed=seed))[1]['changed'])
            upper,decision=policy.intervene(upper,dict(controls,seed=seed))
            self.assertTrue(decision['changed'])
            self.assertEqual(upper['owned_parameters']['observed_expression'],evidence)
            self.assertEqual(before['owned_parameters']['observed_expression'],evidence)
            locked,zero=policy.intervene(upper,dict(controls,**{control:0}))
            self.assertEqual(locked,upper);self.assertFalse(zero['changed'])
            self.assertEqual(realize(locked),realize(upper))
        return upper

    def test_two_accent_edits_reload_zero_and_actual_source_denied_worker(self):
        from pathlib import Path
        import tempfile
        import local_accents as policy
        from test_local_accents import controls
        from connected_tier2 import realize
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        upper=self._successive(policy,extract_documents(documents()),controls(),note_accent_slots=True)
        code,_=bundle(Path(__file__).parent)
        expected,_=policy.intervene(upper,controls())
        with tempfile.TemporaryDirectory()as temp:
            result=execute(code,upper,controls(),realize(expected),Path(temp)/'isolated',timeout=30,purpose='local_accents_intervention')
            self.assertEqual(result['status'],'PASS',result)

    def test_two_mute_edits_reload_and_zero(self):
        import local_palm_mutes as policy
        from test_palm_mute_opportunity_census import documents as source
        from test_local_palm_mutes import TARGET
        self._successive(policy,extract_documents(source()),
            dict(context_policy=policy.POLICY,palm_mute=100,target_ref=TARGET,seed=0),palm_mute_slots=True)

    def test_two_tempo_edits_reload_and_zero(self):
        import local_step_tempos as policy
        from test_local_step_tempos import setup_case
        _,facts,_,_,controls=setup_case()
        self._successive(policy,facts,controls,step_tempos=True)


if __name__ == '__main__':
    unittest.main()
