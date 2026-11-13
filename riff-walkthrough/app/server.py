"""Local-only HTML/API server. No external calls, arbitrary file access, or writes to source corpus."""
import argparse,copy,http.cookies,http.server,json,mimetypes,pathlib,secrets,struct,threading,time,urllib.parse,traceback
import engine as E
ROOT=pathlib.Path(__file__).resolve().parent
STATIC=ROOT/'static'

def strip_raw(o):
 if o is None:return None
 return {k:copy.deepcopy(v) for k,v in o.items() if k!='raw'}
def midi_bytes(audio):
 # Note-offs first at equal ticks. 120 BPM is a rendering default, not inferred expression.
 ticks=960;events=[]
 for i,n in enumerate(audio['notes']):
  a=round(n['start_beats']*ticks);b=round((n['start_beats']+n['duration_beats'])*ticks);p=int(n['midi_pitch'])
  if not 0<=p<=127 or b<=a:raise ValueError('Invalid MIDI note')
  # Preserve all note events on the one requested instrument channel.
  # Overlapping unisons remain separate events; no silent merging.
  ch=0
  events.extend([(a,1,bytes([0x90|ch,p,90])),(b,0,bytes([0x80|ch,p,0]))])
 def var(n):
  out=[n&127];n>>=7
  while n:out.insert(0,128|(n&127));n>>=7
  return bytes(out)
 track=b'\x00\xff\x51\x03\x07\xa1\x20';last=0
 for t,_,data in sorted(events,key=lambda x:(x[0],x[1])):track+=var(t-last)+data;last=t
 end=max(last,round(audio.get('length_beats',0)*ticks));track+=var(end-last)+b'\xff\x2f\x00'
 return b'MThd'+struct.pack('>IHHH',6,0,1,ticks)+b'MTrk'+struct.pack('>I',len(track))+track

class Session:
 def __init__(self):
  self.id=secrets.token_urlsafe(24);self.version=0;self.busy=False;self.error=None;self.lock=threading.RLock()
  self.stages=[{'id':str(i),'status':'empty','applied':None,'output':None,'previous':None} for i in range(1,7)]
 def public(self):
  with self.lock:return {'session_id':self.id,'version':self.version,'busy':self.busy,'error':self.error,'stages':[{**s,'output':strip_raw(s['output']),'previous':strip_raw(s['previous'])} for s in self.stages]}
 def begin(self,stage,params,engine):
  params=engine.validate(params)
  with self.lock:
   if self.busy:raise RuntimeError('Generation already running')
   if stage<1 or stage>5:raise ValueError('Select a generation step from 1 to 5')
   if any(s['status']!='complete' for s in self.stages[:stage-1]):raise ValueError('Generate the preceding steps first')
   self.version+=1;self.busy=True;self.error=None
   for s in self.stages[stage-1:]:
    if s['output'] is not None and (s['output'].get('phrases') or s['output'].get('audio')):s['previous']={**copy.deepcopy(s['output']),'applied':copy.deepcopy(s['applied'])}
    s['output']=None;s['status']='queued';s['applied']=None
   return params
 def run(self,stage,params,engine,job_lock):
  try:
   with job_lock:
    for number in range(stage,7):
     with self.lock:
      state=self.stages[number-1];state['status']='running';state['applied']=copy.deepcopy(params[str(number)])
      upstream=[s['output'] for s in self.stages[:number-1]]
     def progress(partial):
      with self.lock:state['output']=partial
     try:
      if number==5:out=engine.stage5(params['5'],upstream,progress=progress)
      else:out=getattr(engine,'stage'+str(number))(params[str(number)],upstream) if number>1 else engine.stage1(params['1'])
     except Exception as exc:
      # Do not send stack traces/filesystem paths to browsers.
      print('Generation failure',number,repr(exc),flush=True);traceback.print_exc()
      with self.lock:
       state['status']='error';state['output']={'summary':{},'phrases':[],'blocker':str(exc) if isinstance(exc,ValueError) else 'Generation failed. See the local server log.'}
       for s in self.stages[number:]:s['status']='blocked';s['output']={'summary':{},'phrases':[],'blocker':'Waiting for step '+str(number)}
      break
     with self.lock:
      state['output']=out;state['status']='blocked' if out.get('blocker') else 'complete'
      if out.get('blocker'):
       for s in self.stages[number:]:s['status']='blocked';s['output']={'summary':{},'phrases':[],'blocker':'Waiting for step '+str(number)}
       break
  finally:
   with self.lock:self.busy=False

