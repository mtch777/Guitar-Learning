"""Exact notated anchor/contrast relationships, not inferred musical intention."""
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def describe(events,anchor):
    if not events:return None
    start=F(events[0]['onset_q']);end=max(F(e['end_q']) for e in events)
    offsets=[F(e['onset_q'])-start for e in events]
    durations=[F(n['sustain_q']) for e in events for n in e['notes']]
    unit=next((q for q in offsets if q>0),min(durations))
    pitches=[e['pitches'] for e in events]
    rhythm=[(str(q),sorted(n['sustain_q'] for n in e['notes'])) for q,e in zip(offsets,events)]
    scaled=[(str(q/unit),sorted(str(F(n['sustain_q'])/unit) for n in e['notes'])) for q,e in zip(offsets,events)]
    intervals=[[p-min(anchor) for p in ps] for ps in pitches]
    to_each_anchor=[[[p-a for a in anchor] for p in ps] for ps in pitches]
    rhythm_form='monophonic' if all(len(ps)==1 for ps in pitches) else 'polyphonic' if all(len(ps)>1 for ps in pitches) else 'mixed'
    return dict(attack_groups=len(events),notes=sum(len(e['notes']) for e in events),
                start_q=str(start),end_q=str(end),span_q=str(end-start),
                onset_offsets_q=list(map(str,offsets)),ioi_q=[str(b-a) for a,b in zip(offsets,offsets[1:])],
                notated_duration_histogram=dict(Counter(n['duration_q'] for e in events for n in e['notes'])),
                tied_sustain_histogram=dict(Counter(n['sustain_q'] for e in events for n in e['notes'])),
                pitches=pitches,intervals_from_lowest_anchor=intervals,intervals_from_each_anchor=to_each_anchor,
                melodic_steps=[b[0]-a[0] for a,b in zip(pitches,pitches[1:])] if all(len(ps)==1 for ps in pitches) else None,
                register_span_semitones=max(p for ps in pitches for p in ps)-min(p for ps in pitches for p in ps),
                simultaneous_intervals=[[b-a for i,a in enumerate(ps) for b in ps[i+1:]] for ps in pitches],
                note_texture=rhythm_form,
                semitone_dyad_attacks=sum(len(ps)==2 and ps[1]-ps[0]==1 for ps in pitches),
                technique_counts=dict(Counter(k for e in events for n in e['notes'] for k in n['effects'])),
                pitch_signature=fingerprint(pitches),anchor_relative_signature=fingerprint(intervals),
                rhythm_signature=fingerprint(rhythm),scaled_rhythm_signature=fingerprint(scaled),rhythm_unit_q=str(unit))


