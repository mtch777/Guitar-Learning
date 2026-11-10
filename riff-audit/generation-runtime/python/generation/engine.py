"""One retained selection-scoped whole-span proposal, then separate assessment."""
import copy, math, random
from fractions import Fraction as Q
from .evidence import VERSION, LAW, LIMITS, q, meter, metric, digest, seal, check, prior, query, build_selection_model
LAW_VERSION=VERSION

class BudgetAbort(Exception): pass

class Draws:
 def __init__(self,seed,raw): self.rng=random.Random(seed); self.raw=raw; self.table_bytes=0
 def choose(self,name,rows,context=None,backoff=None):
  if len(self.raw['decisions'])>=LIMITS['decisions']: raise BudgetAbort('Decision budget reached')
  rows=[r for r in rows if Q(r['weight_q'])>0]
  if not rows: raise ValueError('Empty construction support: '+name)
  table={'name':name,'context':context or {},'backoff':backoff,'outcomes':rows,'weights_are':'explicit law weights, not calibrated probabilities'}
  tid=digest(table)
  if tid not in self.raw['choice_tables']:
   from .evidence import canonical
   size=len(canonical(table).encode('utf8'))
   if self.table_bytes+size>LIMITS['choice_table_bytes']:
    self.raw['pending_choice']={'name':name,'table_sha256':tid,'estimated_bytes':size}
    raise BudgetAbort('Choice-table memory budget exceeded; no support pruned')
   self.table_bytes+=size; self.raw['choice_tables'][tid]=table
  den=1
  for r in rows:
   den=math.lcm(den,Q(r['weight_q']).denominator)
   if den.bit_length()>4096: raise BudgetAbort('Choice denominator bit budget reached')
  weights=[int(Q(r['weight_q'])*den) for r in rows]; total=sum(weights); draw=self.rng.randrange(total); acc=0
  for i,(row,w) in enumerate(zip(rows,weights)):
   acc+=w
   if draw<acc:
    receipt={'decision_index':len(self.raw['decisions']),'table_id':tid,'outcome_index':i,
     'source_addresses':copy.deepcopy(row.get('source_addresses',[])),'origin':row.get('origin','empirical')}
    self.raw['decisions'].append({'name':name,**receipt,'draw_integer':str(draw),'total_integer_weight':str(total)})
    return copy.deepcopy(row['value']),receipt
  raise AssertionError('Unreachable draw')
 def empirical(self,model,family,context):
  rows,backoff=query(model,family,context); return self.choose(family,rows,context,backoff)

def request(value):
 allowed={'extent_q','meter','start_phase_q','tempo_bpm','piece_count','piece_weights','notation_grid_q'}
 if set(value)-allowed: raise ValueError('Unknown request fields; target/path inputs are not supported')
 if 'extent_q' not in value: raise ValueError('Independent extent_q is required')
 extent=q(value['extent_q']); m=meter(value.get('meter',[4,4])); phase=q(value.get('start_phase_q','0')); grid=q(value.get('notation_grid_q','1/4'))
 if extent<=0 or grid<=0: raise ValueError('Extent and grid must be positive')
 if not 0<=phase<Q(4*m[0],m[1]): raise ValueError('Start phase must lie inside the meter')
 tempo=value.get('tempo_bpm',120)
 if type(tempo) not in (int,float) or not math.isfinite(tempo) or tempo<=0: raise ValueError('Tempo must be finite positive quarter-note BPM')
 r={'extent_q':str(extent),'meter':m,'start_phase_q':str(phase),'tempo_bpm':tempo,'notation_grid_q':str(grid)}
 if 'piece_count' in value:
  if type(value['piece_count']) is not int or value['piece_count']<1: raise ValueError('Positive integer piece_count required')
  r['piece_count']=value['piece_count']
 if 'piece_weights' in value:
  weights=list(map(q,value['piece_weights']))
  if not weights or any(w<=0 for w in weights): raise ValueError('Positive piece weights required')
  if 'piece_count' in r and len(weights)!=r['piece_count']: raise ValueError('Piece count/weights disagree')
  r['piece_count']=len(weights); r['piece_weights']=list(map(str,weights))
 return r

def geometric(draws,name,continue_weight):
 value=1
 while True:
  action,_=draws.choose(name,prior([('stop',1),('continue',continue_weight)]),{'current_value':value})
  if action=='stop': return value
  value+=1
  if name=='independent_piece_count' and value>LIMITS['pieces']: raise BudgetAbort('Geometric count exceeded piece resource cap; value not resampled')

