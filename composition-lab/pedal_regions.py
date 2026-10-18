"""Recurring, temporally separated single/dyad anchors; notation hypotheses only.

Unlike overlapping six-burst windows, reports all anchor attacks in a source
section. Does not mine pitches embedded in changing chords as independent anchors.
"""
from collections import defaultdict
from fractions import Fraction as F


def detect_regions(rows, *, minimum_return_pairs=0, contrast_above_entire_anchor=False):
    """Detect hypotheses; keyword policies are investigation controls.

    Defaults preserve the frozen baseline until corpus/feedback comparisons
    justify replacing it. Count distinct returns separately from answer attacks.
    """
    sections=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if not r['tie_destination'] and r['midi'] is not None and F(r['duration_q'])>0:
            sections[r.get('section_start',r.get('section'))][F(r['onset_q'])].append(r)
    result=[]
    for section,starts in sections.items():
        events=sorted(starts.items());signatures=[frozenset(n['midi'] for n in ns) for q,ns in events]
        pitches=[n['midi'] for q,ns in events for n in ns]
        pcs={p%12 for p in pitches}
        triads=({0,4,7},{0,3,7},{0,3,6},{0,4,8},{0,2,7},{0,5,7})
        chord_collection=any({(p-root)%12 for p in pcs} in triads for root in pcs)
        uniform_durations=len({n['duration_q'] for q,ns in events for n in ns})==1
        uniform_gaps=len({events[i+1][0]-events[i][0] for i in range(len(events)-1)})==1
        if len(events)>=6 and all(len(ns)==1 for q,ns in events) and chord_collection and uniform_durations and uniform_gaps:
            # A regular fixed-chord cycle alone does not establish pedal function.
            # Abstain rather than calling every repeated chord tone an anchor.
            continue
        candidates=defaultdict(list)
        for i,signature in enumerate(signatures):
            if 1<=len(signature)<=2 and len(events[i][1])<=2 and len({n['string'] for n in events[i][1]})==len(events[i][1]):candidates[signature].append(i)
        for anchor,indices in candidates.items():
            if len(indices)<3:continue
            if min(anchor)>(min(pitches)+max(pitches))/2:continue
            # Need multiple actual departures/returns, not an isolated repeated
            # chord followed by a separate melody later in the section.
            contrasts=[];separate=[];return_pairs=0
            for a,b in zip(indices,indices[1:]):
                reference=max(anchor) if contrast_above_entire_anchor else min(anchor)
                middle=[i for i in range(a+1,b) if not (signatures[i]&anchor) and max(signatures[i])>reference]
                if not middle:continue
                contrasts.extend(middle)
                release=max(F(n['onset_q'])+F(n['duration_q']) for n in events[a][1])
                separated=[i for i in middle if events[i][0]>=release]
                separate.extend(separated)
                return_pairs+=bool(separated)
            if len(set(separate))<2:continue
            if return_pairs<minimum_return_pairs:continue
            # Retain the complete continuing run, including repeated chugs in
            # its bursts. Single notes and dyads remain distinct candidates.
            # A qualifying dyad may continue with a reduced voicing. Include
            # standalone subsets while preserving which attacks were partial.
            partial=[i for i,s in enumerate(signatures) if len(anchor)==2 and s<anchor and len(events[i][1])<=2]
            coverage=sorted(set(indices+partial))
            members=[n['occurrence'] for i in coverage for n in events[i][1]]
            result.append(dict(section_start=section,anchor_pitches=sorted(anchor),
                               anchor_kind='single_note' if len(anchor)==1 else 'interval',
                               anchor_occurrences=members,anchor_attacks=len(indices),
                               partial_voicing_attacks=len(partial),
                               contrasting_attacks=len(set(contrasts)),separated_contrasts=len(set(separate)),
                               start_q=str(events[coverage[0]][0]),
                               end_q=str(max(F(n['onset_q'])+F(n['duration_q']) for n in events[coverage[-1]][1])),
                               interpretation='repeated standalone note/dyad with temporally separated higher contrasts; not verified musical function'))
    # Prefer the lowest qualifying concurrent anchor, including equally recurring
    # neighbors. Adjacent nonoverlapping anchor changes remain separate regions.
    retained=[]
    for candidate in result:
        dominated=any(other is not candidate and other['section_start']==candidate['section_start']
                      and max(other['anchor_pitches'])<min(candidate['anchor_pitches'])
                      and max(F(other['start_q']),F(candidate['start_q']))<min(F(other['end_q']),F(candidate['end_q']))
                      for other in result)
        if not dominated:retained.append(candidate)
    return sorted(retained,key=lambda r:(str(r['section_start']),r['anchor_pitches'][0],-r['anchor_attacks']))
