"""Public execution checks; private corpus contracts are verified before packaging."""
from copy import deepcopy
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

PUBLIC=Path(__file__).resolve().parents[1]/'public/riff-builder'
spec=importlib.util.spec_from_file_location('browser_pattern_engine',PUBLIC/'pattern_engine.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
PACK=json.loads(gzip.decompress((PUBLIC/'pattern-pack.json.gz').read_bytes()))

def request(sections=None):
    return {'artists':['Invent Animate'],'mode':'Aeolian','tempo':142,'seed':1,
        'sections':sections or [{'style':'arpeggio','focus':'single','length_q':'8','seed':1}]}

class PatternBrowserTests(unittest.TestCase):
    def test_pack_receipt_and_no_source_score_payload(self):
        receipt=json.loads((PUBLIC/'pattern-manifest.json').read_text())
        self.assertEqual(hashlib.sha256((PUBLIC/'pattern_engine.py').read_bytes()).hexdigest(),receipt['engine_sha256'])
        self.assertEqual(hashlib.sha256(gzip.decompress((PUBLIC/'pattern-pack.json.gz').read_bytes())).hexdigest(),receipt['pattern_pack_sha256'])
        self.assertEqual(len(PACK['templates']),receipt['templates'])
        for value in PACK['templates'].values():
            self.assertLessEqual(F(value['duration_q']),8)
            for event in value['events']:
                for note in event['members']:
                    self.assertNotIn('source_pitch',note)
                    self.assertNotIn('source_fret',note)
                    self.assertNotIn('source_string',note)

    def test_actual_contrasting_structures_and_mode(self):
        for style,focus in [('arpeggio','single'),('arpeggio','interval'),('other','triad'),('pedal','single')]:
            with self.subTest(style=style,focus=focus):
                result=engine.generate(request([{'style':style,'focus':focus,'length_q':'8','seed':1}]),PACK)
                self.assertEqual(result['status'],'generated')
                self.assertEqual(result['sections'][0]['actual_focus'],focus)
                self.assertTrue(any(F(e['onset_q']).denominator>1 for e in result['events']))
                for event in result['events']:
                    strings=[]
                    for n in event['members']:
                        self.assertEqual(n['pitch'],engine.TUNING[n['string_number']-1]+n['fret'])
                        self.assertIn((n['pitch']-4)%12,engine.MODES['Aeolian'])
                        strings.append(n['string_number'])
                    self.assertEqual(len(strings),len(set(strings)))

    def test_repeatability_and_independent_section_regeneration(self):
        r=request([{'style':'arpeggio','focus':'single','length_q':'8','seed':1},
                   {'style':'pedal','focus':'single','length_q':'8','seed':1}])
        before=deepcopy(PACK)
        a=engine.generate(r,PACK);self.assertEqual(a['status'],'generated')
        self.assertEqual(a,engine.generate(r,PACK))
        r['sections'][1]['seed']=2;b=engine.generate(r,PACK)
        self.assertEqual(b['status'],'generated')
        self.assertEqual([e for e in a['events'] if e['section_index']==0],[e for e in b['events'] if e['section_index']==0])
        self.assertNotEqual([e for e in a['events'] if e['section_index']==1],[e for e in b['events'] if e['section_index']==1])
        self.assertEqual(PACK,before)

    def test_missing_labels_are_visible_no_substituted_artist_or_style(self):
        r=request([{'style':'melodic','focus':'single','length_q':'8'}])
        result=engine.generate(r,PACK)
        self.assertEqual(result['status'],'no_choice')
        self.assertEqual(result['events'],[])
        self.assertEqual(result['sections'][0]['candidate_counts']['templates'],0)

    def test_global_inputs_and_limits_are_enforced(self):
        for key,value in [('artists',['Other band']),('mode','Locrian'),('tempo',True),('tempo',201),('seed',1.5),('sections',[])]:
            r=request();r[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError): engine.generate(r,PACK)

if __name__=='__main__': unittest.main()