def inventory(req,draws):
 n=req.get('piece_count')
 if n is None: n=geometric(draws,'independent_piece_count',3)
 if n>LIMITS['pieces']: raise BudgetAbort('Piece budget exceeded; count not reduced')
 weights=[]
 for i in range(n):
  if 'piece_weights' in req: w=q(req['piece_weights'][i])
  else: w=Q(geometric(draws,'independent_piece_weight',1))
  weights.append(w)
 cursor=Q(0); pieces=[]
 for i,w in enumerate(weights):
  length=q(req['extent_q'])*w/sum(weights)
  pieces.append({'id':i,'relative_weight_q':str(w),'start_q':str(cursor),'end_q':str(cursor+length),'length_q':str(length)})
  cursor+=length
 return pieces

def choose_relationships(pieces,draws,model):
 """Inventory first; source relationships choose a NEW generated organization."""
 previous='START'
 for i,piece in enumerate(pieces):
  endpoint=None
  if i:
   rows=prior([(None,3)]+[(j,Q(2,i)) for j in range(i)])
   reports=[]
   for source in model['sources']:
    usable=[]; unavailable=[]
    for r in source['returns']:
     j=i-r['distance']
     if j<0: unavailable.append(r); continue
     usable.append(r)
     rows.append({'value':j,'weight_q':source['weight_q'],'count':1,'origin':'empirical_return_distance_count',
      'source_addresses':[r['address']]})
    reports.append({'scope_sha256':source['scope_sha256'],'positive_distance_edges_available':len(usable),
     'positive_distance_edges_before_generated_history':len(unavailable),'unknown_is_not_new':True,
     'interpretation':'positive edge counts plus authored gate; not empirical NEW/RETURN prevalence'})
   endpoint,receipt=draws.choose('generated_return_endpoint',rows,{'piece_index':i},reports); piece['relation_receipt']=receipt
  if endpoint is None:
   kind,receipt=draws.empirical(model,'kinds',{'previous_kind':previous})
   piece.update(motif_id=i,return_of=None,source_kind=kind,kind_receipt=receipt,operation='new_generated_material')
  else:
   source_piece=pieces[endpoint]
   piece.update(motif_id=source_piece['motif_id'],return_of=endpoint,source_kind=source_piece['source_kind'],operation='scaled_generated_motif_return')
  previous=piece['source_kind']

UNKNOWN_BIRTH={'members':[{'voice':None,'written_duration_q':None,'tied_duration_q':None,'marks':None,
 'source_occurrence':None,'source_ids':None,'source_segments':[],'boundary_censored':None,
 'unknowns':['no_attack_evidence','voice','marks','written_hold','tied_hold']}]}

def token(draws,model,context):
 rows,backoff=query(model,'tokens',context)
 rows += prior([({'gap_q':g,'birth':None},Q(1,16)) for g in ['1/4','1/2','1','2']])
 chosen,receipt=draws.choose('joint_gap_coattack_holds',rows,context,backoff)
 if chosen['birth'] is None:
  births,br=query(model,'tokens',context)
  if births:
   empirical,birth_receipt=draws.choose('prior_gap_empirical_birth',births,context,br)
   chosen['birth']=empirical['birth']; receipt['birth_receipt']=birth_receipt
  else: chosen['birth']=copy.deepcopy(UNKNOWN_BIRTH); receipt['birth_origin']='authored_unknown_neutral_pulse'
 if chosen['gap_q'] is None:
  gap,gap_receipt=draws.choose('unknown_terminal_gap_prior',prior([(g,1) for g in ['1/4','1/2','1','2']]))
  chosen['gap_q']=gap; receipt['unknown_gap']=True; receipt['gap_prior_receipt']=gap_receipt
 return chosen,receipt

def members(birth,onset,event_id,receipt,scale):
 result=[]
 for i,s in enumerate(birth['members']):
  wd,td=s['written_duration_q'],s['tied_duration_q']; neutral=Q(1,8) if td is None else q(td)
  result.append({'id':event_id+'/m'+str(i),'voice':s['voice'],
   'written_end_q':None if wd is None else str(onset+q(wd)*scale),'tied_end_q':None if td is None else str(onset+q(td)*scale),
   'neutral_end_q':str(onset+neutral*scale),'neutral_hold_origin':'authored_unknown_pulse' if td is None else 'sampled_source_hold',
   'marks':copy.deepcopy(s['marks']),'source_receipt':copy.deepcopy(receipt),'source_occurrence':s['source_occurrence'],
   'source_ids':copy.deepcopy(s['source_ids']),'source_segments':copy.deepcopy(s['source_segments']),
   'boundary_censored':s['boundary_censored'],'unknowns':copy.deepcopy(s['unknowns']),'guitar_execution':'not_rendered'})
 return result

