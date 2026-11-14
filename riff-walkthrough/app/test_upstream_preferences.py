import unittest,copy
import engine as E
import phrase_preferences as P
class UpstreamIntervals(unittest.TestCase):
 def test_boundary(self):
  def n(a,d):return {'start_beats':a,'duration_beats':d}
  self.assertFalse(P.interval_slots([n(0,1),n(0,2),n(0,2)],1))
  self.assertTrue(P.interval_slots([n(-1,2),n(0,1)],1))
  self.assertFalse(P.interval_slots([n(0,1),n(1,1)],2))
  self.assertTrue(P.interval_slots([n(0,2),n(1,1)],2))
  self.assertIsNone(P.interval_slots([n(0,-1)],2))
  self.assertIsNone(P.interval_slots([{}],2))
 def test_legacy_and_controls(self):
  e=E.Engine.__new__(E.Engine);e.artists=[];e.roles=[]
  params=copy.deepcopy(E.DEFAULTS)
  for i in ('4','5'):params[i]['phrase_preferences']['intervals']=200
  result=e.validate(params)
  for i in ('4','5'):
   self.assertEqual(result[i]['phrase_preferences'],{'minor_second':2})
   self.assertEqual(E.clean_preferences(i,params[i]['phrase_preferences']),{'minor_second':2})
  self.assertNotIn('phrase_preferences',E.DEFAULTS['1'])
  self.assertEqual(E.DEFAULTS['2']['phrase_preferences'],{'intervals':2})
  self.assertEqual([x['key'] for x in E.preference_controls()['4']],['minor_second'])
if __name__=='__main__':unittest.main()
