"""Pitch-free sequential rhythm choices. No variation-label candidate lookup."""
import sys,pathlib,csv,json,math,random,collections,hashlib,copy
from fractions import Fraction as Q
P=pathlib.Path(__file__).parent;sys.path.insert(0,str(P.parent/'weighted-scoring'))
import weighted_scoring as W,opening_rhythm as R,length_inheritance as L
import phrase_preferences as P
WEIGHTS={'current':40,'previous':25,'history':15,'context':20}
def ratio(a,b):return 100 if a==b==0 else 100*min(a,b)/max(a,b)
def sequence(a,b):
 if not a or not b:return None
 dp=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  nxt=[i]
  for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,dp[j]+1,dp[j-1]+1-ratio(x,y)/100))
  dp=nxt
 return 100*(1-dp[-1]/max(len(a),len(b)))
def features(notes,length):
 length=float(length);starts=sorted(set(n['start_beats'] for n in notes if 0<=n['start_beats']<length));events=[]
 for n in notes:
  a=max(0,n['start_beats']);b=min(length,n['end_beats'])
  if b>a:events.extend([(a,1),(b,-1)])
 ev=collections.defaultdict(int)
 for t,d in events:ev[t]+=d
 prev=0;active=0;held=overlap=0
 for t in sorted(ev):
  if active:held+=t-prev
  if active>1:overlap+=t-prev
  active+=ev[t];prev=t
 return {'density':len(starts)/length,'spacing':[b-a for a,b in zip(starts,starts[1:])],'rest':1-held/length,'overlap':overlap/length}
def categories(row):
 return {'role':row.get('Phrase role'),'texture':row.get('Dominant texture',row.get('Category - dominant texture')),'accent':R.accent(row)}
def match(a,b):
 out={}
 if a.get('features') is not None and b.get('features') is not None:
  x=a['features'];y=b['features'];out['density']=ratio(x['density'],y['density']);out['rest']=100*(1-abs(x['rest']-y['rest']));out['overlap']=100*(1-abs(x['overlap']-y['overlap']));v=sequence(x['spacing'],y['spacing'])
  if v is not None:out['spacing']=v
 return {'score':math.fsum(out.values())/len(out) if out else None,'features':out}
def current(a,b):
 weights={'role':3,'texture':3,'accent':2};v={k:100.*(a[k]==b[k]) for k in weights if a[k] is not None and b[k] is not None and R.known(a[k]) and R.known(b[k])}
 return math.fsum(v[k]*weights[k] for k in v)/sum(weights[k] for k in v) if v else None
def weighted(values):
 present={k:v for k,v in values.items() if v is not None};den=sum(WEIGHTS[k] for k in present)
 return math.fsum(WEIGHTS[k]*v for k,v in present.items())/den if den else None,den
def position(i,n):return (i-1)/(n-1) if n>1 else None
def context(source_score,target_i,target_n,source_i,source_n):
 a=position(target_i,target_n);b=position(source_i,source_n);vals=[]
 if source_score is not None:vals.append(source_score)
 if a is not None and b is not None:vals.append(100*(1-abs(a-b)))
 return math.fsum(vals)/len(vals) if vals else None
def repeat_roots(rows):
 groups={int(r['Phrase #']):{int(r['Phrase #'])} for r in rows}
 for r in rows:
  i=int(r['Phrase #'])
  for label in L.INHERITING:
   for j in L.known_targets(r[label]):
    if j not in groups:raise ValueError('Repeat target outside scaffold')
    union=groups[i]|groups[j]
    for x in union:groups[x]=union
 roots={i:min(g) for i,g in groups.items()}
 lengths={int(r['Phrase #']):Q(str(r['Length (beats)'])) for r in rows}
 if any(lengths[i]!=lengths[root] for i,root in roots.items()):raise ValueError('Repeat group length conflict; no resizing in rhythm selection')
 return roots
