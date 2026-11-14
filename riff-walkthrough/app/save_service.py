from runtime_options import SESSION_COOKIE
"""Narrow companion: save current generated MIDI through existing Git credentials.
Does not load, restart, regenerate, or persist generator sessions.
"""
import argparse, hashlib, http.client, http.cookies, http.server, json, math, os, pathlib, re, subprocess, threading, urllib.parse

from runtime_options import output_path

REPOSITORY='https://github.com/mtch777/Guitar-Learning.git'
BRANCH='generated-midi'
FOLDER='generated-midi'
WEB='https://github.com/mtch777/Guitar-Learning'
PREFIXES={1:'1_seed_rhythm_',2:'2_scaffold_rhythm_',3:'3_rhythm_',4:'4_opening_pitches_',5:'5_remaining_pitches_',6:'6_review_'}

class SaveError(Exception): pass

def midi_hash(data):
 if len(data)<14 or data[:4]!=b'MThd':raise SaveError('The generator did not return a valid MIDI file.')
 return hashlib.sha256(data).hexdigest()

class Publisher:
 def __init__(self,repo,source_port=8768):
  self.repo=output_path(repo);self.source_port=source_port;self.lock=threading.Lock()
 def git(self,*args,check=True):
  env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
  try:r=subprocess.run(['git','-C',str(self.repo),*args],capture_output=True,timeout=90,env=env)
  except (OSError,subprocess.TimeoutExpired) as e:raise SaveError('GitHub save timed out or Git is unavailable. Retry Save.') from e
  if check and r.returncode:raise SaveError('GitHub save could not be verified. Retry Save; identical files will not duplicate.')
  return r
 def current_audio_midi(self,cookie,stage,version,include_output=False,view='current'):
  from server import midi_bytes
  parsed=http.cookies.SimpleCookie()
  try:parsed.load(cookie or '')
  except http.cookies.CookieError:pass
  sid=parsed.get(SESSION_COOKIE)
  if not sid or not re.fullmatch(r'[A-Za-z0-9_-]{32}',sid.value):raise SaveError('This browser has no generator session. Return to the generator.')
  conn=http.client.HTTPConnection('127.0.0.1',self.source_port,timeout=30)
  try:
   conn.request('GET','/api/state',headers={'Cookie':SESSION_COOKIE+'='+sid.value})
   response=conn.getresponse();state=json.loads(response.read())
   if response.status!=200 or state.get('session_id')!=sid.value or state.get('version')!=version or state.get('busy'):raise SaveError('This result changed or is generating. Save the current result.')
  except (OSError,http.client.HTTPException,ValueError) as e:raise SaveError('Cannot read the running generator.') from e
  finally:conn.close()
  entry=next((s for s in state.get('stages',[]) if str(s.get('id'))==str(stage)),{})
  if view not in ('current','previous'):raise SaveError('Invalid playback snapshot.')
  out=(entry.get('previous') if view=='previous' else entry.get('output')) or {}
  audio=out.get('audio');partial=stage==5 and (str((audio or {}).get('label','')).startswith('Partial') if view=='previous' else entry.get('status')=='blocked')
  if view=='current' and entry.get('status')!='complete' and not partial:raise SaveError('This step has no current playback to save.')
  if not isinstance(audio,dict) or audio.get('unavailable') or audio.get('reason'):raise SaveError('This step has no available playback to save.')
  def number(x):return type(x) in (int,float) and math.isfinite(x)
  notes=audio.get('notes');length=audio.get('length_beats')
  if not isinstance(notes,list) or not number(length) or length<=0 or audio.get('tempo')!=120:raise SaveError('This playback cannot be exported accurately.')
  if partial and (not notes or (view=='current' and not out.get('blocker')) or not str(audio.get('label','')).startswith('Partial')):raise SaveError('This step has no partial playback to save.')
  for n in notes:
   if not isinstance(n,dict) or not all(number(n.get(k)) for k in ('start_beats','duration_beats','midi_pitch')):raise SaveError('Invalid playback note.')
   if n['start_beats']<0 or n['duration_beats']<=0 or n['midi_pitch']!=int(n['midi_pitch']) or not 0<=n['midi_pitch']<=127 or n['start_beats']+n['duration_beats']>length+1e-8:raise SaveError('Invalid playback note.')
  data=midi_bytes(audio);midi_hash(data)
  return (data,partial,out) if include_output else (data,partial)
 def current_midi(self,cookie,stage,version):return self.current_audio_midi(cookie,stage,version)[0]
 def publish(self,data,version,stage=6,partial=False,selected=False):
  if stage not in PREFIXES or (partial and stage!=5):raise SaveError('Invalid MIDI stage.')
  digest=midi_hash(data);prefix=PREFIXES[stage]+('partial_' if partial else '')+('selected_' if selected else '');relative=f'{FOLDER}/{prefix}{digest}.mid'
  if self.git('remote','get-url','origin').stdout.decode().strip()!=REPOSITORY:raise SaveError('Save repository configuration does not match the project.')
  if self.git('branch','--show-current').stdout.decode().strip()!=BRANCH:raise SaveError('Save repository is on the wrong branch.')
  dirty=self.git('status','--porcelain').stdout.decode().splitlines()
  if any(line[3:]!=relative for line in dirty):raise SaveError('Save repository has unrelated edits; nothing was changed.')
  self.git('fetch','origin',BRANCH)
  self.verify_ahead_midi_only()
  existed=self.git('cat-file','-e',f'FETCH_HEAD:{relative}',check=False).returncode==0
  if existed:
   if hashlib.sha256(self.git('show',f'FETCH_HEAD:{relative}').stdout).hexdigest()!=digest:raise SaveError('Existing saved file does not match; refusing to overwrite it.')
  else:
   self.git('merge','--ff-only','FETCH_HEAD')
   path=self.repo/relative;path.parent.mkdir(parents=True,exist_ok=True)
   if path.exists():
    if path.read_bytes()!=data:raise SaveError('Existing local file differs; refusing to overwrite it.')
   else:
    with path.open('xb') as f:f.write(data)
   self.git('add','--',relative)
   if self.git('diff','--cached','--quiet','--',relative,check=False).returncode:
    self.git('commit','-m','Save generated MIDI '+digest[:12],'--',relative)
   self.verify_ahead_midi_only()
   self.git('push','origin',f'HEAD:refs/heads/{BRANCH}')
   self.git('fetch','origin',BRANCH)
   if hashlib.sha256(self.git('show',f'FETCH_HEAD:{relative}').stdout).hexdigest()!=digest:raise SaveError('GitHub bytes could not be verified. Retry Save.')
  commit=self.git('rev-parse','FETCH_HEAD').stdout.decode().strip()
  return {'saved':True,'version':version,'stage':stage,'partial':partial,'sha256':digest,'size':len(data),'already_saved':existed,'commit':commit,'file_url':f'{WEB}/blob/{BRANCH}/{relative}','folder_url':f'{WEB}/tree/{BRANCH}/{FOLDER}'}
 def verify_ahead_midi_only(self):
  for commit in self.git('rev-list','FETCH_HEAD..HEAD').stdout.decode().splitlines():
   if len(self.git('rev-list','--parents','-n','1',commit).stdout.decode().split())>2:raise SaveError('Save repository has an unexpected local merge; nothing was pushed.')
   changes=self.git('diff-tree','--root','--no-commit-id','--name-status','-r',commit).stdout.decode().splitlines()
   for change in changes:
    parts=change.split('\t')
    if len(parts)!=2 or parts[0]!='A':raise SaveError('Save repository has unrelated local commits; nothing was pushed.')
    path=parts[1];match=re.fullmatch(r'generated-midi/(?:riff-|1_seed_rhythm_(?:selected_)?|2_scaffold_rhythm_(?:selected_)?|3_rhythm_(?:selected_)?|4_opening_pitches_(?:selected_)?|5_remaining_pitches_(?:partial_)?(?:selected_)?|6_review_(?:selected_)?)([a-f0-9]{64})\.mid',path)
    if not match or midi_hash(self.git('show',f'{commit}:{path}').stdout)!=match.group(1):raise SaveError('Save repository has unrelated local commits; nothing was pushed.')
 def save(self,cookie,stage,version):
  # Snapshot the clicked version before waiting for a slow Git operation.
  data,partial=self.current_audio_midi(cookie,stage,version)
  if not self.lock.acquire(blocking=False):raise SaveError('Another MIDI is being saved. Wait, then retry Save.')
  try:return self.publish(data,version,stage,partial)
  finally:self.lock.release()
 def recover(self,sid):
  # This bearer identifier stays between the user's browser and local services.
  # Never log it, return it to the UI, store it, or include it in Git metadata.
  if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}',sid):raise SaveError('No usable previous session reference was found.')
  conn=http.client.HTTPConnection('127.0.0.1',self.source_port,timeout=30)
  try:
   conn.request('GET','/api/state',headers={'Cookie':SESSION_COOKIE+'='+sid});response=conn.getresponse();state=json.loads(response.read())
   if response.status!=200 or state.get('session_id')!=sid:raise SaveError('The previous session is no longer available.')
   version=state.get('version');final=next((s for s in state.get('stages',[]) if str(s.get('id'))=='6'),{})
   if state.get('busy') or type(version) is not int or version<1 or final.get('status')!='complete' or not (final.get('output') or {}).get('can_export'):raise SaveError('The previous session has no complete current MIDI to save.')
  except (OSError,http.client.HTTPException,ValueError) as e:raise SaveError('The previous session could not be read.') from e
  finally:conn.close()
  result=self.save(SESSION_COOKIE+'='+sid,6,version)
  result['previous_session']=True
  return result

