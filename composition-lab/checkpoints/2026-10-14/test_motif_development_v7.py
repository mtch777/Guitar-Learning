import copy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET
from motif_development_v7 import relation,learn_relations,apply_relation,develop,compose

TUNING=[26,31,38,43,48,53,57,62]

def bar(pitches):
    return tuple((2,(p,)) for p in pitches)

def phrase_bars():
    return [[{'units':2,'positions':[(p,1,p-31)]} for p in ps] for ps in [(31,33),(31,33),(32,34),(31,33)]]

class Step7Tests(unittest.TestCase):
    def test_identical_and_transposition_and_variation(self):
        a=[bar((48,55,48,55))]
        self.assertEqual(relation(a,a)['kind'],'repeat')
        self.assertEqual(relation(a,[bar((50,57,50,57))])['kind'],'transpose')
        self.assertEqual(relation(a,[bar((50,57,50,59))])['kind'],'vary')
        self.assertIsNone(relation(a,[((2,(48,52)),(2,(55,)))]))

    def test_detects_variable_length_from_input(self):
        aa=[bar((48,55,48,55)),bar((50,57,50,57))]
        seq=aa+[bar((45,52,45,52))]+aa
        # Construct a minimal extracted score; no need for GP fixture.
        measures=[]
        for b in seq:
            voice=[]
            for units,ps in b:
                voice.append({'duration_q':'1/1','notes':[{'midi':p} for p in ps]})
            measures.append({'time_signature':'4/4','voices':[voice]})
        score={'tracks':[{'tunings':[TUNING],'measures':measures}]}
        model=learn_relations([score],max_span=3)
        self.assertTrue(any(r['span']==2 and r['distance']==3 and r['kind']=='repeat' for r in model['relations']))

    def test_aligned_transposition_preserves_shape(self):
        original=[[{'units':2,'positions':[(48,4,0),(55,6,-2)]},
                   {'units':2,'positions':[]}]]
        rule={'offsets':(2,None)}
        changed=apply_relation(original,rule,TUNING,14)
        self.assertIsNotNone(changed)
        p=changed[0][0]['positions']
        self.assertEqual([x[0] for x in p],[50,57]);self.assertEqual(changed[0][1]['positions'],[])
        self.assertEqual(original[0][0]['positions'][0][0],48)

    def test_empty_relations_never_force_repetition(self):
        initial=phrase_bars()
        out,report=develop(initial,{'relations':[],'counts':{},'recurrence_rate':0},TUNING)
        self.assertEqual(out,initial);self.assertEqual(report['operations'],[])

    def test_deterministic_development(self):
        initial=phrase_bars()
        rules={'relations':[{'span':1,'distance':1,'offsets':(0,0),'kind':'repeat','transpose':0,'deviations':0}],
               'counts':{'repeat':1},'recurrence_rate':1}
        a,ra=develop(initial,rules,TUNING,17)
        b,rb=develop(initial,rules,TUNING,17)
        self.assertEqual((a,ra),(b,rb))
        self.assertGreaterEqual(len(ra['operations']),1)

    def test_source_sensitive_development(self):
        start=phrase_bars()
        repeated={'relations':[{'span':1,'distance':1,'offsets':(0,0),'kind':'repeat','transpose':0,'deviations':0}],
                  'counts':{'repeat':1},'recurrence_rate':1}
        blank={'relations':[],'counts':{},'recurrence_rate':0}
        out_a,_=develop(start,repeated,TUNING,seed=2)
        out_b,_=develop(start,blank,TUNING,seed=2)
        self.assertNotEqual(out_a,out_b)

    def test_export_and_reimport(self):
        base=Path('/mnt/data/Cloud Cascade (Tuned Down).gp')
        sources=[Path('/mnt/data/Immolation of Night (Tuned Down).gp')]
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'test.gp'
            info=compose(base,output,sources,bars=8,track_index=1,seed=9)
            with zipfile.ZipFile(output) as z:
                root=ET.fromstring(z.read('Content/score.gpif'))
            self.assertEqual(len(root.findall('./MasterBars/MasterBar')),8)
            self.assertEqual(len(root.findall('./Notes/Note')),info['notes'])

if __name__=='__main__':unittest.main()