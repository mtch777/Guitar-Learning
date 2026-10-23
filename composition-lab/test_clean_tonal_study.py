import unittest
from run_clean_tonal_study import training_join
from ordered_tonal_factor import fit


class CleanTrainingTests(unittest.TestCase):
    def test_unlabeled_predecessor_kept_for_emission_but_no_supervised_bridge(self):
        source=[dict(id=i,mask=145 if i<2 else 137,previous_mask=None if i==0 else 145,sequence=0,start_q=str(i),end_q=str(i+1)) for i in range(3)]
        teachers=[dict(s,target=None if i==1 else dict(state=0 if i==0 else 12),quarantine_reasons=['NO_LABEL'] if i==1 else []) for i,s in enumerate(source)]
        piece=dict(piece='x',work='w',split='train',rows=teachers)
        joined=training_join(piece,source);model=fit([joined],'ordered')
        self.assertEqual(joined['rows'][2]['previous_mask'],145)
        self.assertEqual(joined['rows'][2]['sequence'],0)
        self.assertEqual(model['training_cells'],2)
        self.assertEqual(model['key_transitions'],[{},{}])
        self.assertEqual(model['contexts'][1]['145']['137'],1)
        self.assertEqual(model['start_modes'],{'0':1,'1':1})

    def test_teacher_cannot_rewrite_source_clock_pitch_or_add_observation(self):
        source=[dict(id=0,mask=145,previous_mask=None,sequence=0,start_q='0',end_q='1')]
        piece=dict(piece='x',work='w',split='train',rows=[dict(source[0],target=dict(state=0),quarantine_reasons=[])])
        piece['rows'][0]['mask']=137
        with self.assertRaises(ValueError):training_join(piece,source)
        piece['rows'][0]['mask']=145;piece['rows'].append(dict(piece['rows'][0],id=1))
        with self.assertRaises(ValueError):training_join(piece,source)


if __name__=='__main__':unittest.main()
