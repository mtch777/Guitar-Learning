"""Frozen source-population conditional step experiment, not a GP consumer.

Family-held-out teacher-forced relationship evidence. No claim of superiority
over the historical track-conditioned sampler, free generation or musical feel.
"""
from collections import defaultdict,Counter
from pathlib import Path
from fractions import Fraction as F
import argparse,hashlib,json,math,random

STEPS=tuple(range(-127,128));FLOOR=1/2000;PRIOR=1;SHUFFLE_SEED=41907


def validate_rows(rows):
    if not rows:raise ValueError('Nonempty source transitions required')
    seen=set();family_for_song={}
    for r in rows:
        if not isinstance(r['family'],str) or not r['family']:raise ValueError('Known family required')
        if any(type(r[k])is not int for k in ('song_id','part_id','origin_register','voicing_span','step','destination_register')):raise ValueError('Exact integer source fields required')
        if r['step'] not in STEPS or r['origin_register']<0 or r['voicing_span']<0 or r['destination_register']<0 or r['origin_register']+r['step']!=r['destination_register']:raise ValueError('Invalid observed transition')
        key=r['song_id'],r['part_id'],F(r['onset_q'])
        if key in seen:raise ValueError('Duplicate transition')
        seen.add(key)
        if r['song_id'] in family_for_song and family_for_song[r['song_id']]!=r['family']:raise ValueError('Song family conflict')
        family_for_song[r['song_id']]=r['family']


def context(r):return f"{r['origin_register']}:{r['voicing_span']}"


def fit(rows,shuffled=False):
    validate_rows(rows);groups=defaultdict(list);families=defaultdict(set)
    for r in rows:groups[r['family'],r['song_id']].append(r);families[r['family']].add(r['song_id'])
    global_counts=Counter();tables=defaultdict(Counter);masses=Counter();support=defaultdict(lambda:dict(families=set(),songs=set()))
    rng=random.Random(SHUFFLE_SEED)
    for (family,song),values in sorted(groups.items()):
        keys=[context(r) for r in values]
        if shuffled:rng.shuffle(keys)
        weight=1/len(families[family])/len(values)
        for r,key in zip(values,keys):
            global_counts[r['step']]+=weight;tables[key][r['step']]+=weight;masses[key]+=weight
            support[key]['families'].add(family);support[key]['songs'].add(song)
    denom=sum(global_counts.values())+len(STEPS)*FLOOR
    global_probs=[(global_counts[k]+FLOOR)/denom for k in STEPS]
    return dict(schema='population-conditional-harmony-step-v1',global_probs=global_probs,
        contexts={key:dict(mass=masses[key],counts=dict(counter),families=sorted(support[key]['families']),songs=sorted(support[key]['songs'])) for key,counter in tables.items()},
        training_families=sorted(families),training_songs=sorted({r['song_id'] for r in rows}),shuffled=shuffled,
        floor=FLOOR,prior=PRIOR,shuffle_seed=SHUFFLE_SEED)


def distribution(model,origin_register,voicing_span,conditional=True):
    base=model['global_probs'];key=f'{origin_register}:{voicing_span}';entry=model['contexts'].get(key)
    if conditional and entry is not None:
        probs=[(entry['counts'].get(k,entry['counts'].get(str(k),0))+PRIOR*p)/(entry['mass']+PRIOR) for k,p in zip(STEPS,base)]
    else:probs=list(base)
    if any(not math.isfinite(p) or p<=0 for p in probs) or not math.isclose(sum(probs),1,abs_tol=1e-9):raise AssertionError('Invalid step distribution')
    return probs,entry


