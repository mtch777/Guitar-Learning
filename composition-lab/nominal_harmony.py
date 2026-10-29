"""Checked written-overlap relationships; existing owners retain every pitch.

Complementary populations are fitted BEFORE querying their excluded focal note.
These are conditional written roles, never inferred intent or acoustic harmony.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import json
import musical_tier2 as music
from harmonic_evidence import context as owned_context
from chord_degree_relations import note_role, pitch_from_degree

SCOPES=('full_focal_part','focal_part_minus_focal','other_parts_only','ensemble_minus_focal')
SEMANTICS='Half-open written intervals; exact conditional vocabulary fits; no preferred chord, key, mode, acoustic sustain or intended note function'


def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)


def prepare(upper):
    """Geometry is a checked projection of already owned source declarations."""
    from source_tie_tier1 import extract_documents
    from contextual_note_roles import source_refusals
    c=owned_context(upper);lower=extract_documents(c['documents']);events={e['id']:e for e in lower['events']}
    from source_semantics import layout, rests
    solved=music.realize(c['core'])
    if encoded(solved['events'])!=encoded(lower['events']):raise ValueError('Owned pitches and source temporal projection disagree')
    parts=[c['documents'][k] for k in sorted(c['documents']) if k.startswith('track-')]
    headers,_=layout(parts);rest_rows=[];rest_warnings=[]
    for part in parts:
        rows,warnings=rests(part,headers,include_provenance=True)
        rest_rows.extend(dict(id=f"rest:{part['partId']}:{i}",part_id=part['partId'],**row) for i,row in enumerate(rows))
        rest_warnings.extend(dict(part_id=part['partId'],**w) for w in warnings)
    raw_refs=[];song=c['documents']['metadata.json']['songId']
    for part in parts:
        for mi,m in enumerate(part.get('measures',[]),1):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    raw_refs.extend(f"event:{song}:{part['partId']}:{mi}:{vi}:{bi}:{ni}" for ni,n in enumerate(b.get('notes',[])) if not n.get('rest'))
    try:geometry=music.geometry_relation(source=lower['measure_geometry'])['parameters'];geometry_error=None
    except ValueError as exc:geometry=None;geometry_error=str(exc)
    flags={ref:source_refusals(c['documents'],events,[ref]) for ref in events}
    return dict(**c,lower=lower,events=events,geometry=geometry,geometry_error=geometry_error,rests=rest_rows,
                rest_warnings=rest_warnings,raw_refs=raw_refs,written_pitch_qualifications=flags)


def coordinate(pitch,hypothesis):
    r=note_role(pitch,hypothesis)
    out=dict(status=r['status'],degree_relationships=r['degree_relationships'])
    if 'root_interval_relationship' in r:
        delta=r['root_interval_relationship']['interval'];out['root_interval']=delta
        if music.relation(anchor=hypothesis['root_pc'],interval=delta)['pitch']!=str(F(pitch)):raise ValueError('Root interval inverse differs')
        if any(pitch_from_degree(hypothesis['root_pc'],hypothesis['kind'],d)!=str(F(pitch)) for d in out['degree_relationships']):raise ValueError('Degree inverse differs')
    return out


@lru_cache(maxsize=4096)
def _fits(pcs):
    # Exact-fit identities depend only on this explicitly declared PC set.
    # Immutable cache entries cannot become a second pitch owner or be poisoned.
    return tuple((h['root_pc'],h['kind'],tuple(h['formula'])) for h in music.context(pcs)['chord_candidates'])


def focal_coordinate(domain,pitch,hypothesis):
    status=('NOT_APPLICABLE_NONPITCHED_DOMAIN' if domain=='nonpitched' else
            'UNKNOWN_INSTRUMENT_DOMAIN_ROLE' if domain=='unknown' else
            'OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE' if pitch is not None and F(pitch).denominator!=1 else None)
    return dict(status=status,degree_relationships=[]) if status else coordinate(pitch,hypothesis)


def population(events,rows,refs,ident):
    """One exact support population, shared by focal and edited-set queries."""
    key=tuple(sorted(refs));included=[r for r in key if rows[r]['domain']!='nonpitched']
    excluded=[dict(occurrence_ref=r,reason='EXPLICIT_NONPITCHED_INSTRUMENT') for r in key if rows[r]['domain']=='nonpitched']
    reasons=sorted({v for r in included for v in rows[r]['qualifications']})
    values=[events[r]['pitch'] for r in included if events[r]['pitch'] is not None]
    if len({F(v)%12 for v in values})<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
    hypotheses=() if reasons else _fits(tuple(sorted({int(F(v)%12) for v in values})))
    return dict(id=ident,support_refs=list(key),included_refs=included,excluded_refs=excluded,refusals=reasons,
                hypotheses=[dict(root_pc=root,kind=kind,formula=list(formula)) for root,kind,formula in hypotheses])


def build(c):
    events=c['events'];parts=sorted(int(p) for p in c['instruments']);geometry=c['geometry']
    rows={};unlocated=sorted(set(c['raw_refs'])-set(events))
    for ref,e in events.items():
        program=c['instruments'].get(str(e['part_id']));p=e['pitch'];d=F(e['duration_q'])
        domain='pitched' if type(program)is int and 0<=program<=127 else 'nonpitched' if type(program)is int and program==1024 else 'unknown'
        issues=[]
        if domain=='unknown':issues.append('UNKNOWN_INSTRUMENT_DOMAIN')
        if p is None:issues.append('UNKNOWN_WRITTEN_PITCH')
        elif F(p).denominator!=1:issues.append('NONINTEGER_WRITTEN_PITCH')
        if d<=0:issues.append('POINT_OR_NONPOSITIVE_DURATION')
        rows[ref]=dict(occurrence_ref=ref,domain=domain,qualifications=issues,written_pitch_qualifications=c['written_pitch_qualifications'][ref])
    out=dict(schema='nominal-harmonic-populations/1',semantics=SEMANTICS,
             pitch_authority='Existing musical owners; this view contains references and checked conditional coordinates',
             theory=deepcopy(music.THEORY_PROVENANCE),geometry_status='AVAILABLE' if geometry else 'UNAVAILABLE',geometry_error=c['geometry_error'],
             occurrence_inventory=[rows[r] for r in sorted(rows)],unlocated_occurrence_refs=unlocated,
             rest_inventory=c['rests'],rest_warnings=c['rest_warnings'],frames=[],cells=[],occurrence_paths=[],
             crossing_occurrence_refs=[],unscoped_positive_occurrence_refs=[])
    if not geometry:
        out['unscoped_positive_occurrence_refs']=sorted(r for r,e in events.items() if F(e['duration_q'])>0)
        out['counts']=counts(out,len(c['raw_refs']));return out
    frames=geometry['frames'];by_bar={f['ordinal']:f for f in frames}
    available={p['part_id']:set(p['frame_refs']) for p in geometry['parts']}
    spans=music.written_spans(c['core']['coattacks']);span_by_bar=defaultdict(list)
    for s in spans:span_by_bar[s['bar']].append(s)
    crossing={}
    for ref,e in events.items():
        frame=by_bar.get(e['bar']);a=F(e['onset_q']);b=a+F(e['duration_q'])
        if frame is None or a<F(frame['start_q']) or b>F(frame['start_q'])+F(frame['duration_q']):crossing[ref]=(a,b,e['part_id'])
    clock_warnings=[w for kind in ('layout_warnings','timing_warnings') for w in c['lower']['source_coverage'][kind]]
    paths=defaultdict(list)
    for frame in frames:
        start=F(frame['start_q']);stop=start+F(frame['duration_q']);bar=frame['ordinal']
        frame_parts=[p for p in parts if frame['id'] in available.get(p,set())]
        frame_spans=span_by_bar[bar]
        overlays=[r for r,(a,b,_) in crossing.items() if a<stop and b>start]
        rest_rows=[r for r in c['rests'] if F(r['onset_q'])<stop and F(r['onset_q'])+F(r['duration_q'])>start]
        points=[r for r,e in events.items() if e['bar']==bar and F(e['duration_q'])==0]
        boundaries={start,stop}
        for s in frame_spans:
            boundaries.update(t for t in (F(s['start_q']),F(s['end_q'])) if start<t<stop)
        for r in rest_rows:
            boundaries.update(t for t in (F(r['onset_q']),F(r['onset_q'])+F(r['duration_q'])) if start<t<stop)
        for ref in overlays:
            boundaries.update(t for t in crossing[ref][:2] if start<t<stop)
        boundaries.update(F(events[r]['onset_q']) for r in points if start<F(events[r]['onset_q'])<stop)
        out['frames'].append(dict(frame_ref=frame['id'],ordinal=bar,start_q=str(start),end_q=str(stop),
                                 observed_part_ids=frame_parts,missing_part_ids=[p for p in parts if p not in frame_parts],point_refs=sorted(points)))
        for a,b in zip(sorted(boundaries),sorted(boundaries)[1:]):
            cell_id=f'cell:{len(out["cells"])}'
            covering=[s for s in frame_spans if F(s['start_q'])<=a and F(s['end_q'])>=b]
            if len(covering)>1:raise ValueError('Overlapping source-bar written spans')
            active=sorted(covering[0]['ensemble_context']['occurrence_refs']) if covering else []
            active_rests=sorted(r['id'] for r in rest_rows if F(r['onset_q'])<=a and F(r['onset_q'])+F(r['duration_q'])>=b)
            crossed=sorted(r for r in overlays if crossing[r][0]<b and crossing[r][1]>a)
            issues=defaultdict(set)
            for p in parts:
                if p not in frame_parts:issues[p].add('MISSING_SOURCE_PART_FRAME')
            for w in clock_warnings:
                if w['bar']==bar:
                    for p in ([w['part_id']] if 'part_id' in w else parts):issues[p].add('UNCERTAIN_SOURCE_CLOCK')
            for ref in crossed:issues[events[ref]['part_id']].add('CROSSING_SOURCE_INTERVAL')
            for w in c['rest_warnings']:
                if w['bar']==bar:issues[w['part_id']].add('CONFLICTING_SOURCE_REST')
            for ref in active:
                e=events[ref]
                if any(r['id'] in active_rests and r['part_id']==e['part_id'] and r['voice']==e['voice'] for r in rest_rows):issues[e['part_id']].add('NOTE_REST_OVERLAP')
            cell=dict(id=cell_id,frame_ref=frame['id'],start_q=str(a),end_q=str(b),active_refs=active,
                      starting_refs=[r for r in active if F(events[r]['onset_q'])==a],continuing_refs=[r for r in active if F(events[r]['onset_q'])<a],
                      crossing_refs=crossed,rest_refs=active_rests,part_refusals=[dict(part_id=p,reasons=sorted(v)) for p,v in sorted(issues.items()) if v],
                      populations=[],focal_contexts=[])
            populations={}
            def cell_population(refs):
                key=tuple(sorted(refs))
                if key in populations:return populations[key]
                p=population(events,rows,key,f'{cell_id}:population:{len(populations)}')
                populations[key]=p;cell['populations'].append(p);return p
            for ref in active:
                e=events[ref];part=e['part_id'];own=[r for r in active if events[r]['part_id']==part]
                others=[p for p in parts if p!=part]
                queries=((own,[part]),([r for r in own if r!=ref],[part]),([r for r in active if events[r]['part_id']!=part],others),([r for r in active if r!=ref],parts))
                q=dict(occurrence_ref=ref,scopes={});paths[ref].append(cell_id)
                for scope,(refs,scope_parts) in zip(SCOPES,queries):
                    pop=cell_population(refs);refusals=sorted({v for p in scope_parts for v in issues[p]})
                    focal_refusals=sorted(issues[part])
                    roles=[] if refusals or focal_refusals else [focal_coordinate(rows[ref]['domain'],e['pitch'],h) for h in pop['hypotheses']]
                    q['scopes'][scope]=dict(population_ref=pop['id'],part_ids=scope_parts,scope_refusals=refusals,
                        focal_refusals=focal_refusals,direct_focal_support=ref in pop['included_refs'],role_results=roles)
                cell['focal_contexts'].append(q)
            out['cells'].append(cell)
    out['crossing_occurrence_refs']=sorted(crossing)
    out['unscoped_positive_occurrence_refs']=sorted(r for r,e in events.items() if F(e['duration_q'])>0 and r not in paths)
    out['occurrence_paths']=[dict(occurrence_ref=r,cell_refs=ids) for r,ids in sorted(paths.items())]
    out['counts']=counts(out,len(c['raw_refs']));return out


def counts(view,raw_count):
    cells=view['cells'];pops=[p for c in cells for p in c['populations']]
    roles=[r for c in cells for q in c['focal_contexts'] for s in q['scopes'].values() for r in s['role_results']]
    inv=view['occurrence_inventory']
    return dict(raw_note_occurrences=raw_count,located_occurrences=len(inv),unlocated_occurrences=len(view['unlocated_occurrence_refs']),
        positive_duration_occurrences=sum('POINT_OR_NONPOSITIVE_DURATION' not in r['qualifications'] for r in inv),
        point_or_nonpositive_occurrences=sum('POINT_OR_NONPOSITIVE_DURATION' in r['qualifications'] for r in inv),
        pitched_occurrences=sum(r['domain']=='pitched' for r in inv),nonpitched_occurrences=sum(r['domain']=='nonpitched' for r in inv),
        unknown_domain_occurrences=sum(r['domain']=='unknown' for r in inv),unknown_pitch_occurrences=sum('UNKNOWN_WRITTEN_PITCH' in r['qualifications'] for r in inv),
        pitched_unknown_pitch_occurrences=sum(r['domain']=='pitched' and 'UNKNOWN_WRITTEN_PITCH' in r['qualifications'] for r in inv),
        fractional_pitch_occurrences=sum('NONINTEGER_WRITTEN_PITCH' in r['qualifications'] for r in inv),crossing_occurrences=len(view['crossing_occurrence_refs']),
        unscoped_positive_occurrences=len(view['unscoped_positive_occurrence_refs']),rest_occurrences=len(view['rest_inventory']),
        nonpositive_rest_occurrences=sum(F(r['duration_q'])<=0 for r in view['rest_inventory']),quarantined_cells=sum(bool(c['part_refusals']) for c in cells),
        frames=len(view['frames']),cells=len(cells),empty_note_cells=sum(not c['active_refs'] for c in cells),
        active_note_cell_incidences=sum(len(c['active_refs']) for c in cells),populations=len(pops),
        populations_with_fits=sum(bool(p['hypotheses']) for p in pops),hypotheses=sum(len(p['hypotheses']) for p in pops),
        conditional_roles=len(roles),nonmember_roles=sum(r['status']=='TEMPLATE_NONMEMBER' for r in roles),
        unknown_roles=sum(r['status']=='UNKNOWN_WRITTEN_PITCH_ROLE' for r in roles),
        nonpitched_roles=sum(r['status']=='NOT_APPLICABLE_NONPITCHED_DOMAIN' for r in roles),
        unknown_domain_roles=sum(r['status']=='UNKNOWN_INSTRUMENT_DOMAIN_ROLE' for r in roles),
        unsupported_pitch_roles=sum(r['status']=='OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE' for r in roles),
        degree_coordinates=sum(len(r['degree_relationships']) for r in roles))


def analyze(upper):return build(prepare(upper))


def edited_set_context(c,view,after_events,changed_refs):
    """Query unchanged support; no edited note certifies another edited note."""
    changed=set(changed_refs);events=c['events'];rows={r['occurrence_ref']:r for r in view['occurrence_inventory']}
    if not changed<=set(events) or not changed<=set(after_events):raise ValueError('Unknown edited occurrence')
    cells=[];parts=sorted(int(p) for p in c['instruments'])
    for cell in view['cells']:
        active=sorted(changed.intersection(cell['active_refs']))
        if not active:continue
        issues={p['part_id']:p['reasons'] for p in cell['part_refusals']}
        for part in sorted({events[r]['part_id'] for r in active}):
            for scope,scope_parts in (('focal_part_minus_edited',[part]),('ensemble_minus_edited',parts)):
                support=[r for r in cell['active_refs'] if r not in changed and events[r]['part_id'] in scope_parts]
                pop=population(events,rows,support,f"{cell['id']}:{part}:{scope}")
                refusals=sorted({v for p in scope_parts for v in issues.get(p,[])})
                focal_refusals=issues.get(part,[]);queries=[]
                for ref in active:
                    if events[ref]['part_id']!=part:continue
                    roles=[] if refusals or focal_refusals else [dict(hypothesis=h,
                        before=focal_coordinate(rows[ref]['domain'],events[ref]['pitch'],h),
                        after=focal_coordinate(rows[ref]['domain'],after_events[ref]['pitch'],h)) for h in pop['hypotheses']]
                    queries.append(dict(occurrence_ref=ref,role_changes=roles))
                cells.append(dict(cell_ref=cell['id'],start_q=cell['start_q'],end_q=cell['end_q'],scope=scope,
                    part_ids=scope_parts,excluded_edited_refs=sorted(changed.intersection(cell['active_refs'])),
                    population=pop,scope_refusals=refusals,focal_refusals=focal_refusals,queries=queries))
    return dict(schema='edited-set-nominal-context/1',changed_refs=sorted(changed),cells=cells,
        unscoped_edited_refs=sorted(changed.intersection(view['unscoped_positive_occurrence_refs'])),
        crossing_edited_refs=sorted(changed.intersection(view['crossing_occurrence_refs'])),
        semantics='Conditional roles against unchanged written support; unknown/no fit remains unresolved, not a musical intent or role lock')


def validate(upper,view):
    expected=analyze(upper)
    if encoded(view)!=encoded(expected):raise ValueError('Stale, incomplete or forged nominal harmonic relationships')
    return expected
