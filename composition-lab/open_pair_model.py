"""Experimental open-string pair probabilities over eligible notation examples.

Origin-context baseline plus family-weighted interval/duration relationships.
One fixed prior and optional permutation control; no musical-quality assertion.
Training requires development-only, unflagged, explicitly labeled opportunities.
"""
import json,math,random,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from fractions import Fraction as F
FEATURES=('hammer_on_from_open','pull_off_to_open')
def family(e):
 known=e.get('known')
 if not isinstance(known,list) or len(known)!=1 or known[0] not in FEATURES:
  raise ValueError('One supported opportunity feature required')
 return known[0]
def destination(e):
 d=e['fret_distance']
 if type(d) is not int or d<=0:raise ValueError('Positive integer fret distance required')
 a,b=F(e['origin_duration_q']),F(e['destination_duration_q'])
 if a<=0 or b<=0:raise ValueError('Positive exact pair durations required')
 dist='1-2' if d<=2 else '3-5' if d<=5 else '6-12' if d<=12 else '13+'
 rel='shorter' if b<a else 'equal' if b==a else 'longer';return dist,rel
def weights(events):
 counts=Counter((family(e),e['family'],e['song_id']) for e in events);songs=defaultdict(set)
 for f,fa,so in counts:songs[f,fa].add(so)
 return {k:F(1,n*len(songs[k[0],k[1]])) for k,n in counts.items()}
def fit(events,permuted=False):
 if not events or any(e['partition']!='development' or e['flagged'] is not False for e in events):raise ValueError('Nonempty development-only unflagged training required')
 seen=set()
 for e in events:
  f=family(e);destination(e)
  if not isinstance(e.get('context'),str) or not e['context'] or not isinstance(e.get('family'),str) or not e['family']:
   raise ValueError('Explicit context and source family required')
  if not isinstance(e.get('labels'),list) or len(e['labels'])>1 or set(e['labels'])-{f}:
   raise ValueError('Known positive/negative annotation label required')
  if type(e.get('song_id')) is not int or e['song_id']<=0 or type(e.get('part_id')) is not int or e['part_id']<0:
   raise ValueError('Explicit source song/part identity required')
  if any(not isinstance(e.get(k),str) or not e[k] for k in ('origin','destination')) or e['origin']==e['destination']:
   raise ValueError('Distinct source endpoint identities required')
  ident=(e['song_id'],e['part_id'],e['origin'],e['destination'],f)
  if ident in seen:raise ValueError('Duplicate opportunity')
  seen.add(ident)
 ws=weights(events);base=defaultdict(lambda:[F(0),F(0)]);pairs=defaultdict(lambda:[F(0),F(0)]);extras=[destination(e) for e in events]
 if permuted:
  groups=defaultdict(list)
  for i,e in enumerate(events):groups[family(e),e['context']].append(i)
  rng=random.Random(47017)
  for key,ids in sorted(groups.items()):
   vals=[extras[i] for i in ids];rng.shuffle(vals)
   for i,v in zip(ids,vals):extras[i]=v
 for e,extra in zip(events,extras):
  f=family(e);w=ws[f,e['family'],e['song_id']];y=f in e['labels']
  for key in ((f,'*'),(f,e['context'])):base[key][0]+=w;base[key][1]+=w*y
  pairkey=(f,e['context'],*extra);pairs[pairkey][0]+=w;pairs[pairkey][1]+=w*y
 return dict(base=dict(base),pairs=dict(pairs),families={e['family'] for e in events},songs={e['song_id'] for e in events})
def predict(model,e):
 f=family(e);key=(f,e['context']);mass=model['base'].get(key);backoff=mass is None;mass=mass or model['base'].get((f,'*'))
 if not mass or mass[0]<=0:raise ValueError('No baseline feature support')
 n,y=mass
 if not 0<=y<=n:raise ValueError('Invalid baseline support')
 alpha=F(1,2000);baseline=float((y+alpha)/(n+2*alpha));pair=model['pairs'].get((f,e['context'],*destination(e)));n2,y2=pair or (F(0),F(0))
 if n2<0 or not 0<=y2<=n2:raise ValueError('Invalid pair support')
 candidate=float((float(y2)+baseline)/(float(n2)+1))
 return baseline,candidate,dict(pair_support=float(n2),pair_backoff=pair is None,origin_backoff=backoff)
def score_rows(model,events,perm):
 rows=[]
 for e in events:
  if e['family'] in model['families'] or e['song_id'] in model['songs']:raise ValueError('Evaluation source leakage')
  b,p,s=predict(model,e);_,c,_=predict(perm,e);y=int(family(e) in e['labels']);preds=dict(baseline=b,pair=p,permutation=c);metrics={}
  for k,v in preds.items():
   if not math.isfinite(v) or not 0<v<1:raise ValueError('Invalid probability')
   metrics[k]=dict(nll=-math.log(v if y else 1-v),brier=(v-y)**2)
  rows.append(dict(feature=family(e),family=e['family'],song_id=e['song_id'],metrics=metrics,support=s))
 return rows
