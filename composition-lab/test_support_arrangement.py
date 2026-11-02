"""Different complete inventories, two simultaneous uses, and live earlier edits."""
from copy import deepcopy
import json
import unittest

import test_musical_support_material as fixture
import test_musical_cell_development as cell_fixture
import musical_cell_development as cell
import musical_support_material as material
import support_material_uses as uses
import support_arrangement as arrangement
from source_fact_tier1 import project_documents
from source_observation_evidence import digest


def build(*,hammer=False):
    docs,_,_,_=fixture.authored()
    for p in (2,3):
        for b,level in ((0,'f'),(1,'mf')):docs[f'track-{p}.json']['measures'][b]['voices'][0]['beats'][0]['velocity']=level
    if hammer:docs['track-2.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0]['hp']=True
    _,_,_,t3=cell_fixture.build(docs=docs)
    # A prior creative phase change already exists before this capability.
    t3,_=cell.intervene(t3,cell_fixture.controls(seed=4))
    specs=[dict(parts=[2,3,4],first_bar=b,last_bar=b)for b in (1,2)]
    owned=material.lift_t3(t3,specs);timed=uses.lift(owned)
    return t3,timed,arrangement.lift(timed,'material-use:0',[0,1])


class ArrangementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cell,cls.t3,cls.t4=build()

    def test_zero_individual_and_composed_boundaries(self):
        self.assertEqual(arrangement.expand(self.t4),self.t3)
        self.assertEqual(uses.expand(self.t3),cell.expand(self.cell))
        self.assertEqual(arrangement.reconstruct(self.t4,{'variation':0}),cell.reconstruct(self.cell,{'variation':0}))

    def test_two_uses_distinct_members_and_single_definition(self):
        changed=arrangement.candidate(self.t4,1);restored=json.loads(json.dumps(changed))
        current,lower,ledger=uses.realize_pair(arrangement.expand(restored))
        self.assertEqual(len({r['identity']for r in ledger}),len(ledger))
        self.assertEqual(len({r['current_address']for r in ledger}),len(ledger))
        self.assertLess(len({r['source_occurrence']for r in ledger}),len(ledger))
        self.assertEqual(restored['lower_tier']['materials'],self.t4['lower_tier']['materials'])
        before=project_documents(arrangement.reconstruct(self.t4,{'variation':0}));expected=deepcopy(before)
        for p in (2,3,4):
            beats=deepcopy(before[f'track-{p}.json']['measures'][1]['voices'][0]['beats'])
            if p!=4:
                beats[0]['velocity']='f'
                for b in beats:
                    if 'velocity'in b:b['velocity']='f'
            expected[f'track-{p}.json']['measures'][0]['voices'][0]['beats']=beats
        self.assertEqual(project_documents(lower),expected)
        self.assertEqual(current['relationship'],self.cell['relationship'])
        self.assertEqual(current['observations'],self.cell['observations'])

    def test_one_use_expression_does_not_alias_other_use(self):
        t3=arrangement.expand(arrangement.candidate(self.t4,1))
        before=project_documents(uses.reconstruct(t3,{'variation':0}))
        changed=deepcopy(t3);changed['uses'][0]['expression'][0]['level']='p'
        after=project_documents(uses.reconstruct(json.loads(json.dumps(changed)),{'variation':0}))
        self.assertEqual(before['track-2.json']['measures'][1:],after['track-2.json']['measures'][1:])
        self.assertEqual(before['track-3.json'],after['track-3.json'])
        self.assertEqual(before['track-4.json'],after['track-4.json'])
        self.assertEqual(changed['materials'],t3['materials'])

    def test_saved_successive_allocation_and_current_zero(self):
        first=arrangement.candidate(self.t4,1);saved=json.loads(json.dumps(first))
        back=arrangement.candidate(saved,0)
        self.assertEqual(arrangement.reconstruct(back,{'variation':0}),arrangement.reconstruct(self.t4,{'variation':0}))
        self.assertEqual(arrangement.expand(saved)['uses'][0]['material_ref'],1)
        self.assertEqual(saved['lower_tier'],self.t4['lower_tier'])

    def test_zero_fifty_hundred_and_atomic_refusal(self):
        frozen=digest(self.t4);flags=[]
        for level,seed in ((0,1),(50,0),(50,1),(100,0),(100,1)):
            result,report=arrangement.intervene(self.t4,dict(context_policy=arrangement.POLICY,arrangement=level,material_ref=1,seed=seed))
            self.assertEqual(report['changed'],result!=self.t4)
            if level==0:self.assertEqual(result,self.t4)
            if level==100:self.assertTrue(report['released'])
            flags.append(report['released'])
        self.assertIn(False,flags);self.assertIn(True,flags)
        with self.assertRaises(ValueError):arrangement.candidate(self.t4,7)
        self.assertEqual(digest(self.t4),frozen)

    def test_crossing_scope_overlap_and_wrong_reference_refuse(self):
        for kind in ('overlap','wrong-clock','hidden','duplicate-use'):
            bad=deepcopy(self.t3)
            if kind=='overlap':bad['slots'][1]=deepcopy(bad['slots'][0])
            elif kind=='wrong-clock':bad['slots'][0]['start_q']='1/2'
            elif kind=='hidden':bad['uses'][0]['notes']=[1,2,3]
            else:bad['uses'][1]['id']=bad['uses'][0]['id']
            with self.subTest(kind=kind),self.assertRaises(ValueError):uses.reconstruct(bad,{'variation':0})

    def test_saved_inverse_enforces_expression_and_closed_inactive_vocabulary(self):
        changed=arrangement.candidate(self.t4,1)
        for kind in ('expression','origin','inactive','constraint'):
            bad=deepcopy(changed)
            if kind=='expression':bad['allocation']['expression'][0]['level']='p'
            elif kind=='origin':bad['constraints']['lower_origin']={'hidden_original':[1,2,3]}
            elif kind=='inactive':bad['lower_tier']['materials'][0]['hidden_original']={'facts':[1,2,3]}
            else:bad['constraints']['target_expression'][0]['notes']=[1,2,3]
            with self.subTest(kind=kind),self.assertRaises(ValueError):arrangement.reconstruct(bad,{'variation':0})

    def test_mapped_internal_execution_is_checked_at_new_use(self):
        _,t3,_=build(hammer=True)
        # Both active uses now use the internally linked first material.
        t3['uses'][1]['material_ref']=0
        uses.reconstruct(t3,{'variation':0})
        t3['materials'][0]['pitch_paths'][0]['steps'][0]='-2'
        with self.assertRaisesRegex(ValueError,'EXECUTION_CHANGED'):uses.reconstruct(t3,{'variation':0})


if __name__=='__main__':unittest.main()
