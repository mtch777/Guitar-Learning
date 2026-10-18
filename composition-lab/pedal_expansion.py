"""Additive continuation of established pedals. Never discovers or rejects seeds.

The evidence detector is deliberately not called or modified here. A single
complete later exchange may extend an established anchor; earlier material needs
two complete exchanges. Exact pitch identity, source attacks, chord-walk and
silence guards remain mandatory. All durations and boundaries are rational.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from fractions import Fraction as F
from statistics import median

from pedal_evidence import arpeggio_onsets
from pedal_register import uniform_arpeggio


def _end(n):
    return F(n['onset_q']) + F(n['duration_q'])


def _merge(regions):
    """Canonical disjoint intervals with every seed's evidence retained."""
    out = []
    for region in sorted(regions, key=lambda r: (F(r['start_q']), F(r['end_q']))):
        if out and F(region['start_q']) < F(out[-1]['end_q']):
            target = out[-1]
            target['end_q'] = str(max(F(target['end_q']), F(region['end_q'])))
            target['start_q'] = str(min(F(target['start_q']), F(region['start_q'])))
            target['seed_ids'] = sorted(set(target['seed_ids'] + region['seed_ids']))
            target['members'].update(region['members'])
            target['roles'].update(region['roles'])
            target['cycles'].extend(c for c in region['cycles'] if c not in target['cycles'])
            target['added_cycles'].extend(c for c in region['added_cycles'] if c not in target['added_cycles'])
        else:
            out.append(deepcopy(region))
    return out


