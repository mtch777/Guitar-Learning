import copy, unittest
import engine as E

class SilenceTests(unittest.TestCase):
 def inputs(self, repeat=False, carry=False):
  slot={'start_beats':0,'end_beats':1,'duration_beats':1}
  rows=[]
  for i in range(1,4):
   rows.append({'Phrase #':str(i),'Length (beats)':'4','Start position (beats)':str((i-1)*4),'Phrase role':'phrase','Dominant texture':'single','Accent function':'none',E.S.EXACT:'2' if repeat and i==3 else ''})
  rest=[{'start_beats':-1,'end_beats':1,'duration_beats':2,'carry_in':True}] if carry else []
  fixed=[{'notes':[slot]},{'notes':rest},{'notes':[]}]
  opening={'notes':[{**slot,'midi_pitch':28}],'selected':{'riff_id':'donor','phrase':1}}
  return [{'raw':{'seed_id':'seed'}},{'raw':{'blueprint':{'phrases':rows,'metadata':{'blueprint_total_beats':12}},'scores':{}}},{'raw':{'report':{'phrases':fixed}}},{'raw':{'report':opening}}]
 def fake(self):
  e=E.Engine.__new__(E.Engine)
  class Pitch:
   def __init__(self):self.calls=0
   def run(self,*args,**kwargs):
    self.calls+=1
    return {'selection_performed':False,'reason':'Carry-in pitch slots have no attacked-note correspondence; not invented or removed'}
  e.pitch=Pitch();return e
 def test_rest_keeps_duration_scales_and_upstream(self):
  e=self.fake();up=self.inputs();before=copy.deepcopy(up)
  out=e.stage5(E.DEFAULTS['5'],up)
  self.assertTrue(out['raw']['complete']);self.assertEqual(e.pitch.calls,0)
  self.assertEqual(up,before);self.assertEqual(out['phrases'][1]['notes'],[])
  self.assertEqual(out['phrases'][1]['length_beats'],4)
  self.assertEqual(out['audio']['length_beats'],12)
  self.assertEqual(out['details']['possible_scales'],E.T.public(E.T.from_notes(up[3]['raw']['report']['notes'])))
  final=e.stage6({},up+[out]);self.assertTrue(final['can_export']);self.assertEqual(len(final['audio']['notes']),1)
 def test_silent_exact_repeat_is_still_a_copy(self):
  e=self.fake();out=e.stage5(E.DEFAULTS['5'],self.inputs(repeat=True))
  self.assertTrue(out['raw']['complete']);self.assertEqual(e.pitch.calls,0)
  self.assertEqual(out['phrases'][2]['method'],'Exact repeat');self.assertEqual(out['phrases'][2]['copy_from'],2)
  self.assertEqual(out['phrases'][2]['notes'],out['phrases'][1]['notes'])
 def test_carry_is_not_misclassified_as_silence(self):
  e=self.fake();out=e.stage5(E.DEFAULTS['5'],self.inputs(carry=True))
  self.assertFalse(out['raw']['complete']);self.assertEqual(e.pitch.calls,1)
  self.assertIn('Carry-in',out['blocker']);self.assertEqual(len(out['phrases']),1)
 def test_silent_repeat_cannot_replace_nonempty_fixed_rhythm(self):
  e=self.fake();up=self.inputs(repeat=True)
  up[2]['raw']['report']['phrases'][2]['notes']=copy.deepcopy(up[2]['raw']['report']['phrases'][0]['notes'])
  with self.assertRaisesRegex(AssertionError,'changed fixed rhythm'):
   e.stage5(E.DEFAULTS['5'],up)

if __name__=='__main__':unittest.main()
