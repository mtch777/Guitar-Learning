"""Read-only joint register/harmony audit. No model fitting or generation.

R=target-lowest-open, D=target-written-harmony-minimum, H=harmony-lowest-open.
R-D=H exactly. Differing locked H means constrain simultaneous marginal means;
this does not prove infeasibility of a TV gate or establish musical quality.
"""
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path
import argparse,json,math
from engine_contract import sha
from generation_freedom import validate
from form_returns import plan_returns


def summarize(rows):
    if not rows:raise ValueError('Nonempty joint support required')
    groups=defaultdict(list);families=defaultdict(set)
    for row in rows:
        if any(type(row[k])is not int for k in ('R','D','H')) or row['R']-row['D']!=row['H']:
            raise ValueError('Exact integer joint identity required')
        key=(row['family'],row['song_id']);groups[key].append(row);families[key[0]].add(key[1])
    means={k:0.0 for k in ('R','D','H')};hist=defaultdict(float)
    for (family,song),values in groups.items():
        weight=1/len(families)/len(families[family])/len(values)
        for row in values:
            for k in means:means[k]+=row[k]*weight
            hist[row['H']]+=weight
    if not math.isclose(means['R']-means['D'],means['H'],abs_tol=1e-9):raise AssertionError('Weighted identity failed')
    return dict(boundaries=len(rows),families=len(families),songs=len({s for _,s in groups}),means=means,H_histogram=dict(hist))


def source_rows(observations):
    rows=[];unknown=0;seen=set()
    for e in observations['events']:
        if e['partition']!='development' or e['role']!='melody':continue
        key=(e['song_id'],e['part_id'],e['bar'])
        if key in seen:raise ValueError('Duplicate source boundary')
        seen.add(key)
        if e['anchor'] is None:unknown+=1;continue
        target,anchor,register=e['target'],e['anchor'],e['register']
        if any(type(x)is not int for x in (target,anchor,register)):raise ValueError('Exact written pitch/register required')
        rows.append(dict(family=e['family'],song_id=e['song_id'],R=register,D=target-anchor,H=anchor-target+register))
    return rows,unknown


def generated_rows(score,sections,core):
    validate(score);plan_returns(score,sections)
    if [t['name'] for t in score['tracks']]!=['harmony','melody','bass']:raise ValueError('Explicit three-role score required')
    if any(len(m['voices'])!=1 for t in score['tracks'] for m in t['measures']):raise ValueError('Main voice only')
    section_for={s['start']+i:s['start'] for s in sections for i in range(s['length'])};t=score['tracks'][1];harmony=score['tracks'][0];rows=[];unknown=0
    for mi,m in enumerate(t['measures']):
        if not mi or section_for[mi]!=section_for[mi-1]:continue
        e=m['voices'][0][0];prev=t['measures'][mi-1]['voices'][0][-1]
        if not e['notes'] or not prev['notes'] or F(prev['onset_q'])+F(prev['duration_q'])!=F(e['onset_q']):continue
        q=F(e['onset_q']);hs=[h for h in harmony['measures'][mi]['voices'][0] if h['notes'] and F(h['onset_q'])<=q<F(h['onset_q'])+F(h['duration_q'])]
        if not hs:unknown+=1;continue
        pitch=min(n['midi'] for n in e['notes']);anchor=min(n['midi'] for n in hs[-1]['notes']);lowest=min(t['tunings'][0])
        rows.append(dict(family=str(core),song_id=core,R=pitch-lowest,D=pitch-anchor,H=anchor-lowest))
    return rows,unknown


def compare(source,generated):
    a,b=source['means'],generated['means'];shift=b['H']-a['H']
    if not math.isclose((b['R']-a['R'])-(b['D']-a['D']),shift,abs_tol=1e-9):raise AssertionError('Mean identity failed')
    x,y=source['H_histogram'],generated['H_histogram']
    return dict(locked_H_mean_shift=shift,minimum_unavoidable_max_mean_error=abs(shift)/2,
        unseen_H_share=sum(v for k,v in y.items() if k not in x),H_TV=sum(abs(y.get(k,0)-x.get(k,0)) for k in set(x)|set(y))/2)


def run(observations,comparisons):
    rows,unknown=source_rows(observations);source=summarize(rows);results=[];contexts={};identities=set()
    for c in comparisons:
        identity=(c['core'],c['seed'],c['method'])
        if identity in identities:raise ValueError('Duplicate comparison')
        identities.add(identity);rows,missing=generated_rows(c['score'],c['sections'],c['core']);summary=summarize(rows)
        # Methods on the same core/seed must share the exact eligible H sequence.
        key=(c['core'],c['seed']);context=[r['H'] for r in rows]
        if key in contexts and contexts[key]!=context:raise ValueError('Locked accompaniment context changed')
        contexts[key]=context
        results.append(dict(core=c['core'],seed=c['seed'],method=c['method'],summary=summary,unknown_harmony=missing,**compare(source,summary)))
    if not results:raise ValueError('Nonempty comparisons required')
    leave_family=[]
    original,_=source_rows(observations)
    for family in sorted({r['family'] for r in original}):
        remaining=[r for r in original if r['family']!=family]
        if remaining:leave_family.append(summarize(remaining)['means']['H'])
    return dict(schema='joint-register-harmony-audit-v1',source=source,source_unknown_harmony=unknown,
        leave_one_family_source_H_range=[min(leave_family),max(leave_family)] if leave_family else None,results=results,
        limitations=['Exact first-moment constraint only; not proof no better joint distribution or passing TV result exists.',
            'Known harmony subset only; missing is not negative and full-corpus generalization is unverified.',
            'Written minima and heuristic roles; not functional harmony, source feel or listening acceptance.',
            'No model fitted, generation performed, gate relaxed or default changed.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('observations','comparisons','output'):p.add_argument(name,type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.output.resolve().parts:p.error('Private output required')
    if a.output.exists():raise FileExistsError('Preserve prior output')
    read=lambda v:json.loads(Path(v).read_text(encoding='utf-8-sig'))
    specs=read(a.comparisons);paths=[a.observations,a.comparisons]+[Path(c[k]) for c in specs for k in ('score','sections')]
    seals={str(v):sha(v) for v in paths};result=run(read(a.observations),[dict(c,score=read(c['score']),sections=read(c['sections'])) for c in specs])
    if seals!={v:sha(v) for v in seals}:raise AssertionError('Input changed during audit')
    result['input_sha256']=seals;a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(source_boundaries=result['source']['boundaries'],source_unknown=result['source_unknown_harmony'],comparisons=len(result['results']),source_H_mean=result['source']['means']['H'],leave_family_H_range=result['leave_one_family_source_H_range'])))
