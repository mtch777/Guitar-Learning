"""Pure, explicit selected-reference evidence. No file, network or target access."""
import copy, hashlib, json
from fractions import Fraction as Q

VERSION = 'selection-renewal/1.3'
LIMITS = {'source_events':20000,'pieces':64,'events':4096,'members':32768,'decisions':12000,'batch':16,'rational_bits':512,'choice_table_bytes':16777216}
LAW = {'version':VERSION,'kind':'exploratory authored constructor with empirical selected timing; not neural or semantic',
 'inventory':'positive geometric count stop1:continue3 and positive geometric relative weights stop1:continue1; explicit count/weights override; normalize all weights proportionally before timing; separately abort at resource cap, never resample',
 'relationships':'source ordered structural annotation-kind transitions; generated NEW/RETURN choice with authored NEW weight3 and total RETURN weight2 plus selected measured-positive return-distance counts; not semantic return prevalence',
 'clock':'joint outgoing gap, coattack, voice, marks, written/tied holds; previous gap and actual global phase condition selected counts; no donor sequence',
 'context':'most specific nonempty context gets mass3/4, all selected observations mass1/4; global-only when no local context; no observation is masked',
 'gap_prior':'positive gaps 1/4,1/2,1,2 each weight1/16; empirical token mass1; sampled prior gap uses separately sampled empirical birth',
 'start':'equal authored attack-now or one renewal-step wait; no forced downbeat attack or source-template shift',
 'return':'copy newly generated motif clock/holds and scale by independent new-piece length; never copy a source phrase',
 'boundary':'carry sampled absolute pending onset through NEW piece boundaries; RETURN keeps generated motif unchanged and reports boundary-gap conflict, including silent-return pending-clock replacement, for end assessment; final pending onset retained as right-censored, no invented note; holds never clipped',
 'unknowns':'missing hold gets labeled neutral audition pulse1/8; original written/tied hold remains null; no guitar rendering claim',
 'support':'finite source token plus four-gap prior; positive count/weight priors with separate resource aborts; one global requested meter and quarter-BPM; no notation-grid enforcement',
 'limits':LIMITS}

def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
def seal(x,key):
 x[key]=digest({k:v for k,v in x.items() if k!=key}); return x
def check(x,key):
 if x.get(key)!=digest({k:v for k,v in x.items() if k!=key}): raise ValueError(key+' changed')
def q(x):
 if type(x) not in (str,int,Q): raise ValueError('Exact quarter values must be integers or rational strings')
 r=Q(x)
 if max(r.numerator.bit_length(),r.denominator.bit_length())>LIMITS['rational_bits']: raise ValueError('Rational bit budget exceeded')
 return r
def meter(x):
 if isinstance(x,str): x=x.split('/')
 if not isinstance(x,(list,tuple)) or len(x)!=2: raise ValueError('Meter must be [numerator, denominator]')
 n,d=map(int,x)
 if not 0<n<=1024 or not 0<d<=1024: raise ValueError('Meter numerical bounds exceeded')
 return [n,d]
def metric(onset,m,phase=Q(0)): return {'meter':m,'phase_q':str((onset+phase)%Q(4*m[0],m[1]))}
def prior(items): return [{'value':v,'weight_q':str(w),'count':0,'origin':'authored_prior','source_addresses':[]} for v,w in items]

