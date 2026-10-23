"""Research observations from existing exact source extraction; no key targets.

Preserves physical occurrence identity and original note/measure boundaries.
Only nominal written base pitches are observed, never acoustic bend execution.
"""
from collections import defaultdict
from fractions import Fraction as F
from tonal_context_observations import mask


def extract_cells(lower):
    if lower.get('schema')!='normalized-written-tie-context/4':raise ValueError('Existing complete written/tie extraction required')
    coverage=lower['source_coverage']
    if coverage['layout_warnings'] or coverage['timing_warnings']:raise ValueError('Source timing warnings retained; no guessed observation repair')
    parts={p['part_id']:p['fields'] for p in lower['tie_notation']['parts']}
    declarations={n['occurrence_ref']:n['fields'] for n in lower['tie_notation']['occurrences']}
    events=lower['events']
    if len({e['id'] for e in events})!=len(events):raise ValueError('Duplicate source occurrence')
    frames=lower['measure_geometry']['frames']
    if not frames:raise ValueError('No source measure geometry')
    start=F(frames[0]['start_q']);stop=max(F(f['start_q'])+F(f['span_q']) for f in frames)
    clocks={start,stop};begins=defaultdict(list);ends=defaultdict(list);witnesses=defaultdict(list)
    excluded=[];zero=[];domains={};unknown={}
    for f in frames:
        at=F(f['start_q']);clocks.add(at);witnesses[at].append('source_measure_boundary:'+f['id'])
    for e in events:
        ref=e['id'];instrument=parts[e['part_id']].get('instrumentId')
        domain='explicit_nonpitched' if type(instrument) is int and instrument==1024 else 'pitched' if type(instrument) is int and 0<=instrument<=127 else 'unknown'
        domains[ref]=domain
        if domain=='explicit_nonpitched':excluded.append(ref);continue
        a=F(e['onset_q']);duration=F(e['duration_q']);b=a+duration
        if duration<0 or not start<=a<=b<=stop:raise ValueError('Source occurrence outside verified written geometry')
        clocks.update((a,b));witnesses[a].append('written_onset:'+ref);witnesses[b].append('written_end:'+ref)
        if declarations[ref].get('tie'):witnesses[a].append('written_tie_declaration:'+ref)
        if duration==0:zero.append(ref);continue
        begins[a].append(e);ends[b].append(e)
        if domain!='pitched' or e['pitch'] is None or F(e['pitch']).denominator!=1:unknown[ref]='UNKNOWN_OR_NONINTEGER_WRITTEN_PITCH_DOMAIN'
    clocks=sorted(clocks);active={};rows=[];observations=[];supports={};boundary_events={};previous=None
    for i,(a,b) in enumerate(zip(clocks,clocks[1:])):
        for e in ends[a]:active.pop(e['id'],None)
        for e in begins[a]:active[e['id']]=e
        refs=sorted(active);unresolved=[ref for ref in refs if ref in unknown]
        pcs=sorted({int(F(active[ref]['pitch'])%12) for ref in refs if ref not in unknown})
        reasons=sorted({unknown[ref] for ref in unresolved})
        sequence=previous['sequence'] if not reasons and previous is not None and previous['end_q']==str(a) else i
        observation=dict(id=i,mask=mask(pcs),previous_mask=previous['mask'] if not reasons and previous is not None and sequence==previous['sequence'] else None,sequence=sequence,start_q=str(a),end_q=str(b))
        row=dict(observation=observation,active_note_refs=refs,unresolved_note_refs=unresolved,
                 boundary_events=sorted(witnesses[a]),quarantine_reasons=reasons)
        rows.append(row)
        if reasons:previous=None;continue
        observations.append(observation);supports[i]=refs;boundary_events[i]=row['boundary_events'];previous=observation
    return dict(schema='source-written-sonority-cells/1',span_q=[str(start),str(stop)],rows=rows,
                observations=observations,supports=supports,boundary_events=boundary_events,
                excluded_nonpitched_refs=excluded,zero_duration_refs=zero,
                source_occurrences=len(events),scope='Written base-pitch overlap only; no targets, picked-attack, key or acoustic inference')
