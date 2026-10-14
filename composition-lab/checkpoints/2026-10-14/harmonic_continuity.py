"""Conservative chord continuity between concordant observed anchors.

A gap is labeled only when it is bounded by two matching, non-conflicting
observed chords. Unsupported sections remain explicitly unresolved.
No key, meter, genre, root progression, or phrase length is assumed.
"""
from fractions import Fraction


def expand_agreed_anchors(anchors, *, max_gap=None):
    """Return nonoverlapping evidence-backed windows and diagnostics.

    Never extrapolate past the first or last chord. No interpolation when
    adjacent anchors disagree, overlap incompatibly, or exceed max_gap.
    """
    if max_gap is not None and Fraction(max_gap)<0:
        raise ValueError('max_gap cannot be negative')
    spans=sorted(anchors,key=lambda s:(s['start'],s['end']))
    windows=[]
    rejected=0
    for s in spans:
        if Fraction(s['start'])>=Fraction(s['end']):
            raise ValueError('Invalid chord span')
        if windows and s['start']<windows[-1]['end']:
            # Conflict = no safe inference for overlapping disagreement.
            if s['chord']!=windows[-1]['chord']:
                windows.pop();rejected+=1
                continue
            windows[-1]['end']=max(windows[-1]['end'],s['end'])
        else:
            windows.append(dict(s))
    combined=[];bridged=0;beats=Fraction(0)
    for s in windows:
        if combined and combined[-1]['chord']==s['chord']:
            gap=Fraction(s['start'])-Fraction(combined[-1]['end'])
            if gap>=0 and (max_gap is None or gap<=Fraction(max_gap)):
                if gap>0:
                    bridged+=1;beats+=gap
                combined[-1]['end']=s['end']
                continue
        combined.append(dict(s))
    return combined,{'bridged_gaps':bridged,'bridged_beats_q':str(beats),
                     'overlap_conflicts_skipped':rejected,'continuity_windows':len(combined)}


def at_time(windows, onset):
    matches=[s for s in windows if s['start']<=onset<s['end']]
    if len(matches)>1:raise ValueError('Conflicting harmonic windows')
    return matches[0] if matches else None