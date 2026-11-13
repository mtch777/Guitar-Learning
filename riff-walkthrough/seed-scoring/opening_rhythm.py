"""Opening-phrase rhythm selection only. No pitches, no other phrases, no generated patterns."""
import csv,json,math,random,secrets,pathlib,hashlib
from fractions import Fraction
import weighted_scoring as W
WEIGHTS={'role':3,'texture':3,'accent':2,'source_riff_similarity':1}
def known(s):return bool(s.strip()) and not W.N.bad(s) and s not in ['none assigned']
def unresolved_role(row):
 return row.get('Phrase role','').strip().lower()=='unresolved'
def source_pool_ids(first):
 return {rid for rid,r in first.items() if known(r['Phrase role'])}
def accent(row):return row['Accent function'].split(';')[0].removeprefix('phrase function: ').strip()
def score(seed,row,riff_score):
 values={};a=seed['Phrase role'];b=row['Phrase role']
 if known(a) and known(b):values['role']=100.*(a==b)
 a=seed['Category - dominant texture'];b=row['Category - dominant texture']
 if known(a) and known(b):values['texture']=100.*(a==b)
 a=accent(seed);b=accent(row)
 if known(a) and known(b):values['accent']=100.*(a==b)
 if riff_score is not None and math.isfinite(riff_score) and 0<=riff_score<=100:values['source_riff_similarity']=riff_score
 denominator=sum(WEIGHTS[k] for k in values)
 return {'score':sum(WEIGHTS[k]*v for k,v in values.items())/denominator if denominator else None,'known_weight':denominator,'possible_weight':sum(WEIGHTS.values()),'components':values}
def load_source(path):
 # Adapter is strict: source extractor must supply verified pitch-free structured intervals.
 obj=json.loads(pathlib.Path(path).read_text())
 records=obj['candidates']
 lookup={(r['riff_id'],int(r['phrase_number'])):r for r in records}
 if len(lookup)!=len(records):raise ValueError('Duplicate source phrase timing records')
 return lookup,obj

def validated_notes(record,required_length):
 reasons=[]
 if not record.get('complete',record.get('status')=='complete'):reasons.extend(record.get('rejection_reasons') or record.get('reasons') or ['Structured note timing incomplete'])
 if reasons:return [],reasons
 try:
  if Fraction(str(record.get('length_q',record.get('length_beats'))))!=required_length:reasons.append('Structured phrase length does not match seed')
 except (ValueError,TypeError,ZeroDivisionError):reasons.append('Structured phrase length unavailable')
 notes=record.get('notes')
 if not isinstance(notes,list):reasons.append('Structured notes list unavailable')
 clean=[]
 for i,n in enumerate(notes or [],1):
  try:
   start=Fraction(str(n.get('onset_q',n.get('start_beats'))));duration=Fraction(str(n.get('tied_duration_q',n.get('duration_beats'))));end=Fraction(str(n.get('tied_end_q',n.get('end_beats'))))
   if duration<=0 or end-start!=duration:raise ValueError('invalid duration/end')
   if start>=required_length or end<=0:raise ValueError('note does not intersect phrase window')
   clean.append({'note_slot':i,'start_beats':float(start),'duration_beats':float(duration),'end_beats':float(end),'start_exact':str(start),'duration_exact':str(duration),'end_exact':str(end),'voice':n.get('voice'),'carry_in':start<0,'carry_out':end>required_length,'tie_extended':bool(n.get('tie_extended',False)),'written_duration_exact':n.get('written_duration_q','')})
  except (KeyError,ValueError,ZeroDivisionError,TypeError) as e:reasons.append(f'Note {i}: incomplete/invalid timing ({e})')
 return clean,reasons

