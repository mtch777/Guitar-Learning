"""Transactional, phrase-scoped edits of an already completed Review snapshot.
Never changes the original session or regenerates unselected pipeline stages.
"""
import copy, math, pathlib, random, tempfile
from fractions import Fraction as Q
import engine as E
C,R,S,T=E.C,E.R,E.S,E.T

class EditBlocked(ValueError): pass

def _groups(notes):
 groups={}
 for n in notes:
  start=Q(str(n.get('start_exact',n.get('start_beats'))))
  if n.get('carry_in') or start<0:raise EditBlocked('Carry-in notes cannot be reassigned without changing another phrase.')
  groups.setdefault(start,[]).append(n)
 return [sorted(v,key=lambda n:n['note_slot']) for _,v in sorted(groups.items())]

def _signature(notes):return tuple(map(len,_groups(notes)))

def _transfer_pitches(old,new):
 oldgroups,newgroups=_groups(old),_groups(new)
 if list(map(len,oldgroups))!=list(map(len,newgroups)):raise EditBlocked('New rhythm cannot preserve the existing ordered pitch groups.')
 result=[]
 for olds,news in zip(oldgroups,newgroups):
  for before,after in zip(olds,news):
   note=copy.deepcopy(after)
   for key in ('midi_pitch','source_midi_pitch','target_attack_group','source_attack_group'):
    if key in before:note[key]=copy.deepcopy(before[key])
   result.append(note)
 return sorted(result,key=lambda n:n['note_slot'])

def _stage(state,i):
 entry=next((s for s in state.get('stages',[]) if str(s.get('id'))==str(i)),None)
 if not entry or not isinstance(entry.get('output'),dict):raise EditBlocked('Required original stage is unavailable.')
 return entry

def _members(roots,selected):
 wanted={roots[i] for i in selected}
 return {i for i,root in roots.items() if root in wanted}

