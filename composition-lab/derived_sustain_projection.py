"""Reduce verified generated written continuations for relationship comparison.

The caller supplies the carrier rows from its recomputed authoritative carry
plan. This module checks those rows against the complete ACTUAL current score;
it does not accept an arbitrary replacement snapshot or detect generated notes
from music alone. Actual notation/native checks remain separate.
"""
from copy import deepcopy
from fractions import Fraction as F

import backing_execution_constraints as execution
from source_fact_tier1 import project_documents

FIELDS={'identity','occurrence_ref','origin_ref','predecessor_ref','destination_ref',
    'before_destination_ref','execution_record_id','support_record_ids','relationship_kinds',
    'beat_ref','onset_q','duration_q','added_attacks'}
KINDS={'continuous_gesture','guarded_written_contact','guarded_coending_member'}
BEAT_FIELDS={'duration','type','dots','notes','palmMute'}


def _note(documents,ref):
    song,part,bar,voice,beat,member=execution.address(ref)
    if documents['metadata.json']['songId']!=song:raise ValueError('Carrier song identity changed')
    try:
        event=documents[f'track-{part}.json']['measures'][bar-1]['voices'][voice]['beats'][beat]
        return event,event['notes'][member]
    except (KeyError,IndexError,TypeError)as error:raise ValueError('Carrier occurrence is absent')from error


def _beat_ref(ref):
    _,part,bar,voice,beat,member=execution.address(ref)
    return f'track-{part}.json#/measures/{bar-1}/voices/{voice}/beats/{beat}'


def _q(value):
    if type(value)is not str or str(F(value))!=value:raise ValueError('Canonical carrier clock required')
    return F(value)


def _identity(row):
    prefix='entry-carry-member:'
    if type(row['identity'])is not str or not row['identity'].startswith(prefix):
        raise ValueError('Explicit generated carry identity required')
    parts=row['identity'][len(prefix):].split('->')
    if len(parts)!=2 or parts[1]!=row['before_destination_ref']:
        raise ValueError('Generated carry origin identity changed')
    prior=execution.address(parts[0]);current=execution.address(row['predecessor_ref'])
    before=execution.address(row['before_destination_ref']);destination=execution.address(row['destination_ref'])
    if (prior[:4]+prior[5:]!=current[:4]+current[5:]or current[4]-prior[4]not in(0,1)
            or before[4]!=0 or destination!=before[:4]+(1,)+before[5:]):
        raise ValueError('Carrier does not follow the declared entry address projection')


