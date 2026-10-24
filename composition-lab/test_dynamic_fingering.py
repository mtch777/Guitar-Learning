"""Dynamic tuning lookup: string is owned choice, fret is SAME pitch equation."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from source_fact_tier1 import extract_documents,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct


REF='track-0.json#/measures/0/voices/0/beats/0/notes/0/string'


def documents():
    def measure(string,fret):return dict(signature=[4,4],voices=[dict(beats=[dict(duration=[1,1],notes=[dict(string=string,fret=fret)])])])
    return {'metadata.json':dict(songId=87,revisionId=1,artist='Fixture',title='Fingering lookup',tracks=[dict(name='Guitar',instrumentId=25)]),
        'track-0.json':dict(songId=87,revisionId=1,partId=0,instrumentId=25,capo=2,tuning=[64,59,55,50,45,40],frets=24,measures=[measure(0,5),measure(1,10)])}


def choice(upper):return next(r for r in upper['owned_parameters']['source_choices']if r['fact_ref']==REF)


def physical(upper):return next(r for r in upper['owned_parameters']['physical_positions']if r['string_ref']==REF)


class DynamicFingeringTests(unittest.TestCase):
    def fixture(self):
        lower=extract_documents(documents());return lower,strip_lower(analyze(lower))

    def test_owned_string_selects_tuning_array_without_manual_fret_patch(self):
        lower,upper=self.fixture();self.assertEqual(physical(upper)['tuning_array_ref'],'track-0.json#/tuning');self.assertNotIn('tuning_ref',physical(upper))
        self.assertEqual(reconstruct(upper,dict(variation=0)),lower)
        changed=deepcopy(upper);choice(changed)['parameter']=dict(normalized='1',negative_zero=False)
        self.assertEqual(changed['musical_relationships'],upper['musical_relationships'])
        self.assertEqual(changed['owned_parameters']['physical_positions'],upper['owned_parameters']['physical_positions'])
        actual=reconstruct(changed,dict(variation=0));docs=project_documents(actual)
        self.assertEqual(docs['track-0.json']['measures'][0]['voices'][0]['beats'][0]['notes'][0],dict(string=1,fret=10))
        old={r['id']:r for r in lower['facts']};new={r['id']:r for r in actual['facts']}
        self.assertEqual({r for r in old if old[r]!=new[r]},{REF,REF[:-6]+'fret'})
        self.assertEqual(59+2+10,64+2+5)

    def test_legacy_exact_index_is_readable_but_not_silently_retargeted(self):
        lower,upper=self.fixture();legacy=deepcopy(upper)
        for p in legacy['owned_parameters']['physical_positions']:
            value=next(r for r in legacy['owned_parameters']['source_choices']if r['fact_ref']==p['string_ref'])['parameter']['normalized']
            p['tuning_ref']=p.pop('tuning_array_ref')+'/'+value
        self.assertEqual(reconstruct(legacy,dict(variation=0)),lower)
        choice(legacy)['parameter']=dict(normalized='1',negative_zero=False)
        with self.assertRaises(ValueError):reconstruct(legacy,dict(variation=0))

    def test_array_reference_must_exist_be_same_part_array_and_unambiguous(self):
        _,upper=self.fixture()
        for ref in ('track-0.json#/tuning/0','metadata.json#/tracks/0/tuning','track-1.json#/tuning','track-0.json#/missing'):
            changed=deepcopy(upper);physical(changed)['tuning_array_ref']=ref
            with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))
        for mutation in ('missing','both'):
            changed=deepcopy(upper)
            if mutation=='missing':physical(changed).pop('tuning_array_ref')
            else:physical(changed)['tuning_ref']='track-0.json#/tuning/0'
            with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))
        changed=deepcopy(upper);physical(changed).pop('string_ref')
        with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))
        changed=deepcopy(upper)
        changed['owned_parameters']['source_choices']=[c for c in changed['owned_parameters']['source_choices']if c['fact_ref']!=REF]
        # Missing ownership may fail at address lookup or owner validation;
        # neither path may silently substitute string zero.
        with self.assertRaises((ValueError,KeyError)):reconstruct(changed,dict(variation=0))

    def test_negative_out_of_range_and_noninteger_strings_are_rejected(self):
        _,upper=self.fixture()
        for value in ('-1','6','999','1/2'):
            changed=deepcopy(upper);choice(changed)['parameter']=dict(normalized=value,negative_zero=False)
            with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))
        changed=deepcopy(upper);next(r for r in changed['source_structure']['facts']if r['id']==REF)['type']='float'
        choice(changed)['parameter']=dict(normalized='1',negative_zero=False)
        with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))
        changed=deepcopy(upper);next(r for r in changed['source_structure']['facts']if r['id']==REF)['type']='boolean';choice(changed)['parameter']=dict(symbol=True)
        with self.assertRaises(ValueError):reconstruct(changed,dict(variation=0))

    def test_actual_isolated_inverse_uses_dynamic_owned_choice(self):
        from run_connected_tier2_qa import bundle
        from qa_isolation_harness import execute
        _,upper=self.fixture();choice(upper)['parameter']=dict(normalized='1',negative_zero=False);expected=reconstruct(upper,dict(variation=0))
        code,_=bundle(Path(__file__).parent)
        with tempfile.TemporaryDirectory()as temp:report=execute(code,upper,dict(variation=0),expected,Path(temp)/'worker',timeout=30)
        self.assertEqual(report['status'],'PASS',report)
        self.assertFalse(report['parent_expected_staged'])


if __name__=='__main__':unittest.main()