class SelectiveEditor:
 def __init__(self,engine):self.engine=engine
 def plan(self,state,current_phrases,selected,mode):
  if mode not in ('rhythm','pitches','both'):raise EditBlocked('Choose rhythm, pitches, or both.')
  if not isinstance(selected,list) or not selected or any(type(i) is not int for i in selected):raise EditBlocked('Select at least one phrase.')
  blueprint=_stage(state,2)['output']['details']['blueprint'];rows=blueprint['phrases']
  ids=[int(r['Phrase #']) for r in rows]
  if ids!=list(range(1,len(rows)+1)) or [p.get('phrase') for p in current_phrases]!=ids:raise EditBlocked('Review phrase positions do not match the scaffold.')
  if not set(selected)<=set(ids):raise EditBlocked('Selected phrase is outside this riff.')
  exact=S.exact_roots(rows);rhythm=C.repeat_roots(rows)
  timing=_members(rhythm,selected) if mode!='pitches' else set()
  pitch=_members(exact,selected) if mode!='rhythm' else set()
  return {'selected':sorted(set(selected)),'affected':sorted(timing|pitch),'rhythm_affected':sorted(timing),'pitch_affected':sorted(pitch),'pitch_preserved':sorted(timing-pitch),'mode':mode}
 def regenerate(self,state,current_phrases,selected,mode,rng):
  if type(rng) is not int:raise EditBlocked('Random seed must be an integer.')
  expected=state.get('dataset',state.get('_dataset'))
  if not isinstance(expected,dict) or any(expected.get(k)!=v for k,v in self.engine.hashes.items()):raise EditBlocked('Dataset changed or is unverified; this riff was not edited.')
  plan=self.plan(state,current_phrases,selected,mode)
  rows=_stage(state,2)['output']['details']['blueprint']['phrases'];seed=_stage(state,1)['output']['summary']['Riff']
  original=copy.deepcopy(current_phrases);phrases=copy.deepcopy(current_phrases)
  for row,phrase in zip(rows,phrases):
   if Q(str(phrase['length_beats']))!=Q(str(row['Length (beats)'])) or Q(str(phrase['start_beats']))!=Q(str(row['Start position (beats)'])):raise EditBlocked('Review phrase positions changed; refusing to shift other phrases.')
   self._validate_notes(phrase['notes'],phrase['length_beats'],phrase['phrase'] in set(plan['affected']))
  timing=set(plan['rhythm_affected']);pitch=set(plan['pitch_affected']);affected=timing|pitch
  exact=S.exact_roots(rows);rhythm=C.repeat_roots(rows)
  p2=_stage(state,2);p3=_stage(state,3);p4=_stage(state,4);p5=_stage(state,5)
  weights=p2['output']['details']['field_weights']
  rp={**E.DEFAULTS['3'],**p3.get('applied',{})};scores=self.engine.scores(seed,weights)
  decisions=[]
  # Frozen pitches include rhythm-only siblings and all untouched phrases.
  frozen=[n for p in phrases if p['phrase'] not in pitch for n in p['notes']]
  scales=T.from_notes(frozen)
  if not scales:raise EditBlocked('Unchanged phrases do not share a compatible scale; no other phrase was altered.')
  with E.settings(fields=weights,fit=rp['opening_weights'],context=rp['context_weights'],preferences=rp['phrase_preferences']):
   for root in sorted({rhythm[i] for i in timing}):
    members=sorted(i for i in timing if rhythm[i]==root)
    constraints={_signature(phrases[i-1]['notes']) for i in members if i not in pitch}
    if len(constraints)>1:raise EditBlocked('Linked rhythms have incompatible ordered pitch groups; keeping pitches requires a compatible rhythm.')
    signature=next(iter(constraints)) if constraints else None
    notes,decision=self._rhythm_draw(rows,root,phrases,scores,rp['method'],rng+root*2,signature)
    for i in members:
     phrases[i-1]['notes']=copy.deepcopy(notes) if i in pitch else _transfer_pitches(original[i-1]['notes'],notes)
    decisions.append({'kind':'rhythm','phrases':members,**decision})
  with tempfile.TemporaryDirectory(prefix='riff-selective-') as temporary:
   for root in sorted({exact[i] for i in pitch}):
    members=sorted(i for i in pitch if exact[i]==root);row=rows[root-1];slots=S.stripped(phrases[root-1]['notes'])
    if any(S.stripped(phrases[i-1]['notes'])!=slots for i in members):raise EditBlocked('Exact-repeat timing is inconsistent; no changes were applied.')
    if not slots:
     notes=[];decision={'method':'Preserved silence'}
    else:
     pp={**E.DEFAULTS['4' if root==1 else '5'],**(p4 if root==1 else p5).get('applied',{})}
     target={'Phrase role':row['Phrase role'],'Category - dominant texture':row['Dominant texture'],'Accent function':row['Accent function']}
     with E.settings(fit=pp['fit_weights'],tiers=pp['tier_weights'],preferences=pp['phrase_preferences']):
      # With no frozen or earlier chosen notes, the opening remains unrestricted.
      prior=None if not frozen and not any(d['kind']=='pitch' and d.get('notes_count',0) for d in decisions) else scales
      report=self.engine.pitch.run(seed,{'selection_performed':True,'selected_rhythm':slots},pathlib.Path(temporary)/str(root),rng+root*2+1,target_row=target,current_scales=prior,similarities=scores)
     if not report.get('selection_performed'):raise EditBlocked('Phrase '+str(root)+': '+report.get('reason','No compatible pitch reference.'))
     notes=report['notes'];decision={'method':'Weighted pitch selection','source_riff':report['selected']['riff_id'],'source_phrase':report['selected']['phrase'],'tier':report['selected']['tier']}
    if S.stripped(notes)!=slots:raise EditBlocked('Pitch lookup changed fixed rhythm; edit was discarded.')
    scales=T.from_notes(notes,scales)
    if not scales:raise EditBlocked('New pitches do not share a scale with unchanged phrases; edit was discarded.')
    for i in members:phrases[i-1]['notes']=copy.deepcopy(notes)
    decisions.append({'kind':'pitch','phrases':members,'notes_count':len(notes),**decision})
  for i,(before,after) in enumerate(zip(original,phrases),1):
   if i not in affected and after!=before:raise AssertionError('Unselected phrase changed')
   if before['start_beats']!=after['start_beats'] or before['length_beats']!=after['length_beats']:raise AssertionError('Phrase window changed')
   self._validate_notes(after['notes'],after['length_beats'],i in affected)
   if i in affected and i not in pitch and [[n['midi_pitch'] for n in g] for g in _groups(before['notes'])]!=[[n['midi_pitch'] for n in g] for g in _groups(after['notes'])]:raise AssertionError('Frozen pitch sequence changed')
   if i not in timing and S.stripped(after['notes'])!=S.stripped(before['notes']):raise AssertionError('Frozen rhythm changed')
  for i,root in exact.items():
   if phrases[i-1]['notes']!=phrases[root-1]['notes']:raise EditBlocked('Exact-repeat notes are inconsistent; edit was discarded.')
  for i,root in rhythm.items():
   if S.stripped(phrases[i-1]['notes'])!=S.stripped(phrases[root-1]['notes']):raise EditBlocked('Rhythm-repeat notes are inconsistent; edit was discarded.')
  if not T.from_notes([n for p in phrases for n in p['notes']]):raise EditBlocked('Edited riff has no shared compatible scale; edit was discarded.')
  provenance_keys=('method','source_riff','source_phrase','tier','candidate_count','selected_score','selected_probability','components','random_seed','rng_seed','copy_from','matching_scale_sets','matching_estimated_scale_sets','pitch_source_riff','pitch_source_phrase','source_tonic','source_tonal_status','source_mode_status','uniform_draw','weight_sum','known_weight','history_pairs')
  for i in sorted(affected):
   before=original[i-1];after=phrases[i-1]
   prior={k:copy.deepcopy(before[k]) for k in provenance_keys if k in before}
   previous=before.get('edit_provenance',{})
   for k in provenance_keys:after.pop(k,None)
   details={'mode':mode,'random_seed':rng}
   for kind,changed in (('rhythm',timing),('pitch',pitch)):
    if i in changed:
     decision=next(d for d in decisions if d['kind']==kind and i in d['phrases'])
     details[kind]={'status':'changed',**copy.deepcopy(decision)}
     if i!=min(decision['phrases']):details[kind]['copy_from']=min(decision['phrases'])
    else:details[kind]={'status':'preserved','provenance':copy.deepcopy(previous.get(kind,prior))}
   after['edit_provenance']=details
  return {**plan,'phrases':phrases,'audio':E.audio(phrases,'Edited riff'),'decisions':decisions,'random_seed':rng,'possible_scales':T.public(scales)}
 @staticmethod
 def _validate_notes(notes,length,bounded=True):
  for n in notes:
   if not isinstance(n,dict) or any(type(n.get(k)) not in (int,float) or not math.isfinite(n[k]) for k in ('start_beats','end_beats','midi_pitch')):raise EditBlocked('Incomplete note evidence; no changes were applied.')
   if (bounded and (n['start_beats']<0 or n['end_beats']>float(length)+1e-8)) or n['end_beats']<=n['start_beats'] or n['midi_pitch']!=int(n['midi_pitch']) or not 0<=n['midi_pitch']<=127:raise EditBlocked('Notes cross a phrase boundary or have invalid pitch evidence; no changes were applied.')
 def _rhythm_draw(self,rows,idx,phrases,scores,mode,rng,signature):
  row=rows[idx-1];length=Q(str(row['Length (beats)']));cats=C.categories(row);candidates=[]
  for c in self.engine.rhythm.lengths.get(length,[]):
   if signature is not None:
    try:
     if _signature(c['notes'])!=signature:continue
    except EditBlocked:continue
   candidates.append(c)
  chosen=[{'notes':p['notes'],'features':C.features(p['notes'],p['length_beats']),'categories':C.categories(rows[i])} for i,p in enumerate(phrases[:idx-1])]
  audit=[]
  for c in candidates:
   rid,j=c['key'];prev=self.engine.rhythm.items.get((rid,j-1));prevfit=C.match(chosen[-1],prev)['score'] if prev and chosen else None;aligned=[]
   for offset in range(1,min(idx,j)):
    earlier=self.engine.rhythm.items.get((rid,j-offset))
    if earlier:
     value=C.match(chosen[-offset],earlier)['score']
     if value is not None:aligned.append(value)
   vals={'current':C.current(cats,c['categories']),'previous':prevfit,'history':math.fsum(aligned)/len(aligned) if aligned else None,'context':C.context(scores.get(rid),idx,len(rows),j,len(self.engine.rhythm.by[rid]))}
   if idx==1 or mode=='independent':
    target={'Phrase role':cats['role'],'Category - dominant texture':cats['texture'],'Accent function':cats['accent']};result=R.score(target,c['row'],scores.get(rid));score=result['score']
   else:score,_=C.weighted(vals)
   factor,flags=E.P.rhythm(c['notes'],c['row'])
   audit.append((c,(score or 0)*factor,vals))
  total=math.fsum(a[1] for a in audit)
  if total<=0:raise EditBlocked('Phrase '+str(idx)+': no positive-weight exact-length rhythm fits the pitches that must stay unchanged.')
  u=random.Random(rng).random();acc=0;winner=None
  for candidate,score,vals in audit:
   acc+=score
   if u*total<acc:winner=(candidate,score,vals);break
  if winner is None:raise EditBlocked('Rhythm selection could not be resolved.')
  c,score,vals=winner
  return copy.deepcopy(c['notes']),{'method':'Weighted rhythm selection','source_riff':c['key'][0],'source_phrase':c['key'][1],'candidate_count':len(candidates),'selected_score':score,'selected_probability':score/total,'components':vals,'pitch_group_pattern_required':list(signature) if signature is not None else None}

def plan_selection(state,current_phrases,selected,mode):
 """Pure scope preview; does not load data, choose notes, or mutate input."""
 return SelectiveEditor(None).plan(state,current_phrases,selected,mode)
