from copy import deepcopy
import unittest
from research_observation_cuts import prepare,canonicalize,restore


def rows():return [dict(id=i,mask=145,previous_mask=None if i==0 else 145,sequence=0,start_q=str(i),end_q=str(i+1)) for i in range(2)]


class ResearchCutsTests(unittest.TestCase):
    def test_artificial_held_support_inverse_exact(self):
        original=rows()[:1];original[0]['end_q']='1/3'
        packet,unsplit=prepare(original,{0:['held-note']});before=deepcopy(packet);c=canonicalize(packet)
        self.assertEqual(c['observations'],original);self.assertEqual(restore(c),packet);self.assertEqual(before,packet);self.assertFalse(unsplit)

    def test_same_pitch_real_reattacks_and_ties_keep_boundaries(self):
        original=rows()
        for support,event in (({0:['note0'],1:['note1']},'source_note_start'),({0:['tie-origin'],1:['tie-destination']},'written_tie_continuation_not_verified_attack')):
            packet,_=prepare(original,support,{1:[event]});c=canonicalize(packet)
            self.assertEqual(c['observations'],original);self.assertEqual(len(c['observations']),2)
            self.assertEqual(c['subdivision_witnesses'][1]['children'][0]['boundary_events'],[event])
            self.assertEqual(restore(c),packet)

    def test_changed_support_real_boundary_gap_and_sequence_refuse(self):
        packet,_=prepare(rows()[:1],{0:['note0']})
        for mutate in ('support','event','boundary','sequence','gap','rest'):
            bad=deepcopy(packet);child=bad['children'][1]
            if mutate=='support':child['support_refs']=['new-note']
            elif mutate=='event':child['boundary_events']=['release']
            elif mutate=='boundary':child['boundary_kind']='original_source_boundary'
            elif mutate=='sequence':child['observation']['sequence']=8;child['observation']['previous_mask']=None
            elif mutate=='gap':child['observation']['start_q']='3/4'
            else:child['observation']['mask']=0
            with self.assertRaises(ValueError):canonicalize(bad)

    def test_rest_stays_unsplit_missing_duplicate_and_raw_witness_refused(self):
        r=rows()[:1];r[0]['mask']=0
        packet,unsplit=prepare(r,{0:[]});self.assertEqual(len(packet['children']),1);self.assertEqual(len(unsplit),1)
        self.assertEqual(canonicalize(packet)['observations'],r)
        with self.assertRaises(ValueError):prepare(rows(),{0:['note']})
        p,_=prepare(rows()[:1],{0:['note']});bad=deepcopy(p);bad['membership'][0]['child_refs']*=2
        with self.assertRaises(ValueError):canonicalize(bad)
        c=canonicalize(p);c['subdivision_witnesses'][0]['children'][0]['raw_pitch']=60
        with self.assertRaises(ValueError):restore(c)


if __name__=='__main__':unittest.main()
