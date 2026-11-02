"""Carry a local melody's onset intervals with one explicitly selected backing part.

No root/function guess or learned ending selector. Original observations alone
establish correspondences. Existing pitch/string owners and inverse do all writes.
"""
from copy import deepcopy
from fractions import Fraction as F
import math
import re
import nominal_harmony as nominal
import backing_motion_relations as relations
from source_observation_evidence import require

POLICY = 'observed_backing_motion'
FIELDS = {'context_policy','melody','physical','source_refs','target_refs','backing_part','seed'}
OPTIONAL_FIELDS = {'allow_note_octave_changes','backing_mode'}
SONORITY_MODE = 'matched_sonorities'
STREAM_MODE = 'explicit_occurrence_stream'
STREAM_FIELDS = {'backing_voice','source_backing_refs','target_backing_refs'}
REF = re.compile(r'event:\d+:\d+:\d+:\d+:\d+:\d+')
PLAIN_BEAT = {'notes','type','duration','dots','dotted','velocity','beamStart','beamStop','tupletStart','tupletStop','tuplet'}

def validate_controls(controls):
    if type(controls) is not dict:
        raise ValueError('Explicit backing-motion controls required')
    mode=controls.get('backing_mode',SONORITY_MODE)
    if type(mode) is not str or mode not in (SONORITY_MODE,STREAM_MODE):
        raise ValueError('Explicit supported backing correspondence mode required')
    required=FIELDS | (STREAM_FIELDS if mode==STREAM_MODE else set())
    if set(controls)-OPTIONAL_FIELDS!=required or controls['context_policy']!=POLICY:
        raise ValueError('Explicit backing-motion scope and coupled physical permission required')
    if type(controls['melody']) not in (int,float) or not math.isfinite(controls['melody']) or not 0<=controls['melody']<=100:
        raise ValueError('Melody release must be finite0..100')
    if type(controls['physical']) is not int or controls['physical'] not in (0,100):
        raise ValueError('This bounded coupled operation requires physical0(lock) or100(required reassignment permission)')
    if type(controls.get('allow_note_octave_changes',False)) is not bool:
        raise ValueError('Explicit Boolean note-octave permission required')
    if type(controls['seed']) is not int or type(controls['backing_part']) is not int or controls['backing_part']<0:
        raise ValueError('Typed seed and explicit backing part required')
    for key in ('source_refs','target_refs'):
        values=controls[key]
        if type(values) is not list or len(values)<2 or any(type(r) is not str or not REF.fullmatch(r) for r in values) or len(set(values))!=len(values):
            raise ValueError('Ordered distinct source occurrences required')
    if len(controls['source_refs'])!=len(controls['target_refs']) or set(controls['source_refs'])&set(controls['target_refs']):
        raise ValueError('Disjoint equal-length reference and edited passages required')
    if mode==STREAM_MODE:
        if type(controls['backing_voice']) is not int or controls['backing_voice']<0:
            raise ValueError('Explicit nonnegative backing voice required')
        for key in ('source_backing_refs','target_backing_refs'):
            refs=controls[key]
            if type(refs) is not list or len(refs)!=len(controls['source_refs']) or any(type(r) is not str or not REF.fullmatch(r) for r in refs):
                raise ValueError('One explicit backing occurrence per focal attack required')
            # The same held occurrence can cover several attacks. These are
            # repeated references to one observation, not additional votes.

def pointer(e):
    return f"track-{e['part_id']}.json#/measures/{e['bar']-1}/voices/{e['voice']}/beats/{e['beat']}/notes/{e['note']}"

def pitched_instrument(doc):
    program=doc.get('instrumentId')
    if type(program) is not int or not 0<=program<128:
        raise ValueError('Known pitched instrument required; drums/unknown domains cannot supply pitch correspondence')
    capo=doc.get('capo',0)
    if capo is None: capo=0
    if type(capo) is not int or capo<0:
        raise ValueError('Known nonnegative integer capo required')
    return capo

def original_contact(doc,note,pitch):
    capo=pitched_instrument(doc); string=note.get('string'); fret=note.get('fret')
    tuning=doc.get('tuning'); limit=doc.get('frets')
    if (type(tuning) is not list or type(string) is not int or not 0<=string<len(tuning)
            or type(fret) is not int or fret<0 or type(tuning[string]) is not int):
        raise ValueError('Valid original written string/fret/tuning contact required')
    if limit is not None and (type(limit) is not int or limit<0 or fret>limit):
        raise ValueError('Original contact violates declared fret bound')
    if F(pitch)!=tuning[string]+capo+fret:
        raise ValueError('Original contact disagrees with written pitch')

