import copy
import json
import unittest
import context_spacing_study as study


def row(i,bar,spacing=('0','7'),duration='1'):
    context=dict(part_id=1,instrument=25,member_pitch_classes=['0','7'],duration_q=duration,
        meter={'beats':4,'beat_unit_q':'1'},metrical_offset_q='0',overlaps=[],execution_uncertainty=[])
    return dict(id='event:'+str(i),part_id=1,bar=bar,onset_q=str((bar-1)*4),member_refs=['a','b'],refusal_reasons=[],
        family_context_key=json.dumps(context),family_full_context_key=json.dumps([context,[[0],[7]]]),
        realization=dict(anchor='48',intervals=list(spacing)),duration_q=duration,
        source_geometry={'members':[[48,5,8],[55,3,5]]},fixed_output_strings=[5,3])


class ContextStudyTests(unittest.TestCase):
    def test_spacing_physical_target_mutation_cannot_change_features_or_split(self):
        catalog={'x':{'units':[row(i,b)for i,b in enumerate((2,3,10,11,18,19))]}}
        before,labels=study.prepare(catalog);changed=copy.deepcopy(catalog)
        for r in changed['x']['units']:
            r['realization']['intervals']=['0','19'];r['fixed_output_strings']=[2,1];r['source_geometry']={}
        after,new=study.prepare(changed)
        self.assertEqual(before,after);self.assertNotEqual(labels,new)

    def test_near_repetition_components_never_cross_folds(self):
        units=[row(i,b,duration=str(i+1))for i,b in enumerate((2,3,10,11,18,19))]
        data,_=study.prepare({'x':{'units':units}})
        self.assertEqual(study.audit_split(data)['status'],'PASS')
        self.assertEqual(len({r['group']for r in data['rows']}),1)
        altered=copy.deepcopy(data);altered['rows'][-1]['fold']=2
        self.assertEqual(study.audit_split(altered)['status'],'FAIL')

    def test_boundary_exclusions_and_refusals_counted(self):
        units=[row(i,b)for i,b in enumerate((1,2,8,9,10))];units[-1]['refusal_reasons']=['LOCKED']
        data,_=study.prepare({'x':{'units':units}});c=data['counts']['x']
        self.assertEqual(c['total'],5);self.assertEqual(c['refused'],1)
        self.assertEqual(c['eligible'],c['retained']+c['boundary_excluded'])

    def test_unseen_labels_do_not_enter_train_vocabulary(self):
        train=[dict(id='a',family='f',features={k:'a'for k in study.FEATURES})]
        target=dict(id='b',family='f',features={k:'b'for k in study.FEATURES})
        p=study.distribution(train,target,{'a':'known','b':'SECRET'},True)
        self.assertEqual(set(p),{'known',None});self.assertAlmostEqual(sum(p.values()),1)

    def test_no_independent_support_is_not_a_pass(self):
        data,labels=study.prepare({'x':{'units':[row(i,b,spacing=('0',str(7+12*(i%2))))for i,b in enumerate((2,3,10,11))]}})
        self.assertEqual(study.evaluate(data,labels)['status'],'INCONCLUSIVE_INDEPENDENT_SUPPORT')

    def test_long_held_other_part_note_unites_distant_windows(self):
        units=[row(i,b)for i,b in enumerate((2,3,10,11))]
        # Distinguish context enough that recurrence grouping alone cannot join.
        for i,r in enumerate(units):
            c=json.loads(r['family_context_key']);c['duration_q']=str(i+1);c['metrical_offset_q']=str(i)
            c['overlaps']=[[2,0,'0','1',str(i)]];r['family_context_key']=json.dumps(c)
            r['family_full_context_key']=json.dumps([c,[[i],[i+1]]])
        events={'x':[dict(id='long',onset_q='0',duration_q='100')]}
        data,_=study.prepare({'x':{'units':units}},events)
        self.assertEqual(len({r['group']for r in data['rows']}),1)
        self.assertTrue(all('x/long'in r['dependency_refs']for r in data['rows']))
        changed=copy.deepcopy(data);changed['rows'][-1]['fold']=1
        self.assertIn('SOURCE_DEPENDENCY_CROSSES_FOLDS',study.audit_split(changed)['issues'])

    def test_laplace_posterior_and_unseen_family(self):
        train=[dict(id='a',family='f',features={k:'a'for k in study.FEATURES})]
        target=dict(id='b',family='f',features={k:'a'for k in study.FEATURES})
        p=study.distribution(train,target,{'a':'A','b':'B'},False)
        self.assertAlmostEqual(p['A'],2/3);self.assertAlmostEqual(p[None],1/3)
        q=study.distribution(train,target,{'a':'A','b':'B'},True)
        odds=2*(4/3)**len(study.FEATURES)
        self.assertAlmostEqual(q['A'],odds/(1+odds))
        target['family']='unseen'
        self.assertEqual(study.distribution(train,target,{'a':'A'},True),{None:1.0})


if __name__=='__main__':unittest.main()
