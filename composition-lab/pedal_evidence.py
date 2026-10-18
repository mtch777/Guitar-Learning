"""Experimental pedal acceptance gates; the frozen register detector stays intact.

No song identities or tuned pitch constants. All comparisons use exact rational
times. Policy switches support controlled comparisons, not user-facing levers.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F
from statistics import median, median_low

from pedal_register import uniform_arpeggio


def finalize(events, roles, *, identity=True):
    """Recheck the FINAL evidence graph; pruning must not leave orphan calls."""
    runs=[]
    for e in events:
        calls=[n for n in e['notes'] if roles.get(n['occurrence'])=='call']
        answers=[n for n in e['notes'] if roles.get(n['occurrence'])=='response']
        if calls and answers:raise AssertionError('Same-onset call and response')
        if calls:kind='call';signature={n['midi'] for n in calls}
        elif answers:kind='response';signature=set()
        elif all(n['midi'] is None and 'dead' in n.get('effects',[]) for n in e['notes']):continue
        else:kind='break';signature=set()
        changing=(kind=='call' and runs and runs[-1]['kind']=='call' and not(runs[-1]['signature'] & signature))
        if not runs or kind!=runs[-1]['kind'] or changing:
            runs.append(dict(kind=kind,signature=signature,events=[]))
        elif kind=='call':runs[-1]['signature'] &= signature
        runs[-1]['events'].append(e)
    units=[(a,b,c) for a,b,c in zip(runs,runs[1:],runs[2:]) if [a['kind'],b['kind'],c['kind']]==['call','response','call']]
    valid=[]
    for index,(a,b,c) in enumerate(units):
        stable=bool(a['signature'] & c['signature'])
        next_stable=(index+1<len(units) and units[index+1][0] is c and
                     bool(c['signature'] & units[index+1][2]['signature']))
        transition=(len(a['events'])>=2 and len(c['events'])>=2 and next_stable
                    and len(units[index+1][2]['events'])>=2)
        if identity and not(stable or transition):continue
        valid.append((a,b,c))
    chains=[]
    for unit in valid:
        if not chains or chains[-1][-1][2] is not unit[0]:chains.append([])
        chains[-1].append(unit)
    keep={};cycles=[]
    for chain in chains:
        if len(chain)<2:continue
        for a,b,c in chain:
            call=[n['occurrence'] for e in a['events'] for n in e['notes'] if roles.get(n['occurrence'])=='call']
            response=[n['occurrence'] for e in b['events'] for n in e['notes'] if roles.get(n['occurrence'])=='response']
            keep.update({i:'call' for i in call});keep.update({i:'response' for i in response})
            cycles.append(dict(call_start_q=a['events'][0]['onset_q'],response_start_q=b['events'][0]['onset_q'],
                return_q=c['events'][0]['onset_q'],call_members=call,response_members=response))
        final=chain[-1][2]
        for e in final['events']:
            keep.update({n['occurrence']:'call' for n in e['notes'] if roles.get(n['occurrence'])=='call'})
        i=next(i for i,r in enumerate(runs) if r is final)
        if i+1<len(runs) and runs[i+1]['kind']=='response':
            for e in runs[i+1]['events']:
                keep.update({n['occurrence']:'response' for n in e['notes'] if roles.get(n['occurrence'])=='response'})
    return keep,cycles


def arpeggio_onsets(events):
    """Find maximal uniform chord walks locally, even inside a varied section."""
    marked = set()
    forms = ({0,4,7},{0,3,7},{0,3,6},{0,4,8},{0,2,7},{0,5,7})
    for root in range(12):
        for form in forms:
            pcs = {(root+p)%12 for p in form}; run=[]; duration=None; gap=None
            def finish():
                counts=Counter(e['notes'][0]['midi']%12 for e in run)
                if (len(run)>=6 and set(counts)==pcs and min(counts.values())>=2
                        and max(counts.values())-min(counts.values())<=1):
                    marked.update(e['onset_q'] for e in run)
            for e in events:
                ns=e['notes'];valid=(len(ns)==1 and ns[0]['midi'] is not None and ns[0]['midi']%12 in pcs)
                if not valid:
                    finish();run=[];duration=None;gap=None;continue
                d=F(ns[0]['duration_q'])
                step=F(e['onset_q'])-F(run[-1]['onset_q']) if run else None
                if run and (d!=duration or ns[0]['midi']==run[-1]['notes'][0]['midi'] or (gap is not None and step!=gap)):
                    finish();run=[];gap=None
                if run and gap is None:gap=F(e['onset_q'])-F(run[-1]['onset_q'])
                run.append(e);duration=d
            finish()
    return marked


def analyze_evidence(rows, *, identity=True, connectivity=True, arpeggio=True,
                     standalone=True, return_identity=True, low_position=True,
                     complete=True, _context_rows=None):
    context_rows=rows if _context_rows is None else _context_rows
    groups = defaultdict(list)
    written = defaultdict(list)
    for n in rows:
        if F(n['duration_q']) > 0:written[F(n['onset_q'])].append(n)
        if not n['tie_destination'] and F(n['duration_q']) > 0:
            groups[F(n['onset_q'])].append(n)
    events = [dict(onset_q=str(q), notes=ns) for q, ns in sorted(groups.items())]
    empty = dict(accepted=False, anchor_pitches=[], roles={}, cycles=[], events=events,
                 reason='No connected, locally recurring anchor and later answer established.')
    if not events:
        return empty
    known = all(n['midi'] is not None for e in events for n in e['notes'])
    if arpeggio and known and uniform_arpeggio(events):
        return dict(empty, reason='Uniform traversal of a fixed chord; no independent pedal evidence.')
    arp_times = arpeggio_onsets(events) if arpeggio else set()
    if arpeggio:
        for index,e in enumerate(events):
            local=events[max(0,index-3):index+4]
            pcs=[n['midi']%12 for event in local for n in event['notes'] if n['midi'] is not None]
            counts=Counter(pcs)
            if (len(pcs)==len(local) and len(local)>=6 and all(a!=b for a,b in zip(pcs,pcs[1:]))
                    and uniform_arpeggio(local) and max(counts.values())-min(counts.values())<=1):
                arp_times.add(e['onset_q'])
    chord_blocks=set();block=[];last_signature=None
    for q,ns in sorted(written.items()):
        signature=tuple(sorted(n['midi'] for n in ns if n['midi'] is not None))
        if signature != last_signature:
            if len(block)>=3:chord_blocks.update(block)
            block=[]
        if len({p%12 for p in signature})>=3:block.append(q)
        last_signature=signature
    if len(block)>=3:chord_blocks.update(block)
    gaps = [F(b['onset_q']) - F(a['onset_q']) for a, b in zip(events, events[1:])]
    typical_gap = median(gaps) if gaps else F(0)
    levels = sorted({n['midi'] for e in events for n in e['notes'] if n['midi'] is not None})
    rejected = Counter()
    for ceiling in levels[:-1]:
        runs = []
        previous_end = None
        for event in events:
            q = F(event['onset_q'])
            ps = [n['midi'] for n in event['notes']]
            dead = all(n['midi'] is None and 'dead' in n.get('effects', []) for n in event['notes'])
            if dead:
                # Explicit dead strikes have no pitch to classify. They can sit
                # inside a burst but never supply anchor or response evidence.
                continue
            kind = 'unknown' if None in ps else 'call' if min(ps) <= ceiling else 'response'
            # A silence beyond the observed attack cadence interrupts evidence.
            # Sustain is allowed: a later answer need not wait for note release.
            if connectivity and previous_end is not None and q - previous_end > 4 * typical_gap:
                runs.append(dict(kind='break', events=[]))
            signature = {p for p in ps if p is not None and p <= ceiling}
            changing_call = (kind == 'call' and runs and runs[-1]['kind'] == 'call'
                             and not (runs[-1]['anchor_signature'] & signature))
            if not runs or runs[-1]['kind'] != kind or changing_call:
                runs.append(dict(kind=kind, events=[], anchor_signature=signature))
            elif kind == 'call':
                runs[-1]['anchor_signature'] &= signature
            runs[-1]['events'].append(event)
            previous_end = max([q + F(n['duration_q']) for n in event['notes']] +
                               ([previous_end] if previous_end is not None else []))
        candidates = []
        for a, b, c in zip(runs, runs[1:], runs[2:]):
            if [a['kind'], b['kind'], c['kind']] != ['call', 'response', 'call']:
                continue
            candidates.append((a, b, c))
        # Count anchor identity at the CALL-BURST level, not pooled note counts.
        signatures = {}
        for run in runs:
            if run['kind'] != 'call':
                continue
            counter = Counter(tuple(sorted({n['midi'] for n in e['notes'] if n['midi'] <= ceiling}))
                              for e in run['events'])
            signatures[id(run)] = counter
        chains = []
        for candidate in candidates:
            if not chains or chains[-1][-1][2] is not candidate[0]:
                chains.append([])
            chains[-1].append(candidate)
        accepted = []
        for chain in chains:
            if len(chain) < 2:
                continue
            if return_identity and not any(set(signatures[id(a)]) & set(signatures[id(c)])
                                           for a, b, c in chain):
                rejected['no_anchor_return'] += 1
                continue
            calls = [v[0] for v in chain] + [chain[-1][2]]
            periods = [F(c['events'][0]['onset_q'])-F(a['events'][0]['onset_q']) for a,b,c in chain]
            typical_return = median_low(periods)
            burst_counts = Counter(s for run in calls for s in signatures[id(run)] if 1 <= len(s) <= 2)
            valid = []
            for unit_index, (a, b, c) in enumerate(chain):
                if arpeggio:
                    neighbor = chain[unit_index+1] if unit_index+1<len(chain) else chain[max(0,unit_index-1)]
                    lo=min(F(a['events'][0]['onset_q']),F(neighbor[0]['events'][0]['onset_q']))
                    hi=max(F(c['events'][0]['onset_q']),F(neighbor[2]['events'][0]['onset_q']))
                    local_events=[e for e in events if lo<=F(e['onset_q'])<=hi]
                    pcs=Counter(n['midi']%12 for e in local_events for n in e['notes'] if n['midi'] is not None)
                    if (all(n['midi'] is not None for e in local_events for n in e['notes']) and uniform_arpeggio(local_events) and pcs and
                            max(pcs.values())-min(pcs.values())<=1):
                        continue
                if connectivity and periods[unit_index] > 4 * typical_return:
                    rejected['return_period_outlier'] += 1
                    continue
                # Each local call needs repeated identity, either within its burst
                # or across call bursts. Changing registers alone cannot qualify.
                supported = {s for s, count in signatures[id(a)].items()
                             if 1 <= len(s) <= 2 and (count >= 2 or burst_counts[s] >= 3)}
                if standalone:
                    independent = Counter(tuple(sorted({n['midi'] for n in e['notes']}))
                                   for run in calls for e in run['events']
                                   if all(n['midi'] <= ceiling for n in e['notes'])
                                   and len({n['midi'] for n in e['notes']}) <= 2)
                    supported &= {s for s, count in independent.items() if count >= 3}
                    # Tied chord members still belong to the written voicing.
                    # Rearticulating one member of a repeated full chord cannot
                    # manufacture a standalone single-note call.
                    local = {tuple(sorted({n['midi'] for n in e['notes'] if n['midi'] <= ceiling}))
                             for e in a['events']
                             if F(e['onset_q']) not in chord_blocks}
                    supported &= local
                if low_position:
                    bars=[n['bar'] for run in (a,b,c) for e in run['events'] for n in e['notes'] if 'bar' in n]
                    # Register belongs to the exchange's actual source measures,
                    # not the extrema of an arbitrarily large analysis scope.
                    # Complete measures supply surrounding melodic context even
                    # when the evidence itself starts midway through a bar.
                    ps=([n['midi'] for n in context_rows if n['midi'] is not None
                         and min(bars)<=n.get('bar',-1)<=max(bars)] if bars else levels)
                    supported = {s for s in supported if min(s) <= (min(ps) + max(ps)) / 2}
                if return_identity:
                    returned = set(signatures[id(c)])
                    next_stable = (unit_index + 1 < len(chain) and
                        bool(set(signatures[id(chain[unit_index + 1][0])]) &
                             set(signatures[id(chain[unit_index + 1][2])])))
                    supported = {s for s in supported if any(set(t) <= set(s) for t in returned)
                                 or (next_stable and signatures[id(a)][s] >= 2)}
                if identity and not supported:
                    rejected['local_identity'] += 1
                    continue
                valid.append((a, b, c, supported))
            # Invalid local units break the chain instead of supplying returns.
            parts = []
            for unit in valid:
                if not parts or parts[-1][-1][2] is not unit[0]:
                    parts.append([])
                parts[-1].append(unit)
            accepted.extend(part for part in parts if len(part) >= 2)
        roles = {}; support = []; anchors = set()
        for chain in accepted:
            for a, b, c, supported in chain:
                call_ids = []; answer_ids = []
                for e in a['events']:
                    signature = tuple(sorted({n['midi'] for n in e['notes'] if n['midi'] <= ceiling}))
                    if identity and signature not in supported:
                        continue
                    if F(e['onset_q']) in chord_blocks:
                        continue
                    for n in e['notes']:
                        if n['midi'] <= ceiling:
                            roles[n['occurrence']] = 'call'; anchors.add(n['midi']); call_ids.append(n['occurrence'])
                        # A coattacked upper note is context, NEVER an answer.
                for e in b['events']:
                    for n in e['notes']:
                        roles[n['occurrence']] = 'response'; answer_ids.append(n['occurrence'])
                if call_ids:
                    support.append(dict(call_start_q=a['events'][0]['onset_q'],
                        response_start_q=b['events'][0]['onset_q'], return_q=c['events'][0]['onset_q'],
                        call_members=call_ids, response_members=answer_ids))
            # The final return is evidence, but never extends through a new,
            # unestablished pitch just because it is below the same threshold.
            final = chain[-1][2]
            established = set().union(*(u[3] for u in chain))
            for e in final['events']:
                signature = tuple(sorted({n['midi'] for n in e['notes'] if n['midi'] <= ceiling}))
                if identity and not any(set(signature) <= set(s) for s in established):
                    continue
                if F(e['onset_q']) in chord_blocks:
                    continue
                for n in e['notes']:
                    if n['midi'] <= ceiling:
                        roles[n['occurrence']] = 'call'; anchors.add(n['midi'])
            final_index = next(i for i, run in enumerate(runs) if run is final)
            if final_index + 1 < len(runs) and runs[final_index + 1]['kind'] == 'response':
                for e in runs[final_index + 1]['events']:
                    for n in e['notes']:
                        roles[n['occurrence']] = 'response'
        if len(support) >= 2:
            byid = {n['occurrence']:n for n in rows}
            # Restore an interval only when its WHOLE recurring voicing actually
            # has later answers above it; arbitrary upper coattacks stay context.
            dyads = Counter(tuple(sorted({n['midi'] for n in e['notes']}))
                            for e in events if all(n['midi'] is not None for n in e['notes'])
                            and len({n['midi'] for n in e['notes']}) == 2
                            and any(roles.get(n['occurrence']) == 'call' for n in e['notes']))
            for dyad, count in dyads.items():
                if count < 3:
                    continue
                evidence = [c for c in support
                            if any(byid[i]['midi'] == min(dyad) for i in c['call_members'])
                            and min(byid[i]['midi'] for i in c['response_members']) > max(dyad)]
                if len(evidence) < 2:
                    continue
                for e in events:
                    if {n['midi'] for n in e['notes']} == set(dyad) and any(
                            roles.get(n['occurrence']) == 'call' for n in e['notes']):
                        for n in e['notes']:
                            roles[n['occurrence']] = 'call'; anchors.add(n['midi'])
            for c in support:
                lo, hi = F(c['call_start_q']), F(c['response_start_q'])
                c['call_members'] = [n['occurrence'] for e in events if lo <= F(e['onset_q']) < hi
                                     for n in e['notes'] if roles.get(n['occurrence']) == 'call']
            # An occasional lower accent can answer an already established
            # middle-register pedal. It cannot establish a new acceptance, and
            # a recurring lower candidate is never silently relabeled this way.
            call_times = sorted({F(byid[i]['onset_q']) for i, role in roles.items() if role == 'call'})
            pitch_counts = Counter(n['midi'] for n in rows if not n['tie_destination'])
            for e in events:
                if len(e['notes']) != 1 or not call_times:
                    continue
                n = e['notes'][0]; q = F(e['onset_q']); p = n['midi']
                if (p is not None and p < min(anchors) and pitch_counts[p] < 3
                        and n['occurrence'] not in roles and call_times[0] < q < call_times[-1]):
                    roles[n['occurrence']] = 'response'
            if complete:
                selected = [F(byid[i]['onset_q']) for i in roles]
                lo, hi = min(selected), max(selected)
                # Independently establish earlier/later pedals; never let a low
                # candidate suppress a different valid pedal in another passage.
                for remaining in ([n for n in rows if F(n['onset_q']) < lo],
                                  [n for n in rows if F(n['onset_q']) > hi]):
                    extra = analyze_evidence(remaining, identity=identity, connectivity=connectivity,
                        arpeggio=arpeggio, standalone=standalone, return_identity=return_identity,
                        low_position=low_position, complete=True, _context_rows=context_rows)
                    roles.update(extra['roles']); support.extend(extra['cycles']); anchors.update(extra['anchor_pitches'])
                # A long answer may itself contain a separately established
                # higher pedal. Analyze contiguous call-free regions without
                # borrowing the outer anchor's recurrence.
                free=[];regions=[]
                for e in events:
                    if any(roles.get(n['occurrence'])=='call' for n in e['notes']):
                        if free:regions.append(free);free=[]
                    else:free.append(e)
                if free:regions.append(free)
                for region in regions:
                    if len(region)<5 or len(region)==len(events):continue
                    start,end=F(region[0]['onset_q']),F(region[-1]['onset_q'])
                    remaining=[n for n in rows if start<=F(n['onset_q'])<=end]
                    extra=analyze_evidence(remaining,identity=identity,connectivity=connectivity,
                        arpeggio=arpeggio,standalone=standalone,return_identity=return_identity,
                        low_position=low_position,complete=True,_context_rows=context_rows)
                    call_onsets={F(byid[i]['onset_q']) for i,role in extra['roles'].items() if role=='call'}
                    for e in region:
                        if F(e['onset_q']) in call_onsets:
                            # Establishing an inner anchor changes the event's
                            # role atomically. Its coattacked upper voices cannot
                            # retain an outer-response label at that same onset.
                            for n in e['notes']:roles.pop(n['occurrence'],None)
                    roles.update(extra['roles'])
            if arpeggio:
                for e in events:
                    if e['onset_q'] in arp_times:
                        for n in e['notes']:roles.pop(n['occurrence'],None)
            roles,support=finalize(events,roles,identity=return_identity)
            if len(support)<2:
                continue
            anchors={byid[i]['midi'] for i,role in roles.items() if role=='call'}
            return dict(accepted=True, anchor_pitches=sorted(anchors), roles=roles,
                        cycles=support, events=events, register_ceiling=ceiling,
                        reason='Repeated local anchor bursts with strictly later answers.',
                        diagnostics=dict(rejected))
    return dict(empty, diagnostics=dict(rejected))
