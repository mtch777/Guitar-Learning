"""Thin stateful adapter around validated analytical generator modules.
The original CSV, extraction and generator modules are read-only inputs.
"""
from __future__ import annotations
import collections, contextlib, copy, csv, hashlib, json, math, os, pathlib, random, secrets, sys, tempfile, threading, time
from fractions import Fraction as Q
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT.parent
sys.path[:0]=[str(BASE/'seed-scoring'),str(BASE/'weighted-scoring')]
import weighted_scoring as W, blueprint as B, opening_rhythm as R
import contextual_rhythm as C, first_phrase_pitch as F, tonal_scale_sets as T, sequential_pitch as S
CSV=pathlib.Path(os.environ.get('RIFF_CSV',str(BASE/'csv-current/all_riffs_phrase_composition.csv')))
TIMING=pathlib.Path(os.environ.get('RIFF_TIMING',str(BASE/'opening-rhythm/source-all-lengths/pitch_free_all_lengths_phrase_rhythms.json')))
TITLES=['Seed','Scaffold','Rhythms','Opening pitches','Remaining pitches','Review']
DEFAULT_FIELD_WEIGHTS={str(f['schema_id']):f['weight'] for f in W.FIELDS}
DEFAULTS={
 '1':{'artist':'all','role':'all','random_seed':''},
 '2':{'field_weights':DEFAULT_FIELD_WEIGHTS,'random_seed':''},
 '3':{'method':'contextual','opening_weights':dict(R.WEIGHTS),'context_weights':dict(C.WEIGHTS),'random_seed':''},
 '4':{'tier_weights':{str(k):v for k,v in F.MULTIPLIERS.items()},'fit_weights':dict(R.WEIGHTS),'random_seed':''},
 '5':{'tier_weights':{str(k):v for k,v in F.MULTIPLIERS.items()},'fit_weights':dict(R.WEIGHTS),'random_seed':''},
 '6':{}}

def seed_of(p):return int(p['random_seed']) if p.get('random_seed') not in ['',None] else secrets.randbits(52)
def draw(items,weights,seed):
 total=math.fsum(weights)
 if not math.isfinite(total) or total<=0:raise ValueError('No positive-weight candidates')
 u=random.Random(seed).random();acc=0
 for item,w in zip(items,weights):
  acc+=w
  if u*total<acc:return item,{'random_seed':seed,'uniform_draw':u,'candidate_count':len(items),'selected_probability':w/total,'selected_score':w,'weight_sum':total}
 raise AssertionError('Weighted draw not found')
def audio(phrases,label):
 notes=[];length=0
 for p in phrases:
  start=float(p.get('start_beats',0));length=max(length,start+float(p.get('length_beats',0)))
  for n in p.get('notes',[]):
   a=max(0,start+float(n['start_beats']));b=start+float(n['end_beats'])
   if b>a:
    notes.append({'start_beats':a,'duration_beats':b-a,'midi_pitch':n.get('midi_pitch',28),'placeholder':'midi_pitch' not in n});length=max(length,b)
 return {'label':label,'notes':notes,'tempo':120,'length_beats':length}
def public_phrase(row,notes=None,**extra):
 return {'phrase':int(row['Phrase #']),'start_beats':float(row.get('Start position (beats)',0)),'length_beats':float(row.get('Length (beats)',row.get(B.BEATS,0))),'role':row.get('Phrase role'),'texture':row.get('Dominant texture',row.get('Category - dominant texture')),'notes':copy.deepcopy(notes or []),**extra}
@contextlib.contextmanager
def settings(fields=None,fit=None,context=None,tiers=None):
 old=(copy.deepcopy(W.FIELDS),R.WEIGHTS.copy(),C.WEIGHTS.copy(),F.MULTIPLIERS.copy())
 try:
  if fields is not None:
   for f in W.FIELDS:f['weight']=fields[str(f['schema_id'])]
  if fit is not None:R.WEIGHTS=dict(fit)
  if context is not None:C.WEIGHTS=dict(context)
  if tiers is not None:F.MULTIPLIERS={int(k):v for k,v in tiers.items()}
  yield
 finally:W.FIELDS[:]=old[0];R.WEIGHTS=old[1];C.WEIGHTS=old[2];F.MULTIPLIERS=old[3]

