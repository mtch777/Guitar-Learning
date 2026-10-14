import unittest
from fractions import Fraction
from pathlib import Path
from xml.etree import ElementTree as ET
from extract import extract_score
from sequence_model import SequenceModel, event_token, track_sequences
from sequence_generator_balanced import generate
from sequence_generator_v6 import export_score
from music_events import meter_length, validate_events

SOURCE=Path('/mnt/data/Chet Baker - I Fall In Love Too Easily (ver 2 by omsoc1950).gp')
TUNING=[40,45,50,55,59,64]

class ExactRhythmTests(unittest.TestCase):
 def test_triplet_event_preserved(self):
  beat={'duration_q':'1/3','notes':[{'midi':60}]}
  token,pitch=event_token(beat,None)
  self.assertEqual(token,(Fraction(4,3),None,(0,)))
  self.assertEqual(pitch,60)
 def test_dotted_event_preserved(self):
  token,_=event_token({'duration_q':'3/4','notes':[{'midi':60}]},60)
  self.assertEqual(token[0],3)
 def test_varied_meter(self):
  score={'tracks':[{'tunings':[[40,45,50,55,59,64]], 'measures':[
   {'time_signature':'3/4','voices':[[{'duration_q':'2/3','notes':[{'midi':60}]},{'duration_q':'1/3','notes':[{'midi':64}]},{'duration_q':'2','notes':[]}]]},
   {'time_signature':'5/4','voices':[[{'duration_q':'4','notes':[{'midi':65}]},{'duration_q':'1','notes':[{'midi':67}]}]]}]}]}
  seq=track_sequences(score)
  self.assertEqual(sum(len(x) for x,_ in seq),5)
  self.assertEqual(meter_length('5/8'),Fraction(5,2))
 def test_no_silent_event_drop_on_chet(self):
  if not SOURCE.exists():self.skipTest('Chet source file unavailable')
  s=extract_score(SOURCE)
  all_events=sum(len(v) for t in s['tracks'] for m in t['measures'] for v in m['voices'])
  sequences=track_sequences(s)
  self.assertEqual(sum(len(seq) for seq,_ in sequences),all_events)
  self.assertEqual(all_events,322)
  self.assertEqual(sum(len(e['notes']) for t in s['tracks'] for m in t['measures'] for v in m['voices'] for e in v),559)
  self.assertGreater(sum(token[0].denominator!=1 for seq,_ in sequences for token in seq),0)
  self.assertFalse(validate_events(s))
 def test_exact_export_triplets_and_odd_meter(self):
  if not SOURCE.exists():self.skipTest('Chet template unavailable')
  outfile=Path('/mnt/data/Step10_Exact_Timing/test_output_5_4.gp')
  bars=[[{'units':Fraction(4,3),'positions':[(60,4,1)]} for _ in range(3)]+[{'units':16,'positions':[]}]]
  rep=export_score(SOURCE,outfile,bars,'5/4',0,'Tuplet Test')
  actual=extract_score(outfile)
  durations=[Fraction(e['duration_q']) for e in actual['tracks'][0]['measures'][0]['voices'][0]]
  self.assertEqual(durations,[Fraction(1,3)]*3+[Fraction(4)])
  self.assertEqual(sum(durations),5)
  self.assertEqual(rep['notes'],3)
 def test_generation_uses_fractional_rhythms(self):
  m=SequenceModel(max_order=2)
  m.add_sequence([(Fraction(4,3),None,(0,)),(Fraction(4,3),7,(0,)),(Fraction(4,3),-7,(0,))]*30,60)
  bars,_=generate(m,TUNING,bars=4,seed=9)
  self.assertTrue(all(sum((e['units'] for e in bar),Fraction())==16 for bar in bars))
  self.assertTrue(any(e['units'].denominator!=1 for bar in bars for e in bar))
 def test_determinism(self):
  m=SequenceModel.from_paths([SOURCE])
  a,_=generate(m,TUNING,bars=4,seed=31)
  b,_=generate(m,TUNING,bars=4,seed=31)
  self.assertEqual(a,b)

if __name__=='__main__':unittest.main()