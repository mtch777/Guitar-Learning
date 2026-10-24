"""Arpeggio declaration ownership: exact source facts, no execution inference."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents
from technique_observation_relations import lift,realize,scalar_relation
from connected_tier2 import analyze,strip_lower,reconstruct
from check_technique_connections import check


ABSENT=object()


def documents(value=ABSENT):
    beat=dict(duration=[1,1],notes=[dict(string=5,fret=0),dict(string=4,fret=2),dict(string=3,fret=2)])
    if value is not ABSENT:beat['arpeggio']=value
    return {'metadata.json':dict(songId=83,revisionId=2,artist='Fixture',title='Source declaration',tracks=[dict(name='Guitar',instrumentId=25)]),
            'track-0.json':dict(songId=83,revisionId=2,partId=0,instrumentId=25,tuning=[64,59,55,50,45,40],frets=24,
                measures=[dict(signature=[4,4],voices=[dict(beats=[beat])])])}


class SourceArpeggioOwnershipTests(unittest.TestCase):
    def test_registered_object_exact_presence_and_unit_one(self):
        for value in ({'direction':'down','duration':57,'shift':100},{'shift':0,'direction':'up','duration':-1},{},{'direction':'uninterpreted'}):
            docs=documents(value);lower=extract_documents(docs);upper=analyze(lower)
            self.assertFalse(upper['unsupported'])
            self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)
            groups=[g for g in upper['owned_parameters']['technique_declarations']['groups']if g['field']=='arpeggio']
            self.assertEqual(len(groups),1);self.assertEqual(groups[0]['scope'],'beat')
            self.assertTrue(all(p['unit']=='1'for p in groups[0]['parameters']))
            self.assertEqual(check(docs,upper)['status'],'PASS_SOURCE_BACKED_RELATIONSHIPS')
            # Declaration ownership must not invent rolled per-note timing.
            self.assertEqual([m['duration_q']for g in upper['musical_relationships']['coattacks']for m in g['members']],['4']*3)
            self.assertEqual({g['onset_q']for g in upper['musical_relationships']['coattacks']},{'0'})

    def test_absence_does_not_create_empty_declaration(self):
        lower=extract_documents(documents());upper=analyze(lower)
        self.assertFalse(any(g['field']=='arpeggio'for g in upper['owned_parameters']['technique_declarations']['groups']))
        self.assertEqual(reconstruct(strip_lower(upper),dict(variation=0)),lower)

    def test_unknown_shapes_types_and_hidden_payload_remain_unsupported(self):
        for value in (None,False,1,'down',[],{'duration':True},{'duration':1.5},{'direction':1},{'shift':None},{'notes':[60,64,67]},{'direction':{'hidden':'down'}}):
            model=lift(extract_documents(documents(value)))
            self.assertFalse(any(g['field']=='arpeggio'for g in model['groups']),value)
            self.assertTrue(model['unsupported'],value)
            with self.assertRaises(ValueError):reconstruct(strip_lower(analyze(extract_documents(documents(value)))),dict(variation=0))

    def test_inverse_rejects_forged_scalar_and_unknown_child_shapes(self):
        original=lift(extract_documents(documents(dict(direction='down',duration=57,shift=100))))
        for value in ({'duration':True},{'direction':'down','notes':[60,64,67]}):
            facts=extract_documents(documents(value))['facts'];model=deepcopy(original);g=model['groups'][0];root=g['source_fact_ref']
            rows=[r for r in facts if r['id']==root or r['id'].startswith(root+'/')]
            g['structure']=[{k:v for k,v in r.items()if k!='value'}for r in rows]
            g['parameters']=[dict(fact_ref=r['id'],unit='1',parameter=scalar_relation(r['type'],source=r['value']))for r in rows if 'value'in r]
            with self.assertRaises(ValueError):realize(model)
        model=deepcopy(original);model['groups'][0]['parameters'][0]['unit']='60'
        with self.assertRaises(ValueError):realize(model)

    def test_independent_raw_checker_catches_omission_and_changed_declaration(self):
        docs=documents(dict(direction='down',duration=57,shift=100));upper=analyze(extract_documents(docs))
        for mutation in ('omit','duplicate','direction','duration'):
            changed=deepcopy(upper);groups=changed['owned_parameters']['technique_declarations']['groups']
            index=next(i for i,g in enumerate(groups)if g['field']=='arpeggio')
            if mutation=='omit':groups.pop(index)
            elif mutation=='duplicate':groups.append(deepcopy(groups[index]))
            else:
                p=next(p for p in groups[index]['parameters']if p['fact_ref'].endswith('/'+mutation))
                p['parameter']=dict(symbol='up')if mutation=='direction'else dict(normalized='58',negative_zero=False)
            self.assertEqual(check(docs,changed)['status'],'FAIL',mutation)

    def test_actual_stripped_worker_reconstructs_declaration(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        lower=extract_documents(documents(dict(direction='down',duration=57,shift=100)));upper=strip_lower(analyze(lower));code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:
            report=execute(code,upper,dict(variation=0),lower,Path(temp)/'worker',timeout=30)
        self.assertEqual(report['status'],'PASS',report)


if __name__=='__main__':unittest.main()
