"""One source-observed melodic-note change through the existing pitch owner.

This bounded operation preserves two directional moves and conditional chord
membership over the entire edited note. It does not select a key, infer a phrase
or claim that matching those relationships proves artistic suitability.
"""
from copy import deepcopy
from fractions import Fraction as F
from collections import defaultdict
import melodic_contour_choices as choices
import context_membership as membership
import nominal_harmony as nominal


def prepare(upper):
    from connected_tier2 import realize
    before=realize(upper)
    c=nominal.prepare_tier1(before)
    return dict(before=before,inventory=choices.inventory(before),
        context=c,harmony=nominal.build(c),packets={})


def packet(c,ref):
    if ref not in c['packets']:
        c['packets'][ref]=membership.from_context(c['context'],c['harmony'],
            dict(edited_refs=[ref],scope='ensemble_minus_edited'),pitch_support='verified_written_ties')
    return c['packets'][ref]


def signature(row,contract):
    """Same complete relative-time support; no source labels made into truth."""
    start=F(row['times'][1][0]);result=[]
    for cell in contract['contexts']:
        result.append(dict(span_q=[str(F(cell['start_q'])-start),str(F(cell['end_q'])-start)],
            part_ids=cell['part_ids'],hypotheses=cell['hypotheses'],
            memberships=cell['memberships'][0]['values']))
    return result


def closure(row,contract):
    return set(row['closure_refs'])|{r for cell in contract['contexts']
        for key in ('support_refs','included_refs') for r in cell[key]}|{
        r for chain in contract.get('written_tie_support',[])for r in chain['occurrence_refs']}


def apply_pitch(upper,target_ref,pitch):
    """Change the single existing anchor; the original inverse solves the fret."""
    import musical_tier2 as music
    from voicing_families import SCHEMA as FAMILY
    from declared_chord_ownership import SCHEMA as DECLARED
    if type(pitch)is not str or str(F(pitch))!=pitch or F(pitch).denominator!=1:
        raise ValueError('Exact observed integer pitch required')
    result=deepcopy(upper);shared=result['musical_relationships']
    rhythm=shared.get('schema')=='source-group-rhythm/1'
    rhythm_members={m['occurrence_ref']for g in shared['groups']for m in g['members']}if rhythm else set()
    if rhythm:shared=shared['pitch_relationships']
    wrapped=shared.get('schema')in(FAMILY,DECLARED)
    body=shared['core'] if wrapped else shared
    if body.get('schema')!='musical-context-relations/2':
        raise ValueError('Unsupported musical owner; never bypass an unknown wrapper')
    matches=[g for g in body['coattacks'] if any(m['id']==target_ref for m in g['members'])]
    if len(matches)!=1 or len(matches[0]['members'])!=1:
        raise ValueError('Exactly one independently owned single-note coattack required')
    group=matches[0]
    fields=music.MEMBER_FIELDS-{'duration_q'}if target_ref in rhythm_members else music.MEMBER_FIELDS
    if 'bass_register_anchor'not in group or set(group['members'][0])!=fields or group['members'][0]['voicing_interval']!='0':
        raise ValueError('Selected occurrence has another pitch owner')
    group['bass_register_anchor']=pitch
    if not wrapped and not rhythm:
        # Regenerate the existing interpretation, overlap and tonal equations.
        # No old derived pitch/timing payload is used to realize the change.
        group['interpretation']=music.interpreted(group)
        groups=body['coattacks']
        body.update(ensemble_coattacks=music.ensemble(groups),
            nominal_written_spans=music.written_spans(groups),
            tonal_evidence=music.tonal_evidence(groups),
            temporal_tonal_evidence=music.temporal_tonal_evidence(groups,body['measure_geometry']))
        music.validate(body)
    return result


