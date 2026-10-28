from copy import deepcopy
from itertools import product
import unittest
from check_fretting_contacts import check,expected,effective,canonical_required

def hand(values,strings=None):return [dict(string=s,fret=f)for s,f in zip(range(len(values))if strings is None else strings,values)]

def report(required,max_digits=4,search_limit=100000):
    e=expected(required,max_digits=max_digits,search_limit=search_limit)
    return dict(schema='fretting-contact-coverage/1',required=canonical_required(required,max_digits,search_limit),
        max_digits=max_digits,search_limit=search_limit,examined=e['examined_subsets'],status=e['status'],
        minimum_contacts=e['minimum_contacts'],covers=e['covers'],human_playability='UNVERIFIED')

class IndependentContactTests(unittest.TestCase):
    def test_known_contact_equations_and_complete_minima(self):
        for values,minimum in [([0,0],0),([2,2],1),([3,3,2],2),([8,5,5,7],3),([2,0,2],2)]:
            required=hand(values);r=report(required);self.assertEqual(r['minimum_contacts'],minimum)
            self.assertEqual(check(required,r)['issues'],[])
        r=report(hand([8,5,5,7]));wanted=[dict(fret=5,first_string=1,last_string=2),dict(fret=7,first_string=3,last_string=3),dict(fret=8,first_string=0,last_string=0)]
        self.assertIn(wanted,r['covers'])

    def test_open_lower_inactive_and_duplicate_obstructions(self):
        bad=[(hand([2,0,2]),[dict(fret=2,first_string=0,last_string=2)]),
             (hand([3,2]),[dict(fret=3,first_string=0,last_string=1)]),
             (hand([2,2],[0,2]),[dict(fret=2,first_string=0,last_string=2)])]
        for required,cover in bad:
            with self.assertRaises(ValueError):effective(required,cover)
        required=hand([2]);contact=dict(fret=2,first_string=0,last_string=0)
        with self.assertRaises(ValueError):effective(required,[contact,contact])

    def test_covers_omissions_extras_minimum_types_and_claims(self):
        required=hand([3,3,2]);good=report(required)
        changes=[lambda r:r['covers'].pop(),lambda r:r['covers'].append(deepcopy(r['covers'][0])),
            lambda r:r.update(minimum_contacts=True),lambda r:r.update(human_playability='VERIFIED'),
            lambda r:r.update(max_digits=True),lambda r:r.update(examined=True),
            lambda r:r.update(search_limit=999),lambda r:r.update(extra_pitch_stream=[60]),
            lambda r:r['covers'][0][0].update(fret=0)]
        for change in changes:
            bad=deepcopy(good);change(bad);self.assertEqual(check(required,bad)['status'],'FAIL')
        bad=deepcopy(good);bad['covers'][0].append(dict(fret=1,first_string=0,last_string=0))
        self.assertEqual(check(required,bad)['status'],'FAIL')

    def test_no_cover_and_resource_refusal_are_distinct(self):
        required=hand([1]*5,[0,2,4,6,8]);r=report(required)
        self.assertEqual(r['status'],'NO_COVER_WITHIN_MODEL');self.assertEqual(check(required,r)['issues'],[])
        required=hand([8,5,5,7]);r=report(required,search_limit=1)
        self.assertEqual(r['status'],'SEARCH_LIMIT');v=check(required,r,search_limit=1)
        self.assertEqual(v['issues'],[]);self.assertFalse(v['complete'])
        r['covers']=[[dict(fret=5,first_string=1,last_string=2)]]
        self.assertEqual(check(required,r,search_limit=1)['status'],'FAIL')
        false=report(hand([0]));false.update(status='SEARCH_LIMIT',minimum_contacts=None,covers=[],examined=100000)
        self.assertEqual(check(hand([0]),false)['status'],'FAIL')

    def test_invalid_typed_input_and_detached_results(self):
        for rows in [[],[dict(string=True,fret=1)],[dict(string=0,fret=1.0)],[dict(string=0,fret=-1)],hand([1,2],[0,0]),[dict(string=0,fret=1,raw='x')]]:
            with self.assertRaises(ValueError):expected(rows)
        for digits,limit in [(True,100),(0,100),(5,100),(4,False),(4,0)]:
            with self.assertRaises(ValueError):expected(hand([1]),max_digits=digits,search_limit=limit)
        r=report(hand([2,2]));r['covers'][0][0]['fret']=99
        self.assertEqual(report(hand([2,2]))['covers'][0][0]['fret'],2)

    def test_exhaustive_small_grid_against_independent_producer(self):
        from fretting_contacts import analyze
        for values in product(range(4),repeat=4):
            required=hand(values);self.assertEqual(check(required,analyze(required))['issues'],[],values)
        for required in (hand([8,5,5,7]),hand([2,2],[0,2]),hand([0,0,0])):
            self.assertEqual(check(required,analyze(required))['issues'],[])

if __name__=='__main__':unittest.main()