def analyze_dialogue(track,region):
    anchor=region['anchor_pitches'];anchor_set=set(anchor)
    rows=track['rows'];lookup={n['occurrence']:n for n in rows}
    # Tied segments contribute duration, not extra attacks. Use existing exact
    # chains; avoid silently treating unresolved tie destinations as new attacks.
    chains={c['origin']:c for c in track.get('sustain_relationships',{}).get('chains',[])}
    section=next((s for s in track['sections'] if s['id']==region['section_start']),None)
    if section is None:raise ValueError('Missing source section')
    start=F(region['start_q']);stop=min(F(section['end_q']),F(region.get('scope_end_q',section['end_q'])))
    groups=defaultdict(list)
    for n in rows:
        q=F(n['onset_q'])
        if n['section_start']!=region['section_start'] or not start<=q<stop or n['tie_destination']:continue
        c=chains.get(n['occurrence']);end=F(c['end_q']) if c else q+F(n['duration_q'])
        groups[q].append(dict(occurrence=n['occurrence'],midi=n['midi'],string=n['string'],fret=n['fret'],voice=n['voice'],
                              duration_q=n['duration_q'],sustain_q=str(end-q),end_q=str(end),
                              effects=sorted(set(k for ident in (c['members'] if c else [n['occurrence']]) for k in lookup[ident]['effects'])),
                              tied_occurrences=c['members'] if c else [n['occurrence']]))
    events=[]
    for q,notes in sorted(groups.items()):
        pitches=sorted({n['midi'] for n in notes if n['midi'] is not None});ps=set(pitches)
        kind='unknown' if any(n['midi'] is None for n in notes) else ('call' if ps<=anchor_set else 'mixed' if ps&anchor_set else 'response')
        events.append(dict(onset_q=str(q),end_q=str(max(F(n['end_q']) for n in notes)),notes=notes,pitches=pitches,kind=kind,
                           bar=lookup[notes[0]['occurrence']]['bar'],bar_offset_q=lookup[notes[0]['occurrence']]['bar_offset_q']))
    runs=[]
    for e in events:
        if not runs or runs[-1]['kind']!=e['kind']:runs.append(dict(kind=e['kind'],events=[]))
        runs[-1]['events'].append(e)
    cycles=[]
    for i,run in enumerate(runs[:-1]):
        if run['kind']!='call' or runs[i+1]['kind']!='response':continue
        call=describe(run['events'],anchor);response=describe(runs[i+1]['events'],anchor)
        next_run=runs[i+2] if i+2<len(runs) else None
        closed=bool(next_run and next_run['kind']=='call')
        first_response=F(response['start_q']);call_end=F(call['end_q'])
        next_call=F(next_run['events'][0]['onset_q']) if closed else None
        response_end=F(response['end_q'])
        cycles.append(dict(call=call,response=response,
                           response_to_call_span_ratio=str(F(response['span_q'])/F(call['span_q'])),
                           anchor_return_period_q=str(next_call-F(call['start_q'])) if closed else None,
                           response_last_intervals_to_anchor=[min(anchor)-p for p in response['pitches'][-1]],
                           call_to_response_gap_q=str(max(F(0),first_response-call_end)),
                           call_sustain_into_response_q=str(max(F(0),call_end-first_response)),
                           response_to_next_call_gap_q=str(max(F(0),next_call-response_end)) if closed else None,
                           response_sustain_into_next_call_q=str(max(F(0),response_end-next_call)) if closed else None,
                           closed_by_anchor_return=closed,right_censored=not closed,
                           call_members=[n['occurrence'] for e in run['events'] for n in e['notes']],
                           response_members=[n['occurrence'] for e in runs[i+1]['events'] for n in e['notes']]))
    comparisons=[]
    for a,b in zip(cycles,cycles[1:]):
        # Mixed/unknown intervening events break adjacency; retain that status.
        comparisons.append(dict(adjacent_without_interruption=F(a['response']['end_q'])<=F(b['call']['start_q']) and
                                not any(F(a['response']['start_q'])<F(e['onset_q'])<F(b['call']['start_q']) and e['kind'] in ('mixed','unknown') for e in events),
                                call_same_pitch=a['call']['pitch_signature']==b['call']['pitch_signature'],
                                call_same_rhythm=a['call']['rhythm_signature']==b['call']['rhythm_signature'],
                                response_same_pitch=a['response']['pitch_signature']==b['response']['pitch_signature'],
                                response_same_rhythm=a['response']['rhythm_signature']==b['response']['rhythm_signature'],
                                response_same_scaled_rhythm=a['response']['scaled_rhythm_signature']==b['response']['scaled_rhythm_signature'],
                                response_time_scale=str(F(b['response']['rhythm_unit_q'])/F(a['response']['rhythm_unit_q']))))
    eligible=[p for p in comparisons if p['adjacent_without_interruption']]
    total_pairs=len(eligible)
    consistency={k:dict(equal=sum(p[k] for p in eligible),compared=total_pairs) for k in ('call_same_pitch','call_same_rhythm','response_same_pitch','response_same_rhythm','response_same_scaled_rhythm')}
    consistency['same_call_changed_response']=dict(count=sum(p['call_same_pitch'] and p['call_same_rhythm'] and not(p['response_same_pitch'] and p['response_same_rhythm']) for p in eligible),compared=total_pairs)
    families=defaultdict(list)
    for i,cycle in enumerate(cycles):
        signature=fingerprint([cycle['call']['anchor_relative_signature'],cycle['call']['rhythm_signature']])
        families[signature].append((i,cycle))
    conditional=[]
    for signature,members in families.items():
        answers=Counter(fingerprint([c['response']['anchor_relative_signature'],c['response']['rhythm_signature']]) for i,c in members)
        conditional.append(dict(call_signature=signature,cycles=[i for i,c in members],observed=len(members),
                                distinct_responses=len(answers),response_frequencies=dict(answers),
                                response_textures=dict(Counter(c['response']['note_texture'] for i,c in members))))
    return dict(anchor_pitches=anchor,section_start=region['section_start'],scope_start_q=str(start),scope_end_q=str(stop),
                events=events,cycles=cycles,comparisons=comparisons,consistency=consistency,call_response_families=conditional,
                event_kind_counts=dict(Counter(e['kind'] for e in events)),
                limitations=['Call means an anchor-only attack group; response means a subsequent non-anchor group. These are operational labels, not inferred intent.',
                             'Mixed/unknown attacks retained separately; polyphony is not projected to an invented melody.',
                             'Scope continues to source-section end; final responses are censored, not asserted phrase endings.',
                             'Written pitches and durations, not performed expression; unmarked let-ring extension is unknown.'])
