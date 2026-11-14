from runtime_options import SESSION_COOKIE, output_path
"""Revisioned Review working copies. Original generator sessions are read-only."""
import copy,hashlib,http.client,http.cookies,json,pathlib,re,secrets,threading
SaveError=ValueError
from server import midi_bytes

def selected_audio(output,selected):
 phrases=output['phrases'];ids={p['phrase'] for p in phrases}
 if not isinstance(selected,list) or not selected or any(type(i) is not int or i not in ids for i in selected):raise SaveError('Select at least one valid phrase.')
 chosen=[p for p in phrases if p['phrase'] in set(selected)];spans=[]
 for p in chosen:
  a=float(p['start_beats']);b=a+float(p['length_beats'])
  if spans and abs(spans[-1][1]-a)<1e-8:spans[-1]=(spans[-1][0],b)
  else:spans.append((a,b))
 notes=[];offset=0
 for a,b in spans:
  for n in output['audio']['notes']:
   start=max(a,n['start_beats']);end=min(b,n['start_beats']+n['duration_beats'])
   if end>start:notes.append({**n,'start_beats':offset+start-a,'duration_beats':end-start})
  offset+=b-a
 return {'label':'Selected phrases · joined, edge holds clipped','notes':notes,'tempo':120,'length_beats':offset}