def extract(ref):
 s=copy.deepcopy(ref.get('selection',{})); bounds=s.get('range_q')
 if not bounds or len(bounds)!=2: raise ValueError('Explicit selection.range_q required; no scope widening')
 a,b=map(q,bounds)
 if b<=a: raise ValueError('Selection must have positive extent')
 scope={'selection':s,'source_hash_bindings':copy.deepcopy(ref.get('source_hash_bindings',{})),
  'annotation_origin':copy.deepcopy(ref.get('annotation',{})), 'coverage':copy.deepcopy(ref.get('coverage',{})),
  'boundary_censorship':{'selection_boundary':s.get('boundary'),'carry_in_count':len(ref.get('carry_in',[])),
  'carry_out_count':len(ref.get('carry_out',[])),'outside_context':'unknown_not_negative'},
  'component_id':ref.get('record',{}).get('component'),
  'record_provenance':{k:copy.deepcopy(ref.get('record',{}).get(k)) for k in ('id','artist','song','split','collection','origin','identity','boundary','model_eligibility')},
  'evaluation_status':'exploratory selection fitting, not held-out generalization'}
 sid=digest(scope)
 views=ref.get('views',[])
 view=next((v for v in views if v.get('id',v.get('view_id'))==s.get('view_id')), {})
 all_units=view.get('ordered_units',[])
 units=[(i,u) for i,u in enumerate(all_units) if u.get('range_q') and q(u['range_q'][0])<b and q(u['range_q'][1])>a]
 kinds=[]; prev='START'; lookup={}
 for i,u in units:
  kind=u.get('unit_kind',u.get('kind','untyped')); lookup[i]=u
  address={'scope_sha256':sid,'unit_id':u.get('id'),'range_q':u['range_q'],'partially_selected':not(a<=q(u['range_q'][0]) and q(u['range_q'][1])<=b)}
  kinds.append({'value':kind,'context':{'previous_kind':prev},'address':address}); prev=kind
 if not kinds: kinds=[{'value':'untyped','context':{'previous_kind':'START'},'address':{'scope_sha256':sid,'grouping':'unknown'}}]
 relation_rows=[]; relation_evidence=[]
 for r in view.get('relations',[]):
  i,j=r.get('earlier_unit_index'),r.get('later_unit_index')
  if i not in lookup or j not in lookup: continue
  censored=any(not(a<=q(lookup[k]['range_q'][0]) and q(lookup[k]['range_q'][1])<=b) for k in (i,j))
  saved={'source':copy.deepcopy(r),'boundary_censored':censored,'scope_sha256':sid}; relation_evidence.append(saved)
  if r.get('known') is True and r.get('comparable',True) and not censored and j>i and ('return' in r.get('relation_kind','')) and not any(t in r.get('relation_kind','') for t in ('nonreturn','non_return','unequal')):
   relation_rows.append({'distance':j-i,'address':saved})
 voices=s.get('voices'); voices=None if not voices else {str(v) for v in voices}
 events=ref.get('events',[])
 if len(events)>LIMITS['source_events']: raise ValueError('Source event budget exceeded; no subsampling')
 selected=[]
 for e in events:
  onset=q(e['onset_q'])
  if not a<=onset<b: continue
  members=[m for m in e.get('members',[]) if voices is None or str(m.get('voice')) in voices]
  if not members: continue
  unit_hits=[u for _,u in units if q(u['range_q'][0])<=onset<q(u['range_q'][1])]
  unit=min(unit_hits,key=lambda u:q(u['range_q'][1])-q(u['range_q'][0])) if unit_hits else {}
  kind=unit.get('unit_kind',e.get('construction_type','untyped'))
  mp=e.get('metric_phase') or members[0].get('metric_phase') or {}
  phase=mp.get('phase_q'); sig=mp.get('signature',mp.get('meter'))
  source_metric={'meter':meter(sig) if sig else None,'phase_q':str(q(phase)) if phase is not None else None}
  address={'scope_sha256':sid,'attack_id':e.get('attack_id'),'onset_q':str(onset),'unit_id':unit.get('id')}
  mm=[]
  for m in members:
   if q(m.get('onset_q',e['onset_q']))!=onset: raise ValueError('Inconsistent coattack')
   wd=None if m.get('written_end_q') is None else q(m['written_end_q'])-onset
   td=None if m.get('tied_end_q') is None else q(m['tied_end_q'])-onset
   if (wd is not None and wd<0) or (td is not None and td<0): raise ValueError('Negative source hold')
   # Segment clocks/technique facts retained, but pitches are not generation inputs.
   segments=[{k:copy.deepcopy(v) for k,v in seg.items() if k not in ('pitch','midi','fret','string','raw_note')} for seg in m.get('segments',[])]
   mm.append({'voice':m.get('voice'),'written_duration_q':None if wd is None else str(wd),'tied_duration_q':None if td is None else str(td),
    'marks':copy.deepcopy(m.get('marks')),'source_occurrence':m.get('occurrence'),'source_ids':copy.deepcopy(m.get('source_ids')),
    'source_segments':segments,'boundary_censored':m.get('carry_in') or m.get('carry_out') or m.get('unresolved',False),
    'unknowns':[name for name,val in [('voice',m.get('voice')),('marks',m.get('marks')),('written_hold',wd),('tied_hold',td)] if val is None]})
  selected.append({'onset':onset,'kind':kind,'metric':source_metric,'birth':{'members':mm},'address':address})
 selected.sort(key=lambda e:e['onset'])
 if any(x['onset']>=y['onset'] for x,y in zip(selected,selected[1:])): raise ValueError('Coattack clocks not strictly increasing')
 tokens=[]; previous=None
 for i,e in enumerate(selected):
  gap=selected[i+1]['onset']-e['onset'] if i+1<len(selected) else None
  context={'kind':e['kind'],**e['metric'],'previous_gap_q':previous}
  tokens.append({'value':{'gap_q':None if gap is None else str(gap),'birth':e['birth']},'context':context,'address':e['address']})
  previous=None if gap is None else str(gap)
 return {'scope':scope,'scope_sha256':sid,'tokens':tokens,'kinds':kinds,'returns':relation_rows,'relations':relation_evidence,
  'onsets_q':[str(e['onset']-a) for e in selected], 'source_meter_phases':[e['metric'] for e in selected],
  'explicit_rests':[], 'warnings':copy.deepcopy(ref.get('warnings',[]))}

