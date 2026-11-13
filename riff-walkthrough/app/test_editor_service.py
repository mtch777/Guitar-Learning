import copy,json,pathlib,tempfile,threading,unittest
from unittest.mock import patch
from editor_service import selected_audio,EditorManager
from server import midi_bytes
class ExportTests(unittest.TestCase):
 def setUp(self):
  self.output={'phrases':[{'phrase':i+1,'start_beats':i*4,'length_beats':4} for i in range(3)],'audio':{'notes':[{'start_beats':3,'duration_beats':6,'midi_pitch':28},{'start_beats':10,'duration_beats':1,'midi_pitch':31}],'length_beats':12,'tempo':120}}
 def test_contiguous_holds_not_retriggered(self):
  a=selected_audio(self.output,[2,1]);self.assertEqual(a['length_beats'],8);self.assertEqual(a['notes'],[{'start_beats':3,'duration_beats':5,'midi_pitch':28}])
 def test_nonconsecutive_clipped_joined_sorted_dedup(self):
  a=selected_audio(self.output,[3,1,3]);self.assertEqual(a['length_beats'],8);self.assertEqual([(n['start_beats'],n['duration_beats']) for n in a['notes']],[(3,1),(4,1),(6,1)])
 def test_rest_and_invalid(self):
  self.output['audio']['notes']=[];a=selected_audio(self.output,[2]);self.assertEqual(a['length_beats'],4);self.assertEqual(a['notes'],[]);self.assertTrue(midi_bytes(a).startswith(b'MThd'))
  for selection in [[],None,[0],[True],[4]]:
   with self.assertRaises(ValueError):selected_audio(self.output,selection)
class WorkspaceTests(unittest.TestCase):
 def test_revision_transactions_persistence_and_export(self):
  with tempfile.TemporaryDirectory() as d:
   class Pub:
    repo=pathlib.Path(d)/'repo';lock=threading.Lock()
    def publish(self,data,version,stage,partial,selected=False):self.saved=data;return {'saved':True,'selected_prefix':selected}
   pub=Pub();m=EditorManager(pub)
   out={'phrases':[{'phrase':1,'start_beats':0,'length_beats':4,'notes':[]}],'audio':{'notes':[],'length_beats':4,'tempo':120},'summary':{},'details':{},'can_export':True}
   state={'version':2,'dataset':{'csv':'hash'},'stages':[{'id':'6','output':out}]};original=copy.deepcopy(state)
   m.source=lambda cookie,version:('test',copy.deepcopy(state));m.engine=object()
   opened=m.request('/editor/open','private',{'version':2});self.assertEqual(opened['revision'],0)
   plan={'affected':[1],'rhythm_affected':[1],'pitch_affected':[]}
   with patch('selective_edit.plan_selection',return_value=plan),patch('selective_edit.SelectiveEditor.regenerate',side_effect=ValueError('no candidates')):
    before=m.path('test').read_bytes()
    with self.assertRaisesRegex(ValueError,'no candidates'):m.request('/editor/regenerate','private',{'version':2,'revision':0,'selected':[1],'mode':'rhythm'})
    self.assertEqual(before,m.path('test').read_bytes())
   with patch('selective_edit.plan_selection',return_value=plan),patch('selective_edit.SelectiveEditor.regenerate',return_value={'phrases':copy.deepcopy(out['phrases']),**plan}):
    edited=m.request('/editor/regenerate','private',{'version':2,'revision':0,'selected':[1],'mode':'rhythm'});self.assertEqual(edited['revision'],1)
   with self.assertRaisesRegex(ValueError,'changed'):m.request('/editor/save','private',{'version':2,'revision':0,'selected':[1]})
   saved=m.request('/editor/save','private',{'version':2,'revision':1,'selected':[1]});self.assertEqual(pub.saved,midi_bytes(out['audio']));self.assertTrue(saved['selected_prefix'])
   self.assertEqual(state,original);self.assertNotIn('private',m.path('test').read_text())
   reopened=EditorManager(pub);reopened.source=m.source;self.assertEqual(reopened.request('/editor/open','private',{'version':2})['revision'],1)
if __name__=='__main__':unittest.main()