def validate_projection(tier1,derived_sustains):
    """Return a comparison snapshot reduced ONLY by proven continuation rows.

    No source IO, cached original or new pitch choice is used. Every other
    current contact and every original tie remains. The input is never mutated.
    Provenance of the generated rows comes from the caller's recomputed plan;
    a raw score alone cannot establish which author originally wrote a note.
    """
    if type(derived_sustains)is not list:raise ValueError('Explicit generated sustain rows required')
    data=execution._snapshot(execution.encoded(tier1))
    if not derived_sustains:return deepcopy(data)
    documents=project_documents(tier1);nodes=data['nodes'];seen=set();predecessors=set();beats={}
    for row in derived_sustains:
        if type(row)is not dict or set(row)!=FIELDS:raise ValueError('Closed generated sustain row required')
        _identity(row)
        if (type(row['added_attacks'])is not int or row['added_attacks']!=0
                or type(row['relationship_kinds'])is not list or not row['relationship_kinds']
                or len(set(row['relationship_kinds']))!=len(row['relationship_kinds'])
                or set(row['relationship_kinds'])-KINDS
                or type(row['support_record_ids'])is not list or not row['support_record_ids']
                or len(set(row['support_record_ids']))!=len(row['support_record_ids'])
                or row['execution_record_id']not in row['support_record_ids']):
            raise ValueError('Explicit supported continuation without an attack required')
        refs=[row[k]for k in('origin_ref','predecessor_ref','occurrence_ref','destination_ref')]
        if any(type(ref)is not str or ref not in nodes for ref in refs):raise ValueError('Carrier current identity is absent')
        origin,previous,carrier,destination=(nodes[ref]for ref in refs)
        ref=row['occurrence_ref'];prior=row['predecessor_ref']
        if ref in seen or prior in predecessors or len({prior,ref,row['destination_ref']})!=3:
            raise ValueError('Duplicate, cyclic or overlapping carrier authority')
        if prior in seen or ref in predecessors:raise ValueError('Nested generated carrier chain is unsupported')
        seen.add(ref);predecessors.add(prior)
        if (carrier['beat']!=0 or destination['beat']!=1 or carrier['bar']!=destination['bar']
                or previous['bar']+1!=carrier['bar']or row['beat_ref']!=_beat_ref(ref)
                or (previous['part'],previous['voice'],previous['string'])!=
                   (carrier['part'],carrier['voice'],carrier['string'])
                or (destination['part'],destination['voice'])!=(carrier['part'],carrier['voice'])):
            raise ValueError('Carrier is not the declared same-lane entry continuation')
        if ('guarded_coending_member'not in row['relationship_kinds']and
                destination['string']!=carrier['string']):
            raise ValueError('Continuous contact destination changed string')
        if (not carrier['tie_destination']or carrier['grace']or previous['grace']or
                not carrier['string_valid']or not previous['string_valid']or carrier['pitch']is None
                or previous['pitch']is None or carrier['fret']is None
                or carrier['pitch']!=previous['pitch']or carrier['fret']!=previous['fret']):
            raise ValueError('Carrier must remain an equal-pitch written tie')
        start,duration=_q(row['onset_q']),_q(row['duration_q'])
        if (duration<=0 or carrier['onset']!=start or carrier['duration']!=duration
                or previous['onset']+previous['duration']!=start
                or start+duration!=destination['onset']):
            raise ValueError('Carrier written spans are no longer contiguous')
        beat,note=_note(documents,ref);previous_beat,previous_note=_note(documents,prior)
        if (set(note)!={'string','fret','tie'}or note['tie']is not True
                or note['string']!=previous_note.get('string')or note['fret']!=previous_note.get('fret')
                or set(beat)-BEAT_FIELDS or beat.get('palmMute')!=previous_beat.get('palmMute')):
            raise ValueError('Carrier contains an extra attack, declaration or changed execution state')
        if (carrier['part']in data['uncertain_parts']or origin['part']!=carrier['part']or
                origin['voice']!=carrier['voice']or origin['string']!=carrier['string']or
                origin['onset']>previous['onset']):
            raise ValueError('Carrier has uncertain clock or inconsistent existing origin')
        beats.setdefault(row['beat_ref'],set()).add(ref)
        # Examine the complete current score. A new voice/contact may not be
        # removed merely because the intended tie itself remains contiguous.
        for other_ref,other in nodes.items():
            if other_ref in(prior,ref)or(other['part'],other['string'])!=(carrier['part'],carrier['string']):continue
            overlaps=(start<=other['onset']<start+duration if other['grace']else
                      other['onset']<start+duration and other['onset']+other['duration']>start)
            if overlaps:raise ValueError('Another current contact intersects the derived sustain')
    for beat_ref,claimed in beats.items():
        actual={ref for ref in nodes if _beat_ref(ref)==beat_ref}
        if actual!=claimed:raise ValueError('Incomplete generated sustain beat authority')
    result=deepcopy(data)
    for row in derived_sustains:
        previous=result['nodes'][row['predecessor_ref']]
        previous['duration']+=result['nodes'].pop(row['occurrence_ref'])['duration']
    for row in result['records']:
        if any(row[k]in seen for k in('origin_ref','destination_ref','candidate_destination_ref')):
            raise ValueError('Generated sustain became an execution endpoint')
        removed=set(row['member_refs'])&seen
        if not removed<=set(row['tied_member_refs']):
            raise ValueError('Generated sustain became an original declaration member')
        row['member_refs']=[ref for ref in row['member_refs']if ref not in seen]
        row['tied_member_refs']=[ref for ref in row['tied_member_refs']if ref not in seen]
        row['id']=execution.identity(row)
    result['derived_sustain_refs']=execution.ordered(seen)
    return result
