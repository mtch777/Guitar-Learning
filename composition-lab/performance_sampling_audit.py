"""Separate proposal opportunities, expected selections and realized draws.

Read existing exported decision traces; never change generation to force quotas.
Bernoulli variance is a descriptive reference, not a significance test: related
contexts and reused sections are not independent musical observations.
"""
import argparse,json,math
from collections import defaultdict
from pathlib import Path


def summarize(decisions):
    groups=defaultdict(list)
    for d in decisions:
        if not d.get('eligible',True) or not d.get('released'):continue
        p=d.get('probability')
        if p is None:continue
        if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0<=p<=1:
            raise ValueError('Invalid proposal probability')
        groups[d.get('family','palm_mute')].append(d)
    result={}
    for feature,rows in groups.items():
        expected=sum(r['probability'] for r in rows)
        variance=sum(r['probability']*(1-r['probability']) for r in rows)
        selected=sum(bool(r['proposed_selected']) for r in rows)
        known=[r for r in rows if 'context_backoff' in r]
        result[feature]=dict(released_eligible_decisions=len(rows),nominal_expected_selections=expected,
            selected_proposals=selected,mean_conditional_probability=expected/len(rows),
            bernoulli_reference_sd=math.sqrt(variance),
            backoff_decisions=sum(bool(r['context_backoff']) for r in known),backoff_known=len(known))
    return result


def run(directory,pattern):
    pieces=[];combined=[]
    for p in sorted(directory.glob(pattern)):
        rows=json.loads(p.read_text(encoding='utf-8'))['decisions'];combined.extend(rows)
        pieces.append(dict(file=p.name,features=summarize(rows)))
    if not pieces:raise ValueError('No decision traces')
    return dict(schema='performance-proposal-audit-v1',pieces=pieces,pooled_decisions=summarize(combined),
        limitations=['Proposal decisions, not independently measured exported annotations.',
            'Opportunity units differ by technique; never sum them as note counts.',
            'Pooled decision weighting differs from source family/equal-piece rates.',
            'Bernoulli reference SD is descriptive, not a musical independence assumption.',
            'Absent backoff metadata is unknown, not evidence of context support.',
            'Nominal expectations use logged model probabilities; zero-positive-support or missing-template guards can suppress selections. Verify those gates before interpreting expected counts.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--pattern',default='*-100.performance.json');a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private report only')
    if a.out.exists():p.error('Output exists')
    result=run(a.directory,a.pattern)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['pooled_decisions'],indent=2))
