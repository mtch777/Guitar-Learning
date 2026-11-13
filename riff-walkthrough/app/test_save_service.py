import hashlib,http.client,http.server,json,pathlib,subprocess,tempfile,threading,unittest
import save_service as S

MIDI=bytes.fromhex('4d546864000000060000000103c04d54726b0000000400ff2f00')

class SaveHTTPTests(unittest.TestCase):
 def setUp(self):
  self.calls=[]
  outer=self
  class Stub:
   def save(self,cookie,stage,version):outer.calls.append((cookie,stage,version));return {'saved':True,'version':version}
  self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),S.handler_for(Stub(),['http://127.0.0.1:8768']))
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join()
 def request(self,body,origin='http://127.0.0.1:8768',method='POST'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);headers={'Content-Type':'application/json','Cookie':'riff_session=test'}
  if origin is not None:headers['Origin']=origin
  c.request(method,'/save',json.dumps(body),headers);r=c.getresponse();out=(r.status,dict(r.getheaders()),r.read());c.close();return out
 def test_origin_missing_or_foreign_rejected(self):
  for origin in [None,'https://evil.invalid','null']:
   status,headers,_=self.request({'stage':6,'version':2},origin);self.assertEqual(status,403);self.assertNotIn('Access-Control-Allow-Origin',headers)
  self.assertEqual(self.calls,[])
 def test_exact_request_and_credentials_cors(self):
  status,headers,_=self.request({'stage':6,'version':2});self.assertEqual(status,200)
  self.assertEqual(headers['Access-Control-Allow-Origin'],'http://127.0.0.1:8768');self.assertEqual(headers['Access-Control-Allow-Credentials'],'true')
  self.assertEqual(self.calls,[('riff_session=test',6,2)])
 def test_client_cannot_choose_repo_path_or_invalid_version(self):
  for body in [{'stage':6,'version':2,'repo':'other'},{'stage':7,'version':2},{'stage':6,'version':True},{'stage':6,'version':0}]:
   self.assertEqual(self.request(body)[0],400)
  self.assertEqual(self.calls,[])
 def test_get_cannot_publish(self):self.assertEqual(self.request({},method='GET')[0],405);self.assertEqual(self.calls,[])

class SourceTests(unittest.TestCase):
 def test_recovery_uses_local_identity_and_complete_version_only(self):
  sid='a'*32;seen=[];state={'session_id':sid,'version':2,'busy':False,'stages':[{'id':'6','status':'complete','output':{'can_export':True}}]}
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):
    seen.append((self.path,self.headers.get('Cookie')));self.send_response(200);self.end_headers();self.wfile.write(json.dumps(state).encode())
   def log_message(self,*args):pass
  class FakePublisher(S.Publisher):
   def save(self,cookie,stage,version):
    self.saved=(cookie,stage,version);return {'saved':True,'version':version}
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  try:
   p=FakePublisher('.',server.server_port);result=p.recover(sid)
   self.assertEqual(p.saved,('riff_session='+sid,6,2));self.assertEqual(seen,[('/api/state','riff_session='+sid)])
   self.assertNotIn(sid,json.dumps(result));self.assertTrue(result['previous_session'])
   state['session_id']='b'*32
   with self.assertRaises(S.SaveError):p.recover(sid)
   state['session_id']=sid;state['stages'][0]['status']='blocked'
   with self.assertRaises(S.SaveError):p.recover(sid)
   with self.assertRaises(S.SaveError):p.recover('invalid')
  finally:server.shutdown();server.server_close();t.join()
 def test_all_stage_snapshots_and_blockers(self):
  from server import midi_bytes
  sid='a'*32;seen=[]
  audio={'notes':[{'start_beats':0,'duration_beats':1,'midi_pitch':28}],'tempo':120,'length_beats':4,'label':'Rhythm'}
  state={'session_id':sid,'version':2,'busy':False,'stages':[{'id':str(i),'status':'complete','output':{'audio':dict(audio)}} for i in range(1,7)]}
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_GET(self):
    seen.append((self.path,self.headers.get('Cookie')));self.send_response(200);self.end_headers();self.wfile.write(json.dumps(state).encode())
   def log_message(self,*args):pass
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
  try:
   p=S.Publisher('.',server.server_port);cookie='unrelated=secret; riff_session='+sid
   for i in range(1,7):self.assertEqual(p.current_audio_midi(cookie,i,2),(midi_bytes(audio),False))
   self.assertTrue(all(x==('/api/state','riff_session='+sid) for x in seen))
   with self.assertRaises(S.SaveError):p.current_midi(cookie,1,1)
   with self.assertRaises(S.SaveError):p.current_midi('',1,2)
   state['busy']=True
   with self.assertRaises(S.SaveError):p.current_midi(cookie,1,2)
   state['busy']=False;state['session_id']='b'*32
   with self.assertRaises(S.SaveError):p.current_midi(cookie,1,2)
   state['session_id']=sid
   for status in ['stale','pending','error','blocked','empty']:
    state['stages'][0]['status']=status
    with self.assertRaises(S.SaveError):p.current_midi(cookie,1,2)
   state['stages'][0]['status']='complete';a=state['stages'][0]['output']['audio']
   for key,value in [('unavailable','bad'),('tempo',90),('length_beats',0)]:
    old=a.get(key);a[key]=value
    with self.assertRaises(S.SaveError):p.current_midi(cookie,1,2)
    if old is None:a.pop(key)
    else:a[key]=old
   a['notes']=[];self.assertEqual(p.current_midi(cookie,1,2),midi_bytes(a))
   partial=state['stages'][4];partial['status']='blocked';partial['output']['blocker']='Stopped';partial['output']['audio']['label']='Partial generated pitches'
   data,ispartial=p.current_audio_midi(cookie,5,2);self.assertTrue(ispartial);self.assertEqual(data,midi_bytes(partial['output']['audio']))
   partial['output']['audio']['notes']=[]
   with self.assertRaises(S.SaveError):p.current_midi(cookie,5,2)
  finally:server.shutdown();server.server_close();t.join()

