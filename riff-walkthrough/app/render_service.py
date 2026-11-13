"""Isolated Kontakt renders of captured playback. Never regenerates source music."""
import array,concurrent.futures,copy,hashlib,http.cookies,json,math,os,pathlib,struct,subprocess,threading,time,uuid,wave
from server import midi_bytes
from editor_service import selected_audio

PRESETS={'modern-metal-1':('Modern Metal 1','verify-console-live.state'),'ready-to-djent':('Ready to Djent','verify-console-djent.state')}

def owner(cookie):
 import re
 parsed=http.cookies.SimpleCookie()
 try:parsed.load(cookie or '')
 except http.cookies.CookieError:pass
 sid=parsed.get('riff_session')
 if not sid or not re.fullmatch(r'[A-Za-z0-9_-]{32}',sid.value):raise ValueError('No current generator session.')
 return hashlib.sha256(sid.value.encode()).hexdigest()

def selected_in_place(output,selected):
 # Keep source time positions, including leading rests and unselected gaps.
 selected_audio(output,selected) # Validate IDs using the export policy.
 spans=[]
 for p in output['phrases']:
  if p['phrase'] not in set(selected):continue
  a=float(p['start_beats']);b=a+float(p['length_beats'])
  if spans and abs(spans[-1][1]-a)<1e-8:spans[-1]=(spans[-1][0],b)
  else:spans.append((a,b))
 audio=copy.deepcopy(output['audio']);audio['notes']=[]
 for a,b in spans:
  for n in output['audio']['notes']:
   start=max(a,n['start_beats']);end=min(b,n['start_beats']+n['duration_beats'])
   if end>start:audio['notes'].append(copy.deepcopy(n) if start==n['start_beats'] and end==n['start_beats']+n['duration_beats'] else {**n,'start_beats':start,'duration_beats':end-start})
 return audio

