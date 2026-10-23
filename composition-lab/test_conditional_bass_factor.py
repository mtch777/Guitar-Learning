from copy import deepcopy
import math
import unittest
from conditional_bass_factor import fit,probability,update


def feature(ident,pc=0,status='KNOWN'):
    return dict(piece='train',observation_ref=ident,start_q=str(ident),end_q=str(ident+1),status=status,
                lowest_midi=48+pc if status=='KNOWN' else None,lowest_pc=pc if status=='KNOWN' else None,
                lowest_note_refs=[f'n:{ident}'] if status=='KNOWN' else [],active_note_refs=[] if status=='EMPTY' else [f'n:{ident}'],
                unknown_note_refs=[f'n:{ident}'] if status=='UNRESOLVED' else [])


def fixture():
    rows=[dict(id=i,start_q=str(i),end_q=str(i+1),mask=145,target=dict(state=0 if i<4 else 7),quarantine_reasons=[]) for i in range(8)]
    p=dict(piece='train',work='work',split='train',rows=rows,source_observations=[{k:r[k] for k in ('id','mask','start_q','end_q')} for r in rows])
    f={'train':{i:feature(i,0 if i<4 else 4) for i in range(8)}}
    return [p],f


class ConditionalBassTests(unittest.TestCase):
    def test_conditional_probability_normalizes_over_actual_mask_support(self):
        pieces,features=fixture();model,_=fit(pieces,features)
        for state in range(24):
            self.assertAlmostEqual(sum(probability(model,145,b,state,10) for b in (0,4,7)),1)
        prior=[0.]*24;prior[0]=prior[7]=.5
        result=update(model,prior,145,feature(0,0),1)
        self.assertGreater(result['posterior'][0],result['posterior'][7])
        self.assertAlmostEqual(sum(result['posterior']),1)

    def test_empty_and_unresolved_are_neutral_not_guessed_bass(self):
        pieces,features=fixture();model,_=fit(pieces,features);prior=[1/24]*24
        for status,mask in (('EMPTY',0),('UNRESOLVED',145)):
            result=update(model,prior,mask,feature(0,status=status),10)
            self.assertEqual(result['posterior'],prior);self.assertEqual(result['likelihoods'],[1.]*24)

    def test_transposition_equivariance_of_same_conditional_relationship(self):
        from tonal_context_observations import rotate
        pieces,features=fixture();model,_=fit(pieces,features)
        for shift in range(12):
            shifted=rotate(145,(-shift)%12)
            for state in range(24):
                moved=12*(state//12)+(state%12+shift)%12
                self.assertAlmostEqual(probability(model,145,4,state,10),probability(model,shifted,(4+shift)%12,moved,10))

    def test_training_only_and_labels_cannot_enter_query(self):
        pieces,features=fixture();model,_=fit(pieces,features)
        bad=feature(0);bad['target']=dict(state=7)
        with self.assertRaises(ValueError):update(model,[1/24]*24,145,bad,1)
        pieces[0]['split']='test'
        with self.assertRaises(ValueError):fit(pieces,features)
        for value in (True,float('nan'),0):
            with self.assertRaises(ValueError):update(model,[1/24]*24,0,feature(0,status='EMPTY'),value)

    def test_shuffled_control_preserves_actual_mask_membership_and_margins(self):
        pieces,features=fixture();before=deepcopy(features);model,rows=fit(pieces,features,True,17)
        self.assertEqual(features,before)
        self.assertEqual(sorted(r['bass'] for r in rows),[0]*4+[4]*4)
        self.assertTrue(all(r['mask']&(1<<r['bass']) for r in rows))
        self.assertEqual(model['shuffled_control'],True)
        self.assertEqual(len(model['control_donors']),8)

    def test_unlabeled_source_cells_exist_without_becoming_training_targets(self):
        pieces,features=fixture();pieces[0]['source_observations'].append(dict(id=8,mask=145,start_q='8',end_q='9'));features['train'][8]=feature(8,7)
        model,_=fit(pieces,features)
        self.assertEqual(model['availability'],{'KNOWN':8})
        self.assertEqual(len(features['train']),9)
        features['train'][8]['lowest_pc']=2
        with self.assertRaises(ValueError):fit(pieces,features)


if __name__=='__main__':unittest.main()
