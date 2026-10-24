"""Independent retained-detector/source-fact dependency oracle checks."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from source_fact_tier1 import extract_documents
from execution_dependencies import build
from check_execution_dependencies import expected,check
from test_execution_dependencies import documents,n


class IndependentExecutionOracleTests(unittest.TestCase):
    def test_agrees_across_positive_unresolved_grace_roll_and_timing_scopes(self):
        examples=[documents([n(0,hp=True),n(2),n(4),n(5)]),documents([n(0,hp=True),n(0),n(4),n(5)]),
            documents([n(2,slide='belowdownwards'),n(4),None,None]),documents([n(2,slide='shift'),n(2,tie=True),n(4),None]),
            documents([n(2,slide='shift',hp=True),n(4),None,None],{0:dict(graceNote='beforeBeat')}),
            documents([n(0),n(2),None,None],{0:dict(arpeggio=dict(direction='down',duration=57,shift=100),letRing=True),1:dict(brushStroke={},letRing=False)})]
        overflow=documents([n(0,slide='shift',hp=True),n(2)]);overflow['track-0.json']['measures'][0]['voices'][0]['beats'][0]['duration']=[1,1];examples.append(overflow)
        for docs in examples:
            lower=extract_documents(docs);before=deepcopy(lower);graph=build(lower)
            self.assertEqual(expected(lower),graph)
            self.assertEqual(check(lower,graph)['status'],'PASS_INDEPENDENT_EXECUTION_DEPENDENCIES')
            self.assertEqual(lower,before)

    def test_oracle_does_not_call_producer_or_mapping_helpers(self):
        lower=extract_documents(documents([n(0,hp=True),n(2),n(4),n(5)]));truth=expected(lower)
        with patch('execution_dependencies.build',side_effect=AssertionError('Producer called')),patch('execution_dependencies._value',side_effect=AssertionError('Producer helper called')):
            self.assertEqual(expected(lower),truth)

    def test_missing_fabricated_duplicate_and_false_endpoint_data_fail(self):
        lower=extract_documents(documents([n(2,slide='belowdownwards'),n(4),None,None],{1:dict(letRing=True)}));graph=build(lower)
        variants=[]
        g=deepcopy(graph);g['edges'].pop();variants.append(g)
        g=deepcopy(graph);g['edges'].append(g['edges'][0]);variants.append(g)
        g=deepcopy(graph);g['pinned_members'].pop();variants.append(g)
        g=deepcopy(graph);g['pinned_members'].append('event:86:0:99:0:0:0');variants.append(g)
        g=deepcopy(graph);g['signature']={};variants.append(g)
        g=deepcopy(graph);g['uncertainty']=[];variants.append(g)
        g=deepcopy(graph);g['edges'][0]['semantics']['origin']='event:86:0:1:0:1:0';variants.append(g)
        g=deepcopy(graph);g['edges'][0]['status']='verified_performed_slide';variants.append(g)
        g=deepcopy(graph);g['raw_notes']=[60,64,67];variants.append(g)
        for g in variants:self.assertEqual(check(lower,g)['status'],'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')

    def test_source_changes_and_inactive_declaration_omissions_cannot_hide(self):
        docs=documents([n(0,hp=True),n(2),n(4),n(5)],{2:dict(letRing=False)});lower=extract_documents(docs);graph=build(lower)
        changed=deepcopy(graph);changed['signature']['declarations']=[]
        self.assertEqual(check(lower,changed)['status'],'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')
        docs['track-0.json']['measures'][0]['voices'][0]['beats'][1]['notes'][0]['fret']=3
        self.assertEqual(check(extract_documents(docs),graph)['status'],'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')
        self.assertEqual(graph['signature']['parts'][0]['hopo_pairs'][0]['fret_distance'],2)


if __name__=='__main__':unittest.main()
