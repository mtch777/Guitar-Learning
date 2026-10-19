"""Opt-in open-string pair consumer with literal locks and hidden target input.

No existing generation default changes. Model probabilities describe notation,
not physical execution, audible legato quality or artist feel.
"""
import sys,json,random
from pathlib import Path
from collections import defaultdict
from fractions import Fraction as F
from xml.etree import ElementTree as E
from engine_contract import _read,sha
from recreation_window import redact
from learned_performance import apply as baseline_apply
from technique_edits import transact,enable_property
from technique_strength import released
from exact_score import extract_score
from artist_profiles import context,stable_hash
from open_pair_model import predict
FAMILIES={'hammer_on_from_open','pull_off_to_open'}
def load_model(path):
 data=json.loads(Path(path).read_text(encoding='utf-8'))
 if data.get('schema')!='experimental-open-pair-conditioned-v1' or not data.get('baseline_model_content_sha256') or not data.get('training_source_sha256') or not data.get('artist'):
  raise ValueError('Explicit experimental model and baseline/source provenance required')
 if (not isinstance(data.get('prior_mass'),str) or F(data['prior_mass'])!=1
     or not isinstance(data.get('baseline_alpha'),str) or F(data['baseline_alpha'])!=F(1,2000)):
  raise ValueError('Model differs from fixed experimental prior/baseline')
 tables={}
 for name,width in (('base',2),('pairs',4)):
  table={}
  for row in data[name]:
   key=tuple(row['key']);n,y=F(row['mass']),F(row['selected'])
   if (len(key)!=width or key in table or n<=0 or not 0<=y<=n or key[0] not in FAMILIES
       or not isinstance(key[1],str) or not key[1]):raise ValueError('Invalid/duplicate model cell')
   if width==4 and (key[2] not in ('1-2','3-5','6-12','13+') or key[3] not in ('shorter','equal','longer')):
    raise ValueError('Unsupported experimental pair bin')
   table[key]=[n,y]
  tables[name]=table
 return dict(**tables,families=set(data['training_families']),songs=set(data['training_songs']),artist=data['artist'],baseline_model_content_sha256=data['baseline_model_content_sha256'],training_source_sha256=data['training_source_sha256'])
def apply(source,dest,baseline_model,shapes,pair_model,freedom,seed=17,artist=None):
 if set(freedom)-FAMILIES or any(type(v)is not int or not 0<=v<=100 for v in freedom.values()):raise ValueError('Supported integer open-HP freedom required')
 if type(seed)is not int:raise ValueError('Integer seed required')
 if not any(freedom.values()):return dict(**transact(source,dest,{},{}),all_locked=True,decisions=[])
 artist=artist or pair_model.get('artist')
 if (not isinstance(artist,str) or not artist or pair_model.get('artist')!=artist
     or pair_model.get('baseline_model_content_sha256')!=stable_hash(baseline_model)
     or pair_model.get('training_source_sha256')!=baseline_model.get('training_source_sha256')):
  raise ValueError('Exact baseline/source/artist provenance required')
 dest=Path(dest);hidden=dest.with_suffix('.hidden.gp');mask=dest.with_suffix('.eligibility.gp')
 if any(p.exists() for p in (dest,hidden,mask)):raise FileExistsError('Output or private proposal input already exists')
 if Path(source).resolve() in {p.resolve() for p in (dest,hidden,mask)}:raise ValueError('Source/output paths overlap')
 redact(source,hidden,'hammer_on_from_open')
 eligibility=baseline_apply(hidden,mask,baseline_model,shapes,artist,{f:100 for f,v in freedom.items() if v},seed)
 score=extract_score(hidden);contexts={};_,_,_,rows=_read(hidden);_,_,_,original=_read(source)
 for ti,track in enumerate(score['tracks']):
  pitches=[n['midi'] for m in track['measures'] for v in m['voices'] for e in v for n in e['notes'] if n['midi'] is not None and not n.get('grace_type') and F(e['duration_q'])>0]
  if not pitches:continue
  register=(min(pitches),max(pitches));groups=defaultdict(list)
  for m in track['measures']:
   for v in m['voices']:
    for e in v:
     for n in e['notes']:
      if not n.get('grace_type') and F(e['duration_q'])>0 and not(n.get('tie') or {}).get('destination')=='true':groups[F(e['onset_q'])].append(dict(midi=n['midi'],fret=n['fret'],duration_q=e['duration_q'],bar_offset_q=e['local_onset_q']))
  for o,r in rows.items():
   if int(o.split(':')[0])==ti and r['onset'] in groups:
    g=groups[r['onset']];contexts[o]=context(g[0],g,register)
 permissions={};values={};decisions=[]
 for d in eligibility['decisions']:
  f=d['family'];o=d['origin'];z=d['destination'];a=rows[o]['note'];b=rows[z]['note'];e=dict(known=[f],context=contexts[o],fret_distance=abs(a['fret']-b['fret']),origin_duration_q=a['duration_q'],destination_duration_q=b['duration_q'])
  base,p,support=predict(pair_model,e)
  if abs(base-d['probability'])>1e-12:raise ValueError('Baseline/context differs from frozen source-fitted baseline')
  selected=random.Random(f'{seed}:{f}:{o}>{z}').random()<p;unlocked=released((f,o,z),freedom[f])
  for oid,name in ((o,'HopoOrigin'),(z,'HopoDestination')):
   key=('note',rows[oid]['note']['note_id'],'property');permissions.setdefault(key,set()).add(name)
   prior=E.fromstring(original[oid]['note']['note_xml']).find("./Properties/Property[@name='%s']"%name)
   values.setdefault(key,{})[name]=enable_property(name) if unlocked and selected else None if unlocked or prior is None else E.tostring(prior,encoding='unicode')
  decisions.append(dict(family=f,origin=o,destination=z,eligible=True,context=e['context'],fret_distance=e['fret_distance'],origin_duration_q=e['origin_duration_q'],destination_duration_q=e['destination_duration_q'],baseline_probability=base,probability=p,support=support,proposed_selected=selected,released=unlocked,context_backoff=support['pair_backoff'] or support['origin_backoff']))
 edits={k:[v for name,v in sorted(vals.items()) if v is not None] for k,vals in values.items()};audit=transact(source,dest,edits,permissions)
 return dict(**audit,decisions=decisions,seed=seed,freedom=freedom,hidden_target_input_sha256=sha(hidden),eligible_pair_count=len(decisions),musical_acceptance=False)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('source','baseline_model','shapes','pair_model','output'):parser.add_argument(name,type=Path)
 parser.add_argument('--hammer',type=int,default=100);parser.add_argument('--pull',type=int,default=100)
 parser.add_argument('--seed',type=int,default=17);parser.add_argument('--artist')
 args=parser.parse_args();audit_path=args.output.with_suffix('.audit.json')
 if 'local-artifacts' not in args.output.resolve().parts or audit_path.exists():parser.error('Fresh private local-artifacts output required')
 model=json.loads(args.baseline_model.read_text(encoding='utf-8'));shapes=json.loads(args.shapes.read_text(encoding='utf-8'))
 result=apply(args.source,args.output,model,shapes,load_model(args.pair_model),
              {'hammer_on_from_open':args.hammer,'pull_off_to_open':args.pull},args.seed,args.artist)
 with audit_path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
 print(json.dumps(dict(output=str(args.output),decisions=len(result['decisions']),musical_acceptance=False)))
