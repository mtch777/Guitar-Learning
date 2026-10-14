import random
import unittest
from collections import Counter
from sequence_model import SequenceModel
from sequence_generator_balanced import generate

TUNING=[26,31,38,43,48,53,57,62]

class BalancedTests(unittest.TestCase):
    def test_deterministic(self):
        model=SequenceModel(max_order=3)
        model.add_sequence([(2,None,(0,)),(2,7,(0,)),(2,-7,(0,)),(2,7,(0,)),(4,-7,(0,)),(4,0,(0,))],60)
        a=generate(model,TUNING,bars=4,seed=31)
        b=generate(model,TUNING,bars=4,seed=31)
        self.assertEqual(a,b)
    def test_rest_free_data_produces_no_rest(self):
        model=SequenceModel(max_order=2)
        model.add_sequence([(4,None,(0,)),(4,2,(0,)),(4,-2,(0,)),(4,0,(0,))]*8,60)
        bars,meta=generate(model,TUNING,bars=6,seed=17)
        self.assertEqual(meta['rest_events'],0)
        self.assertTrue(all(ev['positions'] for bar in bars for ev in bar))
    def test_polyphony_and_meter(self):
        model=SequenceModel(max_order=2)
        model.add_sequence([(4,None,(0,7)),(4,0,(0,7)),(4,-2,(0,7)),(4,2,(0,7))]*8,50)
        bars,_=generate(model,TUNING,bars=5,meter='3/4',seed=9)
        self.assertEqual(len(bars),5)
        self.assertTrue(all(sum(ev['units'] for ev in bar)==12 for bar in bars))
        self.assertTrue(all(len(ev['positions'])==2 for bar in bars for ev in bar))
    def test_mixed_input_does_not_fix_genre(self):
        model=SequenceModel(max_order=2)
        model.add_sequence([(4,None,(0,)),(4,0,(0,)),(4,0,(0,))]*12,60)
        model.add_sequence([(4,None,(0,4,7)),(4,0,(0,4,7))]*12,48)
        bars,meta=generate(model,TUNING,bars=20,seed=17)
        sizes={len(e['positions']) for bar in bars for e in bar}
        self.assertIn(1,sizes)
        self.assertIn(3,sizes)
if __name__=='__main__':unittest.main()