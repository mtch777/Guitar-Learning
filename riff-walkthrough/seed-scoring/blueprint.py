"""Core structure blueprint only. Never copies pitches, rhythm events, fingering, or optional features."""
import csv,json,pathlib
import length_inheritance as L
BEATS='Length (quarter-note beats)'
RELATION_FIELDS={
 'Intended same notes and timing as (phrase #s)':'Same notes and timing as (phrase #s)',
 'Intended same pitch sequence as (phrase #s)':'Same pitch sequence as (phrase #s)',
 'Intended same rhythm and holds as (phrase #s)':'Same rhythm and holds as (phrase #s)',
 'Intended variation of (phrase #s)':'Variation of (phrase #s)',
 'Variation target - what stays the same':'Variation - what stays the same',
 'Variation target - what changes':'Variation - what changes',
 'Source variation evidence status':'Variation - relationship status'}
def phrase_accent(s):
 # Keep phrase function only; source note accent counts/locations are not blueprint content.
 return s.split(';')[0].removeprefix('phrase function: ').strip()
def targets(s):
 if s=='none':return []
 try:return [int(x.strip()) for x in s.split(';')]
 except ValueError:return None

def build(seed,reference):
 reference=sorted(reference,key=lambda r:int(r['Phrase #']))
 assert [int(r['Phrase #']) for r in reference]==list(range(1,len(reference)+1))
 rows=[];core=[seed]+reference[1:];lengths={i+1:float(r[BEATS]) for i,r in enumerate(core)};conflicts=[]
 for i,(actual,donor) in enumerate(zip(core,reference),1):
  row={'Phrase #':i,'Length (beats)':float(actual[BEATS]),'Phrase role':actual['Phrase role'],'Accent function':phrase_accent(actual['Accent function']),'Dominant texture':actual['Category - dominant texture']}
  # Every target comes from donor topology, including first-position links now targeting actual seed.
  for output,source in RELATION_FIELDS.items():row[output]=donor[source]
  linked=[];bad=[]
  for label in ['Intended same notes and timing as (phrase #s)','Intended same rhythm and holds as (phrase #s)']:
   links=targets(row[label])
   if links is not None:
    for j in links:
     if j<1 or j>len(core):raise ValueError('Reference relationship target out of range')
     if lengths[i]!=lengths[j]:
      bad.append(j);conflicts.append({'phrase':i,'target':j,'relationship':label,'phrase_beats':lengths[i],'target_beats':lengths[j]})
  row['Relationship status']='Intended targets only; unverified until new notes/rhythm are generated.'
  row['Length conflict']=('Exact repeat/rhythm targets conflict with current lengths: phrase(s) '+', '.join(map(str,sorted(set(bad))))+'. No automatic resizing.') if bad else 'none detected for known exact-repeat/rhythm targets'
  rows.append(row)
 m={'type':'core scaffold blueprint','phrase_count':len(rows),'seed_riff_id':seed['Riff ID'],'seed_source_phrase':int(seed['Phrase #']),'seed_artist':seed['Artist'],'reference_riff_id':reference[0]['Riff ID'],'reference_artist':reference[0]['Artist'],'first_phrase_source':'actual seed; not donor opening','relationship_source':'reference topology for every position, including intended links to seed at position1','reference_opening_beats':float(reference[0][BEATS]),'seed_opening_beats':float(seed[BEATS]),'reference_total_beats':sum(float(r[BEATS]) for r in reference),'blueprint_total_beats':sum(lengths.values()),'length_conflicts':conflicts,'notes_or_rhythm_copied':False,'optional_scaffold_features_copied':False,'new_generation_performed':False,'unverified_relationships':'All targets are plans, not generated identity claims. Unknown source variation evidence stays unknown.'}
 resolution=L.resolve(rows)
 m['before_length_inheritance_total_beats']=m['blueprint_total_beats']
 m.update(resolution)
 return rows,m

def write(out,rows,metadata):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 with (out/'riff_blueprint.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 (out/'riff_blueprint.json').write_text(json.dumps({'metadata':metadata,'phrases':rows},indent=2))
 return out/'riff_blueprint.csv'
