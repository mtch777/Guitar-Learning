import copy,csv,hashlib,http.server,json,pathlib,tempfile,threading,unittest
from unittest.mock import patch
from selection_service import SelectionManager
from server import midi_bytes
from editor_service import selected_audio
class SelectionTests(unittest.TestCase):
 def make(self):
  class Publisher:
   lock=threading.Lock();repo=pathlib.Path('.')
   def current_audio_midi(self,cookie,stage,version,include_output=False):
    if cookie!='private' or version!=2:raise ValueError('stale')
    return b'',stage==5,copy.deepcopy(self.outputs[stage])
   def publish(self,body,version,stage,partial,selected=False):self.saved=body;return {'stage':stage,'version':version,'partial':partial,'selected_flag':selected,'saved':True}
  p=Publisher();audio={'notes':[{'start_beats':0,'duration_beats':1,'midi_pitch':28},{'start_beats':3,'duration_beats':3,'midi_pitch':31},{'start_beats':7,'duration_beats':1,'midi_pitch':33}],'tempo':120,'length_beats':8,'label':'test'}
  p.outputs={i:{'audio':copy.deepcopy(audio),'phrases':[{'phrase':1,'start_beats':0,'length_beats':4},{'phrase':2,'start_beats':4,'length_beats':4}],'details':{'reference_audio_riff':'donor'}} for i in range(1,6)}
  p.outputs[1]['phrases']=[{'phrase':1,'start_beats':999,'length_beats':8}]
  return p
 def test_every_stage_independent_exact_audio_and_donor_windows(self):
  p=self.make();m=SelectionManager(p);m.donor_windows=lambda cookie,riff:[{'phrase':1,'start_beats':0,'length_beats':6},{'phrase':2,'start_beats':6,'length_beats':2}]
  for stage in range(1,6):
   context=m.request('/selection/open','private',{'stage':stage,'version':2});self.assertEqual(context['phrases'][0]['start_beats'],0)
   chosen=[1] if stage==1 else [2];out=m.request('/selection/save','private',{'stage':stage,'version':2,'selected':chosen})
   expected=selected_audio({'phrases':context['phrases'],'audio':p.outputs[stage]['audio']},chosen)
   self.assertEqual(p.saved,midi_bytes(expected));self.assertEqual(out['stage'],stage);self.assertEqual(out['partial'],stage==5)
   if stage==2:self.assertEqual(context['phrases'][1]['start_beats'],6);self.assertEqual(expected['length_beats'],2)
 def test_stale_invalid_and_silent(self):
  p=self.make();m=SelectionManager(p)
  for payload in [{'stage':6,'version':2},{'stage':1,'version':1},{'stage':True,'version':2},{'stage':1,'version':2,'notes':[]}]:
   with self.assertRaises(ValueError):m.request('/selection/open','private',payload)
  p.outputs[3]['audio']['notes']=[];result=m.request('/selection/save','private',{'stage':3,'version':2,'selected':[2]});self.assertTrue(result['saved']);self.assertEqual(p.saved,midi_bytes({'notes':[],'length_beats':4}))
  p.outputs[4]['audio']['length_beats']=5
  with self.assertRaises(ValueError):m.request('/selection/open','private',{'stage':4,'version':2})
 def test_donor_csv_hash_and_cache_revalidation(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'data.csv'
   path.write_text('Riff ID,Status,Phrase #,Length (quarter-note beats)\ndonor,complete,2,3/2\ndonor,complete,1,5/2\n',encoding='utf-8')
   config={'dataset':{'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
   class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(json.dumps(config).encode())
    def log_message(self,*args):pass
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    p=self.make();p.source_port=server.server_port;m=SelectionManager(p)
    with patch('selection_service.E.CSV',path):
     rows=m.donor_windows('riff_session='+'a'*32,'donor');self.assertEqual(rows,[{'phrase':1,'start_beats':0,'length_beats':2.5},{'phrase':2,'start_beats':2.5,'length_beats':1.5}])
     self.assertEqual(m.donor_windows('riff_session='+'a'*32,'donor'),rows)
     config['dataset']['csv_sha256']='wrong'
     with self.assertRaisesRegex(ValueError,'changed'):m.donor_windows('riff_session='+'a'*32,'donor')
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