def silences(events,horizon):
 intervals=sorted((q(e['onset_q']),max([q(m['neutral_end_q']) for m in e['members']] or [q(e['onset_q'])])) for e in events)
 cursor=Q(0); result=[]
 for a,b in intervals:
  if a>cursor: result.append({'start_q':str(cursor),'end_q':str(a),'kind':'unoccupied_neutral_clock','notated_rest':False})
  cursor=max(cursor,b)
 if horizon>cursor: result.append({'start_q':str(cursor),'end_q':str(horizon),'kind':'unoccupied_neutral_clock','notated_rest':False})
 return result

def generate(model,independent_request,seed):
 raw={'schema':VERSION,'status':'invalid_input','seed':seed,'model_sha256':model.get('model_sha256'),'law_sha256':digest(LAW),'statistics_sha256':model.get('statistics_sha256'),
  'scope_receipt':copy.deepcopy(model.get('scope_receipt')),'scope_mode':model.get('scope_mode'),'coverage':copy.deepcopy(model.get('coverage',{})),
  'request':copy.deepcopy(independent_request),'pieces':[],'events':[],'decisions':[],'choice_tables':{},'terminal_proposals':[],
  'source_relation_evidence':[],'boundary_conflicts':[],'target_access':False,'hidden_retries':0,'clock_complete':False,'playable':False,
  'unknowns':['Structural annotation kinds are not musical phrase roles.','Guitar feasibility and target melody mapping are not evaluated.'],
  'construction_support':copy.deepcopy(LAW),'source_onsets_relative_q':[]}
 try:
  check(model,'model_sha256')
  if model.get('schema')!='selection-evidence/1' or model.get('law_sha256')!=digest(LAW): raise ValueError('Model law/version mismatch')
  if type(seed) is not int or not -(2**63)<=seed<2**63: raise ValueError('Signed 64-bit integer seed required')
  req=request(independent_request); raw['request']=req; draws=Draws(seed,raw)
  pieces=inventory(req,draws); raw['pieces']=pieces
  raw['independent_inventory_sha256']=digest(pieces); raw['inventory_decision_count']=len(raw['decisions'])
  choose_relationships(pieces,draws,model)
  raw['structure_sha256']=digest(pieces); raw['structure_decision_count']=len(raw['decisions'])
  raw['source_relation_evidence']=[{'scope_sha256':s['scope_sha256'],'relations':copy.deepcopy(s['relations'])} for s in model['sources']]
  raw['source_onsets_relative_q']=model['sources'][0]['onsets_q'][:]
  m,phase=req['meter'],q(req['start_phase_q']); memory={}; last_attack=None; previous_gap=None; member_count=0; pending=None
  for piece in pieces:
   start,end=q(piece['start_q']),q(piece['end_q']); length=end-start; material=[]
   incoming_pending=pending
   if piece['return_of'] is not None:
    original=memory[piece['motif_id']]; scale=length/original['length']; piece['return_scale_q']=str(scale)
    material=[{'offset':e['offset']*scale,'birth':e['birth'],'scale':scale,
      'receipt':{**e['receipt'],'generated_return_of':piece['motif_id'],'return_scale_q':str(scale)}} for e in original['material']]
    pending=start+original['exit_offset']*scale
    first=start+material[0]['offset'] if material else None
    comparison_clock=first if first is not None else pending
    if incoming_pending is not None and comparison_clock!=incoming_pending:
     raw['boundary_conflicts'].append({'piece':piece['id'],'kind':'generated_return_vs_incoming_gap' if first is not None else 'silent_return_vs_incoming_pending','incoming_proposed_q':str(incoming_pending),'returned_first_attack_q':None if first is None else str(first),'returned_pending_q':str(pending),'difference_q':str(comparison_clock-incoming_pending),'resolution':'both original proposals retained; no shifting or clipping'})
   else:
    cursor=start if pending is None else max(start,pending)
    piece['incoming_pending_q']=None if pending is None else str(pending)
    mode='carry_pending'
    if pending is None: mode,_=draws.choose('leading_silence',prior([('attack',1),('wait',1)]))
    if mode=='wait':
     t,receipt=token(draws,model,{'kind':piece['source_kind'],**metric(cursor,m,phase),'previous_gap_q':previous_gap})
     cursor+=q(t['gap_q']); raw['terminal_proposals'].append({'piece':piece['id'],'kind':'leading_wait','from_q':str(start),'proposed_q':str(cursor),'crosses_piece_end':cursor>=end,'receipt':receipt})
    while cursor<end:
     if last_attack is not None: previous_gap=str(cursor-last_attack)
     if len(raw['events'])+len(material)>=LIMITS['events']: raise BudgetAbort('Event budget reached; no truncated complete plan emitted')
     t,receipt=token(draws,model,{'kind':piece['source_kind'],**metric(cursor,m,phase),'previous_gap_q':previous_gap})
     material.append({'offset':cursor-start,'birth':t['birth'],'receipt':receipt,'scale':Q(1)})
     raw['partial_piece']={'piece_id':piece['id'],'material':[{'offset_q':str(v['offset']),'birth':v['birth'],'receipt':v['receipt']} for v in material]}
     if last_attack is not None: previous_gap=str(cursor-last_attack)
     last_attack=cursor
     next_cursor=cursor+q(t['gap_q'])
     if next_cursor>=end: raw['terminal_proposals'].append({'piece':piece['id'],'kind':'renewal_exit','from_q':str(cursor),'proposed_q':str(next_cursor),'piece_end_q':str(end),'overshoot_q':str(next_cursor-end),'receipt':receipt})
     cursor=next_cursor
    pending=cursor
    memory[piece['motif_id']]={'length':length,'material':copy.deepcopy(material),'exit_offset':cursor-start}
   for entry in material:
    onset=start+entry['offset']; eid='generated:p%s:a%s'%(piece['id'],len(raw['events'])); mm=members(entry['birth'],onset,eid,entry['receipt'],entry['scale'])
    member_count+=len(mm)
    if len(raw['events'])>=LIMITS['events'] or member_count>LIMITS['members']: raise BudgetAbort('Event/member budget reached; no complete clock')
    raw['events'].append({'attack_id':eid,'piece_id':piece['id'],'motif_id':piece['motif_id'],'onset_q':str(onset),
     'metric_phase':metric(onset,m,phase),'members':mm,'source_receipt':entry['receipt'],'rendering':'neutral_coattack_not_guitar'})
    if piece['return_of'] is not None:
     if last_attack is not None: previous_gap=str(onset-last_attack)
     last_attack=onset
   raw.pop('partial_piece',None)
   piece['outgoing_pending_q']=None if pending is None else str(pending)
  extent=q(req['extent_q']); natural=max([extent]+[q(mb['neutral_end_q']) for e in raw['events'] for mb in e['members']])
  raw.update(status='complete',clock_complete=True,playable=True,extent_q=str(extent),natural_end_q=str(natural),silences=silences(raw['events'],extent),
   pending_after_horizon={'onset_q':None if pending is None else str(pending),'status':'right_censored_next_attack_clock_no_birth_invented'},
   tempo_map=[{'onset_q':'0','bpm':req['tempo_bpm'],'quarter_bpm':req['tempo_bpm'],'linear':False}],
   meter_map=[{'bar':1,'start_q':str(-phase),'span_q':str(Q(4*m[0],m[1])),'signature':m}])
 except BudgetAbort as exc: raw.update(status='resource_abort',error={'category':'numerical_resource','message':str(exc)},playable=False)
 except (ValueError,TypeError,KeyError,OverflowError,ZeroDivisionError) as exc: raw.update(status='invalid_input',error={'category':'data_type_or_numerical_safety','message':str(exc)},playable=False)
 return seal(raw,'raw_sha256')

def generate_batch(model,independent_request,seeds,rule_profile=None):
 from .assessment import assess
 seeds=list(seeds)
 if len(seeds)>LIMITS['batch']: raise ValueError('Batch resource budget exceeded; seeds not truncated')
 results=[]
 for i,seed in enumerate(seeds):
  raw=generate(model,independent_request,seed); results.append({'request_index':i,'seed':seed,'raw':raw,'assessment':assess(raw,rule_profile)})
 return {'schema':'selection-batch/1','seeds':seeds,'results':results,'selection_policy':'all outcomes in request order','hidden_retries':0}
