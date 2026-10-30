"""Qualify known written tie chains as supporting pitch evidence.

Uses the accepted written-lane equations. It neither merges occurrences nor
invents sounding durations. An expression anywhere in the complete chain keeps
the supporting pitch unresolved; selected notes cannot belong to any chain.
"""
from fractions import Fraction as F
from collections import defaultdict
import musical_tier2 as music

MODE='verified_written_ties'
TIE_REASON='written_tie_continuation_or_unsupported_tie'
NOTE_CONTEXT={'string','fret','rest','tie','velocity','accentuated'}
BEAT_CONTEXT={'notes','type','duration','beamStart','beamStop','beam','beamMode',
    'velocity','chord','rest','dots','dotted','tuplet','tupletStart','tupletStop'}


def other_execution(context,ref):
    event=context['events'][ref]
    part=context['documents'][f"track-{event['part_id']}.json"]
    beat=part['measures'][event['bar']-1]['voices'][event['voice']]['beats'][event['beat']]
    note=beat['notes'][event['note']]
    return any(k not in NOTE_CONTEXT and v is not None and v is not False for k,v in note.items())or any(
        k not in BEAT_CONTEXT and v is not None and v is not False for k,v in beat.items())


def qualify(context,edited_refs):
    core=context['core'];notation=context['lower']['tie_notation']
    try:
        nodes,true=music.written_tie_context(notation,core)
        links,unresolved=music.written_tie_edges(nodes,true)
    except (ValueError,TypeError,KeyError):
        return dict(chains=[],cleared_refs=[],blocked_edited_refs=[],
            unavailable='UNSUPPORTED_WRITTEN_TIE_CONTEXT')
    incoming={r['destination']:r for r in links}
    outgoing={r['origin']:r for r in links}
    unknown_declarations={r['occurrence_ref']for r in notation['occurrences']
        if 'tie'in r['fields']and r['fields']['tie']is not None
        and r['fields']['tie']is not False and r['fields']['tie']is not True}
    unresolved_refs={r['destination']for r in unresolved}|unknown_declarations
    groups={m['id']:g for g in core['coattacks']for m in g['members']}
    # A broken continuation adjacent to an otherwise valid chain is still part
    # of its uncertainty. It cannot be hidden by ending the chain one note early.
    unresolved_predecessors=set()
    lanes=defaultdict(list)
    for node in nodes.values():
        if node['lane'] is not None:lanes[node['lane']].append(node)
    for ref in unresolved_refs:
        node=nodes[ref]
        unresolved_predecessors.update(r['id']for r in lanes.get(node['lane'],[])
            if r['id']!=ref and r['onset']+r['duration']==node['onset'])
    chains=[];cleared=set();edited=set(edited_refs)
    blocked=edited&(set(incoming)|set(outgoing)|unresolved_refs|unresolved_predecessors)
    for origin in sorted(set(outgoing)-set(incoming)):
        refs=[origin];seen={origin}
        while refs[-1]in outgoing:
            ref=outgoing[refs[-1]]['destination']
            if ref in seen:raise ValueError('Cycle in written tie time')
            seen.add(ref);refs.append(ref)
        reasons=[]
        if any(outgoing[r]['kind']!='written_pitched_tie'for r in refs[:-1]):
            reasons.append('UNPITCHED_TIE_CHAIN')
        if set(refs)&unresolved_refs:reasons.append('UNRESOLVED_INCOMING_TIE')
        if set(refs)&unresolved_predecessors:reasons.append('UNRESOLVED_OUTGOING_TIE')
        if any(groups[r]['timing_uncertain']for r in refs):reasons.append('UNCERTAIN_TIE_CLOCK')
        if any(q!=TIE_REASON for r in refs for q in context['written_pitch_qualifications'][r]):
            reasons.append('OTHER_CHAIN_PITCH_OR_EXECUTION_UNCERTAINTY')
        if any(other_execution(context,r)for r in refs):reasons.append('OTHER_CHAIN_EXECUTION_OR_UNKNOWN_DECLARATION')
        pitches=[context['events'][r]['pitch']for r in refs]
        if any(p is None or F(p).denominator!=1 for p in pitches)or len(set(pitches))!=1:
            reasons.append('UNKNOWN_OR_DIFFERENT_CHAIN_PITCH')
        if edited.intersection(refs):
            blocked.update(edited.intersection(refs));reasons.append('EDITED_NOTE_IN_TIE_CHAIN')
        record=dict(origin_ref=origin,occurrence_refs=refs,
            status='VERIFIED_WRITTEN_PITCH_CONTINUITY'if not reasons else'UNRESOLVED_WRITTEN_CHAIN',
            reasons=sorted(set(reasons)))
        chains.append(record)
        if not reasons:cleared.update(refs[1:])
    return dict(chains=chains,cleared_refs=sorted(cleared),
        blocked_edited_refs=sorted(blocked),unavailable=None)


def witnesses(result,support_refs):
    support=set(support_refs)
    return [dict(origin_ref=r['origin_ref'],occurrence_refs=list(r['occurrence_refs']),
        status=r['status'])for r in result['chains']
        if r['status']=='VERIFIED_WRITTEN_PITCH_CONTINUITY'and support.intersection(r['occurrence_refs'])]


def validate_witness_shape(rows):
    if type(rows)is not list:raise ValueError('Written tie support list required')
    origins=[]
    for row in rows:
        if type(row)is not dict or set(row)!={'origin_ref','occurrence_refs','status'}or row['status']!='VERIFIED_WRITTEN_PITCH_CONTINUITY':
            raise ValueError('Typed verified written chain required')
        refs=row['occurrence_refs']
        if type(refs)is not list or len(refs)<2 or any(type(r)is not str or not r for r in refs)or len(set(refs))!=len(refs)or row['origin_ref']!=refs[0]:
            raise ValueError('Complete ordered tie occurrence references required')
        origins.append(row['origin_ref'])
    if origins!=sorted(set(origins)):raise ValueError('Unique canonical tie origins required')
