"""CLI for the existing archived aligned-pattern experiment, not a new batch.

Verifies preserved artifact hashes/canonical identities; reports interval-change
preservation without equating unlocked differences with musical errors.
"""
import json,sys,subprocess,hashlib,argparse
from pathlib import Path
from collections import Counter
from fractions import Fraction as F
from aligned_relationship_audit import interval_stream,compare
from compose_controlled import plain_core
from engine_contract import sha
parser=argparse.ArgumentParser(description='Read-only archived aligned-pattern stage audit; private output only')
parser.add_argument('artifacts_root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
if 'local-artifacts' not in args.output.resolve().parts:parser.error('Private output required')
if args.output.exists():raise FileExistsError('Preserve previous audit')
r=args.artifacts_root;read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
corebatch=read(r/'aligned-core-v1/batch.json');rolebatch=read(r/'aligned-role-v1/batch.json');modelpath=r/'compositions-v3/model.json';assert sha(modelpath)==corebatch['model_sha256'];model=read(modelpath)
rolemodels=[p for p in r.glob('role-pitch-v*/model.json') if sha(p)==rolebatch['model_sha256']];assert len(rolemodels)==1
provenance=[]
for batch in (corebatch,rolebatch):
 for name,digest in batch['code_sha256'].items():
  path='composition-lab/'+name;match=None
  for revision in subprocess.check_output(['git','log','-100','--format=%H','--',path],text=True).splitlines():
   blob=subprocess.check_output(['git','show',revision+':'+path])
   if hashlib.sha256(blob).hexdigest()==digest:match=revision;break
  provenance.append(dict(file=name,sha256=digest,git_revision=match,status='recovered exact blob' if match else 'unknown; no current-code substitution'))
index={}
for role,fs in model['parts'].items():
 for family,parts in fs.items():
  for p in parts:
   key=(role,p['song_id'],p['part_id'],p['bar']);assert key not in index;index[key]=p
rows=[];totals={method:Counter() for method in ('raw','role100')};seals={str(p):sha(p) for p in (modelpath,rolemodels[0],r/'aligned-core-v1/batch.json',r/'aligned-role-v1/batch.json')}
for output in corebatch['outputs']:
 gp=r/'aligned-core-v1'/output['file'];assert sha(gp)==output['sha256'];core=read(gp.with_suffix('.expected.json'));plan=read(gp.with_suffix('.plan.json'));plain_core(gp,core)
 number=output['file'].split('-')[1];rolefile='piece-'+number+'-aligned-roles-100.gp';record=next(o for o in rolebatch['outputs'] if o['file']==rolefile);role_gp=r/'aligned-role-v1'/rolefile;assert sha(role_gp)==record['sha256'];integrated=read(role_gp.with_suffix('.expected.json'));plain_core(role_gp,integrated)
 for p in (gp,gp.with_suffix('.expected.json'),gp.with_suffix('.plan.json'),role_gp,role_gp.with_suffix('.expected.json')):seals[str(p)]=sha(p)
 manifests={}
 for s in plan['sources']:manifests.setdefault(s['bar'],{})[s['track']]=s
 for bar,sources in manifests.items():
  assert set(sources)=={0,1,2};assert len({(s['training_song'],s['training_bar']) for s in sources.values()})==1
  patterns={}
  for ti,role in enumerate(('harmony','melody','bass')):
   s=sources[ti];p=index[role,s['training_song'],s['training_part'],s['training_bar']];patterns[role]=p
   for score in (core,integrated):
    events=score['tracks'][ti]['measures'][bar-1]['voices'][0]
    assert [(F(e['duration_q']),bool(e['notes'])) for e in events]==[(F(e['duration_q']),bool(e['intervals'])) for e in p['events']]
    if score is core:assert [len(e['notes']) for e in events]==[len(e['intervals']) for e in p['events']]
  source=interval_stream(patterns['harmony']['root_events'],patterns['melody']['root_events'])
  def roots(score,ti):return [dict(local_q=e['local_onset_q'],duration_q=e['duration_q'],root=min(n['midi'] for n in e['notes'])) for e in score['tracks'][ti]['measures'][bar-1]['voices'][0] if e['notes']]
  row=dict(piece=number,bar=bar,source=sources,source_stream=source)
  for method,score in [('raw',core),('role100',integrated)]:
   stream=interval_stream(roots(score,0),roots(score,1));metrics=compare(source,stream);row[method]=dict(metrics=metrics,stream=stream)
   for k,v in metrics.items():totals[method][k]+=v
  rows.append(row)
assert len(rows)==222
assert seals=={p:sha(p) for p in seals}
result=dict(new_cells=len(rows),pieces=len(corebatch['outputs']),totals={k:dict(v) for k,v in totals.items()},varied_source_cells=sum(r['raw']['metrics']['source_nonzero_changes']>0 for r in rows),no_transition_cells=sum(r['raw']['metrics']['transitions']==0 for r in rows),provenance=provenance,inputs_sha256=seals,rows=rows,limitations=['Within selected original bars only, not inferred phrases or musical intent','Source-relative interval changes ignore constant per-role transposition but not independent motion','Root minima and heuristic roles; no listening or source-fidelity verdict','Artifact-stage comparison, not causal claim that one implementation line causes artist-feel failure','Older studies already measured rhythm/cardinality matching and marginal rates; this adds exact paired interval trajectory'])
p=args.output;p.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','inputs_sha256')},indent=2))