def handler_for(publisher,allowed_origins):
 allowed_origins=frozenset(allowed_origins)
 from editor_service import EditorManager
 from selection_service import SelectionManager
 from render_service import RenderManager
 editor=None
 selection=None
 renderer=None
 routes=['/save','/recover','/editor/open','/editor/plan','/editor/regenerate','/editor/delete','/editor/save','/selection/open','/selection/save','/render/presets','/render/start','/render/status','/render/audio']
 class Handler(http.server.BaseHTTPRequestHandler):
  def reply(self,code,data,origin=None):
   body=json.dumps(data).encode();self.send_response(code)
   self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
   if origin in allowed_origins:
    self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Vary','Origin')
   self.end_headers();self.wfile.write(body)
  def do_OPTIONS(self):
   origin=self.headers.get('Origin')
   if urllib.parse.urlparse(self.path).path not in routes or origin not in allowed_origins:self.reply(403,{'error':'Origin not allowed'});return
   self.send_response(204);self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Access-Control-Allow-Methods','GET, POST');self.send_header('Access-Control-Allow-Headers','Content-Type, Range');self.send_header('Vary','Origin');self.end_headers()
  def do_POST(self):
   nonlocal editor,selection,renderer
   origin=self.headers.get('Origin')
   if self.path not in routes or origin not in allowed_origins:self.reply(403,{'error':'Origin not allowed'});return
   try:
    if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=2048:raise ValueError('Invalid request size')
    data=json.loads(self.rfile.read(length))
    if not isinstance(data,dict):raise ValueError('Object required')
    if self.path.startswith('/render/'):
     if editor is None:editor=EditorManager(publisher)
     if selection is None:selection=SelectionManager(publisher)
     if renderer is None:renderer=RenderManager(publisher,editor,selection)
     try:
      if self.path=='/render/presets' and not data:result={'presets':renderer.available()}
      elif self.path=='/render/start':result=renderer.start(self.headers.get('Cookie'),data)
      elif self.path=='/render/status' and set(data)=={'job_id'}:result=renderer.status(self.headers.get('Cookie'),data['job_id'])
      else:raise ValueError('Invalid Kontakt request.')
     except ValueError as e:raise SaveError(str(e)) from e
     self.reply(200,result,origin);return
    if self.path.startswith('/selection/'):
     if selection is None:selection=SelectionManager(publisher)
     try:result=selection.request(self.path,self.headers.get('Cookie'),data)
     except (ValueError,KeyError,AssertionError) as e:raise SaveError(str(e)) from e
     self.reply(200,result,origin);return
    if self.path.startswith('/editor/'):
     if editor is None:editor=EditorManager(publisher)
     try:result=editor.request(self.path,self.headers.get('Cookie'),data)
     except (ValueError,KeyError,AssertionError) as e:raise SaveError(str(e)) from e
     self.reply(200,result,origin);return
    if self.path=='/recover':
     if set(data)!={'session_id'}:raise ValueError('Invalid recovery request')
     self.reply(200,publisher.recover(data['session_id']),origin);return
    stage=data.get('stage');version=data.get('version')
    if set(data)!={'stage','version'} or type(stage) is not int or stage not in PREFIXES or type(version) is not int or version<1:raise ValueError('Invalid current MIDI version')
    result=publisher.save(self.headers.get('Cookie'),stage,version);self.reply(200,result,origin)
   except (ValueError,TypeError,json.JSONDecodeError):self.reply(400,{'error':'Provide a current stage 1–6 MIDI version.'},origin)
   except SaveError as e:self.reply(409,{'error':str(e)},origin)
   except Exception:self.reply(500,{'error':'Save failed. No successful GitHub save was confirmed.'},origin)
  def do_GET(self):
   origin=self.headers.get('Origin');query=urllib.parse.urlparse(self.path)
   if query.path!='/render/audio':self.reply(405,{'error':'Use the generator controls.'});return
   if origin not in allowed_origins:self.reply(403,{'error':'Origin not allowed'});return
   try:
    if renderer is None:raise ValueError('Audio is not ready.')
    args=urllib.parse.parse_qs(query.query)
    if set(args)!={'job'} or len(args['job'])!=1:raise ValueError('Invalid audio request.')
    body=renderer.audio(self.headers.get('Cookie'),args['job'][0]);size=len(body);start=0;end=size-1;code=200
    requested=self.headers.get('Range')
    if requested:
     match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
     invalid=not match or not any(match.groups())
     if not invalid and match.group(1):start=int(match.group(1));end=min(end,int(match.group(2))) if match.group(2) else end
     elif not invalid:start=max(0,size-int(match.group(2)))
     if invalid or not 0<=start<=end<size:
      self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.end_headers();return
     code=206
    self.send_response(code);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Vary','Origin')
    if code==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
    self.end_headers();self.wfile.write(body[start:end+1])
   except ValueError as e:self.reply(409,{'error':str(e)},origin)
  def log_message(self,*args):pass  # Never put cookies or request payloads in logs.
 return Handler

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8769);p.add_argument('--source-port',type=int,default=8768);p.add_argument('--origin',action='append',required=True);a=p.parse_args()
 publisher=Publisher(a.repo,a.source_port)
 server=http.server.ThreadingHTTPServer((a.host,a.port),handler_for(publisher,a.origin))
 print('MIDI save companion ready',flush=True);server.serve_forever()