def run(seed,candidates,source_csv,source_data,out,*,cached=None,rng_seed_override=None):
 if unresolved_role(seed):raise ValueError('Unresolved seed role is excluded from selection; CSV retained')
 pool={r:s for r,s,_ in candidates};required=Fraction(seed['Length (quarter-note beats)']);records,raw=load_source(source_data) if cached is None else cached['source']
 seed_record=records.get((seed['Riff ID'],int(seed['Phrase #'])))
 if seed_record:
  try:source_length=Fraction(str(seed_record.get('length_q',seed_record.get('length_beats'))))
  except (ValueError,TypeError,ZeroDivisionError):source_length=required
  if abs(source_length-required)<=Fraction(1,10**8):required=source_length
 eligible=[];excluded=[];unavailable_riffs=set();other_length_count=0;unprocessed=[];unresolved_phrase_exclusions=0
 with pathlib.Path(source_csv).open(encoding='utf-8-sig',newline='') as f:
  allrows=list(csv.DictReader(f)) if cached is None else cached['rows']
  first={r['Riff ID']:r for r in allrows if r['Status']=='complete' and r['Phrase #']=='1'}
  expected=source_pool_ids(first)
  if set(pool)!=expected:raise ValueError('Rhythm pool must include every known-opening-role riff, including self and different known roles')
  for row in allrows:
   rid=row['Riff ID']
   if row['Status']!='complete':unavailable_riffs.add(rid);continue
   if rid not in pool:continue
   if unresolved_role(row):unresolved_phrase_exclusions+=1;continue
   if Fraction(row['Length (quarter-note beats)'])!=Fraction(seed['Length (quarter-note beats)']):other_length_count+=1;continue
   key=(rid,int(row['Phrase #']));record=records.get(key)
   if record is None:
    unprocessed.append({'riff_id':rid,'phrase':key[1]});excluded.append({'riff_id':rid,'phrase':key[1],'reason':'No extraction record; not yet evaluated, not presumed invalid'});continue
   notes,reasons=validated_notes(record,required)
   if reasons:excluded.append({'riff_id':rid,'phrase':key[1],'reason':'; '.join(reasons)});continue
   result=score(seed,row,pool[rid])
   if result['score'] is None:excluded.append({'riff_id':rid,'phrase':key[1],'reason':'No comparable scoring fields'});continue
   eligible.append({'riff_id':rid,'phrase':key[1],'artist':row['Artist'],'length_beats':float(required),'role':row['Phrase role'],'texture':row['Category - dominant texture'],'accent_function':accent(row),'source_riff_score':pool[rid],**result,'notes':notes,'source_record':record})
 eligible.sort(key=lambda r:(r['riff_id'],r['phrase']));total=math.fsum(r['score'] for r in eligible);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 report={'stage':'opening phrase rhythm selection only','seed_riff_id':seed['Riff ID'],'seed_phrase':int(seed['Phrase #']),'seed_length_beats':float(required),'source_riff_count':len(pool),'pool_rule':'All completed riffs with known opening role; different known roles and self included; no cap; exact-length reference phrases with unresolved role excluded','source_opening_role_filter':'exclude unknown only','unresolved_reference_phrase_exclusions':unresolved_phrase_exclusions,'unknown_opening_role_riffs_excluded':len(first)-len(expected),'self_excluded':False,'artist_filter':False,'minimum_score_threshold':None,'source_riffs_with_missing_similarity':sum(v is None for v in pool.values()),'unavailable_failed_riff_count':len(unavailable_riffs),'different_length_phrases':other_length_count,'exact_length_candidate_count':len(eligible)+len(excluded),'eligible_candidate_count':len(eligible),'unevaluated_source_candidate_count':len(unprocessed),'excluded':excluded,'field_weights':WEIGHTS,'unknowns_excluded_from_denominator':True,'deduplication':False,'source_data_sha256':hashlib.sha256(pathlib.Path(source_data).read_bytes()).hexdigest() if cached is None else cached['source_hash'],'sum_candidate_scores':total,'pitch_generated_or_copied':False,'other_phrase_rhythms_selected':False,'new_rhythm_pattern_generated':False,'pool':[{'riff_id':r,'score':s} for r,s in pool.items()]}
 if unprocessed:
  report.update({'status':'blocked: full source extraction not finished; refusing partial-universe draw','selection_performed':False});(out/'opening_rhythm_selection.json').write_text(json.dumps(report,indent=2));return report
 if not eligible or total<=0:
  report.update({'status':'blocked: no positive-weight complete exact-length rhythm candidates','selection_performed':False});(out/'opening_rhythm_selection.json').write_text(json.dumps(report,indent=2));return report
 path=out/'opening_rhythm_selection.json'
 if path.exists():
  old=json.loads(path.read_text())
  if old.get('selection_performed'):
   if old['source_data_sha256']!=report['source_data_sha256'] or old['pool']!=report['pool']:raise ValueError('Existing rhythm draw belongs to a different pool/source snapshot; do not silently redraw')
   rng_seed=old['rng_seed'];u=old['uniform_draw']
  else:rng_seed=(secrets.randbits(128) if rng_seed_override is None else rng_seed_override);u=random.Random(rng_seed).random()
 else:rng_seed=(secrets.randbits(128) if rng_seed_override is None else rng_seed_override);u=random.Random(rng_seed).random()
 assert random.Random(rng_seed).random()==u
 threshold=u*total;cumulative=0;selected=None
 for row in eligible:
  cumulative+=row['score'];row['probability']=row['score']/total
  if selected is None and threshold<cumulative:selected=row
 assert selected is not None and abs(math.fsum(r['probability'] for r in eligible)-1)<1e-12
 if path.exists() and old.get('selection_performed'):assert (selected['riff_id'],selected['phrase'])==(old['selected_riff_id'],old['selected_phrase']),'Do not silently redraw'
 notes=selected['notes']
 for n in notes:n['overlaps_note_slots']='; '.join(str(other['note_slot']) for other in notes if other['note_slot']!=n['note_slot'] and max(Fraction(n['start_exact']),Fraction(other['start_exact']))<min(Fraction(n['end_exact']),Fraction(other['end_exact'])))
 intervals=[]
 for note in sorted(notes,key=lambda n:Fraction(n['start_exact'])):
  a=max(Fraction(0),Fraction(note['start_exact']));b=min(required,Fraction(note['end_exact']))
  if intervals and a<=intervals[-1][1]:intervals[-1][1]=max(intervals[-1][1],b)
  else:intervals.append([a,b])
 rests=[];cursor=Fraction(0)
 for a,b in intervals:
  if a>cursor:rests.append({'start_beats':float(cursor),'end_beats':float(a),'duration_beats':float(a-cursor)})
  cursor=b
 if cursor<required:rests.append({'start_beats':float(cursor),'end_beats':float(required),'duration_beats':float(required-cursor)})
 report.update({'rest_intervals':rests,'complete_silence':not notes,'status':'selected for review','selection_performed':True,'rng_seed':rng_seed,'uniform_draw':u,'selected_riff_id':selected['riff_id'],'selected_phrase':selected['phrase'],'selected_artist':selected['artist'],'selected_score':selected['score'],'selected_probability':selected['probability'],'selected_known_weight':selected['known_weight'],'selected_score_components':selected['components'],'note_slots':len(notes),'selected_rhythm':notes,'carry_in_slots':sum(n['carry_in'] for n in notes),'carry_out_slots':sum(n['carry_out'] for n in notes),'relationship_to_existing_seed':'Rhythm proposal only; not applied to seed notes or other blueprint phrases.'})
 path.write_text(json.dumps(report,indent=2))
 public_fields=['note_slot','start_beats','duration_beats','end_beats','voice','carry_in','carry_out','tie_extended','overlaps_note_slots']
 with (out/'opening_rhythm_notes.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=public_fields);w.writeheader();w.writerows({k:n[k] for k in public_fields} for n in notes)
 audit=[]
 for r in eligible:audit.append({'Artist':r['artist'],'Riff ID':r['riff_id'],'Source phrase #':r['phrase'],'Score':r['score'],'Probability':r['probability'],'Known weight':r['known_weight'],'Possible weight':r['possible_weight'],'Role':r['role'],'Texture':r['texture'],'Accent function':r['accent_function'],'Role score':r['components'].get('role',''),'Texture score':r['components'].get('texture',''),'Accent score':r['components'].get('accent',''),'Source riff similarity':r['source_riff_score'],'Note slots':len(r['notes']),'Selected':r is selected})
 with (out/'opening_rhythm_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
 return report