class EditorManager:
 def __init__(self,publisher):
  self.publisher=publisher;self.directory=output_path(publisher.repo.parent/'riff-editor-state');self.lock=threading.RLock();self.engine=None
 def source(self,cookie,version):
  c=http.cookies.SimpleCookie()
  try:c.load(cookie or '')
  except http.cookies.CookieError:pass
  sid=c.get(SESSION_COOKIE)
  if not sid or not re.fullmatch(r'[A-Za-z0-9_-]{32}',sid.value):raise SaveError('No current generator session.')
  def get(path):
   conn=http.client.HTTPConnection('127.0.0.1',self.publisher.source_port,timeout=30)
   try:
    conn.request('GET',path,headers={'Cookie':SESSION_COOKIE+'='+sid.value});r=conn.getresponse();data=json.loads(r.read())
    if r.status!=200:raise SaveError('Generator is unavailable.')
    return data
   finally:conn.close()
  state=get('/api/state')
  if state.get('session_id')!=sid.value or state.get('version')!=version or state.get('busy'):raise SaveError('The original result changed or is generating.')
  final=next((s for s in state['stages'] if str(s['id'])=='6'),{})
  if final.get('status')!='complete' or not final.get('output',{}).get('can_export'):raise SaveError('A complete Review is required.')
  state.pop('session_id',None);state['dataset']=get('/api/config')['dataset']
  key=hashlib.sha256((sid.value+':'+str(version)).encode()).hexdigest()
  return key,state
 def path(self,key):return self.directory/(key+'.json')
 def write(self,key,workspace):
  self.directory.mkdir(parents=True,exist_ok=True);p=self.path(key);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(workspace),encoding='utf-8');tmp.replace(p)
 def public(self,w):
  from engine import DEFAULTS,clean_preferences
  preferences={step:clean_preferences(step,next((s.get('applied',{}).get('phrase_preferences',{}) for s in w['state']['stages'] if str(s['id'])==step),{})) for step in ('3','4','5')}
  return {**{k:copy.deepcopy(w[k]) for k in ('source_version','revision','output')},'preferences':preferences}
 def workspace(self,key,state):
  p=self.path(key)
  if p.exists():
   w=json.loads(p.read_text(encoding='utf-8'))
   if w['state']['dataset']!=state['dataset']:raise SaveError('The source dataset changed.')
   return w
  output=next(s['output'] for s in state['stages'] if str(s['id'])=='6')
  return {'source_version':state['version'],'revision':0,'output':copy.deepcopy(output),'state':state}
 def request(self,path,cookie,data):
  if type(data.get('version')) is not int or data['version']<1:raise SaveError('Invalid source version.')
  key,state=self.source(cookie,data['version'])
  with self.lock:
   w=self.workspace(key,state)
   if path=='/editor/open':
    if set(data)!={'version'}:raise SaveError('Invalid editor request.')
    self.write(key,w);return self.public(w)
   if type(data.get('revision')) is not int or data['revision']!=w['revision']:raise SaveError('Edited result changed. Open the current Review again.')
   if path=='/editor/save':
    if set(data)!={'version','revision','selected'}:raise SaveError('Invalid selected MIDI request.')
    audio=w['output']['audio'] if data['selected'] is None else selected_audio(w['output'],data['selected'])
    body=midi_bytes(audio)
    if not self.publisher.lock.acquire(blocking=False):raise SaveError('Another MIDI is being saved. Retry shortly.')
    try:
     result=self.publisher.publish(body,data['version'],6,False,selected=data['selected'] is not None)
     return {**result,'editor_revision':w['revision'],'selected':data['selected'],'timing':'full' if data['selected'] is None else 'joined; edge holds clipped'}
    finally:self.publisher.lock.release()
   if path=='/editor/delete':
    if set(data)!={'version','revision','selected'}:raise SaveError('Invalid phrase deletion request.')
    from selective_edit import delete_phrases
    from engine import audio
    result=delete_phrases(w['state'],w['output']['phrases'],data['selected'])
    updated=copy.deepcopy(w);updated['revision']+=1;updated['state']=result['state']
    phrases=result['phrases'];a=audio(phrases,'Edited riff')
    details=copy.deepcopy(w['output'].get('details',{}))
    for k in ('overlapping_unison_events','MIDI playback note','edit'):details.pop(k,None)
    details['edit']={'mode':'delete','deleted':result['deleted'],'old_to_new':{str(k):v for k,v in result['old_to_new'].items()}}
    updated['output']={**copy.deepcopy(w['output']),'phrases':phrases,'audio':a,'details':details,'summary':{'Phrases':len(phrases),'Beats':a['length_beats'],'Notes':len(a['notes']),'Edit':updated['revision']}}
    # A normal recoverable revision copy, never remove the original generator result.
    self.write(key+'.revision-'+str(w['revision']),w)
    self.write(key,updated)
    return {**self.public(updated),**{k:result[k] for k in ('selected','affected','deleted','old_to_new')}}
   required={'version','revision','selected','mode'}
   if set(data) not in (required,required|{'preferences'}) or ('preferences' in data and path!='/editor/regenerate'):raise SaveError('Invalid selective regeneration request.')
   from selective_edit import plan_selection,SelectiveEditor
   plan=plan_selection(w['state'],w['output']['phrases'],data['selected'],data['mode'])
   if path=='/editor/plan':return {**plan,'revision':w['revision']}
   if path!='/editor/regenerate':raise SaveError('Unknown editor action.')
   if self.engine is None:
    from engine import Engine
    self.engine=Engine()
   # The engine works on a private copy. Nothing is committed on lookup failure.
   edit_state=copy.deepcopy(w['state'])
   if 'preferences' in data:
    from engine import clean_preferences
    if not isinstance(data['preferences'],dict) or set(data['preferences'])!={'3','4','5'}:raise SaveError('Invalid review weights')
    for step,value in data['preferences'].items():
     clean=clean_preferences(step,value)
     entry=next((s for s in edit_state['stages'] if str(s['id'])==step),None)
     if entry is None:raise SaveError('Required stage missing for review weights')
     entry.setdefault('applied',{})['phrase_preferences']=clean
   result=SelectiveEditor(self.engine).regenerate(edit_state,copy.deepcopy(w['output']['phrases']),data['selected'],data['mode'],secrets.randbits(52))
   updated=copy.deepcopy(w);updated['revision']+=1;updated['state']=edit_state
   from engine import audio
   phrases=result['phrases'];a=audio(phrases,'Edited riff')
   details=copy.deepcopy(w['output'].get('details',{}));details.pop('overlapping_unison_events',None);details.pop('MIDI playback note',None)
   overlapping=0;by_pitch={}
   for note in a['notes']:by_pitch.setdefault(note['midi_pitch'],[]).append(note)
   for notes in by_pitch.values():
    ends=[]
    for note in sorted(notes,key=lambda n:n['start_beats']):
     ends=[end for end in ends if end>note['start_beats']]
     if ends:overlapping+=1
     ends.append(note['start_beats']+note['duration_beats'])
   details['overlapping_unison_events']=overlapping
   if overlapping:details['MIDI playback note']='Overlapping same-pitch notes are preserved as separate MIDI events; receiver playback may differ.'
   details['possible_scales']=result.get('possible_scales',[])
   updated['output']={**copy.deepcopy(w['output']),'phrases':phrases,'audio':a,'details':{**details,'edit':{k:v for k,v in result.items() if k not in ('phrases','audio')}},'summary':{'Phrases':len(phrases),'Beats':a['length_beats'],'Notes':len(a['notes']),'Edit':updated['revision']}}
   self.write(key,updated);return {**self.public(updated),**plan}
