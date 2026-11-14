"""Isolated first-phrase pitch transfer; four tiers share one weighted draw."""
import pathlib,sys,csv,json,re,collections,math,random,hashlib,copy
from fractions import Fraction as Q
P=pathlib.Path(__file__).parent;sys.path.insert(0,str(P.parent/'weighted-scoring'))
import weighted_scoring as W,opening_rhythm as R
import tonal_scale_sets as T
import phrase_preferences as P
MULTIPLIERS={1:1.,2:.75,3:.5,4:.25}
EVENTS='Rhythmic events in order (all attacks/rests; dotted notes/tuplets/ties; simultaneous chords grouped)'
CENTER='Provisional tonal center/key (riff; mapped)'
MODES_FIELD='Compatible modes (phrase; mapped; provisional riff tonic)'
MODE_STATUS='Mode compatibility status (phrase; mapped; provisional riff tonic)'
PCS={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def midi(s):
 m=re.fullmatch(r'([A-G](?:#|b)?)(-?\d+)',s)
 return PCS[m[1]]+12*(int(m[2])+1) if m else None
def groups(row):
 gg=re.findall(r'(?:^|; )([^:;]+): \[([^\]]*)\]',row[EVENTS])
 out=[[midi(p) for p in notes.split()] for _,notes in gg]
 if len(out)!=int(row['Attack count']) or sum(map(len,out))!=int(row['Individual note count']):raise ValueError('Incomplete attack group export')
 return out
def alignment(target,source,valid=None):
 """Closest eligible tier; earliest valid alignment. One result per reference."""
 valid=valid or [True]*len(source);n=len(target);m=len(source)
 if not n:return None
 if m==n:
  if not all(valid):return None
  if target==source:return 1,list(range(n))
  if collections.Counter(target)==collections.Counter(source):
   available=collections.defaultdict(list)
   for i,x in enumerate(source):available[x].append(i)
   return 2,[available[x].pop(0) for x in target]
  return None
 if m<n:return None
 for start in range(m-n+1):
  if source[start:start+n]==target and all(valid[start:start+n]):return 3,list(range(start,start+n))
 chosen=[];cursor=0
 for want in target:
  while cursor<m and (source[cursor]!=want or not valid[cursor]):cursor+=1
  if cursor==m:return None
  chosen.append(cursor);cursor+=1
 return 4,chosen
class Engine:
 def __init__(self,csv_path):
  self.csv_path=pathlib.Path(csv_path)
  with self.csv_path.open(encoding='utf-8-sig',newline='') as f:self.rows=[r for r in csv.DictReader(f) if r['Status']=='complete']
  self.first={r['Riff ID']:r for r in self.rows if r['Phrase #']=='1'}
  self.parsed={rid:W.parse_phrase(r) for rid,r in self.first.items()};self.refs=[]
  for r in self.rows:
   g=groups(r);self.refs.append((r,g,[len(x) for x in g]))
 def run(self,seed_id,rhythm,out,rng_seed,*,target_row=None,current_scales=None,similarities=None,context_notes=None):
  out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
  path=out/'first_phrase_pitch.json'
  if path.exists():raise ValueError('Refuse overwrite existing pitch draw; use isolated output')
  seed=self.first[seed_id];fit_target=target_row if target_row is not None else seed;slots=rhythm.get('selected_rhythm',[]);gg=collections.defaultdict(list)
  report={'stage':'first phrase pitch review only','seed_riff_id':seed_id,'target_tonic':seed.get(CENTER,''),'target_tonal_status':seed.get('Tonal estimate status (riff; mapped)',''),'candidate_scope':'All completed phrases except unresolved reference phrase roles; all artists and self included; no length cutoff, similarity threshold, tier gateway or tonal compatibility requirement','tier_multipliers':MULTIPLIERS,'similarity_weights':R.WEIGHTS,'similarity_is_provisional':True,'target_timing_preserved':True,'production_draws_modified':False,'other_phrase_pitches_generated':False,'csv_sha256':hashlib.sha256(self.csv_path.read_bytes()).hexdigest()}
  def blocked(reason):
   report.update({'status':'blocked','reason':reason,'selection_performed':False});path.write_text(json.dumps(report,indent=2));return report
  if R.unresolved_role(seed):return blocked('Unresolved seed role is excluded from selection; CSV retained')
  if not rhythm.get('selection_performed'):return blocked('Opening rhythm not selected')
  if any(n.get('carry_in') or Q(n['start_exact'])<0 for n in slots):return blocked('Carry-in pitch slots have no attacked-note correspondence; not invented or removed')
  for n in slots:gg[Q(n['start_exact'])].append(n)
  target_groups=[sorted(v,key=lambda n:n['note_slot']) for t,v in sorted(gg.items())];pattern=list(map(len,target_groups));report['target_pattern']=pattern
  if not pattern:return blocked('Selected rhythm has no attacked notes; no pitch transfer needed')
  if current_scales is not None and not current_scales:return blocked('No common diatonic scale remains from generated notes')
  if similarities is None:similarities={rid:W.compare_parsed(self.parsed[seed_id],p)['score'] for rid,p in self.parsed.items()}
  report['current_possible_scales']=T.public(current_scales) if current_scales is not None else None
  report['tonal_matching_used']=current_scales is not None
  if current_scales is not None:report['candidate_scope']=report['candidate_scope'].replace(' or tonal compatibility requirement','')+'; subsequent phrase additionally requires estimated relative-key/scale match and actual matched notes fit'
  candidates=[];excluded=collections.Counter();structural=collections.Counter()
  for row,pitches,source_pattern in self.refs:
   key=(row['Riff ID'],int(row['Phrase #']))
   if R.unresolved_role(row):excluded['unresolved reference phrase role']+=1;continue
   a=alignment(pattern,source_pattern)
   if a is None:excluded['no structural match']+=1;continue
   structural[a[0]]+=1
   valid=[all(p is not None and 0<=p<=127 for p in group) for group in pitches]
   common=None
   if current_scales is not None:
    source_scales,key_error=T.estimated(row)
    if key_error:excluded[key_error]+=1;continue
    common=sorted(set(current_scales)&set(source_scales))
    if not common:excluded['no matching current relative key/scale']+=1;continue
    alignments=[]
    for scale in common:
     v=[ok and all(p%12 in scale for p in group) for ok,group in zip(valid,pitches)]
     match=alignment(pattern,source_pattern,v)
     if match is not None:alignments.append(match)
    a=min(alignments,key=lambda x:(x[0],x[1])) if alignments else None
   else:a=alignment(pattern,source_pattern,valid)
   if a is None:excluded['no fully known in-range matched pitch alignment']+=1;continue
   tier,indices=a;sc=R.score(fit_target,row,similarities.get(key[0]));score=sc['score']
   if score is None:excluded['no comparable similarity fields']+=1;continue
   flags=P.sounding_flags(P.assigned_notes(slots,[pitches[i] for i in indices])+(context_notes or []));preference=P.multiplier(flags)
   candidates.append({'preference_multiplier':preference,'preference_flags':flags,'riff_id':key[0],'phrase':key[1],'artist':row['Artist'],'tier':tier,'similarity':score,'known_weight':sc['known_weight'],'components':sc['components'],'tier_multiplier':MULTIPLIERS[tier],'weight':score*MULTIPLIERS[tier]*preference,'source_group_indices_zero_based':indices,'source_pattern':source_pattern,'source_tonic':row.get(CENTER,''),'source_tonal_status':row.get('Tonal estimate status (riff; mapped)',''),'source_warnings':row['Unknowns and warnings'],'source_compatible_modes':row.get(MODES_FIELD,''),'source_mode_status':row.get(MODE_STATUS,''),'matching_current_scales':[list(k) for k in (common or [])],'transpose_semitones':0,'mapped_source_pitch_groups':[pitches[i] for i in indices]})
  candidates.sort(key=lambda c:(c['riff_id'],c['phrase']));total=math.fsum(c['weight'] for c in candidates)
  report.update({'all_completed_reference_phrases':len(self.refs),'structural_tier_counts':dict(structural),'eligible_tier_counts':dict(collections.Counter(c['tier'] for c in candidates)),'excluded_counts':dict(excluded),'eligible_candidates':len(candidates),'positive_weight_candidates':sum(c['weight']>0 for c in candidates),'sum_weights':total})
  if total<=0:return blocked('No positive-weight pitch candidates after evidence checks')
  u=random.Random(rng_seed).random();acc=0;selected=None
  for c in candidates:
   c['probability']=c['weight']/total;acc+=c['weight']
   if selected is None and u*total<acc:selected=c
  assert selected is not None and abs(math.fsum(c['probability'] for c in candidates)-1)<1e-12
  notes=[]
  for i,(target,source) in enumerate(zip(target_groups,selected['mapped_source_pitch_groups'])):
   for n,pitch in zip(target,sorted(source)):
    notes.append({**copy.deepcopy(n),'midi_pitch':pitch,'source_midi_pitch':pitch,'target_attack_group':i+1,'source_attack_group':selected['source_group_indices_zero_based'][i]+1})
  notes.sort(key=lambda n:n['note_slot'])
  assert len(notes)==len(slots)
  report.update({'status':'selected for review','selection_performed':True,'rng_seed':rng_seed,'uniform_draw':u,'selected':selected,'selected_exact_seed_phrase':(selected['riff_id'],selected['phrase'])==(seed_id,1),'notes':notes,'register_diagnostics':{'notes_below_E1_MIDI28':sum(n['midi_pitch']<28 for n in notes),'lowest_midi_pitch':min(n['midi_pitch'] for n in notes),'highest_midi_pitch':max(n['midi_pitch'] for n in notes),'guitar_playability_verified':False},'mapping_rule':'Within each matched source chord, ascending pitch assigned to ascending target slot ID. Tier2 uses earliest unused source group of required multiplicity; tier3 earliest valid window; tier4 earliest valid subsequence. One candidate per reference phrase.','transposition_rule':'No transposition. Preserve original mapped MIDI pitches exactly. No tonal center, mode, key or scale requirement for first phrase.','limitations':['Source tonal labels are provenance only and are not selection requirements. Generated first phrase is the tonal evidence for a later stage; no later generation or tonal inference is performed here.','Simultaneous groups preserved; compatibility of notes sustained across later attacks is unverified, not silently repaired.','Tiers2-4 transfer selected groups, not a claim of melodic equivalence.','Output velocities are neutral rendering defaults, not inferred expression.']})
  if current_scales is not None:report['limitations'][0]='Candidate provisional tonic and all compatible modes gate subsequent-phrase lookup. Running possibilities are refined from actual generated notes, not forced donor key labels.'
  path.write_text(json.dumps(report,indent=2))
  with (out/'pitch_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
   fields=['riff_id','phrase','artist','tier','similarity','known_weight','tier_multiplier','weight','probability','source_tonic','source_tonal_status','source_mode_status','transpose_semitones','source_group_indices_zero_based','matching_current_scales']; w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(c[k]) if isinstance(c[k],list) else c[k] for k in fields} for c in candidates)
  with (out/'first_phrase_notes.csv').open('w',encoding='utf-8-sig',newline='') as f:
   fields=['note_slot','start_beats','duration_beats','end_beats','midi_pitch','source_midi_pitch','target_attack_group','source_attack_group','overlaps_note_slots'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:n.get(k,'') for k in fields} for n in notes)
  return report
