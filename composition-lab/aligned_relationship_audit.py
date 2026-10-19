"""Exact within-bar inter-role interval-change audit, not musical quality."""
from fractions import Fraction as F


def interval_stream(harmony,melody):
    """Rows use local_q,duration_q,root; rests are absent and gaps remain gaps."""
    def normalize(rows):
        out=[]
        for r in rows:
            q=F(r['local_q']);end=q+F(r['duration_q'])
            if end<=q or type(r['root'])is not int:raise ValueError('Exact positive written event required')
            if out and out[-1][1]>q:raise ValueError('Overlapping root events unsupported')
            out.append((q,end,r['root']))
        return out
    a,b=normalize(harmony),normalize(melody);out=[]
    for q in sorted({x[0] for x in a+b}):
        left=[x for x in a if x[0]<=q<x[1]];right=[x for x in b if x[0]<=q<x[1]]
        if left and right:out.append(dict(q=str(q),until=str(min(left[0][1],right[0][1])),interval=right[0][2]-left[0][2]))
    return out


def changes(stream):
    return [(b['q'],b['interval']-a['interval']) for a,b in zip(stream,stream[1:]) if F(b['q'])<=F(a['until'])]


def compare(source,candidate):
    if [(x['q'],x['until']) for x in source]!=[(x['q'],x['until']) for x in candidate]:raise ValueError('Joint clocks/activity differ')
    a,b=changes(source),changes(candidate)
    if [q for q,d in a]!=[q for q,d in b]:raise ValueError('Transition cohorts differ')
    return dict(points=len(source),transitions=len(a),source_nonzero_changes=sum(d!=0 for q,d in a),
        exact_change_matches=sum(x==y for x,y in zip(a,b)),
        nonzero_source_change_matches=sum(x==y for x,y in zip(a,b) if x[1]!=0),
        complete_trajectory_equal=a==b)