class GitTests(unittest.TestCase):
 def test_ahead_merge_rejected_before_diff(self):
  class Fake(S.Publisher):
   def git(self,*args,**kwargs):
    if args==('rev-list','FETCH_HEAD..HEAD'):return subprocess.CompletedProcess([],0,stdout=b'commit\n')
    if args==('rev-list','--parents','-n','1','commit'):return subprocess.CompletedProcess([],0,stdout=b'commit parent1 parent2\n')
    raise AssertionError('Unexpected Git operation')
  with self.assertRaisesRegex(S.SaveError,'merge'):Fake('.').verify_ahead_midi_only()
 def test_exact_remote_bytes_and_idempotent_retry(self):
  old=S.REPOSITORY
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);remote=root/'remote.git';work=root/'work'
   def run(*args):return subprocess.run(['git',*map(str,args)],check=True,capture_output=True)
   run('init','--bare',remote);run('init','-b','generated-midi',work)
   run('-C',work,'config','user.name','Fixture');run('-C',work,'config','user.email','fixture@example.invalid')
   (work/'generated-midi').mkdir();(work/'generated-midi/README.md').write_text('Test fixture')
   run('-C',work,'add','.');run('-C',work,'commit','-m','Fixture');run('-C',work,'remote','add','origin',remote);run('-C',work,'push','origin','HEAD')
   try:
    S.REPOSITORY=str(remote);p=S.Publisher(work);first=p.publish(MIDI,2);again=p.publish(MIDI,2)
    self.assertFalse(first['already_saved']);self.assertTrue(again['already_saved']);self.assertEqual(first['commit'],again['commit'])
    path='generated-midi/6_review_'+hashlib.sha256(MIDI).hexdigest()+'.mid'
    self.assertEqual(run('--git-dir',remote,'show','generated-midi:'+path).stdout,MIDI)
    for stage in range(1,7):
     result=p.publish(MIDI,2,stage);prefix=S.PREFIXES[stage];expected='generated-midi/'+prefix+hashlib.sha256(MIDI).hexdigest()+'.mid'
     self.assertEqual(run('--git-dir',remote,'show','generated-midi:'+expected).stdout,MIDI)
     self.assertEqual(result['stage'],stage)
     selection=p.publish(MIDI,2,stage,selected=True);self.assertIn(prefix+'selected_',selection['file_url']);self.assertEqual(p.publish(MIDI,2,stage,selected=True)['commit'],selection['commit'])
    result=p.publish(MIDI,2,5,True);self.assertIn('5_remaining_pitches_partial_',result['file_url']);self.assertTrue(result['partial'])
    result=p.publish(MIDI,2,6,False,selected=True);self.assertIn('6_review_selected_',result['file_url'])
    self.assertEqual(p.publish(MIDI,2,6,False,selected=True)['commit'],result['commit'])
    result=p.publish(MIDI,2,5,True,True);self.assertIn('5_remaining_pitches_partial_selected_',result['file_url'])
    first=result
    (work/'unrelated.txt').write_text('keep')
    with self.assertRaises(S.SaveError):p.publish(MIDI,2)
    self.assertEqual((work/'unrelated.txt').read_text(),'keep')
    run('-C',work,'add','unrelated.txt');run('-C',work,'commit','-m','Unrelated local commit')
    with self.assertRaises(S.SaveError):p.publish(MIDI,2)
    self.assertEqual(run('--git-dir',remote,'rev-parse','generated-midi').stdout.decode().strip(),first['commit'])
   finally:S.REPOSITORY=old

if __name__=='__main__':unittest.main()
