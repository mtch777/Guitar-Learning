"""Independent diagonal scan of every maximal source-group recurrence."""
from collections import Counter,defaultdict
from fractions import Fraction as F
import json
from check_family_policy import normalized_units

BASE=('part_id','instrument','member_pitch_classes','duration_q','meter','metrical_offset_q')


def _token(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def expected_units(units,max_pairs=100000):
    if type(max_pairs)is not int or max_pairs<0:raise ValueError('Typed nonnegative resource bound required')
    parts=defaultdict(list);total=0;found=[]
    for row in units:parts[row['part_id']].append(row)
    for pid,rows in sorted(parts.items()):
        rows=sorted(rows,key=lambda u:(F(u['onset_q']),u['id']))
        signatures=[]
        for row in rows:
            if row['refusal_reasons']:signatures.append(None)
            else:
                context=json.loads(row['family_context_key']);signatures.append(_token([context[k]for k in BASE]))
        counts=Counter(x for x in signatures if x is not None);total+=sum(n*(n-1)for n in counts.values())
        if total>max_pairs:return dict(status='RESOURCE_BOUND_REFUSAL',matched_pairs=total,limit=max_pairs,links=[])
        clocks=[F(u['onset_q'])for u in rows]
        # Scan each alignment diagonal once. A break ends the maximal run;
        # no eligible event, source gap or unknown can be skipped.
        for delta in range(1,len(rows)):
            start=None;length=0
            def emit(i,n):
                if n<2:return
                for a,b in((i,i+delta),(i+delta,i)):
                    target=[u['id']for u in rows[a:a+n]];donor=[u['id']for u in rows[b:b+n]]
                    found.append((pid,a,b,dict(target_refs=target,donor_refs=donor,refusal='OVERLAPPING_SOURCE_RUNS'if set(target)&set(donor)else None)))
            for i in range(len(rows)-delta):
                equal=signatures[i]is not None and signatures[i]==signatures[i+delta]
                extend=equal and start is not None and clocks[i]-clocks[i-1]==clocks[i+delta]-clocks[i+delta-1]
                if extend:length+=1
                else:
                    if start is not None:emit(start,length)
                    start=i if equal else None;length=1 if equal else 0
            if start is not None:emit(start,length)
    return dict(status='COMPLETE_MAXIMAL_SOURCE_MATCHES',matched_pairs=total,limit=max_pairs,links=[x[3]for x in sorted(found,key=lambda x:x[:3])])


def check(documents,reported,max_pairs=100000):
    try:
        units,events,_,_=normalized_units(documents);want=expected_units(units,max_pairs)
        issues=[]if _token(want)==_token(reported)else['COMPLETE_MAXIMAL_RUN_DISCOVERY_MISMATCH']
        return dict(status='PASS_INDEPENDENT_GESTURE_DISCOVERY'if not issues else'FAIL_INDEPENDENT_GESTURE_DISCOVERY',issues=issues,source_occurrences=events,source_units=len(units),matched_pairs=want['matched_pairs'],maximal_run_links=len(want['links']),resource_status=want['status'],scope='Independent diagonal source recurrence enumeration; not phrase identification or artist suitability')
    except Exception as error:return dict(status='FAIL_INDEPENDENT_GESTURE_DISCOVERY',issues=[type(error).__name__+': '+str(error)])
