import unittest,copy,sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).parents[1]/'seed-scoring'))
import phrase_preferences as P
import engine as E
class Preferences(unittest.TestCase):
 def notes(self,n=4,d=1,step=None):
  return [{'start_beats':i*(d if step is None else step),'duration_beats':d} for i in range(n)]
 def test_plain_boundaries(self):
  self.assertTrue(P.rhythm_flags(self.notes(),{})['plain_long_singles'])
  self.assertFalse(P.rhythm_flags(self.notes(3),{})['plain_long_singles'])
  self.assertFalse(P.rhythm_flags(self.notes(d=.5),{})['plain_long_singles'])
  self.assertFalse(P.rhythm_flags(self.notes(d=2,step=1),{})['plain_long_singles'])
  n=self.notes();n[-1]['duration_beats']=2
  self.assertFalse(P.rhythm_flags(n,{})['plain_long_singles'])
 def test_dyad_not_chord_or_unison(self):
  for groups in ([[28]],[[28,28]],[[28,29,35]],[[None,29]]):self.assertEqual(P.pitch_flags(groups),{'intervals':False,'minor_second':False})
  self.assertEqual(P.pitch_flags([[28,29]]),{'intervals':True,'minor_second':True})
  self.assertEqual(P.pitch_flags([[28,41]]),{'intervals':True,'minor_second':False})
 def test_triplet_evidence(self):
  self.assertTrue(P.rhythm_flags(self.notes(),{P.EVENTS:'0: rest eighth triplet'})['triplets'])
  n=self.notes();n[0]['start_beats']=1/3
  self.assertFalse(P.rhythm_flags(n,{})['triplets'])
 def test_stacking_neutral_restore(self):
  before=P.ACTIVE.copy()
  with E.settings(preferences=P.DEFAULTS):
   self.assertEqual(P.multiplier({'intervals':True,'minor_second':True}),4)
  self.assertEqual(P.ACTIVE,before)
  self.assertEqual(P.multiplier(dict.fromkeys(P.DEFAULTS,True),dict.fromkeys(P.DEFAULTS,1)),1)
 def test_controls_validate(self):
  e=E.Engine.__new__(E.Engine);e.artists=[];e.roles=[]
  config=e.config() if False else None
  for value in [0,-1,float('nan'),float('inf')]:
   params=copy.deepcopy(E.DEFAULTS);params['3']['phrase_preferences']['triplets']=value
   with self.assertRaises(ValueError):e.validate(params)

 def test_unknown_timing_safe(self):
  for notes in ([{}],[{'start_beats':0,'duration_beats':'unknown'}],[{'start_exact':'0','duration_exact':'1'}]):
   self.assertFalse(P.rhythm_flags(notes,{})['plain_long_singles'])
  notes=[{'start_exact':str(i),'duration_exact':'1'} for i in range(4)]
  self.assertTrue(P.rhythm_flags(notes,{})['plain_long_singles'])

 def test_extreme_combination_explicit_error(self):
  for value in (1e308,1e-300):
   with self.assertRaises(ValueError):P.multiplier({'intervals':True,'minor_second':True},{'intervals':value,'minor_second':value})

 def test_sounding_overlap(self):
  def n(a,d,p):return {'start_beats':a,'duration_beats':d,'midi_pitch':p}
  self.assertEqual(P.sounding_flags([n(0,2,28),n(1,1,29)]),{'intervals':True,'minor_second':True})
  self.assertEqual(P.sounding_flags([n(0,2,28),n(0,2,29),n(0,2,35)]),{'intervals':False,'minor_second':False})
  self.assertEqual(P.sounding_flags([n(0,2,28),n(0,2,29),n(0,2,None)]),{'intervals':None,'minor_second':None})
  self.assertFalse(P.sounding_flags([n(0,1,28),n(1,1,29)])['intervals'])
  self.assertFalse(P.sounding_flags([n(0,1,28),n(0,1,28),n(0,1,29)])['intervals'])

 def test_source_unequal_holds_unknown(self):
  n=[{'start_beats':0,'duration_beats':1,'note_slot':1},{'start_beats':0,'duration_beats':2,'note_slot':2}]
  self.assertTrue(all(x['midi_pitch'] is None for x in P.assigned_notes(n,[[28,29]],source_evidence=True)))
  self.assertTrue(P.sounding_flags(P.assigned_notes(n,[[28,29]]))['minor_second'])

class SilencePreferences(unittest.TestCase):
 def n(self,a,d):return {'start_exact':str(a),'duration_exact':str(d)}
 def test_boundary_union_and_unknown(self):
  self.assertEqual(P.silence_fraction([self.n(0,2)],4),.5)
  self.assertEqual(P.silence_fraction([self.n(0,2),self.n(0,2)],4),.5)
  self.assertEqual(P.silence_fraction([self.n(-1,3),self.n(3,3)],4),.25)
  self.assertEqual(P.silence_fraction([],4),1)
  for notes,length in [([{}],4),([],None),([],0),([self.n(0,-1)],4)]:self.assertIsNone(P.silence_fraction(notes,length))
  self.assertTrue(P.rhythm_flags([self.n(0,2)],{},4)['mostly_silent'])
  self.assertFalse(P.rhythm_flags([self.n(0,'2.00001')],{},4)['mostly_silent'])
  self.assertTrue(P.rhythm_flags([self.n(0,'1/3')],{},'2/3')['mostly_silent'])
 def test_old_weights_migrate_and_override(self):
  e=E.Engine.__new__(E.Engine);e.artists=[];e.roles=[]
  old=copy.deepcopy(E.DEFAULTS);del old['3']['phrase_preferences']['mostly_silent']
  self.assertEqual(e.validate(old)['3']['phrase_preferences']['mostly_silent'],.1)
  self.assertEqual(E.clean_preferences('3',{'mostly_silent':1})['mostly_silent'],1)
  for value in [0,-1,float('nan'),'']:
   with self.assertRaises(ValueError):E.clean_preferences('3',{'mostly_silent':value})
 def test_penalty_neutral_unknown(self):
  with E.settings(preferences=E.DEFAULTS['3']['phrase_preferences']):
   self.assertEqual(P.rhythm([],{},4)[0],.1)
   self.assertEqual(P.rhythm([],{},None)[0],1)

 def test_config_has_readable_silence_label(self):
  from types import SimpleNamespace
  e=E.Engine.__new__(E.Engine);e.artists=[];e.roles=[];e.first={};e.eligible=[];e.pitch=SimpleNamespace(rows=[]);e.hashes={}
  config=e.config();control=next(p for p in config['stages'][2]['parameters'] if p['key']=='phrase_preferences.mostly_silent')
  self.assertEqual(control['label'],'50% or more silence/rest x')
