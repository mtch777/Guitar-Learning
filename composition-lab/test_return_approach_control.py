"""Composed-return routing and authority preservation; authored boundaries."""
from contextlib import ExitStack
from copy import deepcopy
import unittest
from unittest.mock import patch

import return_approach_control as control
import support_material_uses as uses


def source_documents():
    docs = {'metadata.json': dict(songId=991234, revisionId=42)}
    # Deliberately sparse IDs and reversed document insertion order.
    for part in (11, 4):
        bars = [dict(voices=[]) for _ in range(8)]
        for bar, text in ((1, 'Opening'), (4, 'Return'), (7, 'Ending')):
            bars[bar-1]['marker'] = dict(text=text)
        docs[f'track-{part}.json'] = dict(songId=991234, revisionId=42, partId=part, measures=bars)
    return docs


def mock_models():
    """Small ownership fixtures; the production musical inverse is not mocked as evidence."""
    slots = [dict(scope=dict(parts=[4], first_bar=b, last_bar=b)) for b in (1, 4, 2)]
    t3 = dict(tier=3, schema=uses.RHYTHM_SCHEMA,
        materials=[dict(scope=s['scope'], immutable_observation=i) for i,s in enumerate(slots)],
        slots=slots, uses=[dict(id=f'use:{i}', slot_ref=i, material_ref=i, expression=[]) for i in range(3)],
        observations={'original': ['unchanged']}, relationship={'existing_live_owner': 'keep'},
        instance_attack_refs=['stable'], lower_tier={'all_prior_dependencies': ['foreign'], 'unowned_part11': True})
    t3['uses'][1]['rhythm_offset_q'] = '1/2'
    t3['uses'][2]['approach_mode'] = 'flip'
    owners = [dict(allocation=dict(use_id=f'use:{i}', expression=[], **({'material_ref': 0} if i == 0 else {})),
                   constraints={'independent_obligation': i}) for i in (0, 1)]
    child=deepcopy(t3)
    # Existing recall resolves source material0 at return1.
    t3['uses'][1]['material_ref']=0
    for i in (0,1):
        child['uses'][i].pop('material_ref');child['uses'][i].pop('expression')
    upper=dict(tier=5,schema=control.theme.SCHEMA,relationship=dict(source_use='use:0',return_use='use:1',
        mode='recall',independent_material_ref=1), lower_tier=dict(tier=4,schema=control.sections.SCHEMA,
        choices=owners,lower_tier=child))
    selected=dict(part_id=11,bars=[5,6])
    original=deepcopy(t3);scope=dict(parts=[11],first_bar=5,last_bar=6)
    original['materials'].append(dict(scope=scope,meaning='consecutive degrees to live arrival'))
    original['slots'].append(dict(scope=scope))
    original['uses'].append(dict(id='use:3',slot_ref=3,material_ref=3,expression=[],approach_mode='original'))
    original['lower_tier'].pop('unowned_part11')
    changed=deepcopy(original);changed['uses'][-1]['approach_mode']='flip'
    result=dict(status='PREPARED',original=original,changed=changed,selected=selected,use_id='use:3',
        discovery={'runs': ['outside', 'refused_inside', 'accepted_inside']},attempts=['retained'])
    return upper,t3,result


def expand_theme(upper):
    section=deepcopy(upper['lower_tier'])
    source=next(o for o in section['choices'] if o['allocation']['use_id']==upper['relationship']['source_use'])
    target=next(o for o in section['choices'] if o['allocation']['use_id']==upper['relationship']['return_use'])
    target['allocation']['material_ref']=source['allocation']['material_ref']
    return section


def expand_section(section):
    result=deepcopy(section['lower_tier'])
    for owner in section['choices']:
        use=next(u for u in result['uses'] if u['id']==owner['allocation']['use_id'])
        use.update({k:deepcopy(v) for k,v in owner['allocation'].items() if k!='use_id'})
    return result


def remove_fixture(lower, scopes):
    if scopes != [dict(parts=[11],first_bar=5,last_bar=6)]:
        raise AssertionError('Unexpected ownership transfer')
    result=deepcopy(lower);result.pop('unowned_part11');return result