def expand_phrases(rows, seeds, *, before_exchanges=2, after_exchanges=1, sustain_chains=()):
    """Return expanded disjoint phrases and an auditable mapping to ALL seeds.

    Each seed supplies start_q/end_q, members, roles, cycles and a unique id.
    No-op for an empty seed set. Expansion is outside the original support
    interval only. The terminal call can become the first call of continuation.
    Upper notes at that same onset never supply an answer. Before/after compare
    against canonical original groups, so pre-existing overlap is not a gain.
    """
    if before_exchanges < 2 or after_exchanges < 1:
        raise ValueError('Earlier evidence requires two exchanges; later at least one')
    if len({s['id'] for s in seeds}) != len(seeds):
        raise ValueError('Duplicate seed identity')
    byid = {n['occurrence']: n for n in rows}
    if len(byid) != len(rows):
        raise ValueError('Duplicate source occurrence')
    grouped = defaultdict(list)
    for n in rows:
        if not n['tie_destination'] and F(n['duration_q']) > 0:
            grouped[F(n['onset_q'])].append(n)
    events = [dict(onset_q=str(q), notes=ns) for q, ns in sorted(grouped.items())]
    index = {F(e['onset_q']): i for i, e in enumerate(events)}
    arp = arpeggio_onsets(events)
    for i in range(len(events)-5):
        window=events[i:i+6]
        if all(n['midi'] is not None for e in window for n in e['notes']) and uniform_arpeggio(window):
            arp.update(e['onset_q'] for e in window)
    initial = []
    for s in seeds:
        if not set(s['members']) <= byid.keys():
            raise ValueError('Seed contains an invented occurrence')
        initial.append(dict(start_q=s['start_q'], end_q=s['end_q'], seed_ids=[s['id']],
            members=set(s['members']), roles=dict(s['roles']), cycles=deepcopy(s['cycles']), added_cycles=[]))
    original = _merge(initial)
    phrases = deepcopy(original)

    def signature(e):
        ps = [n['midi'] for n in e['notes']]
        return frozenset(ps) if ps and None not in ps else frozenset()

    def extend(region, forward, bound, inclusive=True):
        calls = [byid[i] for i, role in region['roles'].items() if role == 'call']
        if not calls:
            return
        q = (max if forward else min)(F(n['onset_q']) for n in calls)
        anchor = frozenset(n['midi'] for n in calls if F(n['onset_q']) == q)
        if not anchor or len(anchor) > 2 or None in anchor:
            return
        start_index = index[q]
        seed_events = [e for e in events if F(region['start_q']) <= F(e['onset_q']) < F(region['end_q'])]
        gaps = [F(b['onset_q'])-F(a['onset_q']) for a,b in zip(seed_events,seed_events[1:])]
        cadence = median(gaps) if gaps else F(0)
        periods = [F(c['return_q'])-F(c['call_start_q']) for c in region['cycles']]
        max_period = 4 * median(periods) if periods else F(0)
        if cadence <= 0 or max_period <= 0:
            return
        step = 1 if forward else -1
        cursor = start_index
        accepted = []
        burst = []
        # Only contiguous source context is visited. No fixed bar crop or song rule.
        while 0 <= cursor+step < len(events):
            path = []
            j = cursor + step
            found = None
            while 0 <= j < len(events):
                e = events[j]; t = F(e['onset_q'])
                if (forward and t > bound) or (not forward and t < bound):
                    break
                if not inclusive and t==bound:break
                if abs(t-F(events[cursor]['onset_q'])) > max_period:
                    break
                left, right = sorted((j,j-step))
                previous, current = events[left], events[right]
                sustain_end = max(_end(n) for n in previous['notes'])
                if F(current['onset_q'])-sustain_end > 4*cadence:
                    break
                if not signature(e):
                    break
                if signature(e) == anchor:
                    found = j
                    break
                # A coattack containing the anchor is not a later answer. Neither
                # changed chord blocks nor uniform arpeggios can bridge phrases.
                if signature(e) & anchor or len(signature(e)) >= 3 or e['onset_q'] in arp:
                    break
                path.append(e)
                j += step
            if found is None:
                break
            if not path:
                # Same-anchor attacks belong to the boundary burst. Defer adding
                # them until a genuine exchange is proven beyond the boundary.
                burst.append(events[found]); cursor = found
                continue
            a, c = sorted((cursor,found))
            segment = events[a:c+1]
            if any(e['onset_q'] in arp for e in segment) or uniform_arpeggio(segment):
                break
            response = sorted(path,key=lambda e:F(e['onset_q']))
            upward = any(n['midi'] > max(anchor) for e in response for n in e['notes'])
            # Occasional lower replies are allowed AFTER an established pedal,
            # but cannot by themselves establish backward continuation.
            if not upward and not forward:
                break
            call_event = events[a]
            cycle = dict(call_start_q=call_event['onset_q'],response_start_q=response[0]['onset_q'],
                return_q=events[c]['onset_q'],call_members=[n['occurrence'] for n in call_event['notes'] if n['midi'] in anchor],
                response_members=[n['occurrence'] for e in response for n in e['notes']])
            accepted.append(dict(cycle=cycle, events=segment+burst, upward=upward))
            burst=[];cursor=found
        required = after_exchanges if forward else before_exchanges
        if len(accepted) < required or not any(u['upward'] for u in accepted):
            return
        if forward and burst:
            accepted[-1]['events'].extend(burst)
        # Lower accents must be exceptional, not a second recurring low anchor.
        lower = Counter(n['midi'] for u in accepted for i in u['cycle']['response_members']
                        for n in [byid[i]] if n['midi'] < min(anchor))
        stop = next((i for i,u in enumerate(accepted) if any(lower[byid[n]['midi']] >= 3
                    for n in u['cycle']['response_members'] if byid[n]['midi'] < min(anchor))),len(accepted))
        accepted = accepted[:stop]
        if len(accepted) < required or not any(u['upward'] for u in accepted):
            return
        for unit in accepted:
            cycle = unit['cycle']
            for e in unit['events']:
                is_call=signature(e)==anchor or e['onset_q'] in (cycle['call_start_q'],cycle['return_q'])
                for n in e['notes']:
                    ident=n['occurrence'];region['members'].add(ident)
                    if ident not in region['roles']:
                        if is_call:
                            if n['midi'] in anchor:region['roles'][ident]='call'
                        else:region['roles'][ident]='response'
            if cycle not in region['cycles']:
                region['cycles'].append(cycle);region['added_cycles'].append(cycle)
        ns=[byid[i] for i in region['members']]
        region['start_q']=str(min(F(region['start_q']),min(F(n['onset_q']) for n in ns)))
        region['end_q']=str(max(F(region['end_q']),max(_end(n) for n in ns)))

    # Forward receives the lower recurrence threshold and is evaluated first.
    # Neighbor intervals are immutable barriers unless their boundary anchor is
    # exactly the same; touching its first call creates overlap, then one merge.
    for i, region in enumerate(phrases):
        following=original[i+1] if i+1<len(original) else None
        preceding=original[i-1] if i else None
        def boundary_signature(r, first):
            ns=[byid[k] for k,v in r['roles'].items() if v=='call']
            t=(min if first else max)(F(n['onset_q']) for n in ns)
            return frozenset(n['midi'] for n in ns if F(n['onset_q'])==t),t
        own_right,_=boundary_signature(original[i],False)
        own_left,_=boundary_signature(original[i],True)
        inclusive=True
        after_bound=F(events[-1]['onset_q']) if events else F(0)
        before_bound=F(events[0]['onset_q']) if events else F(0)
        if following:
            other,t=boundary_signature(following,True)
            after_bound=t if other==own_right else F(following['start_q'])
            inclusive=other==own_right
        if preceding:
            other,t=boundary_signature(preceding,False)
            before_bound=t if other==own_left else F(preceding['end_q'])
        extend(region,True,after_bound,inclusive)
        extend(region,False,before_bound)
    phrases=_merge(phrases)
    # Tied destinations lengthen existing notes, never supply another attack.
    # Clip at the next established region to keep the phrase partition disjoint.
    for i,r in enumerate(phrases):
        bound=F(phrases[i+1]['start_q']) if i+1<len(phrases) else None
        for chain in sustain_chains:
            if chain['origin'] not in r['members']:continue
            for ident in chain['members'][1:]:
                if ident not in byid:continue
                n=byid[ident]
                if bound is not None and _end(n)>bound:continue
                r['members'].add(ident)
                r['end_q']=str(max(F(r['end_q']),_end(n)))
    seed_map={s['id']:s for s in seeds}
    for r in phrases:
        sources=[seed_map[i] for i in r['seed_ids']]
        lo=min(F(s['start_q']) for s in sources);hi=max(F(s['end_q']) for s in sources)
        before=F(r['start_q'])<lo;after=F(r['end_q'])>hi
        original_groups=[o for o in original if set(o['seed_ids']) & set(r['seed_ids'])]
        r['direction']='combined' if len(original_groups)>1 else 'both' if before and after else 'before' if before else 'after' if after else 'unchanged'
        r['original_bounds']=[dict(seed_ids=o['seed_ids'],start_q=o['start_q'],end_q=o['end_q']) for o in original_groups]
        r['start_bar']=min(byid[i]['bar'] for i in r['members'])
        r['end_bar']=max(byid[i]['bar'] for i in r['members'])
        r['cycles'].sort(key=lambda c:(F(c['call_start_q']),F(c['return_q'])))
        r['members']=sorted(r['members'])
        assert F(r['start_q'])<=lo and F(r['end_q'])>=hi
        assert all(set(s['members'])<=set(r['members']) for s in sources)
    assert sorted(i for r in phrases for i in r['seed_ids'])==sorted(seed_map)
    assert all(F(a['end_q'])<=F(b['start_q']) for a,b in zip(phrases,phrases[1:]))
    return phrases