def score(rows,model,conditional=True):
    validate_rows(rows)
    if {r['family'] for r in rows}&set(model['training_families']) or {r['song_id'] for r in rows}&set(model['training_songs']):raise ValueError('Held family/song leaked into fit')
    songs=defaultdict(list)
    for r in rows:songs[r['song_id']].append(r)
    totals=Counter();observed=Counter();predicted=Counter();cache={};support_mass=[]
    for song,values in sorted(songs.items()):
        weight=1/len(songs)/len(values)
        for r in values:
            key=context(r)
            if key not in cache:
                probs,entry=distribution(model,r['origin_register'],r['voicing_span'],conditional);cache[key]=(probs,sum(p*p for p in probs),entry)
            probs,squares,entry=cache[key];p=probs[r['step']+127]
            totals['nll']+=-math.log(p)*weight;totals['brier']+=(1-2*p+squares)*weight
            totals['context_absent_rate']+=int(entry is None)*weight
            totals['backoff_rate']+=int(conditional and entry is None)*weight
            totals['below_open_probability']+=sum(probs[:max(0,127-r['origin_register'])])*weight
            mass=entry['mass'] if entry else 0;support_mass.append(mass);totals['mean_context_family_equivalent_mass']+=mass*weight
            observed[r['destination_register']]+=weight
            for step,prob in zip(STEPS,probs):predicted[r['origin_register']+step]+=prob*weight
    totals['destination_register_TV']=sum(abs(observed.get(k,0)-predicted.get(k,0)) for k in set(observed)|set(predicted))/2
    return dict(totals,rows=len(rows),songs=len(songs),context_mass_range=[min(support_mass),max(support_mass)],
        support_interpretation='Weighted family/song mass, not independent-sample confidence')


def evaluate(rows):
    validate_rows(rows);families=sorted({r['family'] for r in rows})
    if len(families)<2:raise ValueError('At least two development families required')
    results=[]
    for family in families:
        train=[r for r in rows if r['family']!=family];test=[r for r in rows if r['family']==family];normal,shuffled=fit(train),fit(train,True)
        if normal['global_probs']!=shuffled['global_probs']:raise AssertionError('Shuffle changed baseline labels/weights')
        for key in normal['contexts']:
            if not math.isclose(normal['contexts'][key]['mass'],shuffled['contexts'][key]['mass'],abs_tol=1e-9):raise AssertionError('Shuffle changed context support')
        methods=dict(population=score(test,normal,False),conditional=score(test,normal),shuffled=score(test,shuffled))
        results.append(dict(family=family,methods=methods))
    metrics=['nll','brier','context_absent_rate','backoff_rate','below_open_probability','destination_register_TV','mean_context_family_equivalent_mass']
    aggregate={method:{k:sum(r['methods'][method][k] for r in results)/len(results) for k in metrics} for method in ('population','conditional','shuffled')}
    wins=sum(all(r['methods']['conditional']['nll']<r['methods'][control]['nll'] for control in ('population','shuffled')) for r in results)
    passed=all(aggregate['conditional'][k]<aggregate[control][k] for k in ('nll','brier') for control in ('population','shuffled')) and wins/len(results)>=.6
    return dict(schema='population-conditional-step-validation-v1',families=len(families),rows=len(rows),aggregate=aggregate,results=results,
        family_NLL_wins_against_both=wins,predeclared_operational_gate_pass=passed,
        limitations=['Population marginal control is not the historical chosen-track sampler.','Teacher-forced origin/shape context; not free generation.','All held-family rows/backoffs included; examined outer held-out not used.','Operational gate is not a user musical requirement or musical acceptance.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('events','plan','output'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private output required')
    if a.output.exists():raise FileExistsError('Preserve frozen experiment')
    before={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (a.events,a.plan,Path(__file__))};plan=json.loads(a.plan.read_text(encoding='utf-8'))
    if before[str(a.events)]!=plan['events_sha256'] or plan['model']['global_pseudocount_per_step']!=FLOOR or plan['model']['context_prior_family_equivalent']!=PRIOR or plan['shuffle_seed']!=SHUFFLE_SEED or plan['model']['global_step_vocabulary']!=list(STEPS):raise ValueError('Frozen plan mismatch')
    result=evaluate(json.loads(a.events.read_text(encoding='utf-8')))
    if before!={x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in before}:raise AssertionError('Study code/input changed')
    result['input_code_sha256']=before;a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('families','rows','aggregate','family_NLL_wins_against_both','predeclared_operational_gate_pass')},indent=2))