def inspect_wav(path,seconds):
 with wave.open(str(path),'rb') as f:
  channels,width,rate,frames=f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes();raw=f.readframes(frames)
 if channels!=2 or width!=2 or rate!=44100 or abs(frames/rate-seconds)>.1 or len(raw)!=frames*4:raise ValueError('Rendered audio format or duration is invalid.')
 values=array.array('h',raw)
 import sys
 if sys.byteorder!='little':values.byteswap()
 if not values or max(abs(v) for v in values)==0:raise ValueError('Kontakt returned silent audio.')
 bins=min(1800,frames);peaks=[]
 for i in range(bins):
  chunk=values[(i*frames//bins)*2:(((i+1)*frames)//bins)*2];peaks.append([min(chunk)/32768,max(chunk)/32768])
 return {'duration_seconds':frames/rate,'sample_rate':rate,'waveform':peaks,'audio_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

class RenderManager:
 def __init__(self,publisher,editor,selection):
  self.publisher=publisher;self.editor=editor;self.selection=selection;self.directory=publisher.repo.parent/'riff-kontakt-renders';self.jobs={};self.lock=threading.Lock();self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=1)
 def available(self):
  directory=os.environ.get('RIFF_KONTAKT_PRESET_DIR');python=os.environ.get('RIFF_RENDER_PYTHON');worker=os.environ.get('RIFF_RENDER_WORKER')
  if not all(x and pathlib.Path(x).exists() for x in (directory,python,worker)):return []
  verified=set(os.environ.get('RIFF_KONTAKT_PRESETS','').split(','))
  return [{'id':key,'label':label} for key,(label,file) in PRESETS.items() if key in verified and (pathlib.Path(directory)/file).is_file()]
 def public(self,job):return {k:copy.deepcopy(v) for k,v in job.items() if k not in ('owner','path')}
 def capture(self,cookie,data):
  stage=data.get('stage');version=data.get('version');revision=data.get('editor_revision');selected=data.get('selected');view=data.get('view')
  if set(data)!={'stage','version','editor_revision','selected','preset','view'} or type(stage) is not int or stage not in range(1,7) or type(version) is not int or version<1:raise ValueError('Invalid render snapshot.')
  if view not in ('current','previous'):raise ValueError('Choose a current or previous playback snapshot.')
  if view=='previous':
   if revision is not None or selected is not None:raise ValueError('Previous renders use the full saved playback snapshot.')
   _,_,output=self.publisher.current_audio_midi(cookie,stage,version,include_output=True,view='previous')
  elif stage==6:
   key,state=self.editor.source(cookie,version)
   with self.editor.lock:
    workspace=self.editor.workspace(key,state)
    if type(revision) is not int or revision!=workspace['revision']:raise ValueError('Edited Review changed. Render the current revision.')
    output=copy.deepcopy(workspace['output'])
  else:
   if revision is not None:raise ValueError('Only Review has an editor revision.')
   _,_,output=self.publisher.current_audio_midi(cookie,stage,version,include_output=True)
   if selected is not None:
    context=self.selection.request('/selection/open',cookie,{'stage':stage,'version':version});output={**output,'phrases':context['phrases']}
  audio=copy.deepcopy(output['audio']) if selected is None else selected_in_place(output,selected)
  if not audio['notes']:raise ValueError('There are no notes to render.')
  if audio.get('tempo')!=120:raise ValueError('Unsupported render tempo.')
  return audio
 def start(self,cookie,data):
  identity=owner(cookie);available={p['id'] for p in self.available()};preset=data.get('preset')
  if preset not in available:raise ValueError('Choose an available Kontakt preset.')
  audio=self.capture(cookie,data);midi=midi_bytes(audio);seconds=audio['length_beats']*.5+2
  presetfile=pathlib.Path(os.environ['RIFF_KONTAKT_PRESET_DIR'])/PRESETS[preset][1];worker=pathlib.Path(os.environ['RIFF_RENDER_WORKER'])
  state_bytes=presetfile.read_bytes();state_sha=hashlib.sha256(state_bytes).hexdigest()
  fingerprint=hashlib.sha256(midi+state_bytes+worker.read_bytes()+str(seconds).encode()).hexdigest()
  jobid=uuid.uuid4().hex;capture={k:copy.deepcopy(data[k]) for k in ('stage','version','editor_revision','selected','preset','view')};capture.update({'tempo':120,'length_beats':audio['length_beats'],'selection_timing':'original positions; unselected regions silent'})
  job={'job_id':jobid,'owner':identity,'status':'queued','capture':capture,'midi_sha256':hashlib.sha256(midi).hexdigest()}
  with self.lock:self.jobs[jobid]=job
  self.executor.submit(self.run,jobid,midi,seconds,preset,fingerprint,state_sha)
  return self.status(cookie,jobid)
 def run(self,jobid,midi,seconds,preset,fingerprint,state_sha):
  with self.lock:self.jobs[jobid]['status']='running'
  folder=self.directory/fingerprint;wav=folder/'render.wav';meta=folder/'render.wav.json';midi_path=folder/'source.mid';host=folder/'host-result.json'
  try:
   folder.mkdir(parents=True,exist_ok=True)
   # Only validated completed artifacts are reusable. Invalid prior artifacts stay untouched.
   reusable=False
   if wav.is_file() and meta.is_file() and host.is_file():
    try:
     old=json.loads(meta.read_text(encoding='utf-8'));host_result=json.loads(host.read_text(encoding='utf-8'));check=inspect_wav(wav,seconds)
     reusable=bool(host_result.get('exit_code') in (0,85) and host_result.get('wav_sha256')==check['audio_sha256'] and old.get('success') and old.get('midi_sha256')==hashlib.sha256(midi).hexdigest() and old.get('preset')==preset and old.get('state_sha256')==state_sha and old.get('wav_sha256')==check['audio_sha256'])
    except Exception:reusable=False
   if not reusable:
    if wav.exists() or meta.exists():
     folder=self.directory/(fingerprint+'-'+uuid.uuid4().hex);folder.mkdir();wav=folder/'render.wav';meta=folder/'render.wav.json';midi_path=folder/'source.mid';host=folder/'host-result.json'
    midi_path.write_bytes(midi)
    command=[os.environ['RIFF_RENDER_PYTHON'],os.environ['RIFF_RENDER_WORKER'],'--midi',str(midi_path),'--output',str(wav),'--preset',preset,'--bpm','120','--duration',str(seconds),'--job-id',jobid]
    result=subprocess.run(command,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    exit_code=result.returncode
   else:exit_code=host_result['exit_code']
   receipt=json.loads(meta.read_text(encoding='utf-8'))
   if not receipt.get('success') or receipt.get('midi_sha256')!=hashlib.sha256(midi).hexdigest() or receipt.get('preset')!=preset or receipt.get('state_sha256')!=state_sha:raise ValueError('Kontakt render receipt does not match this MIDI and preset.')
   if not reusable:
    if receipt.get('job_id')!=jobid:raise ValueError('Kontakt receipt job identity does not match.')
    if exit_code not in (0,85):raise ValueError(f'Kontakt host crashed (code {exit_code}); audio was not accepted.')
    if exit_code==85 and (receipt.get('termination_mode')!='controlled_process_termination' or receipt.get('expected_exit_code')!=85):raise ValueError('Kontakt controlled shutdown receipt is missing.')
   info=inspect_wav(wav,seconds)
   if receipt.get('wav_sha256')!=info['audio_sha256']:raise ValueError('Rendered audio checksum does not match the completed receipt.')
   if not reusable:host.write_text(json.dumps({'exit_code':exit_code,'wav_sha256':info['audio_sha256']}),encoding='utf-8')
   with self.lock:
    self.jobs[jobid].update({'status':'ready','host_exit_code':exit_code,'cached':reusable,'path':str(wav),'audio_url':'/render/audio?job='+jobid,**info})
    if exit_code==85:self.jobs[jobid]['host_shutdown']='controlled_process_termination' 
  except Exception as e:
   message='Kontakt rendering timed out after 180 seconds.' if isinstance(e,subprocess.TimeoutExpired) else str(e) if isinstance(e,ValueError) else 'Kontakt rendering failed. No audio was substituted.'
   with self.lock:self.jobs[jobid].update({'status':'failed','error':message})
 def status(self,cookie,jobid):
  identity=owner(cookie)
  if not isinstance(jobid,str) or len(jobid)!=32 or any(c not in '0123456789abcdef' for c in jobid):raise ValueError('Invalid render identifier.')
  with self.lock:
   job=self.jobs.get(jobid)
   if job is None or job['owner']!=identity:raise ValueError('Render is unavailable for this session.')
   return self.public(job)
 def audio(self,cookie,jobid):
  self.status(cookie,jobid)
  with self.lock:
   job=self.jobs[jobid]
   if job['status']!='ready':raise ValueError('Audio is not ready.')
   return pathlib.Path(job['path']).read_bytes()
