import copy,hashlib,json,os,pathlib,struct,subprocess,tempfile,threading,time,unittest,wave
from unittest.mock import patch
import render_service as R
class RenderTests(unittest.TestCase):
 def fixture(self,folder):
  out={'phrases':[{'phrase':1,'start_beats':0,'length_beats':1},{'phrase':2,'start_beats':1,'length_beats':1}], 'audio':{'notes':[{'start_beats':.5,'duration_beats':1,'midi_pitch':28},{'start_beats':1.75,'duration_beats':.2,'midi_pitch':31}],'length_beats':2,'tempo':120}}
  class Publisher:
   repo=folder/'repo'
   def current_audio_midi(self,cookie,stage,version,include_output=False,view='current'):
    if version!=2:raise ValueError('stale')
    result=copy.deepcopy(out)
    if view=='previous':result['audio']['notes'][0]['midi_pitch']=40
    return b'',False,result
  class Selection:
   def request(self,path,cookie,data):return {'phrases':copy.deepcopy(out['phrases'])}
  class Editor:
   lock=threading.RLock()
   def source(self,cookie,version):return 'key',{}
   def workspace(self,key,state):return {'revision':3,'output':copy.deepcopy(out)}
  return R.RenderManager(Publisher(),Editor(),Selection()),out
 def test_verified_manifest_groups_and_files(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);m,_=self.fixture(root);worker=root/'worker.py';worker.write_text('# worker');state=root/'modern2.state';state.write_bytes(b'initialized verified state')
   manifest=root/'presets.json';manifest.write_text(json.dumps({'presets':[
    {'id':'modern-metal-2','label':'Modern Metal 2','group':'Djentcore','rank':1,'state_file':state.name,'state_sha256':hashlib.sha256(state.read_bytes()).hexdigest(),'verified':True},
    {'id':'not-tested','label':'Unverified','state_file':state.name,'verified':False},
    {'id':'missing','label':'Missing','state_file':'missing.state','verified':True},
    {'id':'changed','label':'Changed','state_file':state.name,'state_sha256':'bad','verified':True},
    {'id':'escape','label':'Escape','state_file':'../outside.state','verified':True}]}))
   with patch.dict(os.environ,{'RIFF_RENDER_PYTHON':__file__,'RIFF_RENDER_WORKER':str(worker),'RIFF_KONTAKT_PRESET_DIR':str(root),'RIFF_KONTAKT_MANIFEST':str(manifest)}):
    self.assertEqual(m.available(),[{'id':'modern-metal-2','label':'Modern Metal 2','group':'Djentcore','rank':1}])
    manifest.write_text('bad json');self.assertEqual(m.available(),[])
   m.executor.shutdown()
 def test_selected_keeps_timeline_and_contiguous_holds(self):
  with tempfile.TemporaryDirectory() as d:
   m,out=self.fixture(pathlib.Path(d))
   a=R.selected_in_place(out,[2]);self.assertEqual(a['length_beats'],2);self.assertEqual(a['notes'][0]['start_beats'],1);self.assertEqual(a['notes'][0]['duration_beats'],.5)
   self.assertEqual(R.selected_in_place(out,[2,1])['notes'],out['audio']['notes'])
   for stage in range(1,7):
    data={'stage':stage,'version':2,'editor_revision':3 if stage==6 else None,'selected':[2],'preset':'modern-metal-1','view':'current'}
    self.assertEqual(m.capture('riff_session='+'a'*32,data),a)
   for stage in range(1,7):
    previous={'stage':stage,'version':2,'editor_revision':None,'selected':None,'preset':'modern-metal-1','view':'previous'}
    self.assertEqual(m.capture('riff_session='+'a'*32,previous)['notes'][0]['midi_pitch'],40)
   data['editor_revision']=2
   with self.assertRaisesRegex(ValueError,'changed'):m.capture('riff_session='+'a'*32,data)
   m.executor.shutdown()
 def test_worker_receipts_cache_and_owner_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);m,out=self.fixture(root);worker=root/'worker.py';worker.write_text('# worker')
   for _,name in R.PRESETS.values():(root/name).write_bytes(name.encode())
   env={'RIFF_RENDER_PYTHON':__file__,'RIFF_RENDER_WORKER':str(worker),'RIFF_KONTAKT_PRESET_DIR':str(root),'RIFF_KONTAKT_PRESETS':'modern-metal-1,ready-to-djent'}
   calls=[]
   def run(command,**kwargs):
    args=dict(zip(command[2::2],command[3::2]));wav=pathlib.Path(args['--output']);seconds=float(args['--duration']);midi=pathlib.Path(args['--midi']).read_bytes();preset=args['--preset'];calls.append(preset)
    pcm=struct.pack('<hh',1200,-1200)*round(seconds*44100)
    with wave.open(str(wav),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100);f.writeframes(pcm)
    receipt={'success':True,'job_id':args['--job-id'],'termination_mode':'controlled_process_termination','expected_exit_code':85,'midi_sha256':hashlib.sha256(midi).hexdigest(),'wav_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'preset':preset,'state_sha256':hashlib.sha256((root/R.PRESETS[preset][1]).read_bytes()).hexdigest()}
    pathlib.Path(str(wav)+'.json').write_text(json.dumps(receipt));return subprocess.CompletedProcess(command,85,stdout=b'',stderr=b'')
   cookie='riff_session='+'a'*32;data={'stage':1,'version':2,'editor_revision':None,'selected':None,'preset':'modern-metal-1','view':'current'}
   with patch.dict(os.environ,env),patch('render_service.subprocess.run',side_effect=run):
    self.assertEqual(len(m.available()),2)
    def complete():
     job=m.start(cookie,data)
     for _ in range(500):
      job=m.status(cookie,job['job_id'])
      if job['status'] in ('ready','failed'):return job
      time.sleep(.01)
     self.fail('render did not finish')
    first=complete();self.assertEqual(first['status'],'ready');self.assertEqual(first['host_shutdown'],'controlled_process_termination');self.assertTrue(m.audio(cookie,first['job_id']).startswith(b'RIFF'));self.assertEqual(first['capture']['version'],2)
    with self.assertRaises(ValueError):m.status('riff_session='+'b'*32,first['job_id'])
    second=complete();self.assertEqual(second['host_shutdown'],first['host_shutdown']);self.assertEqual(second['host_exit_code'],85);self.assertTrue(second['cached']);self.assertEqual(second['audio_sha256'],first['audio_sha256']);self.assertEqual(calls,['modern-metal-1'])
    data['preset']='ready-to-djent';self.assertEqual(complete()['status'],'ready');self.assertEqual(calls,['modern-metal-1','ready-to-djent'])
    with patch.dict(os.environ,{'RIFF_KONTAKT_PRESETS':''}):self.assertEqual(m.available(),[])
   m.executor.shutdown()
 def test_failed_worker_artifacts_never_become_audio(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);m,out=self.fixture(root);worker=root/'worker.py';worker.write_text('worker')
   for _,name in R.PRESETS.values():(root/name).write_bytes(name.encode())
   env={'RIFF_RENDER_PYTHON':__file__,'RIFF_RENDER_WORKER':str(worker),'RIFF_KONTAKT_PRESET_DIR':str(root),'RIFF_KONTAKT_PRESETS':'modern-metal-1'}
   cookie='riff_session='+'a'*32;data={'stage':1,'version':2,'editor_revision':None,'selected':None,'preset':'modern-metal-1','view':'current'}
   for failure in ['timeout','no_receipt','midi_hash','state_hash','wav_hash','silent','malformed']:
    worker.write_text(failure)
    def run(command,**kwargs):
     if failure=='timeout':raise subprocess.TimeoutExpired(command,180)
     if failure=='no_receipt':return subprocess.CompletedProcess(command,1)
     args=dict(zip(command[2::2],command[3::2]));wav=pathlib.Path(args['--output']);midi=pathlib.Path(args['--midi']).read_bytes()
     if failure=='malformed':wav.write_bytes(b'not wav')
     else:
      with wave.open(str(wav),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(44100);f.writeframes(struct.pack('<hh',0 if failure=='silent' else 500,0)*round(float(args['--duration'])*44100))
     receipt={'success':True,'preset':'modern-metal-1','midi_sha256':hashlib.sha256(midi).hexdigest(),'state_sha256':hashlib.sha256((root/R.PRESETS['modern-metal-1'][1]).read_bytes()).hexdigest(),'wav_sha256':hashlib.sha256(wav.read_bytes()).hexdigest()}
     key={'midi_hash':'midi_sha256','state_hash':'state_sha256','wav_hash':'wav_sha256'}.get(failure)
     if key:receipt[key]='wrong'
     pathlib.Path(str(wav)+'.json').write_text(json.dumps(receipt));return subprocess.CompletedProcess(command,1)
    with patch.dict(os.environ,env),patch('render_service.subprocess.run',side_effect=run):
     job=m.start(cookie,data)
     for _ in range(500):
      job=m.status(cookie,job['job_id'])
      if job['status']=='failed':break
      time.sleep(.01)
     self.assertEqual(job['status'],'failed',failure);self.assertNotIn('audio_url',job)
     with self.assertRaises(ValueError):m.audio(cookie,job['job_id'])
   m.executor.shutdown()
if __name__=='__main__':unittest.main()

class RenderHTTPTests(unittest.TestCase):
 def test_authenticated_audio_range_and_origins(self):
  import http.client,http.server,save_service
  class Fake:
   def __init__(self,*args):pass
   def available(self):return [{'id':'modern-metal-1','label':'Modern Metal 1'}]
   def audio(self,cookie,job):
    if cookie!='riff_session='+'a'*32 or job!='b'*32:raise ValueError('unavailable')
    return b'RIFF0123456789'
  class Publisher:repo=pathlib.Path('.')
  with patch('render_service.RenderManager',Fake):
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),save_service.handler_for(Publisher(),['http://127.0.0.1:8768']));t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
   def request(method,path,headers,body=None):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request(method,path,body,headers);r=c.getresponse();result=(r.status,dict(r.getheaders()),r.read());c.close();return result
   base={'Origin':'http://127.0.0.1:8768','Cookie':'riff_session='+'a'*32}
   try:
    status,_,_=request('POST','/render/presets',{**base,'Content-Type':'application/json'},'{}');self.assertEqual(status,200)
    path='/render/audio?job='+'b'*32
    status,headers,body=request('GET',path,{**base,'Range':'bytes=0-3'});self.assertEqual((status,body),(206,b'RIFF'));self.assertEqual(headers['Content-Range'],'bytes 0-3/14');self.assertEqual(headers['Access-Control-Allow-Credentials'],'true')
    for value,expected in [('bytes=4-',b'0123456789'),('bytes=-4',b'6789'),('bytes=0-999',b'RIFF0123456789')]:
     status,_,body=request('GET',path,{**base,'Range':value});self.assertEqual((status,body),(206,expected))
    status,headers,_=request('GET',path,{**base,'Range':'bytes=99-100'});self.assertEqual(status,416);self.assertEqual(headers['Content-Range'],'bytes */14')
    self.assertEqual(request('GET',path,{'Origin':base['Origin']})[0],409)
    self.assertEqual(request('GET',path,{**base,'Origin':'https://evil.invalid'})[0],403)
    self.assertEqual(request('GET','/render/audio?path=secret',base)[0],409)
    self.assertEqual(request('OPTIONS',path,base)[0],204)
   finally:server.shutdown();server.server_close();t.join()
