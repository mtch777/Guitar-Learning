"""Context-local pedal hypotheses with changing bass pitches and note-level roles.

The supplied scope is explicit. This does not claim to infer song sections or
musical intent. Register thresholds come from observed pitches, never song names,
tuning or a prescribed number of chugs. Original occurrences remain immutable.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F


def uniform_arpeggio(events):
    notes=[n for e in events for n in e['notes']]
    if len(events)<6 or any(len(e['notes'])!=1 for e in events):return False
    pcs={n['midi']%12 for n in notes}
    forms=({0,4,7},{0,3,7},{0,3,6},{0,4,8},{0,2,7},{0,5,7})
    chord=any({(p-root)%12 for p in pcs} in forms for root in pcs)
    changes=all(a['notes'][0]['midi']!=b['notes'][0]['midi'] for a,b in zip(events,events[1:]))
    return chord and changes and len({F(n['duration_q']) for n in notes})==1 and len({
        F(b['onset_q'])-F(a['onset_q']) for a,b in zip(events,events[1:])})==1


def analyze_register(rows):
    groups=defaultdict(list)
    for n in rows:
        if not n['tie_destination'] and F(n['duration_q'])>0:
            groups[F(n['onset_q'])].append(n)
    events=[dict(onset_q=str(q),notes=ns) for q,ns in sorted(groups.items())]
    empty=dict(accepted=False,anchor_pitches=[],roles={},cycles=[],events=events,
               reason='No repeated low-call / higher-answer / low-return evidence in this scope.')
    if not events:return empty
    if all(n['midi'] is not None for e in events for n in e['notes']) and uniform_arpeggio(events):
        return dict(empty,reason='Uniform fixed-chord arpeggio; recurrence alone does not establish pedal function.')
    levels=sorted({n['midi'] for e in events for n in e['notes'] if n['midi'] is not None})
    for ceiling in levels[:-1]:
        labeled=[]
        for event in events:
            ns=event['notes'];known=[n['midi'] for n in ns if n['midi'] is not None]
            kind='unknown' if len(known)!=len(ns) else 'call' if min(known)<=ceiling else 'response'
            labeled.append(dict(event,kind=kind))
        runs=[]
        for event in labeled:
            if not runs or runs[-1]['kind']!=event['kind']:runs.append(dict(kind=event['kind'],events=[]))
            runs[-1]['events'].append(event)
        cycles=[]
        for a,b,c in zip(runs,runs[1:],runs[2:]):
            if [a['kind'],b['kind'],c['kind']]!=['call','response','call']:continue
            cycles.append(dict(call_start_q=a['events'][0]['onset_q'],
                response_start_q=b['events'][0]['onset_q'],return_q=c['events'][0]['onset_q'],
                call_members=[n['occurrence'] for e in a['events'] for n in e['notes'] if n['midi']<=ceiling],
                response_members=[n['occurrence'] for e in b['events'] for n in e['notes']]))
        if len(cycles)<2:continue
        # Only retain the uninterrupted evidence chain, never unrelated same-pitch
        # notes elsewhere in the section. Unknown hits interrupt a chain.
        chains=[]
        for c in cycles:
            if not chains or chains[-1][-1]['return_q']!=c['call_start_q']:chains.append([])
            chains[-1].append(c)
        chains=[c for c in chains if len(c)>=2]
        if not chains:continue
        roles={};anchors=set();support=[]
        for chain in chains:
            start=F(chain[0]['call_start_q']);last=F(chain[-1]['return_q'])
            last_run=next(i for i,r in enumerate(runs) if F(r['events'][0]['onset_q'])==last)
            ending=runs[last_run]['events'][:]
            if last_run+1<len(runs) and runs[last_run+1]['kind']=='response':
                ending+=runs[last_run+1]['events']
            last=F(ending[-1]['onset_q'])
            for e in labeled:
                q=F(e['onset_q'])
                if not start<=q<=last:continue
                for n in e['notes']:
                    if n['midi'] is None:continue
                    role='call' if n['midi']<=ceiling else 'response'
                    roles[n['occurrence']]=role
                    if role=='call':anchors.add(n['midi'])
            support.extend(chain)
        counts=Counter(n['midi'] for e in labeled for n in e['notes'] if roles.get(n['occurrence'])=='call')
        if not counts or max(counts.values())<3:continue
        standalone=sum(e['kind']=='call' and len({n['midi'] for n in e['notes']})<=2
                       and all(n['midi']<=ceiling for n in e['notes'])
                       and any(roles.get(n['occurrence'])=='call' for n in e['notes']) for e in labeled)
        if standalone<3:continue
        # A moving dyad keeps its identity under transposition. Only extend a
        # coattack when its whole voicing is independently observed at least
        # three times as a standalone low call; do not absorb arbitrary highs.
        forms=Counter(tuple(p-min(ps) for p in ps) for e in labeled
            if e['kind']=='call' and all(n['midi']<=ceiling for n in e['notes'])
            for ps in [sorted({n['midi'] for n in e['notes']})] if len(ps)<=2)
        for e in labeled:
            ps=sorted({n['midi'] for n in e['notes'] if n['midi'] is not None})
            if not ps or len(ps)>2 or forms[tuple(p-min(ps) for p in ps)]<3:continue
            if any(roles.get(n['occurrence'])=='call' for n in e['notes']):
                for n in e['notes']:
                    roles[n['occurrence']]='call';anchors.add(n['midi'])
        for cycle in support:
            lo,hi=F(cycle['call_start_q']),F(cycle['return_q'])
            members=[n for e in labeled if lo<=F(e['onset_q'])<hi for n in e['notes']]
            cycle['call_members']=[n['occurrence'] for n in members if roles.get(n['occurrence'])=='call']
            cycle['response_members']=[n['occurrence'] for n in members if roles.get(n['occurrence'])=='response']
        return dict(accepted=True,anchor_pitches=sorted(anchors),register_ceiling=ceiling,
            roles=roles,cycles=support,events=labeled,
            reason='Lowest observed register boundary with at least two consecutive departures and returns.',
            limitation='Context-local development hypothesis; changing bass membership is not a phrase or intent claim.')
    return empty