def verify(before,after,target,donor,contract):
    """Compare complete actual output, not just the requested note value."""
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    from execution_dependencies import build as dependencies
    from freeze_technique_baseline import retained
    from voicing_register import tie_relationships
    if {k:v for k,v in before.items()if k!='facts'}!={k:v for k,v in after.items()if k!='facts'}:
        raise ValueError('Source envelope changed')
    if len(before['facts'])!=len(after['facts']):raise ValueError('Source ownership count changed')
    allowed=target['note_ref']+'/fret'
    changed=[]
    for a,b in zip(before['facts'],after['facts']):
        if a==b:continue
        if a['id']!=allowed or {k:v for k,v in a.items()if k!='value'}!={k:v for k,v in b.items()if k!='value'}:
            raise ValueError('Locked source fact changed: '+a['id'])
        changed.append(a['id'])
    docs=project_documents(after);old_docs=project_documents(before)
    old_lower=extract_documents(old_docs);new_lower=extract_documents(docs)
    old_events={e['id']:e for e in old_lower['events']};events={e['id']:e for e in new_lower['events']}
    if list(old_events)!=list(events):raise ValueError('Original occurrence order changed')
    expected=deepcopy(old_lower)
    target_event=next(e for e in expected['events']if e['id']==target['target_ref'])
    target_event['pitch']=donor['pitches'][1]
    # This typed source view also retains physical declarations for tie checks.
    # Only the already-permitted fret projection follows the same pitch change.
    physical=next(r for r in expected['tie_notation']['occurrences']if r['occurrence_ref']==target['target_ref'])
    physical['fields']['fret']=donor['physical'][1][1]
    if expected!=new_lower:raise ValueError('A locked pitch, time or source context changed')
    pitches=[events[r]['pitch']for r in target['occurrence_refs']]
    if choices.contour(pitches)!=choices.contour(target['pitches']):
        raise ValueError('Directed contour changed')
    pid,bar,voice,beat,note=map(int,target['target_ref'].split(':')[2:])
    selected=docs[f'track-{pid}.json']['measures'][bar-1]['voices'][voice]['beats'][beat]['notes'][note]
    if [selected.get('string'),selected.get('fret')]!=donor['physical'][1]:
        raise ValueError('Changed physical note lacks its observed source execution')
    if dependencies(before)['signature']!=dependencies(after)['signature']:
        raise ValueError('Linked technique relationship changed')
    if tie_relationships(old_lower)!=tie_relationships(new_lower):
        raise ValueError('Written tie relationship changed')
    old_pedals=[r['approved_pedal_phrases']for r in retained(old_docs)['tracks']]
    new_pedals=[r['approved_pedal_phrases']for r in retained(docs)['tracks']]
    if old_pedals!=new_pedals:raise ValueError('Approved pedal interpretation changed')
    harmonic=membership.verify(after,contract)
    return dict(status='EXACT_MIDDLE_NOTE_SCOPE_AND_CONDITIONAL_MEMBERSHIP',
        changed_fact_refs=changed,directions=choices.contour(pitches),harmony=harmonic,
        meaning='Observed alternate middle note; same outer notes, two move directions, complete rhythm and conditional chord membership',
        limits='No established key, intended note function, artist fit or human playability claim')


def options(upper,target_ref,prepared=None):
    from connected_tier2 import realize
    c=prepare(upper)if prepared is None else prepared
    source=choices.source_options(c['inventory'],target_ref);target=source['target']
    result=dict(target=target,source_options=source,options=[],rejected=[],witness_pair=None)
    if target['reasons']:return dict(result,status='REFUSED_SOURCE_NEIGHBORHOOD')
    # Harmonic filtering can only remove donors. Without two independent source
    # outcomes there is no possible admitted choice, so no expensive query is needed.
    if source['witness_pair']is None:return dict(result,status='NO_INDEPENDENT_MELODIC_ALTERNATIVES')
    candidates={r['target_ref']:r for r in c['inventory']['neighborhoods']}
    wanted=packet(c,target_ref)
    if wanted['status']!='SUPPORTED':
        return dict(result,status='MISSING_SURROUNDING_HARMONY',harmony_reasons=wanted['reasons'])
    contract=wanted['packet'];target_closure=closure(target,contract);admitted=[]
    for option in source['observed_options']:
        for ref in option['donor_refs']:
            donor=candidates[ref];observed=packet(c,ref)
            reason=None
            if observed['status']!='SUPPORTED':reason='DONOR_SURROUNDING_HARMONY_MISSING'
            elif signature(target,contract)!=signature(donor,observed['packet']):reason='DONOR_HARMONIC_RELATIONSHIP_DIFFERS'
            elif target_closure.intersection(closure(donor,observed['packet'])):reason='SHARED_TARGET_DONOR_SUPPORT'
            if reason:result['rejected'].append(dict(donor_ref=ref,reason=reason));continue
            admitted.append((donor,observed['packet']))
    witness=next(([a['target_ref'],b['target_ref']]for i,(a,ap)in enumerate(admitted)
        for b,bp in admitted[i+1:]if a['pitches'][1]!=b['pitches'][1]
        and not closure(a,ap).intersection(closure(b,bp))),None)
    if witness is None:return dict(result,status='NO_INDEPENDENT_MATCHED_HARMONY_CHOICES')
    result['witness_pair']=witness
    grouped=defaultdict(list)
    for d,_ in admitted:grouped[d['pitches'][1]].append(d)
    for pitch,donors in sorted(grouped.items(),key=lambda pair:F(pair[0])):
        try:
            changed=pitch!=target['pitches'][1]
            proof=verify(c['before'],realize(apply_pitch(upper,target_ref,pitch)),target,donors[0],contract)if changed else dict(status='UNCHANGED_SOURCE_NOTE')
            result['options'].append(dict(pitch=pitch,donor_refs=sorted(d['target_ref']for d in donors),changed=changed,relationships=proof))
        except (ValueError,KeyError,TypeError)as error:
            result['rejected'].append(dict(pitch=pitch,donor_refs=sorted(d['target_ref']for d in donors),reason=str(error)))
    return dict(result,status='SOURCE_SUPPORTED_MELODIC_CHOICES'if any(o['changed']for o in result['options'])else'NO_ADMITTED_CHANGED_MELODIC_NOTE')


def intervene(upper,controls):
    from connected_tier2 import realize
    choices.validate_controls(controls)
    realize(upper)
    if controls['melody']==0:
        return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    evidence=options(upper,controls['target_ref']);chosen,report=choices.sample(evidence,controls)
    report['evidence']=evidence
    return (deepcopy(upper)if chosen is None else apply_pitch(upper,controls['target_ref'],chosen['pitch'])),report
