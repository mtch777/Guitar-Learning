from copy import deepcopy
import unittest
from test_voicing_gestures import documents
from source_fact_tier1 import extract_documents
import voicing_gestures as producer
from check_voicing_gesture_discovery import check,expected_units


class DiscoveryOracleTests(unittest.TestCase):
    def test_complete_source_discovery_and_mutation_rejection(self):
        docs=documents();cat=producer.catalog(extract_documents(docs));discovery=cat['discovery']
        self.assertEqual(check(docs,discovery)['status'],'PASS_INDEPENDENT_GESTURE_DISCOVERY')
        for mode in('omit','duplicate','slice','count','overlap'):
            bad=deepcopy(discovery)
            if mode=='omit':bad['links'].pop()
            elif mode=='duplicate':bad['links'].append(deepcopy(bad['links'][0]))
            elif mode=='slice':bad['links'][0]['target_refs'].pop()
            elif mode=='count':bad['matched_pairs']+=1
            else:bad['links'][0]['refusal']='OVERLAPPING_SOURCE_RUNS'
            self.assertEqual(check(docs,bad)['status'],'FAIL_INDEPENDENT_GESTURE_DISCOVERY',mode)

    def test_diagonal_gap_unknown_overlap_resource_and_order(self):
        cat=producer.catalog(extract_documents(documents()));units=cat['base']['units']
        self.assertEqual(expected_units(units),producer.discover(units))
        self.assertEqual(expected_units(list(reversed(units))),producer.discover(units))
        for mode in('gap','unknown','resource'):
            data=deepcopy(units);limit=100000
            if mode=='gap':data[7]['onset_q']=str(int(data[7]['onset_q'])+1)
            elif mode=='unknown':data[5]['refusal_reasons']=['UNKNOWN']
            else:limit=0
            self.assertEqual(expected_units(data,limit),producer.discover(data,max_pairs=limit),mode)


if __name__=='__main__':unittest.main()