class App:
 def __init__(self):
  self.engine=None;self.loading=True;self.error=None;self.sessions={};self.lock=threading.Lock();self.job_lock=threading.Lock()
 def load(self):
  try:self.engine=E.Engine();print('Engine ready',flush=True)
  except Exception:traceback.print_exc();self.error='Dataset could not be loaded. See the local server log.'
  finally:self.loading=False
 def session(self,cookie):
  c=http.cookies.SimpleCookie()
  try:c.load(cookie or '')
  except http.cookies.CookieError:pass
  sid=c.get('riff_session');sid=sid.value if sid else None
  with self.lock:
   if sid not in self.sessions:
    s=Session();self.sessions[s.id]=s;return s,True
   return self.sessions[sid],False

def handler_for(app):
 class Handler(http.server.BaseHTTPRequestHandler):
  def reply(self,status,body,kind='application/json',cookie=None):
   if not isinstance(body,bytes):body=json.dumps(body,allow_nan=False).encode()
   self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
   if cookie:self.send_header('Set-Cookie','riff_session='+cookie+'; HttpOnly; SameSite=Strict; Path=/')
   self.end_headers();self.wfile.write(body)
  def do_GET(self):
   path=urllib.parse.urlsplit(self.path);s,new=app.session(self.headers.get('Cookie'));cookie=s.id if new else None
   if path.path=='/api/state':self.reply(200,{**s.public(),'loading':app.loading,'load_error':app.error},cookie=cookie);return
   if path.path=='/api/config':
    if app.loading or app.error:self.reply(503,{'loading':app.loading,'error':app.error or 'Loading dataset'},cookie=cookie);return
    self.reply(200,app.engine.config(),cookie=cookie);return
   if path.path=='/api/midi':
    try:
     q=urllib.parse.parse_qs(path.query);i=int(q.get('stage',['6'])[0]);v=int(q.get('version',['-1'])[0])
     with s.lock:
      if s.busy or v!=s.version or not 1<=i<=6:raise ValueError('Result changed; refresh before exporting')
      stage=s.stages[i-1];out=stage['output']
      if stage['status']!='complete' or not out or not out.get('can_export'):raise ValueError('Complete generated notes are required for MIDI export')
      body=midi_bytes(out['audio'])
     self.reply(200,body,'audio/midi',cookie=cookie)
    except (ValueError,KeyError,TypeError):self.reply(409,{'error':'MIDI is unavailable for this result'},cookie=cookie)
    return
   routes={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
   if path.path not in routes:self.reply(404,{'error':'Not found'},cookie=cookie);return
   f=STATIC/routes[path.path]
   if not f.exists():self.reply(503,{'error':'UI build in progress'},cookie=cookie);return
   self.reply(200,f.read_bytes(),mimetypes.guess_type(str(f))[0] or 'application/octet-stream',cookie=cookie)
  def do_POST(self):
   if self.path!='/api/generate':self.reply(404,{'error':'Not found'});return
   # Same-origin requests only, including LAN host:port; no permissive CORS.
   origin=self.headers.get('Origin')
   if origin and urllib.parse.urlsplit(origin).netloc!=self.headers.get('Host'):self.reply(403,{'error':'Cross-origin request rejected'});return
   if app.loading or app.error:self.reply(503,{'error':app.error or 'Dataset is still loading'});return
   s,new=app.session(self.headers.get('Cookie'));cookie=s.id if new else None
   try:
    length=int(self.headers.get('Content-Length','0'))
    if length<=0 or length>100000:raise ValueError('Invalid request size')
    data=json.loads(self.rfile.read(length));stage=int(data['stage']);params=s.begin(stage,data.get('params',{}),app.engine)
    t=threading.Thread(target=s.run,args=(stage,params,app.engine,app.job_lock),daemon=True);t.start();self.reply(202,{'started':True,'version':s.version},cookie=cookie)
   except RuntimeError as e:self.reply(409,{'error':str(e)},cookie=cookie)
   except (ValueError,TypeError,KeyError) as e:self.reply(400,{'error':str(e)},cookie=cookie)
  def log_message(self,format,*args):
   if self.path not in ['/api/state','/api/config']:super().log_message(format,*args)
 return Handler
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8768);a=p.parse_args();app=App();threading.Thread(target=app.load,daemon=True).start();server=http.server.ThreadingHTTPServer((a.host,a.port),handler_for(app));print(f'Listening at http://{a.host}:{a.port}',flush=True);server.serve_forever()
