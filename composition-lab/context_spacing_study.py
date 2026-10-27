"""Frozen development-only context prediction. Never generates or edits notes.

Only explicit invariant family/context features enter the predictor. Targets are
joined after feature/group freeze. Conservative masked-context recurrence grouping
can leave too few independent groups; that is an inconclusive result, not failure
to be remedied by switching to random-note folds.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import random

CASES=('under-pressure','over-the-hills','satisfaction')
FEATURES=('duration','meter_position','neighbors','overlap','uncertainty')
PROTOCOL=dict(version=1, blocks_bars=8, boundary_embargo_bars=1,
    alpha=1.0, seed=310027, folds=3, min_independent_groups=6,
    model='categorical naive Bayes; fixed Laplace alpha=1; no tuning',
    family='song/part/instrument/bass-relative pitch-class MULTISET; invariant under permitted spacing',
    features=FEATURES, near_recurrence='equal family and all but at most one feature category; union whole eight-bar blocks',
    dependency='previous/current/next source unit and every nominal overlap must stay within the same block',
    support='training-only spacing vocabulary plus one UNKNOWN bucket with alpha pseudo-count; no test labels in vocabulary',
    controls='frequency; conditional; within-training-family shuffled context, seed fixed',
    decision='each song >=six independent groups with >=2 TRAIN spacing choices; lower occurrence AND equal-group choice loss than both controls; all outcomes retained',
    scope='prediction of observed spacing, not preference, causal emotion, inverse or output policy')


def token(value):return json.dumps(value,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(token(value).encode()).hexdigest()


def features(row):
    c=json.loads(row['family_context_key'])
    neighbors=json.loads(row['family_full_context_key'])[1]
    return dict(duration=token(c['duration_q']),
        meter_position=token([c['meter'],c['metrical_offset_q']]),
        neighbors=token(neighbors),overlap=token(c['overlaps']),
        uncertainty=token(c['execution_uncertainty']))


def prepare(catalogs,source_events=None):
    """No spacing/fret/string/absolute position enters feature fingerprints."""
    rows=[];counts={};targets={}
    for song,catalog in catalogs.items():
        units=catalog['units'];counts[song]=dict(total=len(units),refused=0,eligible=0,boundary_excluded=0,retained=0)
        parts=defaultdict(list)
        for row in units:parts[row['part_id']].append(row)
        neighborhoods={}
        for values in parts.values():
            values.sort(key=lambda r:(F(r['onset_q']),r['id']))
            for i,row in enumerate(values):neighborhoods[row['id']]=values[max(0,i-1):i+2]
        # Block clock bounds use ALL observed units, independent of target values.
        block_starts={}
        for r in units:
            b=(r['bar']-1)//8;block_starts[b]=min(block_starts.get(b,F(r['onset_q'])),F(r['onset_q']))
        for r in units:
            stat=counts[song]
            if r['refusal_reasons']:stat['refused']+=1;continue
            stat['eligible']+=1;b=(r['bar']-1)//8;near=neighborhoods[r['id']]
            c=json.loads(r['family_context_key']);onset=F(r['onset_q'])
            spans=[(onset,onset+F(r['duration_q']))]
            # overlap tuple: part,voice,relative nominal start,relative nominal end,pc
            spans += [(onset+F(o[2]),onset+F(o[3])) for o in c['overlaps']]
            lo=block_starts[b];hi=block_starts.get(b+1)
            outside=(r['bar']-1)%8 in (0,7) or any((n['bar']-1)//8!=b for n in near)
            outside=outside or any(a<lo or hi is not None and z>hi for a,z in spans)
            if outside:stat['boundary_excluded']+=1;continue
            f=features(r);family=token([song,r['part_id'],c['instrument'],c['member_pitch_classes']])
            dependencies={ref for n in near for ref in n['member_refs']}
            if source_events is not None:
                # Catalog overlap times are clipped to the target window. Use raw
                # occurrence IDs, never clipped slices, to prevent a sustained
                # neighbor/other-part note from leaking across split components.
                stop=onset+F(r['duration_q'])
                dependencies.update(e['id']for e in source_events[song]
                    if F(e['onset_q'])<stop and F(e['onset_q'])+F(e['duration_q'])>onset)
            item=dict(id=song+'/'+r['id'],song=song,bar=r['bar'],block=song+'/'+str(b),family=family,features=f,
                dependency_refs=sorted(song+'/'+ref for ref in dependencies))
            rows.append(item);stat['retained']+=1
            targets[item['id']]=token(r['realization']['intervals'])
    parent={r['block']:r['block'] for r in rows}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    seen={}
    dependency_blocks={}
    for r in rows:
        for ref in r['dependency_refs']:
            if ref in dependency_blocks:union(r['block'],dependency_blocks[ref])
            else:dependency_blocks[ref]=r['block']
        for omitted in FEATURES:
            key=token([r['family'],[(k,r['features'][k])for k in FEATURES if k!=omitted]])
            if key in seen:union(r['block'],seen[key])
            else:seen[key]=r['block']
    for r in rows:r['group']=find(r['block'])
    # Round-robin hash ordering of whole components, separately within each song.
    assignments={}
    for song in catalogs:
        groups=sorted({r['group']for r in rows if r['song']==song},key=lambda g:digest([PROTOCOL['seed'],g]))
        assignments.update({g:i%PROTOCOL['folds']for i,g in enumerate(groups)})
    for r in rows:r['fold']=assignments[r['group']]
    return dict(rows=rows,counts=counts),targets


def audit_split(data):
    issues=[];groups={};blocks={};near={};dependencies={}
    for r in data['rows']:
        if set(r['features'])!=set(FEATURES):issues.append('FEATURE_SCHEMA')
        for table,key in ((groups,r['group']),(blocks,r['block'])):
            if key in table and table[key]!=r['fold']:issues.append('GROUP_CROSSES_FOLDS')
            table[key]=r['fold']
        for omitted in FEATURES:
            key=token([r['family'],[(k,r['features'][k])for k in FEATURES if k!=omitted]])
            if key in near and near[key]!=r['fold']:issues.append('RECURRENCE_CROSSES_FOLDS')
            near[key]=r['fold']
        for ref in r['dependency_refs']:
            if ref in dependencies and dependencies[ref]!=r['fold']:issues.append('SOURCE_DEPENDENCY_CROSSES_FOLDS')
            dependencies[ref]=r['fold']
    return dict(status='PASS'if not issues else'FAIL',issues=sorted(set(issues)),independent_groups=len(groups))


def distribution(train,target,labels,conditional):
    same=[r for r in train if r['family']==target['family']]
    vocabulary=sorted({labels[r['id']]for r in same})
    counts=Counter(labels[r['id']]for r in same);n=len(same);alpha=PROTOCOL['alpha']
    # UNKNOWN mass is explicitly independent of test class identity/count.
    classes=vocabulary+[None];logs={c:math.log((counts[c]+alpha)/(n+alpha*len(classes)))for c in classes}
    if conditional:
        for feature in FEATURES:
            values={r['features'][feature]for r in same};size=len(values)+1
            for c in classes:
                matching=sum(labels[r['id']]==c and r['features'][feature]==target['features'][feature]for r in same)
                logs[c]+=math.log((matching+alpha)/(counts[c]+alpha*size))
    maximum=max(logs.values());weights={k:math.exp(v-maximum)for k,v in logs.items()};total=sum(weights.values())
    return {k:v/total for k,v in weights.items()}


def evaluate(data,labels):
    if audit_split(data)['status']!='PASS':raise ValueError('Invalid frozen split')
    rows=data['rows'];predictions=[]
    for fold in range(PROTOCOL['folds']):
        train=[r for r in rows if r['fold']!=fold];test=[r for r in rows if r['fold']==fold]
        shuffled=[dict(r,features=dict(r['features']))for r in train];families=defaultdict(list)
        for i,r in enumerate(shuffled):families[r['family']].append(i)
        rng=random.Random(PROTOCOL['seed']+fold)
        for indices in families.values():
            contexts=[shuffled[i]['features']for i in indices];rng.shuffle(contexts)
            for i,f in zip(indices,contexts):shuffled[i]['features']=f
        for target in test:
            result=dict(id=target['id'],song=target['song'],group=target['group'],fold=fold,metrics={})
            for method,training,conditional in (('frequency',train,False),('conditional',train,True),('shuffle',shuffled,True)):
                p=distribution(training,target,labels,conditional);truth=labels[target['id']];known=truth in p
                outcome=truth if known else None;probability=p[outcome]
                best=max(p,key=lambda k:(p[k],str(k)))
                result['metrics'][method]=dict(log_loss=-math.log(probability),brier=sum((v-int(k==outcome))**2 for k,v in p.items()),
                    top_correct=bool(known and best==truth),in_support=known,train_vocabulary=len(p)-1,
                    train_family_occurrences=sum(r['family']==target['family']for r in training))
            result['choice_test']=result['metrics']['frequency']['train_vocabulary']>=2
            predictions.append(result)
    def aggregate(values):
        return {m:{k:sum(r['metrics'][m][k]for r in values)/len(values) for k in ('log_loss','brier','top_correct','in_support')}for m in ('frequency','conditional','shuffle')}if values else{}
    songs=[]
    for song in data['counts']:
        values=[r for r in predictions if r['song']==song];groups={r['group']for r in values}
        choices=[r for r in values if r['choice_test']]
        songs.append(dict(song=song,counts=data['counts'][song],groups=len(groups),metrics=aggregate(values),
            choice_test_occurrences=len(choices),choice_test_groups=len({r['group']for r in choices}),choice_metrics=aggregate(choices)))
    overall=aggregate(predictions);choices=[r for r in predictions if r['choice_test']];choice_metrics=aggregate(choices)
    grouped=[aggregate([r for r in choices if r['group']==g])for g in sorted({r['group']for r in choices})]
    equal_group={m:{k:sum(g[m][k]for g in grouped)/len(grouped)for k in ('log_loss','brier','top_correct','in_support')}for m in ('frequency','conditional','shuffle')}if grouped else{}
    enough=all(s['choice_test_groups']>=PROTOCOL['min_independent_groups']for s in songs)
    beats=bool(choices)and all(metrics['conditional']['log_loss']<min(metrics[m]['log_loss']for m in ('frequency','shuffle'))for metrics in (choice_metrics,equal_group))
    status='INCONCLUSIVE_INDEPENDENT_SUPPORT'if not enough else'PASS_PREDICTIVE_SUPPORT'if beats else'NO_PREDICTIVE_SUPPORT'
    # UNKNOWN buckets make open-set loss finite; never call it exact-class accuracy.
    ranked=sorted(predictions,key=lambda r:(r['metrics']['conditional']['log_loss']-r['metrics']['frequency']['log_loss'],r['id']))
    return dict(status=status,songs=songs,overall=overall,choice_metrics=choice_metrics,equal_group_choice_metrics=equal_group,
        groups=[dict(group=g,metrics=aggregate([r for r in predictions if r['group']==g]))for g in sorted({r['group']for r in predictions})],
        examples=dict(help=ranked[:3],hurt=list(reversed(ranked[-3:]))),predictions=predictions,
        limitation='Open-set UNKNOWN-bucket scores include every outcome; not exact unseen-class probabilities. Group dependence limits inference. No generation promotion.')


def run(trial,output):
    if output.exists()or'local-artifacts'not in output.resolve().parts:raise ValueError('Fresh private output required')
    paths={s:trial/s/'catalog.json'for s in CASES}
    catalogs={s:json.loads(p.read_text(encoding='utf-8'))for s,p in paths.items()}
    from source_tie_tier1 import extract_documents
    capture_freeze=trial/'freeze.json'
    original=json.loads(capture_freeze.read_text(encoding='utf-8'))
    source_events={};capture_paths=[]
    for song,case in zip(CASES,original['cases']):
        path=Path(case['capture']);files=sorted(path.glob('*.json'))
        if {p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in files}!=case['files']:raise ValueError('Frozen capture changed')
        documents={p.name:json.loads(p.read_text(encoding='utf-8-sig'))for p in files}
        source_events[song]=extract_documents(documents)['events'];capture_paths.extend(files)
    data,labels=prepare(catalogs,source_events);audit=audit_split(data)
    if audit['status']!='PASS':raise ValueError(audit)
    output.mkdir(parents=True)
    root=Path(__file__).parent
    files=list(paths.values())+list(root.glob('*.py'))+capture_paths
    if capture_freeze.exists():files.append(capture_freeze)
    hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(files)}
    frozen=dict(protocol=PROTOCOL,input_code_hashes=hashes,target_masked_hash=digest(data),audit=audit)
    (output/'features-before-fit.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    (output/'preregistered-before-fit.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    # Only now join targets. Explicit choice witnesses remain in the original tier;
    # prediction neither replaces them nor becomes an inverse authority.
    (output/'observed-targets.json').write_text(json.dumps(labels,indent=2),encoding='utf-8')
    result=evaluate(data,labels)
    result['inputs_unchanged']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    if not result['inputs_unchanged']:raise ValueError('Frozen implementation/input changed')
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return {k:v for k,v in result.items()if k not in ('predictions','groups','examples')}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    print(json.dumps(run(args.trial,args.output)))
