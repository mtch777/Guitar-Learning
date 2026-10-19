"""Conservative timing containment metadata; does not enable any detector.

Regions contain complete, authoritatively timed measures. A consumer must keep
every event of a temporal relationship inside ONE returned region, and must not
carry ties, neighbors, motifs or patterns across a region boundary.
"""
from fractions import Fraction as F


def local_timing_regions(part, headers, timing_warnings, layout_warnings=()):
    measures=part.get('measures',[])
    if len(headers)<len(measures):raise ValueError('Missing authoritative bar headers')
    intervals=[];previous=None
    for h in headers:
        start,span=F(h['start_q']),F(h['span_q'])
        if span<=0 or (previous is not None and start!=previous):raise ValueError('Noncontiguous authoritative bar headers')
        intervals.append((start,start+span));previous=start+span
    voice_count=max((len(m.get('voices',[])) for m in measures),default=0)
    blocked={v:{} for v in range(voice_count)}
    def block(v,bar,reason):
        if v in blocked and 1<=bar<=len(measures):blocked[v].setdefault(bar,set()).add(reason)
    for warning in timing_warnings:
        bar=warning.get('bar');voice=warning.get('voice')
        if not isinstance(bar,int) or not 1<=bar<=len(measures):
            for v in blocked:
                for b in range(1,len(measures)+1):block(v,b,'unlocated_timing_warning')
            continue
        targets=[voice] if isinstance(voice,int) and voice in blocked else list(blocked)
        for v in targets:
            block(v,bar,warning.get('reason','timing_warning'))
            # A known overlong voice can physically intrude into later measures.
            if warning.get('reason')=='voice_overflows_bar':
                end=intervals[bar-1][0]+F(warning['duration_q'])
                for bi in range(bar,len(measures)):
                    if intervals[bi][0]>=end:break
                    block(v,bi+1,'preceding_voice_overflow_intrusion')
    for warning in layout_warnings:
        bar=warning.get('bar')
        for v in blocked:
            # An ambiguous meter also makes subsequent accumulated starts
            # ambiguous, even after a later meter marking becomes explicit.
            affected=(range(bar,len(measures)+1) if warning.get('reason')=='conflicting_track_meter' else [bar]) if isinstance(bar,int) and 1<=bar<=len(measures) else range(1,len(measures)+1)
            for b in affected:
                block(v,b,'shared_layout_warning')
    # Absent/uninterpreted voices cannot establish continuity through a bar.
    for bi,m in enumerate(measures,1):
        for v in blocked:
            voices=m.get('voices',[])
            if v>=len(voices):block(v,bi,'absent_voice')
            elif not voices[v].get('beats') and not (voices[v].get('rest') or m.get('rest')):block(v,bi,'empty_voice_without_rest_evidence')
    def regions(bad):
        result=[];first=None
        for bi in range(1,len(measures)+2):
            safe=bi<=len(measures) and bi not in bad
            if safe and first is None:first=bi
            if not safe and first is not None:
                last=bi-1
                result.append(dict(start_bar=first,end_bar=last,start_q=str(intervals[first-1][0]),end_q=str(intervals[last-1][1])))
                first=None
        return result
    union={b for bad in blocked.values() for b in bad}
    return dict(schema='source-local-timing-regions-v1',
                voice_regions={str(v):regions(bad) for v,bad in blocked.items()},
                all_voice_regions=regions(union) if voice_count else [],
                excluded_voice_bars=[dict(voice=v,bar=b,reasons=sorted(reasons)) for v,bad in blocked.items() for b,reasons in sorted(bad.items())],
                policy='Metadata only; relationships must fit within one region; never bridge boundaries or infer sounding tie continuity')


def relationship_region(regions, events):
    """Return the containing region index, or None; endpoints use exact time.

    This is an explicit consumer gate, not permission to recover existing whole-
    track detector output. Zero-duration/grace events require a separate policy.
    """
    if not events:return None
    spans=[(F(e['onset_q']),F(e['onset_q'])+F(e['duration_q'])) for e in events]
    if any(end<=start for start,end in spans):return None
    for i,r in enumerate(regions):
        if all(F(r['start_q'])<=start<end<=F(r['end_q']) for start,end in spans):return i
    return None