class Engine:
 def __init__(self,csv_path,source_path):
  self.rows=list(csv.DictReader(open(csv_path,encoding='utf-8-sig')));self.first={r['Riff ID']:r for r in self.rows if r['Status']=='complete' and r['Phrase #']=='1'};self.pool=R.source_pool_ids(self.first);self.by=collections.defaultdict(list);self.records,raw=R.load_source(source_path);self.items={};self.lengths=collections.defaultdict(list);self.excluded=collections.Counter();self.unresolved_excluded=collections.Counter();self.parsed={rid:W.parse_phrase(r) for rid,r in self.first.items()}
  expected={(r['Riff ID'],int(r['Phrase #'])) for r in self.rows if r['Status']=='complete'}
  if not expected.issubset(self.records):raise ValueError('Full timing extraction incomplete; refusing partial source universe')
  for row in self.rows:
   if row['Status']!='complete':continue
   rid=row['Riff ID'];i=int(row['Phrase #']);key=(rid,i);self.by[rid].append(key);record=self.records.get(key);notes=None;f=None;reasons=['Source record missing'];length=Q(row['Length (quarter-note beats)'])
   if record:
    try:exact=Q(str(record.get('length_q',record.get('length_beats'))))
    except (ValueError,TypeError,ZeroDivisionError):exact=length
    notes,reasons=R.validated_notes(record,exact)
    if not reasons:f=features(notes,exact)
   item={'key':key,'row':row,'categories':categories(row),'notes':notes,'features':f,'reasons':reasons,'length':length}
   self.items[key]=item
   if rid in self.pool:
    if R.unresolved_role(row):self.unresolved_excluded[length]+=1;continue
    if reasons:self.excluded[length]+=1
    else:self.lengths[length].append(item)
  for items in self.by.values():items.sort(key=lambda k:k[1])
  for items in self.lengths.values():items.sort(key=lambda r:r['key'])
 def source_scores(self,seed):return {rid:W.compare_parsed(self.parsed[seed],self.parsed[rid])['score'] for rid in sorted(self.pool)}
 def run(self,blueprint,opening,mode,out,rng_base):
  rows=blueprint['phrases'];seed=blueprint['metadata']['seed_riff_id']
  if R.unresolved_role(self.first[seed]):raise ValueError('Unresolved seed role is excluded from selection; CSV retained')
  source_opening=self.items.get((opening['selected_riff_id'],opening['selected_phrase']))
  if source_opening and R.unresolved_role(source_opening['row']):raise ValueError('Existing opening rhythm uses excluded unresolved source phrase; no silent redraw')
  if opening['seed_riff_id']!=seed or abs(opening['seed_length_beats']-rows[0]['Length (beats)'])>1e-8:raise ValueError('Opening must match existing scaffold seed and length')
  scores=self.source_scores(seed);roots=repeat_roots(rows);chosen=[];all_audit=[];summaries=[]
  for idx,row in enumerate(rows,1):
   length=Q(str(row['Length (beats)']));cats=categories(row);copyfrom=roots[idx] if roots[idx]!=idx else None
   if idx==1:
    notes=copy.deepcopy(opening['selected_rhythm']);selection={'method':'shared fixed opening','source_riff':opening['selected_riff_id'],'source_phrase':opening['selected_phrase']}
   elif copyfrom is not None:
    notes=copy.deepcopy(chosen[copyfrom-1]['notes']);selection={'method':'exact rhythm copy','copy_from':copyfrom,'source_riff':chosen[copyfrom-1]['selection']['source_riff'],'source_phrase':chosen[copyfrom-1]['selection']['source_phrase']}
   else:
    candidates=self.lengths.get(length,[]);audit=[]
    for c in candidates:
     rid,j=c['key'];prev=self.items.get((rid,j-1));prevfit=match(chosen[-1],prev)['score'] if prev else None
     aligned=[]
     for offset in range(1,min(idx,j)):
      earlier=self.items.get((rid,j-offset))
      if earlier:
       score=match(chosen[-offset],earlier)['score']
       if score is not None:aligned.append(score)
     vals={'current':current(cats,c['categories']),'previous':prevfit,'history':math.fsum(aligned)/len(aligned) if aligned else None,'context':context(scores.get(rid),idx,len(rows),j,len(self.by[rid]))}
     if mode=='independent':
      a={'Phrase role':cats['role'],'Category - dominant texture':cats['texture'],'Accent function':cats['accent']};z=R.score(a,c['row'],scores.get(rid));s=z['score'];den=z['known_weight']
     else:s,den=weighted(vals)
     if s is None:s=0
     base_score=s;factor,flags=P.rhythm(c['notes'],c['row']);s*=factor
     audit.append({'target_phrase':idx,'source_riff':rid,'source_phrase':j,'score':s,'base_score':base_score,'preference_multiplier':factor,'preference_flags':flags,'known_weight':den,**vals,'history_pairs':len(aligned),'target_history_phrases':idx-1,'source_history_phrases':j-1,'source_opening_similarity':scores.get(rid)})
    total=math.fsum(a['score'] for a in audit)
    if total<=0:raise ValueError(f'No positive-score exact-length candidates for phrase{idx}')
    rng_seed=rng_base+idx;u=random.Random(rng_seed).random();threshold=u*total;cum=0;winner=None
    for c,a in zip(candidates,audit):
     a['probability']=a['score']/total;cum+=a['score'];a['selected']=False
     if winner is None and threshold<cum:winner=(c,a);a['selected']=True
    c,a=winner;notes=copy.deepcopy(c['notes']);selection={'method':'weighted draw','source_riff':a['source_riff'],'source_phrase':a['source_phrase'],'candidate_count':len(audit),'timing_exclusions_at_length':self.excluded[length],'unresolved_phrase_exclusions_at_length':self.unresolved_excluded[length],'rng_seed':rng_seed,'uniform_draw':u,'weight_sum':total,'selected_probability':a['probability'],'selected_score':a['score'],'components':{k:a[k] for k in WEIGHTS},'known_weight':a['known_weight'],'history_pairs':a['history_pairs']};all_audit.extend(audit)
   chosen.append({'categories':cats,'features':features(notes,length),'notes':notes,'selection':selection})
   summaries.append({'phrase':idx,'length_beats':float(length),'start_beats':row['Start position (beats)'],'end_beats':row['End position (beats)'],'role':cats['role'],'texture':cats['texture'],'accent':cats['accent'],**selection,'notes':notes})
  out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);report={'mode':mode,'seed_riff_id':seed,'reference_riff_id':blueprint['metadata']['reference_riff_id'],'source_riffs':len(self.pool),'unknown_opening_riffs_excluded':len(self.first)-len(self.pool),'total_beats':rows[-1]['End position (beats)'],'weights':WEIGHTS if mode=='contextual' else R.WEIGHTS,'phrases':summaries,'pitches_generated':False,'variation_labels_used_in_lookup':False}
  (out/'rhythm_sequence.json').write_text(json.dumps(report,indent=2))
  if all_audit:
   with (out/'candidate_scores.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(all_audit[0]));w.writeheader();w.writerows(all_audit)
  public=[{k:v for k,v in s.items() if k not in ['notes','components']} for s in summaries];fields=list(dict.fromkeys(k for r in public for k in r))
  with (out/'phrase_selections.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(public)
  return report