class SourceSectionTests(unittest.TestCase):
    def setUp(self):
        self.docs=source_documents();self.scope=dict(parts=[4],first_bar=4,last_bar=4)

    def test_full_section_and_sparse_part_identities(self):
        result=control.source_section(self.docs,self.scope)
        self.assertEqual({k:result[k] for k in ('first_bar','last_bar','label')},
                         dict(first_bar=4,last_bar=6,label='Return'))
        self.assertEqual([w['part_id'] for w in result['witnesses']],[4,11])

    def test_final_label_ends_at_actual_score_end(self):
        result=control.source_section(self.docs,dict(parts=[11],first_bar=7,last_bar=8))
        self.assertEqual(result['last_bar'],8)
        self.assertTrue(all(w['ending']=='score_end' for w in result['witnesses']))

    def test_missing_conflicting_and_crossing_markers_are_explicit_refusals(self):
        for kind in ('missing','different-label','different-start','different-end','empty','crossing'):
            docs=deepcopy(self.docs);scope=deepcopy(self.scope);bars=docs['track-11.json']['measures']
            if kind=='missing':
                for bar in bars:bar.pop('marker',None)
            elif kind=='different-label':bars[3]['marker']['text']='Other'
            elif kind=='different-start':bars[4]['marker']=bars[3].pop('marker')
            elif kind=='different-end':bars[5]['marker']=bars[6].pop('marker')
            elif kind=='empty':bars[3]['marker']['text']=' '
            else:scope['last_bar']=7
            frozen=deepcopy(docs)
            with self.subTest(kind=kind),self.assertRaises(ValueError):control.source_section(docs,scope)
            self.assertEqual(docs,frozen)

    def test_wrong_song_revision_part_or_missing_track_refuses(self):
        for key,value in (('songId',1),('revisionId',41),('partId',4)):
            docs=deepcopy(self.docs);docs['track-11.json'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):control.source_section(docs,self.scope)
        with self.assertRaises(ValueError):
            control.source_section(self.docs,dict(parts=[99],first_bar=4,last_bar=4))


class ReturnApproachBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.upper,self.t3,self.result=mock_models()
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(control.theme,'expand',side_effect=expand_theme))
        self.stack.enter_context(patch.object(control.sections,'expand',side_effect=expand_section))
        self.stack.enter_context(patch.object(control.uses,'reconstruct',return_value={'source':'exact'}))
        self.reconstruct=self.stack.enter_context(patch.object(control.theme,'reconstruct',return_value={'source':'exact'}))
        self.stack.enter_context(patch.object(control,'project_documents',return_value=source_documents()))
        self.stack.enter_context(patch.object(control.material,'_remove',side_effect=remove_fixture))
        self.prepare=self.stack.enter_context(patch.object(control.discovery,'prepare_first',side_effect=lambda *a,**k:deepcopy(self.result)))

    def test_routes_full_return_and_preserves_live_owners_and_existing_variations(self):
        frozen=deepcopy(self.upper);result=control.prepare(self.upper)
        self.assertEqual(self.upper,frozen)
        self.prepare.assert_called_once_with(self.t3,scope=dict(first_bar=4,last_bar=6))
        self.assertEqual(result['discovery'],self.result['discovery'])
        self.assertEqual(result['changed']['relationship'],self.upper['relationship'])
        self.assertEqual(result['changed']['lower_tier']['choices'],self.upper['lower_tier']['choices'])
        self.assertEqual(result['changed_t3']['uses'][:3],self.t3['uses'])
        self.assertEqual(result['changed_t3']['uses'][1]['rhythm_offset_q'],'1/2')
        self.assertEqual(result['changed_t3']['uses'][2]['approach_mode'],'flip')
        self.assertEqual(len(self.reconstruct.call_args_list),1)
        for owner in result['changed']['lower_tier']['choices']:
            use=next(u for u in result['changed']['lower_tier']['lower_tier']['uses'] if u['id']==owner['allocation']['use_id'])
            self.assertNotIn('material_ref',use);self.assertNotIn('expression',use)

    def test_no_fit_preserves_full_record_without_adding_owner(self):
        self.result=dict(status='NO_APPLICABLE_APPROACH',discovery={'runs':['failed']},attempts=['retained'])
        result=control.prepare(self.upper)
        self.assertEqual(result['status'],'NO_APPLICABLE_APPROACH');self.assertNotIn('changed',result)
        self.reconstruct.assert_not_called()

    def test_outside_or_crossing_selected_run_refuses_before_embedding(self):
        for bars in ([2,3],[3,5],[6,7]):
            self.result['selected']['bars']=bars
            with self.subTest(bars=bars),self.assertRaisesRegex(ValueError,'outside'):
                control.prepare(self.upper)

    def test_prior_meaning_loss_refuses_even_when_reconstructed_notes_match(self):
        good=deepcopy(self.result)
        for field in ('material','slot','use','observation','foreign-owner','rhythm','earlier-approach'):
            self.result=deepcopy(good);value=self.result['changed']
            if field=='material':value['materials'][0]['immutable_observation']='lost'
            elif field=='slot':value['slots'][0]['scope']['first_bar']=2
            elif field=='use':value['uses'][0]['material_ref']=1
            elif field=='observation':value['observations']['original'].append('generated')
            elif field=='foreign-owner':value['lower_tier']['all_prior_dependencies']=[]
            elif field=='rhythm':value['uses'][1].pop('rhythm_offset_q')
            else:value['uses'][2]['approach_mode']='original'
            frozen=deepcopy(self.upper)
            with self.subTest(field=field),self.assertRaises(ValueError):control.prepare(self.upper)
            self.assertEqual(self.upper,frozen)

    def test_current_zero_must_equal_complete_prior_source(self):
        self.reconstruct.return_value={'source':'different'}
        with self.assertRaisesRegex(ValueError,'current-zero'):control.prepare(self.upper)

    def test_existing_owner_cannot_be_repurposed_as_new_approach(self):
        self.result['use_id']='use:2'
        with self.assertRaisesRegex(ValueError,'ownership'):control.prepare(self.upper)


if __name__=='__main__':
    unittest.main()
