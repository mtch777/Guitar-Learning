"""Authored nonadjacent recall, independent endings/drums and successive edits."""
from copy import deepcopy
import json,unittest
import test_musical_support_material as support_fixture
import test_musical_cell_development as cell_fixture
import musical_support_material as material
import support_material_uses as uses
import support_arrangement as single
import section_arrangements as sections
import thematic_return as theme
from source_fact_tier1 import project_documents
from source_observation_evidence import digest


def build():
    docs,_,_,_=support_fixture.authored()
    for part in (2,3):
        track=docs[f'track-{part}.json']
        track['measures'][0]['voices'][0]['beats'][0]['velocity']='f'
        track['measures'][1]['voices'][0]['beats'][0]['velocity']='mf'
        track['measures'][4]=deepcopy(track['measures'][0])
    # This different drum detail at the return must never become part of recall.
    docs['track-4.json']['measures'][4]['voices'][0]['beats']=[dict(duration=[1,1],notes=[dict(string=0,fret=49)])]
    _,_,_,cell=cell_fixture.build(docs=docs)
    t3=uses.lift(material.lift_t3(cell,[dict(parts=[2,3],first_bar=b,last_bar=b)for b in(1,2)]))
    original=single.lift(t3,'material-use:0',[0,1])
    multi=sections.extend(original,[dict(parts=[2,3],first_bar=5,last_bar=5)],
        [dict(use_id='material-use:2',eligible_materials=[0,1])],equivalent_uses=[('material-use:2',0)])
    return original,multi,theme.fit(multi,'material-use:0','material-use:2')


class ReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original,cls.t4,cls.t5=build()

    def test_exact_individual_and_composed_zero_boundaries(self):
        self.assertEqual(theme.expand(self.t5),self.t4)
        self.assertEqual(theme.reconstruct(self.t5,{'variation':0}),single.reconstruct(self.original,{'variation':0}))
        self.assertEqual(self.t4['choices'][0],{k:self.original[k]for k in('allocation','constraints')})
        self.assertNotIn('material_ref',sections._owner(self.t5['lower_tier'],'material-use:2')['allocation'])
        self.assertEqual(len(self.t4['lower_tier']['materials']),2)
        self.assertEqual(len(self.t4['lower_tier']['slots']),3)
        self.assertEqual(self.t4['lower_tier']['materials'],self.original['lower_tier']['materials'])

    def test_independent_and_recalled_changes_differ_after_reload(self):
        independent=theme.change_source(json.loads(json.dumps(self.t5)),1)
        recalled=theme.candidate(json.loads(json.dumps(independent)),'recall')
        original=project_documents(theme.reconstruct(self.t5,{'variation':0}))
        a=project_documents(theme.reconstruct(independent,{'variation':0}))
        b=project_documents(theme.reconstruct(recalled,{'variation':0}))
        for part in (2,3):
            name=f'track-{part}.json'
            self.assertNotEqual(a[name]['measures'][0],original[name]['measures'][0])
            self.assertEqual(a[name]['measures'][4],original[name]['measures'][4])
            self.assertEqual(b[name]['measures'][4],b[name]['measures'][0])
            for i in(1,2,3,5,6,7,8):self.assertEqual(b[name]['measures'][i],original[name]['measures'][i])
        for name in('metadata.json','track-0.json','track-1.json','track-4.json'):self.assertEqual(b[name],original[name])
        self.assertEqual(recalled['lower_tier']['lower_tier']['observations'],self.t5['lower_tier']['lower_tier']['observations'])

    def test_saved_live_reference_changes_again_without_losing_relationship(self):
        linked=theme.candidate(self.t5,'recall')
        first=theme.change_source(json.loads(json.dumps(linked)),1)
        second=theme.change_source(json.loads(json.dumps(first)),0)
        self.assertEqual(second['relationship'],linked['relationship'])
        self.assertEqual(theme.reconstruct(second,{'variation':0}),theme.reconstruct(linked,{'variation':0}))
        original_lower=self.t5['lower_tier']['lower_tier']['lower_tier']['musical_relationships']
        self.assertEqual(second['lower_tier']['lower_tier']['lower_tier']['musical_relationships'],original_lower)

    def test_release_semantics_distinguish_relationship_from_current_audio(self):
        flags=[];changed=[]
        for level in(0,50,100):
            for seed in (0,1,4):
                result,r=theme.intervene(self.t5,dict(context_policy=theme.POLICY,mode='recall',seed=seed,**{'return':level}))
                if level==0:self.assertEqual(result,self.t5)
                if level==100:self.assertTrue(r['released'])
                self.assertEqual(r['changed'],result!=self.t5)
                self.assertFalse(r['material_changed']) # identical first/return material, different future dependency
                if level==50:flags.append(r['released']);changed.append(r['changed'])
        self.assertIn(False,flags);self.assertIn(True,flags);self.assertIn(True,changed)

    def test_unsupported_and_conflicting_updates_are_atomic(self):
        frozen=digest(self.t5)
        for action in(lambda:theme.change_source(self.t5,999),lambda:theme.candidate(self.t5,'guess'),
                      lambda:sections.extend(self.t4,[dict(parts=[2],first_bar=1,last_bar=1)],[])):
            with self.assertRaises(ValueError):action()
            self.assertEqual(digest(self.t5),frozen)
        for kind in('raw-backup','competing-owner','self-return','earlier-return','unknown-choice'):
            bad=deepcopy(self.t5)
            if kind=='raw-backup':bad['relationship']['notes']=[55,57]
            elif kind=='competing-owner':sections._owner(bad['lower_tier'],'material-use:2')['allocation']['material_ref']=0
            elif kind=='self-return':bad['relationship']['source_use']='material-use:2'
            elif kind=='earlier-return':bad['lower_tier']['lower_tier']['slots'][2]['start_q']='0'
            else:bad['relationship']['independent_material_ref']=999
            with self.subTest(kind=kind),self.assertRaises(ValueError):theme.reconstruct(bad,{'variation':0})

    def test_wrong_identity_cannot_be_declared_equivalent(self):
        frozen=digest(self.original)
        with self.assertRaisesRegex(ValueError,'equivalent definition'):
            sections.extend(self.original,[dict(parts=[2,3],first_bar=5,last_bar=5)],
                [dict(use_id='material-use:2',eligible_materials=[0,1])],equivalent_uses=[('material-use:2',1)])
        self.assertEqual(digest(self.original),frozen)

    def test_impossible_nonzero_recall_refuses_before_random_selection(self):
        limited=deepcopy(self.t5)
        sections._owner(limited['lower_tier'],'material-use:2')['constraints']['eligible_materials']=[0]
        independent=theme.change_source(limited,1);frozen=digest(independent)
        for level in(50,100):
            for seed in(0,2,4):
                with self.subTest(level=level,seed=seed),self.assertRaises(ValueError):
                    theme.intervene(independent,dict(context_policy=theme.POLICY,mode='recall',seed=seed,**{'return':level}))
                self.assertEqual(digest(independent),frozen)
        locked,_=theme.intervene(independent,dict(context_policy=theme.POLICY,mode='recall',seed=2,**{'return':0}))
        self.assertEqual(locked,independent)


if __name__=='__main__':unittest.main()
