"""Sequential rhythm/pitch review, no transposition or performance generation."""
import pathlib,csv,json,copy,math,random,collections
from fractions import Fraction as Q
import contextual_rhythm as C,first_phrase_pitch as F,tonal_scale_sets as T,length_inheritance as L
EXACT='Intended same notes and timing as (phrase #s)'
def exact_roots(rows):
 parent={int(r['Phrase #']):int(r['Phrase #']) for r in rows}
 def root(x):
  while parent[x]!=x:x=parent[x]
  return x
 for r in rows:
  i=int(r['Phrase #'])
  for j in L.known_targets(r[EXACT]):
   if j not in parent:raise ValueError('Exact-repeat target outside scaffold')
   a,b=root(i),root(j);parent[max(a,b)]=min(a,b)
 return {i:root(i) for i in parent}
def stripped(notes):
 added={'midi_pitch','source_midi_pitch','target_attack_group','source_attack_group'}
 return [{k:copy.deepcopy(v) for k,v in n.items() if k not in added} for n in notes]
class Engine:
 def __init__(self,csv_path,source_path):
  self.pitch=F.Engine(csv_path);self.rhythm=C.Engine(csv_path,source_path)
 def rhythm_draw(self,rows,idx,chosen,scores,rng_seed,out):
  row=rows[idx-1];length=Q(str(row['Length (beats)']));cats=C.categories(row);candidates=self.rhythm.lengths.get(length,[]);audit=[]
  for c in candidates:
   rid,j=c['key'];prev=self.rhythm.items.get((rid,j-1));prevfit=C.match(chosen[-1],prev)['score'] if prev else None;aligned=[]
   for offset in range(1,min(idx,j)):
    earlier=self.rhythm.items.get((rid,j-offset))
    if earlier:
     v=C.match(chosen[-offset],earlier)['score']
     if v is not None:aligned.append(v)
   vals={'current':C.current(cats,c['categories']),'previous':prevfit,'history':math.fsum(aligned)/len(aligned) if aligned else None,'context':C.context(scores.get(rid),idx,len(rows),j,len(self.rhythm.by[rid]))};score,den=C.weighted(vals)
   audit.append({'source_riff':rid,'source_phrase':j,'score':score or 0,'known_weight':den,**vals,'history_pairs':len(aligned)})
  total=math.fsum(a['score'] for a in audit)
  if total<=0:return None,{'status':'blocked','reason':'No positive-score exact-length rhythm candidates','candidate_count':len(audit)}
  u=random.Random(rng_seed).random();acc=0;winner=None
  for c,a in zip(candidates,audit):
   a['probability']=a['score']/total;acc+=a['score']
   if winner is None and u*total<acc:winner=(c,a)
  c,a=winner
  out.mkdir(parents=True,exist_ok=True)
  with (out/'rhythm_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
  return copy.deepcopy(c['notes']),{'method':'contextual weighted rhythm draw','source_riff':a['source_riff'],'source_phrase':a['source_phrase'],'rng_seed':rng_seed,'uniform_draw':u,'selected_probability':a['probability'],'selected_score':a['score'],'weight_sum':total,'candidate_count':len(audit),'components':{k:a[k] for k in C.WEIGHTS}}
 def run(self,blueprint,opening,out,rng_base):
  out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
  if (out/'riff_pitch_sequence.json').exists():raise ValueError('Refuse overwrite prior sequential run')
  rows=blueprint['phrases'];seed=blueprint['metadata']['seed_riff_id'];exact=exact_roots(rows);rhythm_roots=C.repeat_roots(rows);scales=None;chosen=[];summaries=[]
  scores={rid:F.W.compare_parsed(self.pitch.parsed[seed],p)['score'] for rid,p in self.pitch.parsed.items()}
  report={'stage':'sequential riff pitch review','seed_riff_id':seed,'reference_riff_id':blueprint['metadata']['reference_riff_id'],'planned_phrase_count':len(rows),'rng_base':rng_base,'status':'complete','blocking_reason':None,'first_phrase_preserved':True,'no_transposition':True,'mode_aliases_considered_initially':84,'distinct_possible_scale_collections':12,'exact_repeat_roots':exact,'rhythm_repeat_roots':rhythm_roots,'phrases':summaries,'later_performance_generation':False}
  for idx,row in enumerate(rows,1):
   pdir=out/f'phrase_{idx:03d}';length=Q(str(row['Length (beats)']));before=scales
   def stop(reason):report.update({'status':'blocked','blocked_at_phrase':idx,'blocking_reason':reason})
   if idx==1:
    if not opening.get('selection_performed'):stop('Opening pitch not completed: '+opening.get('reason','unknown'));break
    notes=copy.deepcopy(opening['notes']);method={'method':'preserved first phrase','source_riff':opening['selected']['riff_id'],'source_phrase':opening['selected']['phrase']};rhythminfo={'method':'preserved first-phrase rhythm'}
    scales=T.from_notes(notes)
    if not scales:
     summaries.append({'phrase':idx,'pitch_selection':method,'rhythm_selection':rhythminfo,'notes':notes,'possible_scales_after':[],'start_beats':row['Start position (beats)'],'end_beats':row['End position (beats)']});stop('No common diatonic scale fits actual generated first phrase');break
   elif exact[idx]!=idx:
    ref=exact[idx];notes=copy.deepcopy(chosen[ref-1]['notes']);method={'method':'exact notes-and-timing copy','copy_from':ref};rhythminfo={'method':'exact notes-and-timing copy','copy_from':ref};scales=T.from_notes(notes,scales)
   else:
    if not scales:stop('No common diatonic scale remains');break
    rr=rhythm_roots[idx]
    if rr!=idx:
     notes_rhythm=stripped(chosen[rr-1]['notes']);rhythminfo={'method':'rhythm-only copy; new pitches required','copy_from':rr}
    else:
     notes_rhythm,rhythminfo=self.rhythm_draw(rows,idx,chosen,scores,rng_base+2*idx,pdir)
     if notes_rhythm is None:stop(rhythminfo['reason']);break
    target={'Phrase role':row['Phrase role'],'Category - dominant texture':row['Dominant texture'],'Accent function':row['Accent function']}
    pitch=self.pitch.run(seed,{'selection_performed':True,'selected_rhythm':notes_rhythm},pdir,rng_base+2*idx+1,target_row=target,current_scales=scales,similarities=scores)
    if not pitch.get('selection_performed'):stop(pitch.get('reason','Pitch selection failed'));break
    notes=pitch['notes'];sel=pitch['selected'];method={'method':'new weighted pitch selection','source_riff':sel['riff_id'],'source_phrase':sel['phrase'],'tier':sel['tier'],'rng_seed':pitch['rng_seed'],'uniform_draw':pitch['uniform_draw'],'selected_probability':sel['probability'],'matching_estimated_scale_sets':sel['matching_current_scales'],'source_tonic_provisional':sel['source_tonic'],'source_tonal_status':sel['source_tonal_status'],'source_mode_status':sel['source_mode_status']}
    scales=T.from_notes(notes,scales)
   if not scales:stop('No common diatonic scale after actual selected notes; no fallback');break
   assert before is None or set(scales)<=set(before)
   chosen.append({'notes':notes,'features':C.features(notes,length),'categories':C.categories(row)})
   summaries.append({'phrase':idx,'start_beats':row['Start position (beats)'],'end_beats':row['End position (beats)'],'length_beats':float(length),'scaffold_role':row['Phrase role'],'rhythm_selection':rhythminfo,'pitch_selection':method,'possible_scales_before':T.public(before) if before is not None else None,'possible_scales_after':T.public(scales),'actual_pitch_classes':sorted({n['midi_pitch']%12 for n in notes}),'notes':notes})
  report['completed_phrase_count']=len(summaries);report['final_possible_scales']=T.public(scales or ());report['generated_notes']=sum(len(s['notes']) for s in summaries);report['planned_total_beats']=blueprint['metadata']['blueprint_total_beats']
  (out/'riff_pitch_sequence.json').write_text(json.dumps(report,indent=2))
  return report
