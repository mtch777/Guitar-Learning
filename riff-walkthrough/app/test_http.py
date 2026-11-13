import unittest,threading,urllib.request,urllib.error,http.cookiejar,json,time
import server
class Stub:
 def config(self):return {'stages':[]}
 def validate(self,p):return {str(i):{} for i in range(1,7)}
 def stage1(self,p):return {'summary':{'test':True},'phrases':[{'phrase':1}],'raw':{'private':'no'}}
 def __getattr__(self,name):
  if name.startswith('stage'):return lambda p,u,**kw:{'summary':{},'phrases':[{'phrase':1}],'audio':{'notes':[{'start_beats':0,'duration_beats':1,'midi_pitch':28}],'length_beats':1},'can_export':name=='stage6'}
  raise AttributeError(name)
class TestHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.app=server.App();cls.app.loading=False;cls.app.engine=Stub();cls.http=server.http.server.ThreadingHTTPServer(('127.0.0.1',0),server.handler_for(cls.app));cls.url='http://127.0.0.1:'+str(cls.http.server_address[1]);cls.t=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.t.start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
 def setUp(self):self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def req(self,path,body=None,headers={}):
  r=self.client.open(urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**headers}));return r,json.loads(r.read())
 def test_cookie_and_no_raw(self):
  r,s=self.req('/api/state');self.assertIn('HttpOnly',r.headers.get('Set-Cookie'));_,s2=self.req('/api/state');self.assertEqual(s['session_id'],s2['session_id'])
  self.req('/api/generate',{'stage':1,'params':{}})
  for _ in range(100):
   _,s=self.req('/api/state')
   if not s['busy']:break
   time.sleep(.01)
  self.assertTrue(all(x['status']=='complete' for x in s['stages']));self.assertNotIn('raw',s['stages'][0]['output'])
  r=self.client.open(self.url+'/api/midi?stage=6&version='+str(s['version']));self.assertEqual(r.read()[:4],b'MThd')
  with self.assertRaises(urllib.error.HTTPError) as e:self.client.open(self.url+'/api/midi?stage=6&version=-1')
  self.assertEqual(e.exception.code,409)
 def test_cross_origin_rejected(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/generate',{'stage':1},{'Origin':'https://example.com'})
  self.assertEqual(e.exception.code,403)
 def test_paths_unavailable(self):
  for path in ['/server.py','/../engine.py','/api/files']:
   with self.assertRaises(urllib.error.HTTPError) as e:self.req(path)
   self.assertEqual(e.exception.code,404)
if __name__=='__main__':unittest.main()