def passage(c, refs, backing_part):
    try: events=[c['events'][r] for r in refs]
    except KeyError as error: raise ValueError('Requested original occurrence missing') from error
    if len({(e['part_id'],e['voice']) for e in events})!=1 or events[0]['part_id']==backing_part:
        raise ValueError('One focal lane and an independent backing part required')
    if any(e['pitch'] is None or F(e['pitch']).denominator!=1 for e in events):
        raise ValueError('Known integer focal written pitches required')
    for a,b in zip(events,events[1:]):
        if F(a['onset_q'])+F(a['duration_q'])!=F(b['onset_q']):
            raise ValueError('Contiguous written attacks required for this local operation')
    for e in events:
        peers=[n for n in c['events'].values() if n['part_id']==e['part_id'] and n['voice']==e['voice']
               and F(n['onset_q'])<=F(e['onset_q'])<F(n['onset_q'])+F(n['duration_q'])]
        if len(peers)!=1 or peers[0]['id']!=e['id']:
            raise ValueError('Monophonic independently owned focal attacks required')
        doc=c['documents'][f"track-{e['part_id']}.json"]
        beat=doc['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]
        note=beat['notes'][e['note']]
        original_contact(doc,note,e['pitch'])
        if set(note)-{'string','fret'} or set(beat)-PLAIN_BEAT:
            raise ValueError('Focal execution/notation dependency not supported; preserve source and refuse')
    return events

def backing(c,view,time,part,voice=None):
    doc=c['documents'].get(f'track-{part}.json')
    if doc is None: raise ValueError('Selected backing part missing')
    pitched_instrument(doc)
    cells=[cell for cell in view['cells'] if F(cell['start_q'])<=time<F(cell['end_q'])]
    if len(cells)!=1: raise ValueError('One exact written clock cell required')
    cell=cells[0]
    if any(x.get('part_id')==part for x in cell['part_refusals']):
        raise ValueError('Selected backing clock is qualified')
    refs=[r for r in cell['active_refs'] if c['events'][r]['part_id']==part
          and (voice is None or c['events'][r]['voice']==voice)]
    inv={r['occurrence_ref']:r for r in view['occurrence_inventory']}
    result=[]; qualifications=[]
    for ref in refs:
        event=c['events'][ref]; pitch=event['pitch']
        if pitch is None or F(pitch).denominator!=1:
            raise ValueError('Selected backing contains unknown written pitch')
        note=doc['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]['notes'][event['note']]
        original_contact(doc,note,pitch)
        result.append(dict(ref=ref,pitch=int(F(pitch))))
        qualifications.extend(f'{ref}: {q}' for q in inv[ref]['written_pitch_qualifications']+inv[ref]['qualifications'])
    return result,dict(time_q=str(time),context_refs=refs,qualifications=qualifications)

def prepare(upper,controls):
    """Rebuild only from the supplied T2; no source/cache/file access."""
    from connected_tier2 import realize
    validate_controls(controls)
    # Public option queries cannot learn from previously generated notes either.
    require(upper,dict(controls,melody=100))
    before=realize(upper); c=nominal.prepare_tier1(before); view=nominal.build(c)
    source=passage(c,controls['source_refs'],controls['backing_part'])
    target=passage(c,controls['target_refs'],controls['backing_part'])
    import backing_written_tie_constraints as ties
    owned_refs=controls['source_refs']+controls['target_refs']
    tie_nodes,tie_ids=ties.context(c['core'],c['lower']['tie_notation'])
    tie_scope=ties.build(tie_nodes,tie_ids,owned_refs)
    def clock(es):
        start=F(es[0]['onset_q'])
        return [(str(F(e['onset_q'])-start),e['duration_q']) for e in es]
    if clock(source)!=clock(target): raise ValueError('This operation preserves identical source/target written rhythm')
    mode=controls.get('backing_mode',SONORITY_MODE)
    voice=controls['backing_voice'] if mode==STREAM_MODE else None
    execution_scope=None
    if mode==STREAM_MODE:
        import backing_execution_constraints as execution
        execution_scope=execution.build(before,owned_refs)
    correspondences=[]; pitches=[]
    for i,(s,t) in enumerate(zip(source,target)):
        a,ac=backing(c,view,F(s['onset_q']),controls['backing_part'],voice)
        b,bc=backing(c,view,F(t['onset_q']),controls['backing_part'],voice)
        if mode==STREAM_MODE:
            import explicit_backing_stream as stream
            if [r['ref'] for r in a]!=[controls['source_backing_refs'][i]] or [r['ref'] for r in b]!=[controls['target_backing_refs'][i]]:
                raise ValueError('EXPLICIT_STREAM_IDENTITY_CONFLICT: declared occurrence must be the single active note in its part and voice')
            match=stream.stream_relation(a,b,backing_part=controls['backing_part'],backing_voice=voice,
                                         source_context=ac,target_context=bc)
        else:
            match=relations.maximum_translations(a,b,source_context=ac,target_context=bc)
        if match['selected_delta'] is None:
            raise ValueError('AMBIGUOUS_OR_INSUFFICIENT_BACKING_CORRESPONDENCE: '+str(match['status']))
        solved=relations.solve_pitch(source_pitch=int(F(s['pitch'])),delta=match['selected_delta'])
        pitches.append(solved['target_pitch']); correspondences.append(dict(source_ref=s['id'],target_ref=t['id'],match=match,relation=solved))
    pitch_changes=[dict(occurrence_ref=e['id'],before_pitch=int(F(e['pitch'])),after_pitch=p,
                        semitone_change=p-int(F(e['pitch'])),before_octave=int(F(e['pitch']))//12-1,
                        after_octave=p//12-1) for e,p in zip(target,pitches)]
    if any(r['before_octave']!=r['after_octave'] for r in pitch_changes) and not controls.get('allow_note_octave_changes',False):
        raise ValueError('NOTE_OCTAVE_PERMISSION_REQUIRED: this operation changes absolute letter_octave indices; no generic musical-register policy is implied')
    doc=c['documents'][f"track-{target[0]['part_id']}.json"]
    original_strings=[doc['measures'][e['bar']-1]['voices'][e['voice']]['beats'][e['beat']]['notes'][e['note']]['string'] for e in target]
    fret_limit=doc.get('frets')
    if fret_limit is not None and (type(fret_limit) is not int or fret_limit<0):
        raise ValueError('Uninterpreted fret limit')
    physical=relations.minimum_string_changes(pitches,original_strings,doc['tuning'],doc.get('capo') or 0,max_fret=fret_limit)
    if not physical['assignments']: raise ValueError('No legal physical contacts for derived pitches')
    if controls['physical']==0 and physical['minimum_changes']:
        raise ValueError('PHYSICAL_LOCK_CONFLICT: derived pitches require explicit string-reassignment permission')
    options=[];execution_rejections=[]
    for option_index,contacts in enumerate(physical['assignments']):
        projection={e['id']:dict(pitch=str(p),string=k['string'],valid_position=k['fret']>=0)
                    for e,p,k in zip(target,pitches,contacts)}
        try:
            ties.proposed(tie_scope,tie_nodes,tie_ids,owned_refs,projection)
            if execution_scope is not None:
                execution.proposed(execution_scope,before,owned_refs,
                                   {e['id']:dict(k) for e,k in zip(target,contacts)})
        except ValueError as error:
            execution_rejections.append(dict(option_index=option_index,reason=str(error)))
            continue
        options.append(dict(pitches=[str(p) for p in pitches],contacts=contacts,
            donor_refs=['|'.join(controls['source_refs'])],
            changed=any(str(F(e['pitch']))!=str(p) or s!=k['string'] for e,p,s,k in zip(target,pitches,original_strings,contacts))))
    return dict(before=before,context=c,target=target,source=source,options=options,
        correspondences=correspondences,physical=physical,pitch_changes=pitch_changes,
        backing_mode=mode,execution_constraints=execution_scope,
        written_tie_constraints=tie_scope,execution_rejections=execution_rejections,
        note_octave_permission=controls.get('allow_note_octave_changes',False),
        original_observation_origin=deepcopy(upper['source_origin']),
        meaning='Preserve reference melody intervals to one explicitly selected backing part at written attacks only; no inferred root, phrase or artist decision')

def own_intervals(upper,prepared):
    """Persist BOTH passages as intervals; there is no old focal-pitch fallback."""
    from connected_tier2 import strip_lower,realize
    from backing_pitch_ownership import SCHEMAS,expand,lift,extend_bindings,assert_preserved
    from canonical_backing_bindings import canonical_bindings
    result=strip_lower(upper)
    shared=result['musical_relationships']
    plain=expand(shared) if shared.get('schema')in SCHEMAS else shared
    bindings=canonical_bindings(plain,prepared['correspondences'])
    existing=shared.get('schema')in SCHEMAS
    result['musical_relationships']=(extend_bindings if existing else lift)(shared if existing else plain,bindings,tier1=prepared['before'],
        preserve_execution=prepared.get('backing_mode')==STREAM_MODE)
    if existing:
        assert_preserved(shared,result['musical_relationships'])
    if realize(result)!=prepared['before']:
        raise ValueError('Interval ownership changed original source facts')
    return result

def apply(upper,source,target,option):
    from backing_pitch_ownership import SCHEMAS,LEGACY_SCHEMA,assert_preserved
    if upper['musical_relationships'].get('schema') not in SCHEMAS or upper['musical_relationships'].get('schema')==LEGACY_SCHEMA:
        raise ValueError('Backing-relative pitch ownership required')
    result=deepcopy(upper)
    intervals={r['occurrence_ref']:r for r in result['musical_relationships']['relationships']}
    # Move the observed relationship parameters, not a calculated note stream.
    for reference,e,contact in zip(source,target,option['contacts']):
        intervals[e['id']]['interval_semitones']=intervals[reference['id']]['interval_semitones']
        ident=pointer(e)+'/string'
        matches=[r for r in result['owned_parameters']['source_choices'] if r['fact_ref']==ident]
        if len(matches)!=1: raise ValueError('Exactly one owned string parameter required')
        matches[0]['parameter']=dict(normalized=str(contact['string']),negative_zero=False)
    assert_preserved(upper['musical_relationships'],result['musical_relationships'],
                     mutable_refs=[e['id'] for e in target])
    return result

def verify(prepared,after,option):
    """Every source fact except declared focal string/fret values stays exact."""
    expected=deepcopy(prepared['before']); lookup={r['id']:r for r in expected['facts']}; allowed=[]
    for e,pitch,contact in zip(prepared['target'],option['pitches'],option['contacts']):
        part=prepared['context']['documents'][f"track-{e['part_id']}.json"]
        if F(pitch)!=F(part['tuning'][contact['string']])+F(part.get('capo') or 0)+contact['fret']:
            raise ValueError('Physical contact differs from shared pitch equation')
        for key in ('string','fret'):
            ident=pointer(e)+'/'+key; lookup[ident]['value']=contact[key]; allowed.append(ident)
    if expected!=after: raise ValueError('Unexpected change outside declared focal pitch/physical realization')
    return dict(allowed_fact_refs=allowed,all_other_source_facts_exact=True)

from source_observation_evidence import controlled_update as _controlled_update
@_controlled_update
def intervene(upper,controls):
    from connected_tier2 import realize
    from declared_degree_choices import sample
    validate_controls(controls); realize(upper)
    if controls['melody']==0:
        return deepcopy(upper),dict(status='EXACT_ZERO_LOCK',released=False,changed=False)
    # Physical100 is coupled permission, never a separate edit under melody0.
    require(upper,controls)
    prepared=prepare(upper,controls)
    chosen,decision=sample(prepared,dict(voicing=controls['melody'],seed=controls['seed']))
    decision.update(correspondences=prepared['correspondences'],physical=prepared['physical'],
                    backing_mode=prepared['backing_mode'],execution_constraints=prepared['execution_constraints'],
                    written_tie_constraints=prepared['written_tie_constraints'],execution_rejections=prepared['execution_rejections'],
                    pitch_changes=prepared['pitch_changes'],note_octave_permission=prepared['note_octave_permission'],
                    scope=prepared['meaning'],original_observation_origin=prepared['original_observation_origin'])
    if chosen is None: return deepcopy(upper),decision
    owned=own_intervals(upper,prepared)
    changed=apply(owned,prepared['source'],prepared['target'],chosen)
    decision['verification']=verify(prepared,realize(changed),chosen)
    decision['status']='BACKING_MOTION_DERIVED' if decision['changed'] else 'RELATION_COINCIDENCE'
    return changed,decision
