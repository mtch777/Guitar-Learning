from runtime_options import SESSION_COOKIE
"""Select exact playback phrase windows at each step; no generation or session writes."""
import copy,csv,hashlib,http.client,http.cookies,json,pathlib,threading
from fractions import Fraction
from editor_service import selected_audio
from server import midi_bytes
import engine as E
class SelectionManager:
 def __init__(self,publisher):
  self.publisher=publisher;self.cache={};self.lock=threading.Lock()
 def donor_windows(self,cookie,riff):
  path=pathlib.Path(E.CSV);stat=path.stat();key=(str(path),stat.st_mtime_ns,stat.st_size,riff)
  with self.lock:
   parsed=http.cookies.SimpleCookie();parsed.load(cookie);sid=parsed[SESSION_COOKIE].value
   conn=http.client.HTTPConnection('127.0.0.1',self.publisher.source_port,timeout=30)
   try:
    conn.request('GET','/api/config',headers={'Cookie':SESSION_COOKIE+'='+sid});r=conn.getresponse();config=json.loads(r.read())
    if r.status!=200:raise ValueError('Cannot verify reference dataset.')
   finally:conn.close()
   expected=config.get('dataset',{}).get('csv_sha256')
   if key in self.cache:
    cached=self.cache[key]
    if cached['digest']!=expected:raise ValueError('Reference dataset changed; selection was not exported.')
    return copy.deepcopy(cached['phrases'])
   with path.open('rb') as f:
    digest=hashlib.file_digest(f,'sha256').hexdigest() if hasattr(hashlib,'file_digest') else self.digest(f)
   if digest!=expected:raise ValueError('Reference dataset changed; selection was not exported.')
   with path.open(encoding='utf-8-sig',newline='') as f:rows=[row for row in csv.DictReader(f) if row['Riff ID']==riff and row['Status']=='complete']
   rows.sort(key=lambda row:int(row['Phrase #']));offset=Fraction(0);phrases=[]
   for row in rows:
    length=Fraction(row['Length (quarter-note beats)'])
    phrases.append({'phrase':int(row['Phrase #']),'start_beats':float(offset),'length_beats':float(length)});offset+=length
   if not phrases:raise ValueError('Reference phrases are unavailable.')
   after=path.stat()
   if (after.st_mtime_ns,after.st_size)!=(stat.st_mtime_ns,stat.st_size):raise ValueError('Reference dataset changed during selection.')
   self.cache[key]={'digest':digest,'phrases':phrases};return copy.deepcopy(phrases)
 @staticmethod
 def digest(f):
  h=hashlib.sha256()
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  return h.hexdigest()
 def request(self,path,cookie,data):
  stage=data.get('stage');version=data.get('version')
  if type(stage) is not int or stage not in range(1,6) or type(version) is not int or version<1:raise ValueError('Choose a current step 1–5. Review selections use the edited Review.')
  expected={'stage','version'} if path=='/selection/open' else {'stage','version','selected'}
  if set(data)!=expected or path not in ('/selection/open','/selection/save'):raise ValueError('Invalid phrase selection request.')
  _,partial,out=self.publisher.current_audio_midi(cookie,stage,version,include_output=True)
  if stage==2:
   riff=out.get('details',{}).get('reference_audio_riff')
   if not riff:raise ValueError('Donor reference is unavailable.')
   phrases=self.donor_windows(cookie,riff)
  elif stage==1:
   original=out.get('phrases',[])
   if len(original)!=1:raise ValueError('Seed reference phrase is unavailable.')
   phrases=[{'phrase':1,'start_beats':0,'length_beats':original[0]['length_beats']}]
  else:phrases=[{k:p[k] for k in ('phrase','start_beats','length_beats')} for p in out.get('phrases',[])]
  if not phrases:raise ValueError('No playback phrases are available.')
  end=0
  for p in phrases:
   if p['start_beats']<end-1e-8 or p['length_beats']<=0:raise ValueError('Playback phrase windows are invalid.')
   end=p['start_beats']+p['length_beats']
  if end>out['audio']['length_beats']+1e-8:raise ValueError('Playback phrase windows do not match this audio.')
  if path=='/selection/open':return {'stage':stage,'version':version,'phrases':phrases,'audio_label':out['audio'].get('label',''),'partial':partial}
  audio=selected_audio({'phrases':phrases,'audio':out['audio']},data['selected']);body=midi_bytes(audio)
  if not self.publisher.lock.acquire(blocking=False):raise ValueError('Another MIDI is being saved. Retry shortly.')
  try:return {**self.publisher.publish(body,version,stage,partial,selected=True),'selected':sorted(set(data['selected'])),'timing':'joined; edge holds clipped'}
  finally:self.publisher.lock.release()
