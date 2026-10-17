"""Polyphonic alternating-return evidence; no automatic phrase/function labels."""
from collections import defaultdict
from fractions import Fraction as F


def detect(rows,period_tolerance=F(1,4)):
    if not 0<=period_tolerance<=1:raise ValueError('Invalid relative-period tolerance')
    starts=defaultdict(list)
    for r in rows:
        if not r['tie_destination'] and F(r['duration_q'])>0 and r['midi'] is not None:starts[F(r['onset_q'])].append(r)
    events=sorted(starts.items());out=[]
    for i in range(len(events)-5):
        group=events[i:i+6];sets=[{r['midi'] for r in ns} for q,ns in group]
        if len({r.get('section_start',r['section']) for q,ns in group for r in ns})!=1:continue
        anchors=sets[0]&sets[2]&sets[4]
        periods=[group[2][0]-group[0][0],group[4][0]-group[2][0]]
        if not min(periods):continue
        error=abs(periods[0]-periods[1])/max(periods)
        if error>period_tolerance:continue
        for anchor in sorted(anchors):
            if any(anchor in sets[j] for j in (1,3,5)):continue
            # Mid/low relative to contrasting material; allow one lower response.
            if sum(max(sets[j])>anchor for j in (1,3,5))<2:continue
            out.append(dict(anchor_midi=anchor,source_bar=group[0][1][0]['bar'],section=group[0][1][0]['section'],
                            members=[[r['occurrence'] for r in ns] for q,ns in group],
                            offsets_q=[str(q-group[0][0]) for q,ns in group],
                            relative_pitch_sets=[sorted(p-anchor for p in s) for s in sets],
                            relative_period_error=str(error),period_tolerance=str(period_tolerance),
                            pitch_effects_unresolved=any(r.get('pitch_effects') for q,ns in group for r in ns),
                            interpretation='three alternating returns across co-attack groups; evidence, not verified pedal role'))
    signatures=defaultdict(list)
    for i,r in enumerate(out):signatures[(tuple(map(tuple,r['relative_pitch_sets'])),tuple(r['offsets_q']))].append(i)
    return out,[ids for ids in signatures.values() if len(ids)>1]


def detect_bursts(rows,period_tolerance=F(1,2)):
    """Allow repeated anchor attacks before a contrasting run; retain raw evidence."""
    starts=defaultdict(list)
    for r in rows:
        if not r['tie_destination'] and F(r['duration_q'])>0 and r['midi'] is not None:starts[F(r['onset_q'])].append(r)
    events=sorted(starts.items());pitch_counts=defaultdict(int)
    for q,ns in events:
        for p in {r['midi'] for r in ns}:pitch_counts[p]+=1
    out=[]
    for anchor,count in pitch_counts.items():
        if count<3:continue
        runs=[]
        for q,ns in events:
            present=any(r['midi']==anchor for r in ns)
            section=ns[0].get('section_start',ns[0]['section'])
            if not runs or runs[-1]['anchor']!=present or runs[-1]['section']!=section:runs.append(dict(anchor=present,section=section,events=[]))
            runs[-1]['events'].append((q,ns))
        for i in range(len(runs)-5):
            group=runs[i:i+6]
            if [r['anchor'] for r in group]!=[True,False,True,False,True,False]:continue
            if len({r['section'] for r in group})!=1:continue
            times=[r['events'][0][0] for r in group];periods=[times[2]-times[0],times[4]-times[2]]
            if not min(periods):continue
            error=abs(periods[0]-periods[1])/max(periods)
            if error>period_tolerance:continue
            if sum(max(n['midi'] for q,ns in group[j]['events'] for n in ns)>anchor for j in (1,3,5))<2:continue
            out.append(dict(anchor_midi=anchor,source_bar=group[0]['events'][0][1][0]['bar'],
                            section=group[0]['events'][0][1][0]['section'],
                            burst_attack_counts=[len(r['events']) for r in group],
                            burst_offsets_q=[str(q-times[0]) for q in times],relative_period_error=str(error),
                            members=[[[n['occurrence'] for n in ns] for q,ns in r['events']] for r in group],
                            interpretation='three anchor attack-bursts alternating with contrasting bursts; overlapping candidate, not verified pedal role'))
    return out


def transformation_groups(candidates):
    """Exact pitch-shape match with rational time scaling; not phrase identity."""
    groups=defaultdict(list)
    for i,c in enumerate(candidates):
        offsets=list(map(F,c['offsets_q']))
        unit=next((q for q in offsets if q>0),None)
        if unit is None:continue
        signature=(tuple(map(tuple,c['relative_pitch_sets'])),tuple(q/unit for q in offsets))
        groups[signature].append((i,c,unit))
    out=[]
    for members in groups.values():
        if len(members)<2:continue
        first,base,unit=members[0]
        out.append(dict(reference_candidate=first,members=[dict(candidate=i,transpose_semitones=c['anchor_midi']-base['anchor_midi'],time_scale=str(u/unit),source_bar=c['source_bar'],section=c['section']) for i,c,u in members],
                        interpretation='same relative pitch sets and proportionally scaled attack offsets; not verified motif/phrase identity'))
    return out
