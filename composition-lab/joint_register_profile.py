"""Source-only melody-register prediction from observed harmony register.

Examined development, family-separated validation; heuristic written roles.
No functional harmony inference, algebraic-target trick or generator consumer.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
import math,random

VOCAB=tuple(range(128));FLOOR=1/2000;PRIOR=1;SEED=41907


def validate(rows):
    if not rows:raise ValueError('Nonempty source cohort required')
    seen=set();families={}
    for r in rows:
        key=r['song_id'],r['melody_part'],F(r['onset_q'])
        if key in seen:raise ValueError('Duplicate source boundary')
        seen.add(key)
        if any(type(r[k])is not int for k in ('R','harmony_own_register','tuning_offset')) or r['R'] not in VOCAB or r['harmony_own_register'] not in VOCAB:raise ValueError('Exact valid registers required')
        if r['song_id'] in families and families[r['song_id']]!=r['family']:raise ValueError('Song family conflict')
        families[r['song_id']]=r['family']


def fit(rows,shuffled=False):
    validate(rows);songs=defaultdict(set);groups=defaultdict(list);strata=defaultdict(list)
    for r in rows:songs[r['family']].add(r['song_id']);groups[r['family'],r['song_id']].append(r);strata[r['family'],r['song_id'],r['tuning_offset']].append(r)
    global_=Counter();by_t=defaultdict(Counter);joint=defaultdict(Counter);support=defaultdict(set);rng=random.Random(SEED);changed=0;shufflable=0;coverage=Counter()
    for (family,song,t),values in sorted(strata.items()):
        targets=[r['R'] for r in values]
        variable_r=len(set(targets))>1;variable_a=len({r['harmony_own_register'] for r in values})>1
        if variable_r and variable_a:shufflable+=len(values)
        coverage['strata']+=1
        if len(values)<2:coverage['singleton_strata']+=1
        if not variable_r:coverage['constant_R_strata']+=1
        if not variable_a:coverage['constant_A_strata']+=1
        before=Counter((r['harmony_own_register'],target) for r,target in zip(values,targets))
        if shuffled:rng.shuffle(targets)
        after=Counter((r['harmony_own_register'],target) for r,target in zip(values,targets))
        if shuffled and before==after:coverage['unchanged_joint_strata']+=1;coverage['unchanged_joint_rows']+=len(values)
        weight=1/len(songs[family])/len(groups[family,song])
        for r,target in zip(values,targets):
            key=(r['harmony_own_register'],t);global_[target]+=weight;by_t[t][target]+=weight;joint[key][target]+=weight;support[key].add(family);changed+=target!=r['R']
    denom=sum(global_.values())+len(VOCAB)*FLOOR;base=[(global_[v]+FLOOR)/denom for v in VOCAB]
    return dict(global_probs=base,by_t=by_t,joint=joint,support=support,training_families=set(songs),training_songs={r['song_id'] for r in rows},shuffled=shuffled,shufflable_rows=shufflable,changed_targets=changed,shuffle_coverage=dict(coverage))


def distribution(model,a,t,conditional=True):
    def smooth(counts,prior):
        mass=sum(counts.values());return [(counts[v]+PRIOR*p)/(mass+PRIOR) for v,p in zip(VOCAB,prior)]
    baseline=smooth(model['by_t'].get(t,Counter()),model['global_probs']);key=a,t
    probs=smooth(model['joint'].get(key,Counter()),baseline) if conditional else baseline
    if any(p<=0 or not math.isfinite(p) for p in probs) or not math.isclose(sum(probs),1,abs_tol=1e-9):raise AssertionError('Invalid predictive mass')
    return probs,dict(context_absent=key not in model['joint'],tuning_absent=t not in model['by_t'],mass=sum(model['joint'].get(key,{}).values()),raw_families=len(model['support'].get(key,set())))


def score(rows,model,conditional=True):
    validate(rows)
    if {r['family'] for r in rows}&model['training_families'] or {r['song_id'] for r in rows}&model['training_songs']:raise ValueError('Held family/song leakage')
    by_song=defaultdict(list);totals=Counter()
    for r in rows:by_song[r['song_id']].append(r)
    for values in by_song.values():
        weight=1/len(by_song)/len(values)
        for r in values:
            ps,support=distribution(model,r['harmony_own_register'],r['tuning_offset'],conditional);p=ps[r['R']]
            totals['nll']-=math.log(p)*weight;totals['brier']+=(1-2*p+sum(x*x for x in ps))*weight
            totals['joint_context_absent']+=int(support['context_absent'])*weight
            totals['conditional_backoff']+=int(conditional and support['context_absent'])*weight
            totals['tuning_backoff']+=int(support['tuning_absent'])*weight
            totals['context_mass']+=support['mass']*weight;totals['context_raw_families']+=support['raw_families']*weight
    return dict(totals,rows=len(rows),songs=len(by_song))


def evaluate(rows):
    validate(rows);families=sorted({r['family'] for r in rows});results=[]
    if len(families)<2:raise ValueError('Independent families required')
    for family in families:
        train=[r for r in rows if r['family']!=family];test=[r for r in rows if r['family']==family];normal=fit(train);shuffled=fit(train,True)
        if any(not math.isclose(a,b,abs_tol=1e-12) for a,b in zip(normal['global_probs'],shuffled['global_probs'])):raise AssertionError('Shuffle changed global marginal')
        for t in normal['by_t']:
            if any(not math.isclose(normal['by_t'][t][v],shuffled['by_t'][t][v],abs_tol=1e-12) for v in VOCAB):raise AssertionError('Shuffle changed tuning marginal')
            if any(not math.isclose(a,b,abs_tol=1e-12) for a,b in zip(distribution(normal,0,t,False)[0],distribution(shuffled,0,t,False)[0])):raise AssertionError('Shuffle changed independent baseline')
        methods=dict(independent=score(test,normal,False),paired=score(test,normal),shuffled=score(test,shuffled))
        results.append(dict(family=family,methods=methods,shufflable_training_rows=shuffled['shufflable_rows'],changed_training_targets=shuffled['changed_targets'],shuffle_coverage=shuffled['shuffle_coverage']))
    fields=('nll','brier','joint_context_absent','conditional_backoff','tuning_backoff','context_mass','context_raw_families')
    aggregate={method:{key:sum(r['methods'][method][key] for r in results)/len(results) for key in fields} for method in ('independent','paired','shuffled')}
    wins=sum(all(r['methods']['paired']['nll']<r['methods'][c]['nll'] for c in ('independent','shuffled')) for r in results)
    passed=all(aggregate['paired'][k]<aggregate[c][k] for k in ('nll','brier') for c in ('independent','shuffled')) and wins/len(families)>=.6
    return dict(schema='source-joint-register-profile-study-v1',rows=len(rows),families=len(families),aggregate=aggregate,nll_family_wins_vs_both=wins,gate_pass=passed,results=results,generator_acceptance=False,musical_acceptance=False)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from engine_contract import sha
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source_audit','frozen_plan','output'):p.add_argument(key,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private output required')
    if a.output.exists():raise FileExistsError('Preserve previous result')
    read=lambda path:json.loads(path.read_text(encoding='utf-8-sig'))
    plan=read(a.frozen_plan)
    if plan['source_sha256']!=sha(a.source_audit) or plan['floor']!=FLOOR or plan['prior']!=PRIOR or plan['vocabulary']!=list(VOCAB):raise ValueError('Frozen study/input mismatch')
    seals={str(path):sha(path) for path in (a.source_audit,a.frozen_plan,Path(__file__))}
    source=read(a.source_audit);result=evaluate(source['rows']);result['unknown_harmony']=source['unknown']
    if seals!={path:sha(path) for path in seals}:raise AssertionError('Study input changed')
    result['input_sha256']=seals;a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','input_sha256')}))
