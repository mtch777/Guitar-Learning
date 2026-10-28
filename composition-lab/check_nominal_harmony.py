"""Independent raw interval/native-theory oracle for nominal harmonic context.

Shares accepted source clock/rest/declaration primitives, never producer span,
population, role or counting functions. No nominal_harmony imports.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
import json
import hashlib
from source_fact_tier1 import project_documents,validate as validate_source
from source_tie_tier1 import extract_documents
from contextual_note_roles import source_refusals
from check_harmonic_evidence import native_forms
from musical_tier2 import geometry_relation

SCOPES=('full_focal_part','focal_part_minus_focal','other_parts_only','ensemble_minus_focal')
SEMANTICS='Half-open written intervals; exact conditional vocabulary fits; no preferred chord, key, mode, acoustic sustain or intended note function'
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)

def _native_provenance():
    from music21 import __version__
    if __version__!='9.9.2':raise ValueError('Pinned native theory required')
    forms=tuple((kind,tuple(formula))for kind,formula,_ in native_forms())
    return dict(source='music21.harmony.CHORD_TYPES',version=__version__,
        forms_sha256=hashlib.sha256(json.dumps(forms,separators=(',',':')).encode()).hexdigest(),
        vocabulary_scope='Published Western chord-kind definitions; not exhaustive musical harmony',
        candidate_rule='Exact observed pitch-class set; all twelve roots; singleton excluded')

def _rest_addresses(part,records):
    """Audit NEW provenance without trusting the helper's added pointers.

    Clock/duration semantics are intentionally shared. Which original nodes
    support each emitted rest is independently enumerated from raw containers.
    """
    expected=[]
    for mi,measure in enumerate(part.get('measures',[])):
        actual=measure.get('voices',[]);voices=actual or ([{}]if measure.get('rest')else[])
        for vi,voice in enumerate(voices):
            beats=voice.get('beats',[])
            indices=[None]if not beats and(voice.get('rest')or measure.get('rest'))else[]
            if beats:
                for bi,beat in enumerate(beats):
                    if beat.get('graceNote'):continue
                    if not beat.get('duration'):break
                    if not any(not n.get('rest')for n in beat.get('notes',[])):indices.append(bi)
            for bi in indices:
                mp=f'/measures/{mi}';vp=f'{mp}/voices/{vi}'if vi<len(actual)else None
                bp=f'{vp}/beats/{bi}'if bi is not None else None
                beat=beats[bi]if bi is not None else{};flags=[]
                if measure.get('rest'):flags.append(mp+'/rest')
                if vp is not None and voice.get('rest'):flags.append(vp+'/rest')
                if bp is not None:
                    if beat.get('rest'):flags.append(bp+'/rest')
                    flags.extend(f'{bp}/notes/{ni}/rest'for ni,n in enumerate(beat.get('notes',[]))if n.get('rest'))
                expected.append((mi+1,vi,dict(source_measure_ref=mp,source_voice_ref=vp,source_beat_ref=bp,
                    rest_flag_refs=flags,evidence_kind='literal_rest_flags'if flags else'structural_empty_beat',structural_ref=bp if bp is not None else(vp or mp))))
    if len(records)!=len(expected):raise ValueError('Rest provenance source denominator differs')
    for row,(bar,voice,provenance)in zip(records,expected):
        if row['bar']!=bar or row['voice']!=voice or enc(row.get('provenance'))!=enc(provenance):raise ValueError('Rest provenance does not name its actual source nodes')

@lru_cache(maxsize=4096)
def _fits(pcs):
    return [dict(root_pc=root,kind=kind,formula=formula) for kind,formula,_ in native_forms()
            if len(formula)>1 for root in range(12) if {(root+x)%12 for x in formula}==set(pcs)]

def _role(pitch,h):
    if pitch is None or F(pitch).denominator!=1:
        return dict(status='UNKNOWN_WRITTEN_PITCH_ROLE',degree_relationships=[])
    p=F(pitch);root=h['root_pc'];defs=next(d for k,_,d in native_forms()if k==h['kind'])
    result=[dict(d,relative_octaves=int((p-root-d['theoretical_semitones'])/12))for d in defs if(p-root-d['theoretical_semitones'])%12==0]
    return dict(status='TEMPLATE_CHORD_TONE'if result else'TEMPLATE_NONMEMBER',degree_relationships=result,root_interval=str(p-root))

def _focal_role(pitch,domain,h):
    if domain=='nonpitched':status='NOT_APPLICABLE_NONPITCHED_DOMAIN'
    elif domain=='unknown':status='UNKNOWN_INSTRUMENT_DOMAIN_ROLE'
    elif pitch is not None and F(pitch).denominator!=1:status='OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE'
    else:return _role(pitch,h)
    return dict(status=status,degree_relationships=[])

def _counts(v,raw):
    populations=[p for c in v['cells']for p in c['populations']]
    roles=[r for c in v['cells']for q in c['focal_contexts']for s in q['scopes'].values()for r in s['role_results']]
    return dict(raw_note_occurrences=raw,located_occurrences=len(v['occurrence_inventory']),unlocated_occurrences=len(v['unlocated_occurrence_refs']),
        frames=len(v['frames']),cells=len(v['cells']),empty_note_cells=sum(not c['active_refs']for c in v['cells']),
        active_note_cell_incidences=sum(len(c['active_refs'])for c in v['cells']),populations=len(populations),
        populations_with_fits=sum(bool(p['hypotheses'])for p in populations),hypotheses=sum(len(p['hypotheses'])for p in populations),
        conditional_roles=len(roles),nonmember_roles=sum(r['status']=='TEMPLATE_NONMEMBER'for r in roles),
        unknown_roles=sum(r['status']=='UNKNOWN_WRITTEN_PITCH_ROLE'for r in roles),degree_coordinates=sum(len(r['degree_relationships'])for r in roles),
        nonpitched_roles=sum(r['status']=='NOT_APPLICABLE_NONPITCHED_DOMAIN'for r in roles),
        unknown_domain_roles=sum(r['status']=='UNKNOWN_INSTRUMENT_DOMAIN_ROLE'for r in roles),
        unsupported_pitch_roles=sum(r['status']=='OUTSIDE_SUPPORTED_PITCH_CLASS_DOMAIN_ROLE'for r in roles),
        positive_duration_occurrences=sum('POINT_OR_NONPOSITIVE_DURATION'not in r['qualifications']for r in v['occurrence_inventory']),
        point_or_nonpositive_occurrences=sum('POINT_OR_NONPOSITIVE_DURATION'in r['qualifications']for r in v['occurrence_inventory']),
        pitched_occurrences=sum(r['domain']=='pitched'for r in v['occurrence_inventory']),
        nonpitched_occurrences=sum(r['domain']=='nonpitched'for r in v['occurrence_inventory']),
        unknown_domain_occurrences=sum(r['domain']=='unknown'for r in v['occurrence_inventory']),
        unknown_pitch_occurrences=sum('UNKNOWN_WRITTEN_PITCH'in r['qualifications']for r in v['occurrence_inventory']),
        pitched_unknown_pitch_occurrences=sum(r['domain']=='pitched'and'UNKNOWN_WRITTEN_PITCH'in r['qualifications']for r in v['occurrence_inventory']),
        fractional_pitch_occurrences=sum('NONINTEGER_WRITTEN_PITCH'in r['qualifications']for r in v['occurrence_inventory']),
        crossing_occurrences=len(v['crossing_occurrence_refs']),unscoped_positive_occurrences=len(v['unscoped_positive_occurrence_refs']),
        rest_occurrences=len(v['rest_inventory']),nonpositive_rest_occurrences=sum(F(r['duration_q'])<=0 for r in v['rest_inventory']),
        quarantined_cells=sum(bool(c['part_refusals'])for c in v['cells']))

def expected(tier1):
    """Reconstruct independently expected fields using literal source intervals."""
    validate_source(tier1);docs=project_documents(tier1);lower=extract_documents(docs)
    from source_semantics import layout,rests
    parts=[docs[n]for n in sorted(docs)if n.startswith('track-')]
    part_ids=sorted(p['partId']for p in parts);program={p['partId']:p.get('instrumentId')for p in parts}
    headers,_=layout(parts);rest_rows=[];rest_warnings=[]
    for p in parts:
        rr,ww=rests(p,headers,include_provenance=True)
        _rest_addresses(p,rr)
        rest_rows.extend(dict(id=f"rest:{p['partId']}:{i}",part_id=p['partId'],**r)for i,r in enumerate(rr))
        rest_warnings.extend(dict(part_id=p['partId'],**w)for w in ww)
    events={e['id']:e for e in lower['events']};song=docs['metadata.json']['songId'];raw=[]
    for p in parts:
        for mi,m in enumerate(p.get('measures',[]),1):
            for vi,v in enumerate(m.get('voices',[])):
                for bi,b in enumerate(v.get('beats',[])):
                    raw.extend(f"event:{song}:{p['partId']}:{mi}:{vi}:{bi}:{ni}"for ni,n in enumerate(b.get('notes',[]))if not n.get('rest'))
    try:geo=geometry_relation(source=lower['measure_geometry'])['parameters'];error=None
    except ValueError as exc:geo=None;error=str(exc)
    inventory={}
    for ref,e in events.items():
        inst=program[e['part_id']];domain='pitched'if type(inst)is int and 0<=inst<=127 else'nonpitched'if type(inst)is int and inst==1024 else'unknown';reasons=[]
        if domain=='unknown':reasons.append('UNKNOWN_INSTRUMENT_DOMAIN')
        if e['pitch']is None:reasons.append('UNKNOWN_WRITTEN_PITCH')
        elif F(e['pitch']).denominator!=1:reasons.append('NONINTEGER_WRITTEN_PITCH')
        if F(e['duration_q'])<=0:reasons.append('POINT_OR_NONPOSITIVE_DURATION')
        inventory[ref]=dict(occurrence_ref=ref,domain=domain,qualifications=reasons,written_pitch_qualifications=source_refusals(docs,events,[ref]))
    result=dict(schema='nominal-harmonic-populations/1',semantics=SEMANTICS,
        pitch_authority='Existing musical owners; this view contains references and checked conditional coordinates',theory=_native_provenance(),
        geometry_status='AVAILABLE'if geo else'UNAVAILABLE',geometry_error=error,occurrence_inventory=[inventory[r]for r in sorted(inventory)],
        unlocated_occurrence_refs=sorted(set(raw)-set(events)),rest_inventory=rest_rows,rest_warnings=rest_warnings,frames=[],cells=[],occurrence_paths=[],
        crossing_occurrence_refs=[],unscoped_positive_occurrence_refs=[])
    if not geo:
        result['unscoped_positive_occurrence_refs']=sorted(r for r,e in events.items()if F(e['duration_q'])>0)
        result['counts']=_counts(result,len(raw));return result
    frame_by_bar={f['ordinal']:f for f in geo['frames']};membership={p['part_id']:set(p['frame_refs'])for p in geo['parts']}
    intervals={r:(F(e['onset_q']),F(e['onset_q'])+F(e['duration_q']))for r,e in events.items()}
    crosses=set()
    for ref,e in events.items():
        f=frame_by_bar.get(e['bar']);a,b=intervals[ref]
        if f is None or a<F(f['start_q'])or b>F(f['start_q'])+F(f['duration_q']):crosses.add(ref)
    clock=[w for kind in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][kind]];paths=defaultdict(list)
    for frame in geo['frames']:
        lo=F(frame['start_q']);hi=lo+F(frame['duration_q']);bar=frame['ordinal']
        present=[p for p in part_ids if frame['id']in membership.get(p,set())]
        own=[r for r,e in events.items()if e['bar']==bar and intervals[r][1]>intervals[r][0]]
        over=[r for r in crosses if intervals[r][0]<hi and intervals[r][1]>lo]
        rests_here=[r for r in rest_rows if F(r['onset_q'])<hi and F(r['onset_q'])+F(r['duration_q'])>lo]
        points=sorted(r for r,e in events.items()if e['bar']==bar and F(e['duration_q'])==0)
        cuts={lo,hi}
        for ref in set(own)|set(over):cuts.update(x for x in intervals[ref]if lo<x<hi)
        for r in rests_here:cuts.update(x for x in (F(r['onset_q']),F(r['onset_q'])+F(r['duration_q']))if lo<x<hi)
        cuts.update(F(events[r]['onset_q'])for r in points if lo<F(events[r]['onset_q'])<hi)
        result['frames'].append(dict(frame_ref=frame['id'],ordinal=bar,start_q=str(lo),end_q=str(hi),observed_part_ids=present,missing_part_ids=[p for p in part_ids if p not in present],point_refs=points))
        boundaries=sorted(cuts)
        for a,b in zip(boundaries,boundaries[1:]):
            ident=f"cell:{len(result['cells'])}";active=sorted(r for r in own if intervals[r][0]<=a and intervals[r][1]>=b)
            active_rest=sorted(r['id']for r in rests_here if F(r['onset_q'])<=a and F(r['onset_q'])+F(r['duration_q'])>=b)
            crossing=sorted(r for r in over if intervals[r][0]<b and intervals[r][1]>a);bad=defaultdict(set)
            for p in part_ids:
                if p not in present:bad[p].add('MISSING_SOURCE_PART_FRAME')
            for w in clock:
                if w['bar']==bar:
                    for p in [w['part_id']]if'part_id'in w else part_ids:bad[p].add('UNCERTAIN_SOURCE_CLOCK')
            for r in crossing:bad[events[r]['part_id']].add('CROSSING_SOURCE_INTERVAL')
            for w in rest_warnings:
                if w['bar']==bar:bad[w['part_id']].add('CONFLICTING_SOURCE_REST')
            for ref in active:
                e=events[ref]
                if any(r['id']in active_rest and r['part_id']==e['part_id']and r['voice']==e['voice']for r in rests_here):bad[e['part_id']].add('NOTE_REST_OVERLAP')
            cell=dict(id=ident,frame_ref=frame['id'],start_q=str(a),end_q=str(b),active_refs=active,starting_refs=[r for r in active if intervals[r][0]==a],continuing_refs=[r for r in active if intervals[r][0]<a],crossing_refs=crossing,rest_refs=active_rest,
                part_refusals=[dict(part_id=p,reasons=sorted(v))for p,v in sorted(bad.items())if v],populations=[],focal_contexts=[])
            populations={}
            for ref in active:
                e=events[ref];p=e['part_id'];same=[r for r in active if events[r]['part_id']==p]
                scopes=((same,[p]),([r for r in same if r!=ref],[p]),([r for r in active if events[r]['part_id']!=p],[x for x in part_ids if x!=p]),([r for r in active if r!=ref],part_ids))
                query=dict(occurrence_ref=ref,scopes={});paths[ref].append(ident)
                for scope,(refs,ps)in zip(SCOPES,scopes):
                    key=tuple(sorted(refs))
                    if key not in populations:
                        included=[r for r in key if inventory[r]['domain']!='nonpitched'];exclude=[dict(occurrence_ref=r,reason='EXPLICIT_NONPITCHED_INSTRUMENT')for r in key if inventory[r]['domain']=='nonpitched']
                        reasons=sorted({reason for r in included for reason in inventory[r]['qualifications']});pcs=tuple(sorted({F(events[r]['pitch'])%12 for r in included if events[r]['pitch']is not None}))
                        if len(pcs)<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
                        pop=dict(id=f'{ident}:population:{len(populations)}',support_refs=list(key),included_refs=included,excluded_refs=exclude,refusals=reasons,hypotheses=[]if reasons else deepcopy(_fits(pcs)))
                        populations[key]=pop;cell['populations'].append(pop)
                    pop=populations[key];refusals=sorted({x for part in ps for x in bad[part]});focal=sorted(bad[p]);pitch=e['pitch']
                    query['scopes'][scope]=dict(population_ref=pop['id'],part_ids=ps,scope_refusals=refusals,focal_refusals=focal,direct_focal_support=ref in pop['included_refs'],role_results=[]if refusals or focal else[_focal_role(pitch,inventory[ref]['domain'],h)for h in pop['hypotheses']])
                cell['focal_contexts'].append(query)
            result['cells'].append(cell)
    result['occurrence_paths']=[dict(occurrence_ref=r,cell_refs=ids)for r,ids in sorted(paths.items())]
    result['crossing_occurrence_refs']=sorted(crosses)
    result['unscoped_positive_occurrence_refs']=sorted(r for r,e in events.items()if F(e['duration_q'])>0 and r not in paths)
    result['counts']=_counts(result,len(raw));return result

def check(tier1,view):
    issues=[];want=None
    try:
        want=expected(tier1)
        for key in sorted(set(want)|set(view)):
            if key not in want or key not in view or enc(want[key])!=enc(view[key]):issues.append('Source/native mismatch: '+key)
    except Exception as exc:issues.append(str(exc))
    return dict(status='PASS_INDEPENDENT_NOMINAL_HARMONY'if not issues else'FAIL',issues=issues,counts=want['counts']if want else{},
        scope='Literal written interval/population/native-role consistency, not acoustic sustain, inferred voices, true chord function or edit permission')
