from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct
from voicing_register import inventory,select_target,intervene,effect_reasons,validate_controls,sample_choice


def documents():
    def measure(notes):return dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=notes)])])
    low=[dict(string=5,fret=0),dict(string=4,fret=2),dict(string=3,fret=2)]
    high=[dict(string=3,fret=2),dict(string=2,fret=4),dict(string=1,fret=5)]
    return {'metadata.json':dict(songId=77,revisionId=3,artist='Fixture',title='Observed register choices',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=77,revisionId=3,partId=0,name='Guitar',instrumentId=25,tuning=[64,59,55,50,45,40],
            measures=[measure(low),measure(high),measure(high),measure([dict(string=0,fret=17)])])}


class VoicingRegisterTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(documents());upper=strip_lower(analyze(lower));catalog=inventory(lower);selection=select_target(catalog)
        self.assertIsNotNone(selection['target_ref']);return lower,upper,catalog,selection['target_ref']

    def test_zero_exact_and_observed_nonzero_uses_equations_keeps_other_facts(self):
        lower,upper,catalog,target=self.fixture();zero=dict(voicing=0,register=0,target_ref=target,seed=9427)
        self.assertEqual(reconstruct(upper,zero),lower)
        edited,decision=intervene(upper,dict(zero,voicing=100,register=100))
        self.assertTrue(decision['changed']);actual=reconstruct(edited,dict(variation=0))
        old={r['id']:r for r in lower['facts']};new={r['id']:r for r in actual['facts']}
        differences=[i for i in old if old[i]!=new[i]]
        self.assertEqual(len(differences),3);self.assertTrue(all(i.endswith('/fret') for i in differences))
        self.assertEqual([project_documents(actual)['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][i]['fret'] for i in range(3)],[12,14,14])
        self.assertEqual(reconstruct(upper,dict(zero,voicing=100,register=100)),actual)

    def test_separate_voicing_and_register_locks(self):
        lower,upper,catalog,target=self.fixture()
        _,decision=intervene(upper,dict(voicing=0,register=100,target_ref=target,seed=9427))
        self.assertTrue(decision['changed']);self.assertFalse(decision['released']['voicing'])
        unchanged,decision=intervene(upper,dict(voicing=100,register=0,target_ref=target,seed=9427))
        self.assertFalse(decision['changed']);self.assertEqual(reconstruct(unchanged,dict(variation=0)),lower)

    def test_no_alternative_is_retained_not_guessed(self):
        docs=documents();docs['track-0.json']['measures']=docs['track-0.json']['measures'][:1]
        lower=extract_documents(docs);catalog=inventory(lower)
        self.assertEqual(select_target(catalog)['status'],'NO_ELIGIBLE_ALTERNATIVE')
        upper=strip_lower(analyze(lower));target=catalog['units'][0]['id']
        _,decision=intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427))
        self.assertEqual(decision['status'],'NO_ELIGIBLE_ALTERNATIVE')

    def test_zero_empty_expression_unknowns_not_plain_notes(self):
        for field,value in (('harmonicFret',0),('bend',{}),('vibrato',True),('leftHandVibrato',True),('wideVibrato',True),('tie',True),('hp',True)):
            self.assertTrue(effect_reasons({},dict(string=0,fret=0,**{field:value})),field)
        for field in ('tremoloBar','vibrato','letRing','arpeggio','brushStroke'):
            self.assertTrue(effect_reasons({field:{}},dict(string=0,fret=0)),field)

    def test_physical_conflict_refused_without_source_patch(self):
        docs=documents();docs['track-0.json']['measures'].pop()
        lower=extract_documents(docs);upper=strip_lower(analyze(lower));target=select_target(inventory(lower))['target_ref']
        before=deepcopy(upper)
        with self.assertRaisesRegex(ValueError,'physical envelope'):intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427))
        self.assertEqual(upper,before)

    def test_strict_controls_and_no_hidden_lower_payload(self):
        _,upper,_,target=self.fixture()
        for controls in (dict(voicing=True,register=100,target_ref=target,seed=9427),dict(voicing=100,register=101,target_ref=target,seed=9427),dict(voicing=100,register=100,target_ref=None,seed=9427)):
            with self.assertRaises(ValueError):validate_controls(controls)
        upper['input']={}
        with self.assertRaises(ValueError):intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427))

    def test_actual_isolated_nonzero_worker_has_no_lower_or_source(self):
        lower,upper,catalog,target=self.fixture();controls=dict(voicing=100,register=100,target_ref=target,seed=9427)
        expected=reconstruct(upper,controls)
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:result=execute(code,upper,controls,expected,Path(temp)/'isolated',timeout=30,purpose='voicing_register_intervention')
        self.assertEqual(result['status'],'PASS',result)

    def test_supported_spacing_change_can_keep_anchor_register_locked(self):
        docs=documents()
        for bar in (1,2):docs['track-0.json']['measures'][bar]['voices'][0]['beats'][0]['notes']=[dict(string=5,fret=0),dict(string=2,fret=4),dict(string=1,fret=5)]
        lower=extract_documents(docs);upper=strip_lower(analyze(lower));target=select_target(inventory(lower))['target_ref']
        _,decision=intervene(upper,dict(voicing=100,register=0,target_ref=target,seed=9427))
        self.assertTrue(decision['changed']);self.assertEqual(decision['original']['anchor'],decision['chosen']['realization']['anchor'])
        self.assertFalse(decision['released']['register'])

    def test_full_release_choice_is_invariant_to_original_register_preference(self):
        lower,upper,catalog,target=self.fixture();controls=dict(voicing=100,register=100,target_ref=target,seed=9427)
        original,_=sample_choice(catalog,controls);mutated=deepcopy(catalog)
        next(r for r in mutated['units'] if r['id']==target)['realization']=deepcopy(original)
        actual,decision=sample_choice(mutated,controls)
        self.assertEqual(actual,original);self.assertEqual(decision['status'],'OBSERVED_COINCIDENCE')

    def test_half_strength_releases_dimensions_not_half_the_notes(self):
        lower,upper,catalog,target=self.fixture();counts=dict(voicing=0,register=0)
        for seed in range(1000):
            _,decision=sample_choice(catalog,dict(voicing=50,register=50,target_ref=target,seed=seed))
            for name in counts:counts[name]+=decision['released'][name]
        self.assertTrue(all(400<c<600 for c in counts.values()),counts)

    def test_contextual_assertions_recomputed_after_same_equation_change(self):
        lower,upper,catalog,target=self.fixture()
        from contextual_note_roles import attach
        upper=attach(upper,[dict(version='conditional-passage-note-roles/1',harmonic_request=dict(start_q='0',end_q='4',part_id=None),reference_candidate_ref=None)])
        edited,decision=intervene(upper,dict(voicing=100,register=100,target_ref=target,seed=9427))
        self.assertTrue(decision['changed'])
        self.assertNotEqual(upper['contextual_constraints'],edited['contextual_constraints'])
        reconstruct(edited,dict(variation=0))

    def witnessed_fixture(self):
        docs=documents();part=docs['track-0.json'];part['measures']=part['measures'][:3]
        for i in (1,2):
            part['measures'][i]['voices'][0]['beats'][0]['notes']=[dict(string=5,fret=12),dict(string=4,fret=14),dict(string=3,fret=14)]
            part['measures'][i]['voices'][0]['beats'][0]['beamStart']=True
        lower=extract_documents(docs);catalog=inventory(lower)
        target=select_target(catalog,'source_witnessed_fixed_strings')['target_ref']
        return lower,catalog,target

    def test_joint_shape_witness_and_notation_separate_from_context(self):
        lower,catalog,target=self.witnessed_fixture();self.assertIsNotNone(target)
        upper=strip_lower(analyze(lower));controls=dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy='source_witnessed_fixed_strings')
        edited,decision=intervene(upper,controls);self.assertTrue(decision['changed'])
        self.assertEqual(decision['fixed_string_frets'],[12,14,14])
        from run_voicing_register_qa import locked_diff
        self.assertEqual(locked_diff(lower,reconstruct(edited,dict(variation=0)),decision['member_refs'])['status'],'PASS_LOCKED_DIMENSIONS')
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:
            result=execute(code,upper,controls,reconstruct(edited,dict(variation=0)),Path(temp)/'worker',timeout=30,purpose='voicing_register_intervention')
        self.assertEqual(result['status'],'PASS',result)

    def test_pitches_on_other_strings_cannot_witness_fixed_shape(self):
        lower=extract_documents(documents());catalog=inventory(lower)
        selection=select_target(catalog,'source_witnessed_fixed_strings')
        self.assertIsNone(selection['target_ref'])
        from voicing_register import empirical_options
        evidence=empirical_options(catalog,catalog['units'][0]['id'],'source_witnessed_fixed_strings')
        self.assertTrue(any(r['reason']=='NO_JOINT_FIXED_STRING_WITNESS' for r in evidence['rejected']))

    def test_witness_requires_whole_shape_and_tuning_capo(self):
        from voicing_register import witnessed_geometry
        _,catalog,target_id=self.witnessed_fixture();target=next(r for r in catalog['units'] if r['id']==target_id)
        donor=catalog['units'][1];self.assertTrue(witnessed_geometry(target,donor,donor['realization']))
        for field,value in [('capo',1),('tuning',[65,59,55,50,45,40]),('instrument',26)]:
            changed=deepcopy(donor);changed['source_geometry'][field]=value
            self.assertFalse(witnessed_geometry(target,changed,donor['realization']))
        changed=deepcopy(donor);changed['source_geometry']['members'].pop()
        self.assertFalse(witnessed_geometry(target,changed,donor['realization']))

    def test_final_guard_rejects_broken_tie_even_if_candidate_filter_is_corrupt(self):
        from unittest.mock import patch
        docs=documents();part=docs['track-0.json'];part['measures']=part['measures'][:3]
        for i,measure in enumerate(part['measures']):
            frets=[0,2,2] if i==0 else [12,14,14]
            measure['voices'][0]['beats']=[dict(duration=[1,2],notes=[dict(string=s,fret=f) for s,f in zip((5,4,3),frets)]),dict(duration=[1,2],notes=[dict(string=5,fret=frets[0],tie=True)])]
        lower=extract_documents(docs);catalog=inventory(lower);target=catalog['units'][0]['id']
        self.assertTrue(catalog['units'][0]['locked_tie_members'])
        for unit in catalog['units']:unit['locked_tie_members']=[]
        upper=strip_lower(analyze(lower));controls=dict(voicing=100,register=100,target_ref=target,seed=9427,context_policy='source_witnessed_fixed_strings')
        with patch('voicing_register.inventory',return_value=catalog):
            with self.assertRaisesRegex(ValueError,'Locked written tie relationship'):intervene(upper,controls)
        self.assertEqual(reconstruct(upper,dict(variation=0)),lower)


if __name__=='__main__':unittest.main()
