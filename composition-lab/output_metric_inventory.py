"""Actual written-output units, independent of candidate or policy admission.

These are score measurements, not musical choices or playback certification.
Known tied continuations belong to one attack. Unknown ties stay explicit.
Percussion participates in timing/expression, never melodic pitch percentages.
Explicit dead notes also have no fundamental pitch unit. An unknown normal or
harmonic pitch remains an unknown unit; lack of an editable choice never removes it.
"""
from collections import defaultdict
from fractions import Fraction as F

from source_fact_tier1 import project_documents
from source_tie_tier1 import extract_documents
from local_dynamics import inventory as dynamic_inventory
from source_observation_evidence import digest

SCHEMA='actual-output-unit-inventory/3'
PITCH_FEATURES=('pitched_attack_pitch','pitched_attack_pitch_class','pitched_attack_octave')


def accent_value(note):
    if 'accentuated' not in note or note['accentuated'] is False:
        return 0
    value=note['accentuated']
    return value if type(value) is int and value in (0,1,2) else None


def inventory(tier1):
    from voicing_register import tie_relationships
    docs=project_documents(tier1)
    normal=extract_documents(docs)
    ties=tie_relationships(normal)
    predecessor={edge['destination']:edge['origin'] for edge in ties['links']}
    unresolved={row['destination']:row['reason'] for row in ties['unresolved']}
    states={row['occurrence_ref']:row for row in dynamic_inventory(tier1)['states']}
    events={event['id']:event for event in normal['events']}
    if len(events)!=len(normal['events']):raise ValueError('Unique current written occurrence IDs required')
    parts={part['partId']:part for name,part in docs.items() if name.startswith('track-')}
    nodes={};groups=defaultdict(list)
    for ref,event in events.items():
        part=parts[event['part_id']]
        measure=part['measures'][event['bar']-1]
        voice=measure['voices'][event['voice']]
        beat=voice['beats'][event['beat']];note=beat['notes'][event['note']]
        root=ref;seen=set()
        while root in predecessor:
            if root in seen:raise ValueError('Cyclic written-tie identity')
            seen.add(root);root=predecessor[root]
        if root not in events:raise ValueError('Written tie escaped current occurrence inventory')
        instrument=part.get('instrumentId')
        domain=('pitched' if type(instrument)is int and 0<=instrument<128 else
                'percussion' if instrument==1024 else 'unknown')
        explicit_rest=any(row.get('rest')is True for row in (measure,voice,beat,note))
        pitch=event['pitch'] if domain=='pitched' and note.get('dead')is not True else None
        if pitch is not None and F(pitch).denominator!=1:pitch=None
        nodes[ref]=dict(occurrence_ref=ref,attack_ref=root,part_id=event['part_id'],
            voice=event['voice'],bar=event['bar'],beat=event['beat'],note=event['note'],
            onset_q=event['onset_q'],duration_q=event['duration_q'],pitch=pitch,
            instrument_domain=domain,instrument_id=instrument,explicit_rest=explicit_rest,
            grace=bool(beat.get('graceNote')),dead=note.get('dead')is True,
            tie_continuation=ref in predecessor,unresolved_tie=unresolved.get(ref),
            string=note.get('string'),fret=note.get('fret'),
            accent=accent_value(note),dynamic=states.get(ref),
            mute=beat.get('palmMute',False) if type(beat.get('palmMute',False))is bool else None)
        if not explicit_rest:groups[root].append(ref)
    attacks={};features={name:{} for name in (
        'pitched_attack_pitch','pitched_attack_pitch_class','pitched_attack_octave',
        'attack_onset_q','attack_written_span_q','attack_base_dynamic','attack_accent',
        'guitar_bass_contact','guitar_bass_coattack_mute')}
    pitch_units={}
    for root,members in groups.items():
        members.sort(key=lambda ref:(F(nodes[ref]['onset_q']),ref))
        row=nodes[root]
        unknown=any(nodes[ref]['unresolved_tie'] for ref in members)
        pitch=row['pitch'] if not unknown else None
        dynamic=row['dynamic']
        span=max(F(nodes[ref]['onset_q'])+F(nodes[ref]['duration_q'])for ref in members)-F(row['onset_q'])
        attacks[root]=dict(row,member_refs=members,written_span_q=str(span),attack_identity_known=not unknown)
        features['attack_onset_q'][root]=None if unknown else row['onset_q']
        features['attack_written_span_q'][root]=None if unknown else str(span)
        features['attack_base_dynamic'][root]=(dynamic['marking'] if not unknown and dynamic and dynamic['known'] else None)
        features['attack_accent'][root]=None if unknown else row['accent']
        included=row['instrument_domain']!='percussion' and not row['dead']
        reason=('percussion_has_no_fundamental_pitch_unit'if row['instrument_domain']=='percussion'else
                'explicit_dead_note_has_no_fundamental_pitch_unit'if row['dead']else
                'unknown_fundamental_pitch_remains_a_unit'if pitch is None else'known_written_fundamental_pitch')
        dead_facts=[f"track-{nodes[ref]['part_id']}.json#/measures/{nodes[ref]['bar']-1}/voices/{nodes[ref]['voice']}/beats/{nodes[ref]['beat']}/notes/{nodes[ref]['note']}/dead"
                    for ref in members if nodes[ref]['dead']]
        pitch_units[root]=dict(attack_ref=root,member_refs=list(members),included=included,reason=reason,
            metric_names=list(PITCH_FEATURES),explicit_dead_fact_refs=dead_facts)
        if included:
            features['pitched_attack_pitch'][root]=pitch
            features['pitched_attack_pitch_class'][root]=None if pitch is None else str(F(pitch)%12)
            features['pitched_attack_octave'][root]=None if pitch is None else int(F(pitch)//12)-1
        if type(row['instrument_id'])is int and 24<=row['instrument_id']<=39:
            contacts=[[nodes[ref]['string'],nodes[ref]['fret']]for ref in members]
            # Explicit dead notes can name a string without a fret. Keep that
            # observed string: replacing the whole pair by None hides its edits.
            # None remains an unknown fret, never a fabricated physical position.
            features['guitar_bass_contact'][root]=(contacts if not unknown and all(
                type(nodes[ref]['string'])is int and (type(nodes[ref]['fret'])is int or
                (nodes[ref]['dead'] and nodes[ref]['fret']is None)) for ref in members) else None)
    simultaneous=defaultdict(list)
    for root,row in attacks.items():simultaneous[row['part_id'],F(row['onset_q'])].append(root)
    coattacks={}
    for (part,onset),roots in simultaneous.items():
        roots.sort()
        identity='attack-group:'+digest(roots)
        coattacks[identity]=dict(part_id=part,onset_q=str(onset),attack_refs=roots,
            member_refs=[ref for root in roots for ref in attacks[root]['member_refs']])
        instrument=parts[part].get('instrumentId')
        if type(instrument)is int and 24<=instrument<=39:
            values=[attacks[root]['mute'] for root in roots]
            features['guitar_bass_coattack_mute'][identity]=(None if None in values or any(
                not attacks[root]['attack_identity_known'] for root in roots)
                else 'on' if all(values) else 'off' if not any(values) else 'mixed')
    return dict(schema=SCHEMA,baseline_sha256=digest(tier1),
        features=features,notes=nodes,attacks=attacks,coattacks=coattacks,
        pitch_unit_classification=pitch_units,
        tie_links=ties['links'],unresolved_ties=ties['unresolved'],
        scope='Complete current score facts before admission; no source-observation votes or playback judgment',
        counts=dict(written_occurrences=len(nodes),attack_units=len(attacks),
            tied_continuations=len(predecessor),unresolved_ties=len(unresolved),
            percussion_attacks=sum(row['instrument_domain']=='percussion' for row in attacks.values()),
            pitched_metric_units=len(features['pitched_attack_pitch']),
            explicit_dead_pitch_exclusions=sum(row['reason']=='explicit_dead_note_has_no_fundamental_pitch_unit'for row in pitch_units.values()),
            contact_metric_units=len(features['guitar_bass_contact']),
            unknown_pitched_metric_units=sum(v is None for v in features['pitched_attack_pitch'].values()),
            known_pitched_attacks=sum(v is not None for v in features['pitched_attack_pitch'].values()),
            unknown_accent_units=sum(v is None for v in features['attack_accent'].values())))
