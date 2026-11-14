import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import engine as E
import selective_edit as X
from test_selective_edit import fixture,notes
from editor_service import EditorManager
from server import midi_bytes

class ExactAndDeleteTests(unittest.TestCase):
 def test_current_identity_not_old_links_or_metadata(self):
  s,p,e=fixture();p[2]['notes'][0]['source_attack_group']=999;p[2]['notes'][0]['source_midi_pitch']=99
  self.assertEqual(X.plan_selection(s,p,[1],'both')['affected'],[1,3])
  p[2]['notes'][0]['midi_pitch']=29
  self.assertEqual(X.plan_selection(s,p,[1],'both')['affected'],[1])
  p[3]['notes']=copy.deepcopy(p[0]['notes'])
  self.assertEqual(X.plan_selection(s,p,[1],'rhythm')['affected'],[1,4])
  p[3]['length_beats']=3
  self.assertEqual(X.exact_current_roots(p)[4],4)
 def test_metadata_different_current_matches_regenerate(self):
  s,p,e=fixture();p[2]['notes'][0]['note_slot']=91
  r=X.SelectiveEditor(e).regenerate(s,p,[1],'pitches',22)
  self.assertEqual(r['affected'],[1,3]);self.assertEqual(X._timing_signature(r['phrases'][2]['notes']),X._timing_signature(p[2]['notes']))
 def test_delete_closes_gaps_preserves_input_and_reindexes(self):
  s,p,e=fixture();before=copy.deepcopy((s,p))
  r=X.delete_phrases(s,p,[1]);self.assertEqual(r['deleted'],[1,3]);self.assertEqual(r['old_to_new'],{2:1,4:2})
  self.assertEqual([x['start_beats'] for x in r['phrases']],[0,2]);self.assertEqual(r['audio']['length_beats'],4)
  self.assertEqual([x['notes'] for x in r['phrases']],[p[1]['notes'],p[3]['notes']])
  self.assertEqual((s,p),before)
  rows=X._stage(r['state'],2)['output']['details']['blueprint']['phrases']
  self.assertEqual([x['Phrase #'] for x in rows],[1,2]);self.assertEqual(rows[0]['Intended same rhythm and holds as (phrase #s)'],'none')
  self.assertTrue(midi_bytes(r['audio']).startswith(b'MThd'))
  after=X.SelectiveEditor(e).regenerate(r['state'],r['phrases'],[1],'both',12)
  self.assertEqual(len(after['phrases']),2);self.assertEqual(after['phrases'][1],r['phrases'][1])
 def test_delete_all_empty_and_invalid_atomic(self):
  s,p,e=fixture();before=copy.deepcopy((s,p))
  r=X.delete_phrases(s,p,[1,2,3,4]);self.assertEqual(r['phrases'],[]);self.assertEqual(r['audio']['length_beats'],0)
  self.assertEqual(r['audio']['notes'],[]);self.assertTrue(midi_bytes(r['audio']).startswith(b'MThd'))
  for ids in ([],[0],[True],[5]):
   with self.assertRaises(ValueError):X.delete_phrases(s,p,ids)
  self.assertEqual((s,p),before)
 def test_holds_clip_only_removed_run_edges(self):
  s,p,e=fixture();p[0]['notes'][0].update(end_beats=3,end_exact='3',duration_beats=3)
  # Preserve contiguous1-2: long hold crosses their boundary unchanged.
  r=X.delete_phrases(s,p,[4]);self.assertEqual(r['phrases'][0]['notes'][0]['end_beats'],3)
  # Remove2: source phrase1 hold ends at gap, doesn't bleed into next retained phrase.
  r=X.delete_phrases(s,p,[2]);self.assertEqual(r['phrases'][0]['notes'][0]['end_beats'],2)
 def test_transaction_persist_stale_version_and_reopen(self):
  s,p,e=fixture();s['version']=2
  output={'phrases':p,'audio':E.audio(p,'Original'),'summary':{},'details':{},'can_export':True}
  s['stages'].append({'id':'6','output':output});source=copy.deepcopy(s)
  with tempfile.TemporaryDirectory() as d:
   class Pub:repo=pathlib.Path(d)/'repo'
   m=EditorManager(Pub());m.source=lambda *_:('test',copy.deepcopy(source))
   m.request('/editor/open','',{'version':2});before=m.path('test').read_bytes()
   with self.assertRaises(ValueError):m.request('/editor/delete','',{'version':2,'revision':0,'selected':[99]})
   self.assertEqual(m.path('test').read_bytes(),before)
   r=m.request('/editor/delete','',{'version':2,'revision':0,'selected':[1]})
   self.assertEqual(r['revision'],1);self.assertEqual(r['deleted'],[1,3]);self.assertEqual(len(r['output']['phrases']),2)
   self.assertEqual(json.loads(m.path('test.revision-0').read_text())['output'],output)
   with self.assertRaises(ValueError):m.request('/editor/delete','',{'version':2,'revision':0,'selected':[1]})
   m2=EditorManager(Pub());m2.source=m.source
   self.assertEqual(m2.request('/editor/open','',{'version':2})['output'],r['output']);self.assertEqual(s,source)

if __name__=='__main__':unittest.main()
