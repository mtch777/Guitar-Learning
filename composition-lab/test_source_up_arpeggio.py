"""Observed integer upArpeggio ownership, with execution explicitly unresolved."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from test_source_arpeggio_ownership import documents
from source_fact_tier1 import extract_documents
from connected_tier2 import analyze,strip_lower,reconstruct,owner_kind
from check_technique_connections import check


def source(value=1):
    docs=documents()
    docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['upArpeggio']=value
    return docs


def declaration(upper):
    return next(g for g in upper['owned_parameters']['technique_declarations']['groups'] if g['field']=='upArpeggio')


class UpArpeggioSourceTests(unittest.TestCase):
    def test_observed_integer_has_one_typed_owner_and_exact_zero(self):
        docs=source();lower=extract_documents(docs);upper=analyze(lower)
        self.assertFalse(upper['unsupported'])
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
        group=declaration(upper)
        self.assertEqual(group['scope'],'beat')
        self.assertEqual(group['structure'][0]['type'],'integer')
        self.assertNotIn('value',group['structure'][0])
        self.assertEqual(group['parameters'][0]['unit'],'1')
        self.assertEqual(group['parameters'][0]['parameter'],dict(normalized='1',negative_zero=False))
        self.assertFalse(any(p['fact_ref']==group['source_fact_ref'] for p in upper['owned_parameters']['source_choices']))
        self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
        self.assertEqual({g['onset_q'] for g in upper['musical_relationships']['coattacks']},{'0'})
        self.assertEqual([m['duration_q'] for g in upper['musical_relationships']['coattacks'] for m in g['members']],['4']*3)

    def test_absence_is_absence_unknown_values_and_types_refuse(self):
        absent=analyze(extract_documents(documents()))
        self.assertFalse(any(g['field']=='upArpeggio' for g in absent['owned_parameters']['technique_declarations']['groups']))
        for value in (0,-1,2,57,True,False,None,1.0,'1',{},[],dict(direction='up')):
            with self.subTest(value=value):
                upper=analyze(extract_documents(source(value)))
                self.assertTrue(upper['unsupported'])
                with self.assertRaises(ValueError):reconstruct(strip_lower(upper),dict(variation=0))

    def test_inverse_cannot_change_literal_type_value_or_unit(self):
        upper=strip_lower(analyze(extract_documents(source())))
        for value in ('0','-1','2','1/2'):
            with self.subTest(value=value):
                bad=deepcopy(upper);declaration(bad)['parameters'][0]['parameter']['normalized']=value
                with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))
        bad=deepcopy(upper);group=declaration(bad)
        group['structure'][0]['type']='boolean';group['parameters'][0]['parameter']={'symbol':True}
        with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))
        bad=deepcopy(upper);declaration(bad)['parameters'][0]['unit']='2'
        with self.assertRaises(ValueError):reconstruct(bad,dict(variation=0))

    def test_generic_source_choice_cannot_bypass_technique_owner(self):
        upper=strip_lower(analyze(extract_documents(source())))
        group=declaration(upper)
        upper['owned_parameters']['technique_declarations']['groups'].remove(group)
        shape=deepcopy(group['structure'][0]);upper['source_structure']['facts'].append(shape)
        upper['owned_parameters']['source_choices'].append(dict(fact_ref=shape['id'],owner=owner_kind(shape),parameter=dict(normalized='0',negative_zero=False)))
        with self.assertRaisesRegex(ValueError,'Unregistered source choice'):
            reconstruct(upper,dict(variation=0))

    def test_other_stroke_declarations_remain_separate_and_unchanged(self):
        docs=source();beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
        beat.update(downArpeggio=57,upStroke=0,downStroke=1)
        lower=extract_documents(docs);upper=analyze(lower)
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
        groups={g['field']:g for g in upper['owned_parameters']['technique_declarations']['groups']}
        self.assertEqual({k:groups[k]['parameters'][0]['parameter']['normalized'] for k in ('upArpeggio','downArpeggio','upStroke','downStroke')},dict(upArpeggio='1',downArpeggio='57',upStroke='0',downStroke='1'))

    def test_independent_source_oracle_catches_omission_duplicate_and_tamper(self):
        docs=source();upper=analyze(extract_documents(docs))
        for mutation in ('omit','duplicate','value','field'):
            bad=deepcopy(upper);group=declaration(bad);groups=bad['owned_parameters']['technique_declarations']['groups']
            if mutation=='omit':groups.remove(group)
            elif mutation=='duplicate':groups.append(deepcopy(group))
            elif mutation=='value':group['parameters'][0]['parameter']['normalized']='0'
            else:group['field']='upStroke'
            self.assertEqual(check(docs,bad)['status'],'FAIL',mutation)

    def test_unknown_execution_pins_whole_chord_and_independent_oracle(self):
        from execution_dependencies import build
        from check_execution_dependencies import check as check_graph
        lower=extract_documents(source());graph=build(lower)
        self.assertEqual(check_graph(lower,graph)['status'],'PASS_INDEPENDENT_EXECUTION_DEPENDENCIES')
        edge=next(e for e in graph['edges'] if e['kind']=='upArpeggio')
        self.assertEqual(edge['status'],'declaration_only_unknown_roll_execution')
        self.assertIsNone(edge['semantics']['performed_note_offsets'])
        self.assertEqual(len(edge['member_refs']),3)
        self.assertEqual(set(edge['member_refs']),set(graph['pinned_members']))
        literal=next(d for d in graph['signature']['declarations'] if d['source_fact_ref'].endswith('/upArpeggio'))
        self.assertIs(type(literal['value']),int);self.assertEqual(literal['value'],1)
        for mutation in ('omit','unpin','invent_offsets'):
            bad=deepcopy(graph)
            if mutation=='omit':bad['edges']=[]
            elif mutation=='unpin':bad['pinned_members']=[]
            else:bad['edges'][0]['semantics']['performed_note_offsets']=['0','1','2']
            self.assertEqual(check_graph(lower,bad)['status'],'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES')

    def test_plain_voicing_and_accent_scopes_exclude_marked_beats(self):
        from voicing_register import effect_reasons
        from check_voicing_policy import _source_units
        from check_voicing_context import _nodes
        from local_accents import inventory
        from check_local_accents import inventory as independent_inventory
        docs=source();lower=extract_documents(docs);beat=docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]
        for note in beat['notes']:self.assertIn('BEAT_DEPENDENCY:upArpeggio',effect_reasons(beat,note))
        for unit in _source_units(docs,'joint_source_fingering')[0]:self.assertIn('BEAT_DEPENDENCY:upArpeggio',unit['refusal_reasons'])
        for node in _nodes(lower)[2].values():self.assertIn('BEAT_DEPENDENCY:upArpeggio',node['reasons'])
        for view in (inventory(lower),independent_inventory(lower)):
            for row in view['occurrences']:
                self.assertIn('beat:upArpeggio',row['expression_fields'])
                self.assertIn('OTHER_EXECUTION_OR_ARTICULATION',row['reasons'])
                self.assertIsNone(row['context_key'])

    def test_actual_source_denied_worker_exact_inverse(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(source());upper=strip_lower(analyze(lower));code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory() as temp:
            result=execute(code,upper,dict(variation=0),lower,Path(temp)/'worker',timeout=30)
        self.assertEqual(result['status'],'PASS',result)


if __name__=='__main__':unittest.main()
