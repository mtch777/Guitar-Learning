"""Key-target semantics, distribution validity, leakage and HMM arithmetic."""
from copy import deepcopy
from fractions import Fraction
import itertools,math,unittest
from importlib.util import find_spec
from tonal_context_observations import normalize_target,relative_tonic,mask,rotate
from ordered_tonal_factor import fit,infer,emission,key_transition,public_observations


def pieces():
    rows=[]
    for i,bits in enumerate([mask([0,4,7]),mask([2,7,11]),mask([0,4,7]),mask([9,0,4])]):
        rows.append(dict(id=i,start_q=str(i),end_q=str(i+1),mask=bits,previous_mask=None if not i else rows[-1]['mask'],sequence=0,target=dict(state=0),quarantine_reasons=[]))
    minor=deepcopy(rows)
    for r in minor:r['target']=dict(state=21)
    return [dict(work='one',piece='one-1',split='train',rows=rows),dict(work='two',piece='two-1',split='train',rows=minor)]


class OrderedTonalFactorTests(unittest.TestCase):
    def test_structural_and_applied_targets_are_not_confused(self):
        a=normalize_target(dict(globalkey='C',localkey='vi',relativeroot='V/V'))
        self.assertEqual((a['tonic_pc'],a['mode']),(9,'minor'))
        self.assertEqual(a['applied_target']['tonic_pc'],11)
        self.assertEqual(relative_tonic('vi/VI',0,False),(6,True))
        with self.assertRaises(ValueError):normalize_target(dict(globalkey='C',localkey='I',alt_label='V'))
        with self.assertRaises(ValueError):normalize_target(dict(globalkey='C',localkey='i',localkey_is_minor='0'))

    def test_probability_domains_normalize_and_inputs_are_unchanged(self):
        data=pieces();before=deepcopy(data);model=fit(data,'ordered')
        self.assertEqual(data,before)
        for state in (0,7,12,21):
            self.assertAlmostEqual(sum(emission(model,b,mask([0,4,7]),state)[0] for b in range(4096)),1)
            self.assertAlmostEqual(sum(key_transition(model,state,right) for right in range(24)),1)
        changed=deepcopy(data);changed[0]['split']='test'
        with self.assertRaises(ValueError):fit(changed,'ordered')

    @unittest.skipUnless(find_spec('numpy'),'Optional research-only NumPy inference runtime')
    def test_forward_backward_matches_independent_exhaustive_paths(self):
        model=fit(pieces(),'ordered');observed=public_observations(pieces()[0]['rows'][:2]);result=infer(model,observed)
        starts=model['start_modes'];total=sum(starts.values());weights=[]
        for left,right in itertools.product(range(24),repeat=2):
            prior=(starts.get(str(left//12),0)+model['tau']/2)/(total+model['tau'])/12
            weight=prior*emission(model,observed[0]['mask'],None,left)[0]*key_transition(model,left,right)*emission(model,observed[1]['mask'],observed[1]['previous_mask'],right)[0]
            weights.append((left,right,weight))
        z=sum(w for _,_,w in weights)
        for position in range(2):
            expected=[sum(w for a,b,w in weights if (a,b)[position]==state)/z for state in range(24)]
            for a,b in zip(expected,result['rows'][position]['posterior']):self.assertAlmostEqual(a,b,places=12)
        self.assertAlmostEqual(math.log(z),result['observation_log_likelihood'])

    @unittest.skipUnless(find_spec('numpy'),'Optional research-only NumPy inference runtime')
    def test_transposition_equivariance_and_target_leak_rejection(self):
        model=fit(pieces(),'ordered');observed=public_observations(pieces()[0]['rows']);before=infer(model,observed)
        shifted=deepcopy(observed)
        for r in shifted:
            r['mask']=rotate(r['mask'],7)
            if r['previous_mask'] is not None:r['previous_mask']=rotate(r['previous_mask'],7)
        after=infer(model,shifted)
        for left,right in zip(before['rows'],after['rows']):
            for state,value in enumerate(left['posterior']):self.assertAlmostEqual(value,right['posterior'][state//12*12+(state%12+5)%12],places=12)
        bad=deepcopy(observed);bad[0]['target']=dict(state=0)
        with self.assertRaises(ValueError):infer(model,bad)

    def test_shuffled_control_keeps_marginals_and_key_transitions(self):
        ordered=fit(pieces(),'ordered');shuffled=fit(pieces(),'shuffled_predecessor')
        for field in ('marginal','mode_totals','key_transitions','start_modes'):self.assertEqual(ordered[field],shuffled[field])


if __name__=='__main__':unittest.main()
