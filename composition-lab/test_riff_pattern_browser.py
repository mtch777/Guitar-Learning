"""Public execution checks; private corpus contracts are verified before packaging."""
from copy import deepcopy
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import unittest

PUBLIC=Path(__file__).resolve().parents[1]/'public/riff-builder'
spec=importlib.util.spec_from_file_location('browser_pattern_engine',PUBLIC/'pattern_engine.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
PACK=json.loads(gzip.decompress((PUBLIC/'pattern-pack.json.gz').read_bytes()))

def request(sections=None):
    return {'artists':['Invent Animate'],'mode':'Aeolian','tempo':142,'seed':1,
        'sections':sections or [{'style':'arpeggio','focus':'single','length_q':'8','seed':1}]}

class PatternBrowserTests(unittest.TestCase):
    @staticmethod
    def trace_template(roles, rows):
        return {'id':'trace-fixture','duration_q':'3','source_relative_pitches':roles,
            'links':[], 'events':[{'onset_q':onset,'members':[{
                'role':role,'hold_q':hold,'voice':0,'open_string':opened,
                'marks':{'tapping':tapping}}]} for onset,role,hold,opened,tapping in rows]}

    @staticmethod
    def trace_palette(ident, core=(), extension=(), tapped=()):
        return {'id':ident,'reference':{'riff_id':'fixture-riff','shape_id':ident+'-shape'},
            'contacts':[list(c) for c in (*core,*extension,*tapped)],
            'contact_roles':{'core_contacts':[list(c) for c in core],
                             'extension_contacts':[list(c) for c in extension],
                             'tapped_contacts':[list(c) for c in tapped]}}

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

    def test_exact_selected_window_and_overlapping_source_roles(self):
        t=self.trace_template([0,4],[('0',0,'1/4',None,False),
            ('1/4',1,'1/4',None,False),('1/2',1,'1/4',None,False)])
        palettes=[self.trace_palette('first',core=[(8,5),(8,6),(8,20)]),
                  self.trace_palette('second',core=[(8,8)],extension=[(8,5)])]
        frozen=deepcopy((t,palettes))
        realized,reason=engine._realize(t,palettes,'Aeolian',random.Random(1))
        self.assertIsNotNone(realized,reason);trace=realized['shape_usage']
        self.assertEqual(trace['ordinary_fret_bounds'],[5,8])
        self.assertEqual([(c['string_number'],c['fret']) for c in trace['ordinary_contacts']],[(8,5),(8,8)])
        first=trace['ordinary_contacts'][0]
        self.assertEqual(first['roles'],['core','extension'])
        self.assertEqual({s['shape_id']:s['roles'] for s in first['sources']},
                         {'first-shape':['core'],'second-shape':['extension']})
        self.assertEqual(trace['kind'],'shape_window')
        self.assertEqual(len(trace['reference_shapes']),2)
        self.assertEqual((t,palettes),frozen)

    def test_tapping_is_separate_and_one_contact_is_not_a_shape(self):
        t=self.trace_template([0,4],[('0',0,'3',None,False),
            ('1',1,'1/4',None,True),('2',1,'1/4',None,True)])
        realized,reason=engine._realize(t,[self.trace_palette('tap',core=[(1,2)],tapped=[(2,14)])],
                                       'Dorian',random.Random(1))
        self.assertIsNotNone(realized,reason);trace=realized['shape_usage']
        self.assertEqual(trace['kind'],'single_contact_context')
        self.assertEqual(trace['ordinary_fret_bounds'],[2,2])
        self.assertEqual([c['fret'] for c in trace['tapped_contacts']],[14])
        self.assertEqual(trace['tapped_contacts'][0]['roles'],['tapped'])
        self.assertEqual(trace['used_contacts'][1]['as_tapping'],True)
        self.assertEqual(trace['used_contacts'][1]['as_fretting'],False)

    def test_open_strings_are_context_not_shapes(self):
        t=self.trace_template([0],[('0',0,'1',8,False)])
        realized,reason=engine._realize(t,[self.trace_palette('box',core=[(8,5),(8,8)])],
                                       'Aeolian',random.Random(1))
        self.assertIsNotNone(realized,reason);trace=realized['shape_usage']
        self.assertEqual(trace['kind'],'open_string_only')
        self.assertEqual(trace['used_contacts'],[])
        self.assertEqual(trace['open_strings_played'],[8])
        self.assertTrue(all(c['fret']>0 for c in trace['ordinary_contacts']+trace['tapped_contacts']))

    def test_shape_trace_is_additive_to_frozen_real_generated_music(self):
        # Before-edit canonical full-result hashes: original engine SHA-256
        # 12938194a027d74f19a86cf66a93447f564cb9cb6b6cf5d39120a24ba7b904b1.
        # Strip ONLY the new per-block metadata, leaving every previous field.
        cases=[
            (['Invent Animate'],'Aeolian','arpeggio','single','83198aa3bbf5e2116fa4789a80420f17ab013fe8efd21ec1a6ced3e3b3fa592f'),
            (['Invent Animate'],'Aeolian','arpeggio','interval','183287ae308110ce6e138e316e3c184f6a3da065f1b3a2fa1c1e51d9cf61a8a5'),
            (['Invent Animate'],'Aeolian','other','triad','487dc00f59a10abcfc7d5a829581b9d325b20c0f0b3403df0b2cf8e6b177c4f1'),
            (['Invent Animate'],'Aeolian','pedal','single','94310f66ddc71f2998c82514c5b6b07e125293be93750825be3c5a713def81b5'),
            (['Invent Animate'],'Dorian','arpeggio','single','e7b4471b69fa926cf710950e399e0b9892aba0f1e1a7aeb4b1a12e530d87f09b'),
            (['Invent Animate','Currents','ERRA'],'Aeolian','chordal','interval','c04b94a999cdffc28091b782c9aec1285dd1c35804aa3063da76f7611771da26'),
            (['Invent Animate','Currents','ERRA'],'Phrygian','pedal','single','92ebc38da0bbb75ecb1a95d85b4c439d1f331bbf022cf78f54d05d7714aeabdc')]
        for artists,mode,style,focus,expected in cases:
            with self.subTest(artists=artists,mode=mode,style=style,focus=focus):
                r=request([{'style':style,'focus':focus,'length_q':'8','seed':1}])
                r.update(artists=artists,mode=mode);result=engine.generate(r,PACK)
                self.assertEqual(result['status'],'generated')
                for si,section in enumerate(result['sections']):
                    for bi,block in enumerate(section['blocks']):
                        trace=block.pop('shape_usage')
                        members=[m for e in result['events'] for m in e['members']
                                 if m['id'].startswith(f's{si}:b{bi}:')]
                        self.assertEqual({(c['string_number'],c['fret']) for c in trace['used_contacts']},
                                         {(m['string_number'],m['fret']) for m in members if m['fret']})
                        self.assertEqual(trace['open_strings_played'],
                                         sorted({m['string_number'] for m in members if not m['fret']}))
                        contacts=trace['ordinary_contacts']+trace['tapped_contacts']
                        self.assertTrue(all((c['pitch']-4)%12 in engine.MODES[mode] for c in contacts))
                        self.assertTrue(all(s['palette_id'] in block['palette_ids']
                                            for c in contacts for s in c['sources']))
                        self.assertTrue(all(s['shape_id'] is not None for s in trace['reference_shapes']))
                actual=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                self.assertEqual(actual,expected)

if __name__=='__main__': unittest.main()