class Engine:
 def __init__(self,csv_path=CSV,timing_path=TIMING):
  self.csv=pathlib.Path(csv_path);self.timing=pathlib.Path(timing_path)
  self.rhythm=C.Engine(self.csv,self.timing)
  # Share rows/normalization to avoid loading the large CSV twice.
  self.pitch=F.Engine.__new__(F.Engine);self.pitch.csv_path=self.csv
  self.pitch.rows=[r for r in self.rhythm.rows if r['Status']=='complete']
  self.pitch.first=self.rhythm.first;self.pitch.parsed=self.rhythm.parsed
  self.pitch.refs=[(r,(g:=F.groups(r)),list(map(len,g))) for r in self.pitch.rows]
  self.first=self.rhythm.first
  self.by=collections.defaultdict(list)
  for r in self.pitch.rows:self.by[r['Riff ID']].append(r)
  for rows in self.by.values():rows.sort(key=lambda x:int(x['Phrase #']))
  self.eligible=sorted(rid for rid,r in self.first.items() if R.known(r['Phrase role']))
  self.artists=sorted({self.first[r]['Artist'] for r in self.eligible})
  self.roles=sorted({self.first[r]['Phrase role'] for r in self.eligible})
  self.hashes={'csv_sha256':hashlib.sha256(self.csv.read_bytes()).hexdigest(),'timing_sha256':hashlib.sha256(self.timing.read_bytes()).hexdigest()}
  self.source_cache={'source':(self.rhythm.records,{}),'rows':self.rhythm.rows,'source_hash':self.hashes['timing_sha256']}
  self.score_cache={}
 def scores(self,rid,weights):
  key=(rid,tuple(sorted(weights.items())))
  if key not in self.score_cache:
   with settings(fields=weights):self.score_cache[key]={k:W.compare_parsed(self.pitch.parsed[rid],p)['score'] for k,p in self.pitch.parsed.items()}
  return self.score_cache[key]
 def config(self):
  def group(key,labels,values):return [{'key':key+'.'+k,'label':labels.get(k,k),'type':'number','min':0,'step':'any','default':v,'group':key} for k,v in values.items()]
  rng={'key':'random_seed','label':'Random seed (blank = random)','type':'text','default':'','group':'details'}
  fits={'role':'Phrase role','texture':'Texture','accent':'Accent','source_riff_similarity':'Source riff similarity'}
  context={'current':'Current phrase fit','previous':'Previous phrase','history':'Earlier phrases','context':'Riff context'}
  tiers={'1':'Exact order','2':'Reordered','3':'Consecutive subset','4':'Gapped subset'}
  pars=[
   [{'key':'artist','label':'Artist','type':'select','default':'all','options':[{'value':'all','label':'All artists'}]+[{'value':a,'label':a} for a in self.artists]}, {'key':'role','label':'Opening role','type':'select','default':'all','options':[{'value':'all','label':'All known roles'}]+[{'value':r,'label':r} for r in self.roles]},rng],
   [{'key':'field_weights.'+str(f['schema_id']),'label':f['field'],'type':'number','min':0,'step':'any','default':DEFAULT_FIELD_WEIGHTS[str(f['schema_id'])],'group':'field_weights'} for f in W.FIELDS]+[rng],
   [{'key':'method','label':'Method','type':'select','default':'contextual','options':[{'value':'independent','label':'Independent'},{'value':'contextual','label':'Contextual'}]}]+group('opening_weights',fits,DEFAULTS['3']['opening_weights'])+group('context_weights',context,DEFAULTS['3']['context_weights'])+[rng],
   group('tier_weights',tiers,DEFAULTS['4']['tier_weights'])+group('fit_weights',fits,DEFAULTS['4']['fit_weights'])+[rng],
   group('tier_weights',tiers,DEFAULTS['5']['tier_weights'])+group('fit_weights',fits,DEFAULTS['4']['fit_weights'])+[rng],[]]
  return {'stages':[{'id':str(i),'title':name,'parameters':pars[i-1],'defaults':copy.deepcopy(DEFAULTS[str(i)])} for i,name in enumerate(TITLES,1)],'defaults':copy.deepcopy(DEFAULTS),'counts':{'riffs':len(self.first),'eligible_seed_riffs':len(self.eligible),'phrases':len(self.pitch.rows)},'engine':'existing-analytical-pipeline','dataset':self.hashes}
 def validate(self,params):
  if not isinstance(params,dict):raise ValueError('Parameters must be an object')
  out=copy.deepcopy(DEFAULTS)
  for step,values in params.items():
   if step not in out or not isinstance(values,dict):raise ValueError('Unknown step parameters')
   for key,value in values.items():
    if key not in out[step]:raise ValueError('Unknown parameter: '+key)
    if isinstance(out[step][key],dict):
     if not isinstance(value,dict) or set(value)!=set(out[step][key]):raise ValueError('Weight fields do not match this step')
     clean={}
     for k,v in value.items():
      if isinstance(v,bool):raise ValueError('Weights must be numbers')
      try:v=float(v)
      except (ValueError,TypeError):raise ValueError('Weights must be numbers')
      if not math.isfinite(v) or v<0:raise ValueError('Weights must be finite and non-negative')
      clean[k]=v
     if not any(clean.values()):raise ValueError('At least one weight must be positive')
     out[step][key]=clean
    elif key=='random_seed':
     if value not in ['',None]:
      try:n=int(value)
      except (TypeError,ValueError):raise ValueError('Random seed must be an integer')
      if str(n)!=str(value).strip() or abs(n)>9007199254740991:raise ValueError('Random seed must be a safe integer')
      value=str(n)
     out[step][key]=value or ''
    else:out[step][key]=value
  if out['1']['artist'] not in ['all']+self.artists:raise ValueError('Unknown artist')
  if out['1']['role'] not in ['all']+self.roles:raise ValueError('Unknown opening role')
  if out['3']['method'] not in ['independent','contextual']:raise ValueError('Unknown rhythm method')
  return out
 def reference_audio(self,rid,phrase_numbers,label):
  # Original extraction IDs identify tied occurrences crossing source phrase boundaries.
  phrases=[];offset=0;seen=set();problems=[]
  for number in phrase_numbers:
   item=self.rhythm.items[(rid,number)];record=self.rhythm.records[(rid,number)]
   if item['reasons']:problems.append('Phrase '+str(number)+': '+'; '.join(item['reasons']))
   notes=[]
   for n in record.get('notes',[]):
    event=n.get('source_occurrence_id',n.get('event_id'))
    if event is None:
     problems.append('Phrase '+str(number)+': source note identity unavailable');continue
    if event in seen:continue
    if float(n['start_beats'])<0 and offset==0:
     problems.append('Phrase '+str(number)+': preview starts during a held note');continue
    seen.add(event)
    notes.append({'start_beats':float(n['start_beats']),'end_beats':float(n['tied_end_q']) if '/' not in str(n['tied_end_q']) else float(Q(n['tied_end_q'])),'duration_beats':float(Q(n['tied_duration_q']))})
   phrases.append({'start_beats':offset,'length_beats':float(item['length']),'notes':notes});offset+=float(item['length'])
  if problems:return {'label':label,'notes':[],'tempo':120,'length_beats':offset,'unavailable':'; '.join(dict.fromkeys(problems))}
  return audio(phrases,label)
 def stage1(self,p):
  ids=[r for r in self.eligible if (p['artist']=='all' or self.first[r]['Artist']==p['artist']) and (p['role']=='all' or self.first[r]['Phrase role']==p['role'])]
  if not ids:raise ValueError('No eligible seed riffs for these settings')
  rng=seed_of(p);rid=random.Random(rng).choice(ids);row=self.first[rid];item=self.rhythm.items[(rid,1)]
  ph=public_phrase(row,item['notes'] or [],source_riff=rid,source_phrase=1)
  return {'summary':{'Artist':row['Artist'],'Riff':rid,'Beats':ph['length_beats'],'Role':ph['role'],'Texture':ph['texture']},'phrases':[ph],'audio':self.reference_audio(rid,[1],'Seed reference rhythm · E1'),'details':{'candidate_count':len(ids),'random_seed':rng,'attributes':row,'timing_issues':item['reasons']},'raw':{'seed_id':rid}}
 def stage2(self,p,up):
  rid=up[0]['raw']['seed_id'];seed=self.first[rid];scores=self.scores(rid,p['field_weights'])
  ids=[r for r in sorted(self.first) if r!=rid and self.first[r]['Phrase role']==seed['Phrase role'] and R.known(self.first[r]['Phrase role'])]
  donor,selection=draw(ids,[scores[x] or 0 for x in ids],seed_of(p));rows,meta=B.build(seed,self.by[donor]);blueprint={'phrases':rows,'metadata':meta}
  phrases=[public_phrase(r,source_riff=rid if i==0 else donor,source_phrase=i+1,repeat=r['Intended same notes and timing as (phrase #s)'],rhythm_repeat=r['Intended same rhythm and holds as (phrase #s)']) for i,r in enumerate(rows)]
  refs=[];offset=0
  for row in self.by[donor]:
   ph=public_phrase(row,self.rhythm.items[(donor,int(row['Phrase #']))]['notes'] or [],source_riff=donor,source_phrase=int(row['Phrase #']));ph['start_beats']=offset;offset+=ph['length_beats'];refs.append(ph)
  return {'summary':{'Reference artist':self.first[donor]['Artist'],'Reference riff':donor,'Phrases':len(rows),'Beats':meta['blueprint_total_beats'],'Similarity':selection['selected_score']},'phrases':phrases,'audio':self.reference_audio(donor,[int(r['Phrase #']) for r in self.by[donor]],'Donor reference rhythm · E1'),'details':{**selection,'blueprint':blueprint,'field_weights':p['field_weights'],'reference_audio_riff':donor},'raw':{'blueprint':blueprint,'scores':scores}}
 def stage3(self,p,up):
  rid=up[0]['raw']['seed_id'];seed=self.first[rid];blueprint=up[1]['raw']['blueprint'];scores=up[1]['raw']['scores'];rng=seed_of(p)
  candidates=[(r,scores[r],None) for r in sorted(self.rhythm.pool)]
  with tempfile.TemporaryDirectory(prefix='riff-rhythm-') as tmp,settings(fields=up[1]['details']['field_weights'],fit=p['opening_weights'],context=p['context_weights']):
   opening=R.run(seed,candidates,self.csv,self.timing,pathlib.Path(tmp)/'opening',cached=self.source_cache,rng_seed_override=rng)
   if not opening['selection_performed']:return {'summary':{},'phrases':[],'blocker':opening['status'],'details':{k:v for k,v in opening.items() if k not in ['pool']}}
   report=self.rhythm.run(blueprint,opening,p['method'],pathlib.Path(tmp)/'sequence',rng+1)
  phrases=report['phrases']
  return {'summary':{'Method':p['method'],'Phrases':len(phrases),'Beats':report['total_beats']},'phrases':phrases,'audio':audio(phrases,'Rhythm · E1'),'details':{'random_seed':rng,'opening':{k:v for k,v in opening.items() if k not in ['pool','selected_rhythm','excluded']},'opening_excluded_counts':dict(collections.Counter(x['reason'] for x in opening['excluded'])),'weights':report['weights'],'phrase_selections':[{k:v for k,v in x.items() if k!='notes'} for x in phrases]},'raw':{'report':report,'opening':opening}}
 def stage4(self,p,up):
  rid=up[0]['raw']['seed_id'];rng=seed_of(p);rhythm=up[2]['raw']['report'];opening=up[2]['raw']['opening']
  with tempfile.TemporaryDirectory(prefix='riff-pitch1-') as tmp,settings(fit=p['fit_weights'],tiers=p['tier_weights']):
   report=self.pitch.run(rid,opening,tmp,rng,similarities=up[1]['raw']['scores'])
  if not report['selection_performed']:return {'summary':{},'phrases':[],'blocker':report['reason'],'details':report}
  assert S.stripped(report['notes'])==rhythm['phrases'][0]['notes'],'Opening pitch selection changed its rhythm'
  phrases=copy.deepcopy(rhythm['phrases']);phrases[0]['notes']=report['notes'];selected=report['selected']
  phrases[0]['pitch_source_riff']=selected['riff_id'];phrases[0]['pitch_source_phrase']=selected['phrase'];phrases[0]['tier']=selected['tier']
  return {'summary':{'Reference artist':selected['artist'],'Reference riff':selected['riff_id'],'Reference phrase':selected['phrase'],'Tier':selected['tier'],'Candidates':report['eligible_candidates']},'phrases':phrases,'audio':audio(phrases,'Opening pitches + E1 rhythm'),'details':{k:v for k,v in report.items() if k not in ['notes']},'raw':{'report':report}}
 def stage5(self,p,up,progress=None):
  rid=up[0]['raw']['seed_id'];rows=up[1]['raw']['blueprint']['phrases'];fixed=up[2]['raw']['report']['phrases'];opening=up[3]['raw']['report'];rng=seed_of(p)
  exact=S.exact_roots(rows);scales=None;phrases=[];decisions=[];blocker=None
  def snapshot():
   return {'summary':{'Completed phrases':len(phrases),'Planned phrases':len(rows),'Compatible scale collections':len(scales or ())},'progress':{'completed':len(phrases),'total':len(rows)},'phrases':copy.deepcopy(phrases),'audio':audio(phrases,'Generated pitches' if len(phrases)==len(rows) and not blocker else 'Partial generated pitches'),'details':{'random_seed':rng,'phrase_selections':copy.deepcopy(decisions),'possible_scales':T.public(scales or ()),'scale_policy':'Every generated pitch must fit at least one shared diatonic collection. Chromatic/color notes can stop this version.','rhythms_preserved':True},**({'blocker':blocker} if blocker else {})}
  with tempfile.TemporaryDirectory(prefix='riff-pitches-') as tmp,settings(fit=p['fit_weights'],tiers=p['tier_weights']):
   for idx,row in enumerate(rows,1):
    rhythm=fixed[idx-1]['notes'];before=scales;decision={}
    if idx==1:
     notes=copy.deepcopy(opening['notes']);decision={'method':'Preserved opening','source_riff':opening['selected']['riff_id'],'source_phrase':opening['selected']['phrase']}
     scales=T.from_notes(notes)
    elif exact[idx]!=idx:
     source=exact[idx];notes=copy.deepcopy(phrases[source-1]['notes']);decision={'method':'Exact repeat','copy_from':source};scales=T.from_notes(notes,scales)
    else:
     target={'Phrase role':row['Phrase role'],'Category - dominant texture':row['Dominant texture'],'Accent function':row['Accent function']}
     report=self.pitch.run(rid,{'selection_performed':True,'selected_rhythm':rhythm},pathlib.Path(tmp)/str(idx),rng+idx,target_row=target,current_scales=scales,similarities=up[1]['raw']['scores'])
     if not report['selection_performed']:
      blocker='Phrase '+str(idx)+': '+report['reason'];decisions.append({'phrase':idx,'method':'Blocked','reason':report['reason'],'eligible_candidates':report.get('eligible_candidates',0),'excluded_counts':report.get('excluded_counts',{})});break
     notes=report['notes'];sel=report['selected'];decision={'method':'Weighted pitch selection','source_riff':sel['riff_id'],'source_phrase':sel['phrase'],'tier':sel['tier'],'candidate_count':report['eligible_candidates'],'tier_counts':report['eligible_tier_counts'],'selected_score':sel['similarity'],'selected_probability':sel['probability'],'components':sel['components'],'random_seed':rng+idx,'matching_scale_sets':sel['matching_current_scales']};scales=T.from_notes(notes,scales)
    assert S.stripped(notes)==rhythm,'Pitch step changed fixed rhythm in phrase '+str(idx)
    assert before is None or set(scales)<=set(before),'Running scale set expanded'
    phrase=public_phrase(row,notes,**decision);phrases.append(phrase);decisions.append({'phrase':idx,**decision,'possible_scales_after':T.public(scales)})
    if not scales:
     blocker='Phrase '+str(idx)+': no single diatonic scale contains all generated notes';break
    if progress:progress(snapshot())
  result=snapshot();result['raw']={'complete':not blocker and len(phrases)==len(rows),'phrases':phrases,'decisions':decisions};return result
 def stage6(self,p,up):
  output=up[4]
  if output.get('blocker') or not output['raw']['complete']:raise ValueError('Complete generated notes are required before export')
  phrases=copy.deepcopy(output['phrases'])
  if any('midi_pitch' not in n for ph in phrases for n in ph['notes']):raise ValueError('Final output contains unassigned pitches')
  a=audio(phrases,'Generated riff');overlapping_unisons=0
  by_pitch=collections.defaultdict(list)
  for n in a['notes']:by_pitch[n['midi_pitch']].append(n)
  for notes in by_pitch.values():
   events=sorted(notes,key=lambda n:n['start_beats']);ends=[]
   for n in events:
    ends=[end for end in ends if end>n['start_beats']]
    if ends:overlapping_unisons+=1
    ends.append(n['start_beats']+n['duration_beats'])
  details={'instrument_channels':1,'transposition_semitones':0,'performance_expression':'Neutral preview velocities; no generated slides/bends','overlapping_unison_events':overlapping_unisons,'midi_ticks_per_quarter':960}
  if overlapping_unisons:details['MIDI playback note']='Overlapping same-pitch notes are preserved as separate MIDI events; receiver playback may differ.'
  return {'summary':{'Phrases':len(phrases),'Beats':up[1]['raw']['blueprint']['metadata']['blueprint_total_beats'],'Notes':len(a['notes'])},'phrases':phrases,'audio':a,'details':details,'can_export':True,'raw':{'complete':True}}