def summarize(rows):
 songs=defaultdict(list)
 for r in rows:songs[r['feature'],r['family'],r['song_id']].append(r)
 families=defaultdict(list)
 for (f,fa,so),rs in songs.items():families[f,fa].append({m:{v:sum(r['metrics'][m][v] for r in rs)/len(rs) for v in ('nll','brier')} for m in ('baseline','pair','permutation')})
 familyrows=[]
 for (f,fa),ss in sorted(families.items()):familyrows.append(dict(feature=f,family=fa,metrics={m:{v:sum(s[m][v] for s in ss)/len(ss) for v in ('nll','brier')} for m in ('baseline','pair','permutation')}))
 result={}
 for f in FEATURES:
  fs=[r for r in familyrows if r['feature']==f];result[f]=dict(families=len(fs),eligible=sum(r['feature']==f for r in rows),metrics={m:{v:sum(r['metrics'][m][v] for r in fs)/len(fs) for v in ('nll','brier')} for m in ('baseline','pair','permutation')},pair_backoff=sum(r['feature']==f and r['support']['pair_backoff'] for r in rows),origin_backoff=sum(r['feature']==f and r['support']['origin_backoff'] for r in rows))
 composite={m:{v:sum(result[f]['metrics'][m][v] for f in FEATURES)/len(FEATURES) for v in ('nll','brier')} for m in ('baseline','pair','permutation')}
 return dict(features=result,composite=composite,per_family=familyrows)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def train_file(data_path,baseline_path,output,*,permuted=False):
 """Fit one declared candidate. Never fit on held-out rows or overwrite weights."""
 from artist_profiles import stable_hash
 data_path,baseline_path,output=map(Path,(data_path,baseline_path,output))
 if output.exists() or 'local-artifacts' not in output.resolve().parts:
  raise ValueError('Fresh private local-artifacts output required')
 data=json.loads(data_path.read_text(encoding='utf-8'))
 baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
 if data.get('baseline_model_sha256')!=sha(baseline_path):raise ValueError('Baseline seal differs from joined data')
 if (data.get('schema')!='joined-existing-open-pair-opportunities-v1'
     or data.get('all_existing_opportunities_joined') is not True
     or data.get('duplicate_or_unknown_joins')!=0 or not data.get('source',{}).get('sha256')):
  raise ValueError('Explicit complete joined-opportunity provenance required')
 if (baseline.get('schema')!='artist-performance-opportunity-v1'
     or baseline.get('weighting')!='family' or F(baseline.get('alpha','0'))!=F(1,2000)):
  raise ValueError('Matching family-weighted origin baseline required')
 events=[e for e in data['events'] if e['partition']=='development' and e['flagged'] is False]
 artists={e['artist'] for e in events}
 if len(artists)!=1:raise ValueError('One explicit artist required')
 model=fit(events,permuted)
 held=[e for e in data['events'] if e['partition']=='held_out' and e['flagged'] is False]
 if model['families']&{e['family'] for e in held} or model['songs']&{e['song_id'] for e in held}:
  raise ValueError('Training/held-out song or family leakage')
 serialized={k:[dict(key=list(key),mass=str(v[0]),selected=str(v[1])) for key,v in model[k].items()] for k in ('base','pairs')}
 serialized.update(schema='experimental-open-pair-conditioned-v1',artist=next(iter(artists)),
  training_families=sorted(model['families']),training_songs=sorted(model['songs']),
  prior_mass='1',baseline_alpha='1/2000',permuted=permuted,
  baseline_model_content_sha256=stable_hash(baseline),training_source_sha256=baseline['training_source_sha256'],
  joined_data_sha256=sha(data_path),source_seal=data.get('source'),fit_code_sha256=sha(__file__),
  limitations=['Joined labels/provenance are supplied inputs, not independently authenticated source truth.',
              'Fixed experimental bins/prior, not artist laws. No musical or default promotion.'])
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('x',encoding='utf-8') as stream:json.dump(serialized,stream,separators=(',',':'))
 return serialized

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('joined_data',type=Path);parser.add_argument('baseline',type=Path);parser.add_argument('output',type=Path)
 parser.add_argument('--permuted',action='store_true')
 args=parser.parse_args();result=train_file(args.joined_data,args.baseline,args.output,permuted=args.permuted)
 print(json.dumps(dict(artist=result['artist'],training_families=len(result['training_families']),output=str(args.output))))
