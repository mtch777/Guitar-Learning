"""Recurring, temporally separated single/dyad anchors; notation hypotheses only.

Unlike overlapping six-burst windows, reports all anchor attacks in a source
section. Does not mine pitches embedded in changing chords as independent anchors.
"""
from collections import defaultdict
from fractions import Fraction as F


def detect_regions(rows):
    sections=defaultdict(lambda:defaultdict(list))
    for r in rows:
        if not r['tie_destination'] and r['midi'] is not None and F(r['duration_q'])>0:
            sections[r.get('section_start',r.get('section'))][F(r['onset_q'])].append(r)
    result=[]
    for section,starts in sections.items():
        events=sorted(starts.items());signatures=[frozenset(n['midi'] for n in ns) for q,ns in events]
        candidates=defaultdict(list)
        for i,signature in enumerate(signatures):
            if 1<=len(signature)<=2 and len(events[i][1])<=2 and len({n['string'] for n in events[i][1]})==len(events[i][1]):candidates[signature].append(i)
        for anchor,indices in candidates.items():
            if len(indices)<3:continue
            # Need multiple actual departures/returns, not an isolated repeated
            # chord followed by a separate melody later in the section.
            contrasts=[];separate=[]
            for a,b in zip(indices,indices[1:]):
                middle=[i for i in range(a+1,b) if not (signatures[i]&anchor) and max(signatures[i])>min(anchor)]
                if not middle:continue
                contrasts.extend(middle)
                release=max(F(n['onset_q'])+F(n['duration_q']) for n in events[a][1])
                separate.extend(i for i in middle if events[i][0]>=release)
            if len(set(separate))<2:continue
            # Retain the complete continuing run, including repeated chugs in
            # its bursts. Single notes and dyads remain distinct candidates.
            members=[n['occurrence'] for i in indices for n in events[i][1]]
            result.append(dict(section_start=section,anchor_pitches=sorted(anchor),
                               anchor_kind='single_note' if len(anchor)==1 else 'interval',
                               anchor_occurrences=members,anchor_attacks=len(indices),
                               contrasting_attacks=len(set(contrasts)),separated_contrasts=len(set(separate)),
                               start_q=str(events[indices[0]][0]),
                               end_q=str(max(F(n['onset_q'])+F(n['duration_q']) for n in events[indices[-1]][1])),
                               interpretation='repeated standalone note/dyad with temporally separated higher contrasts; not verified musical function'))
    # A less frequent higher return with no more contrasting departures can be
    # an accent inside a stronger lower-anchor pattern. Preserve both when their
    # recurrence evidence differs rather than forcing one pitch per passage.
    retained=[]
    for candidate in result:
        dominated=any(other is not candidate and other['section_start']==candidate['section_start']
                      and max(other['anchor_pitches'])<min(candidate['anchor_pitches'])
                      and other['anchor_attacks']>=candidate['anchor_attacks']
                      and other['separated_contrasts']>=candidate['separated_contrasts']
                      and F(other['start_q'])<=F(candidate['start_q']) and F(other['end_q'])>=F(candidate['end_q'])
                      for other in result)
        if not dominated:retained.append(candidate)
    return sorted(retained,key=lambda r:(str(r['section_start']),r['anchor_pitches'][0],-r['anchor_attacks']))
