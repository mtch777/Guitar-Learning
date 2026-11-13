"""Narrow companion: save current generated MIDI through existing Git credentials.
Does not load, restart, regenerate, or persist generator sessions.
"""
import argparse, hashlib, http.client, http.cookies, http.server, json, os, pathlib, re, subprocess, threading

REPOSITORY='https://github.com/mtch777/Guitar-Learning.git'
BRANCH='generated-midi'
FOLDER='generated-midi'
WEB='https://github.com/mtch777/Guitar-Learning'

class SaveError(Exception): pass

def midi_hash(data):
 if len(data)<14 or data[:4]!=b'MThd':raise SaveError('The generator did not return a valid MIDI file.')
 return hashlib.sha256(data).hexdigest()

class Publisher:
 def __init__(self,repo,source_port=8768):
  self.repo=pathlib.Path(repo).resolve();self.source_port=source_port;self.lock=threading.Lock()
 def git(self,*args,check=True):
  env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
  try:r=subprocess.run(['git','-C',str(self.repo),*args],capture_output=True,timeout=90,env=env)
  except (OSError,subprocess.TimeoutExpired) as e:raise SaveError('GitHub save timed out or Git is unavailable. Retry Save.') from e
  if check and r.returncode:raise SaveError('GitHub save could not be verified. Retry Save; identical files will not duplicate.')
  return r
 def current_midi(self,cookie,stage,version):
  parsed=http.cookies.SimpleCookie()
  try:parsed.load(cookie or '')
  except http.cookies.CookieError:pass
  sid=parsed.get('riff_session')
  if not sid:raise SaveError('This browser has no generator session. Return to the generator.')
  # Forward only this application's cookie, only to its loopback endpoint.
  conn=http.client.HTTPConnection('127.0.0.1',self.source_port,timeout=30)
  try:
   conn.request('GET',f'/api/midi?stage={stage}&version={version}',headers={'Cookie':'riff_session='+sid.value})
   response=conn.getresponse();data=response.read()
   if response.status!=200:raise SaveError('This MIDI is no longer current or complete. Save the current result.')
  except (OSError,http.client.HTTPException) as e:raise SaveError('Cannot reach the running generator.') from e
  finally:conn.close()
  midi_hash(data);return data
 def publish(self,data,version):
  digest=midi_hash(data);relative=f'{FOLDER}/riff-{digest}.mid'
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
  return {'saved':True,'version':version,'sha256':digest,'size':len(data),'already_saved':existed,'commit':commit,'file_url':f'{WEB}/blob/{BRANCH}/{relative}','folder_url':f'{WEB}/tree/{BRANCH}/{FOLDER}'}
 def verify_ahead_midi_only(self):
  for commit in self.git('rev-list','FETCH_HEAD..HEAD').stdout.decode().splitlines():
   if len(self.git('rev-list','--parents','-n','1',commit).stdout.decode().split())>2:raise SaveError('Save repository has an unexpected local merge; nothing was pushed.')
   changes=self.git('diff-tree','--root','--no-commit-id','--name-status','-r',commit).stdout.decode().splitlines()
   for change in changes:
    parts=change.split('\t')
    if len(parts)!=2 or parts[0]!='A':raise SaveError('Save repository has unrelated local commits; nothing was pushed.')
    path=parts[1];match=re.fullmatch(r'generated-midi/riff-([a-f0-9]{64})\.mid',path)
    if not match or midi_hash(self.git('show',f'{commit}:{path}').stdout)!=match.group(1):raise SaveError('Save repository has unrelated local commits; nothing was pushed.')
 def save(self,cookie,stage,version):
  # Snapshot the clicked version before waiting for a slow Git operation.
  data=self.current_midi(cookie,stage,version)
  if not self.lock.acquire(blocking=False):raise SaveError('Another MIDI is being saved. Wait, then retry Save.')
  try:return self.publish(data,version)
  finally:self.lock.release()
 def recover(self,sid):
  # This bearer identifier stays between the user's browser and local services.
  # Never log it, return it to the UI, store it, or include it in Git metadata.
  if not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32}',sid):raise SaveError('No usable previous session reference was found.')
  conn=http.client.HTTPConnection('127.0.0.1',self.source_port,timeout=30)
  try:
   conn.request('GET','/api/state',headers={'Cookie':'riff_session='+sid});response=conn.getresponse();state=json.loads(response.read())
   if response.status!=200 or state.get('session_id')!=sid:raise SaveError('The previous session is no longer available.')
   version=state.get('version');final=next((s for s in state.get('stages',[]) if str(s.get('id'))=='6'),{})
   if state.get('busy') or type(version) is not int or version<1 or final.get('status')!='complete' or not (final.get('output') or {}).get('can_export'):raise SaveError('The previous session has no complete current MIDI to save.')
  except (OSError,http.client.HTTPException,ValueError) as e:raise SaveError('The previous session could not be read.') from e
  finally:conn.close()
  result=self.save('riff_session='+sid,6,version)
  result['previous_session']=True
  return result

def handler_for(publisher,allowed_origins):
 allowed_origins=frozenset(allowed_origins)
 class Handler(http.server.BaseHTTPRequestHandler):
  def reply(self,code,data,origin=None):
   body=json.dumps(data).encode();self.send_response(code)
   self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
   if origin in allowed_origins:
    self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Vary','Origin')
   self.end_headers();self.wfile.write(body)
  def do_OPTIONS(self):
   origin=self.headers.get('Origin')
   if self.path not in ['/save','/recover'] or origin not in allowed_origins:self.reply(403,{'error':'Origin not allowed'});return
   self.send_response(204);self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Credentials','true');self.send_header('Access-Control-Allow-Methods','POST');self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Vary','Origin');self.end_headers()
  def do_POST(self):
   origin=self.headers.get('Origin')
   if self.path not in ['/save','/recover'] or origin not in allowed_origins:self.reply(403,{'error':'Origin not allowed'});return
   try:
    if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('JSON required')
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=2048:raise ValueError('Invalid request size')
    data=json.loads(self.rfile.read(length))
    if not isinstance(data,dict):raise ValueError('Object required')
    if self.path=='/recover':
     if set(data)!={'session_id'}:raise ValueError('Invalid recovery request')
     self.reply(200,publisher.recover(data['session_id']),origin);return
    stage=data.get('stage');version=data.get('version')
    if set(data)!={'stage','version'} or type(stage) is not int or stage!=6 or type(version) is not int or version<1:raise ValueError('Invalid current MIDI version')
    result=publisher.save(self.headers.get('Cookie'),stage,version);self.reply(200,result,origin)
   except (ValueError,TypeError,json.JSONDecodeError):self.reply(400,{'error':'Provide a current stage 6 MIDI version.'},origin)
   except SaveError as e:self.reply(409,{'error':str(e)},origin)
   except Exception:self.reply(500,{'error':'Save failed. No successful GitHub save was confirmed.'},origin)
  def do_GET(self):self.reply(405,{'error':'Use Save in the generator.'})
  def log_message(self,*args):pass  # Never put cookies or request payloads in logs.
 return Handler

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8769);p.add_argument('--source-port',type=int,default=8768);p.add_argument('--origin',action='append',required=True);a=p.parse_args()
 publisher=Publisher(a.repo,a.source_port)
 server=http.server.ThreadingHTTPServer((a.host,a.port),handler_for(publisher,a.origin))
 print('MIDI save companion ready',flush=True);server.serve_forever()
