import unittest,random,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from sequence_model import SequenceModel,event_token,track_sequences
from sequence_generator import produce_bars,fit_voicing,export

TUNING=[26,31,38,43,48,53,57,62]
class SequenceTests(unittest.TestCase):
    def test_alternating_pattern(self):
        # One initial event, followed by +7,-7, +7,-7 ...
        m=SequenceModel(max_order=3)
        a=(2,None,(0,));up=(2,7,(0,));down=(2,-7,(0,))
        m.add_sequence([a,up,down,up,down,up,down]*8,48)
        self.assertEqual(m.sample(random.Random(3),[a,up,down,up])[0],down)
        self.assertEqual(m.sample(random.Random(3),[a,up,down])[0],up)
    def test_rests_and_chords(self):
        m=SequenceModel(2);seq=[(2,None,(0,4,7)),(2,None,()),(4,2,(0,3,7))]
        m.add_sequence(seq,48)
        self.assertEqual(m.sample(random.Random(1),seq[:2])[0],seq[2])
        self.assertIn(seq[0],m.distribution([])[0])
    def test_backoff(self):
        m=SequenceModel(4);m.add_sequence([(2,None,(0,)),(2,4,(0,)),(2,-4,(0,))],45)
        item,level=m.sample(random.Random(4),[(1,33,(0,))])
        self.assertEqual(level,0)
    def test_determinism(self):
        m=SequenceModel(2);m.add_sequence([(2,None,(0,)),(2,7,(0,)),(2,-7,(0,)),(4,0,(0,))]*30,48)
        x,_=produce_bars(m,TUNING,bars=3,seed=11)
        y,_=produce_bars(m,TUNING,bars=3,seed=11)
        self.assertEqual(x,y)
        self.assertTrue(all(sum(e['units'] for e in b)==16 for b in x))
    def test_chord_playability(self):
        p=fit_voicing(48,(0,4,7),TUNING)
        self.assertEqual([x[0]-p[0][0] for x in p],[0,4,7])
        self.assertIsNone(fit_voicing(48,tuple(range(15)),TUNING))
    def test_no_articulation_invention(self):
        m=SequenceModel(1);m.add_sequence([(2,None,(0,)),(2,7,(0,))]*16,48)
        bars,_=produce_bars(m,TUNING,bars=2,seed=3)
        self.assertFalse(any(e.get('palm_muted') for b in bars for e in b))
    def test_source_change_changes_probabilities(self):
        a=SequenceModel(2);b=SequenceModel(2)
        a.add_sequence([(2,None,(0,)),(2,7,(0,))],48)
        b.add_sequence([(4,None,(0,)),(4,3,(0,))],48)
        self.assertNotEqual(a.distribution([])[0],b.distribution([])[0])
    def test_export_real_gp(self):
        path=Path('/mnt/data/Original_16_Bar_Guitar_Study_V5_Sequence.gp')
        if not path.exists():self.skipTest('No generated file')
        with zipfile.ZipFile(path) as z:
            root=ET.fromstring(z.read('Content/score.gpif'))
        self.assertEqual(len(root.findall('./MasterBars/MasterBar')),16)
        self.assertGreater(len(root.findall('./Notes/Note')),0)
        self.assertEqual(len(root.findall('./Tracks/Track')),1)
        self.assertFalse(any(n.find("./Properties/Property[@name='PalmMuted']") is not None for n in root.findall('./Notes/Note')))
if __name__=='__main__':unittest.main()