def build_selection_model(reference_payload,scope_options=None):
 options=copy.deepcopy(scope_options or {})
 if set(options)-{'mode','background_references','background_weight_q'}: raise ValueError('Unknown scope option')
 mode=options.get('mode','selected_only'); bg=options.get('background_references',[]); weight=q(options.get('background_weight_q','0'))
 if mode not in ('selected_only','selected_plus_background'): raise ValueError('Unknown scope mode')
 if mode=='selected_only' and (bg or weight): raise ValueError('Selected-only cannot mix background')
 if mode=='selected_plus_background' and (not bg or not 0<weight<1): raise ValueError('Explicit background references and weight required')
 primary=extract(reference_payload); sources=[{'role':'selected','weight_q':str(1-weight),**primary}]
 sources += [{'role':'explicit_background','weight_q':str(weight/len(bg)),**extract(r)} for r in bg]
 if len({s['scope_sha256'] for s in sources})!=len(sources): raise ValueError('Duplicate scope cannot create support')
 components={s['scope']['component_id'] for s in sources if s['scope']['component_id']}
 return seal({'schema':'selection-evidence/1','law':copy.deepcopy(LAW),'law_sha256':digest(LAW),'scope_mode':mode,'sources':sources,
  'scope_receipt':primary['scope'],'coverage':{'selected_attacks':len(primary['tokens']),'selected_gaps':max(0,len(primary['tokens'])-1),
  'operational_units':len(primary['kinds']),'positive_relation_edges':len(primary['returns']), 'evidence_scopes':len(sources),
  'independent_components_known':len(components) if components else None,'status':'low-data/exploratory','unobserved_relations':'unknown'},
  'target_access':False,'silent_scope_widening':False,
  'statistics_sha256':digest([{'role':s['role'],'weight_q':s['weight_q'],
   'tokens':[{'context':t['context'],'gap_q':t['value']['gap_q'],'members':[{'voice':m['voice'],'written_duration_q':m['written_duration_q'],'tied_duration_q':m['tied_duration_q'],'marks':m['marks']} for m in t['value']['birth']['members']]} for t in s['tokens']],
   'kinds':[{'value':r['value'],'context':r['context']} for r in s['kinds']], 'return_distances':[r['distance'] for r in s['returns']]} for s in sources])},'model_sha256')

def query(model,family,context):
 """Every selected observation remains positive; specific context adds mass."""
 result=[]; reports=[]
 for source in model['sources']:
  rows=source[family]; sw=Q(source['weight_q'])
  if not rows:
   reports.append({'scope_sha256':source['scope_sha256'],'status':'no_observations'}); continue
  levels=[('previous_kind',)] if family=='kinds' else [('kind','meter','phase_q','previous_gap_q'),('kind','meter','phase_q'),('kind',)]
  hit=[]; level='selected_global'
  for keys in levels:
   if all(context.get(k) is not None for k in keys):
    hit=[r for r in rows if all(r['context'].get(k)==context[k] for k in keys)]
    if hit: level='+'.join(keys); break
  if not hit: hit=rows
  local=Q(3,4) if level!='selected_global' else Q(0); glob=1-local
  reports.append({'scope_sha256':source['scope_sha256'],'level':level,'local_count':len(hit),'global_count':len(rows),
   'local_mass_q':str(local),'global_mass_q':str(glob),'scope_weight_q':str(sw)})
  grouped={}
  contributions=[(r,sw*glob/len(rows),'global') for r in rows]+[(r,sw*local/len(hit),'context') for r in hit if local]
  for r,w,origin in contributions:
   key=digest(r['value'])
   out=grouped.setdefault(key,{'value':r['value'],'weight_q':Q(0),'count':0,'origin':'empirical','source_addresses':[],'contributions':[]})
   out['weight_q']+=w
   if r['address'] not in out['source_addresses']: out['source_addresses'].append(r['address']); out['count']+=1
   out['contributions'].append({'layer':origin,'weight_q':str(w),'source_address':r['address']})
  result += [{**r,'weight_q':str(r['weight_q'])} for r in grouped.values()]
 return result,reports
