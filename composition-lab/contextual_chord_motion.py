"""Two-context harmony and source-voice motion, never a tonicization detector."""
from copy import deepcopy
from fractions import Fraction as F
import musical_tier2 as music
from contextual_note_roles import source_refusals,partial_path_possibilities

VERSION='conditional-chord-voice-motion/1'


def reference_coordinate(reference,pitch):
    if pitch is None or F(pitch).denominator!=1:return None
    difference=music.relation(anchor=reference['tonic_pc'],pitch=pitch)['interval']
    try:degree=music.collection_degree_relation(reference['tonic_pc'],reference['reference_intervals'],pitch=pitch)
    except ValueError:degree=None
    return dict(unwrapped_semitones=difference,interval_pc=str(F(difference)%12),in_reference_collection=degree is not None,degree_relation=degree)


def evaluate_query(upper,documents,events,request):
    if set(request)!={'version','occurrence_refs','at_qs','candidate_ref','harmonic_request'} or request['version']!=VERSION:raise ValueError('Typed chord/voice request required')
    refs=request['occurrence_refs'];clocks=request['at_qs'];harmonic=request['harmonic_request']
    if type(clocks) is not list or len(clocks)!=2 or F(clocks[0])>=F(clocks[1]):raise ValueError('Two ordered explicit clocks required')
    if type(harmonic) is not dict or set(harmonic)!={'start_q','end_q','part_id'}:raise ValueError('Explicit harmonic time/part scope required')
    a=music.fraction(harmonic['start_q']);b=music.fraction(harmonic['end_q'])
    if not 0<b-a<=32 or any(not a<=music.fraction(t)<b for t in clocks):raise ValueError('Chord/voice query outside resource/time bounds')
    source=music.note_pair_motion_evidence(upper,refs)
    reasons=source_refusals(documents,events,refs)+source['refusal_reasons']
    source['attack_and_tie_status']='Complete source tie/expression declarations checked by context wrapper; no acoustic attack claim'
    candidates=[(s,c) for s in upper['tonal_evidence']['scopes'] for c in s['candidates'] if c['id']==request['candidate_ref']]
    if len(candidates)!=1:raise ValueError('One explicit existing tonal-reference candidate required')
    scope,reference=candidates[0]
    if any(scope['id'] not in ('song-pooled',f"part:{events[r]['part_id']}") for r in refs):raise ValueError('Outside tonal reference part scope')
    pitches=[events[r]['pitch'] for r in refs]
    coordinates=[reference_coordinate(reference,p) for p in pitches]
    degrees=[c['degree_relation']['diatonic_coordinate'] if c is not None and c['degree_relation'] is not None else None for c in coordinates]
    diatonic=None if None in degrees else degrees[1]-degrees[0]
    queries=[dict(occurrence_ref=r,at_q=t) for r,t in zip(refs,clocks)]
    for r,t in zip(refs,clocks):
        event=events[r];start=F(event['onset_q'])
        if not start<=F(t)<start+F(event['duration_q']):raise ValueError('Clock outside original half-open written occurrence')
    evidence=None if reasons else music.harmonic_span_evidence(upper,**harmonic,max_edges=2048)
    joint=None if evidence is None or evidence['status']!='SCORED_NOT_MUSICAL_TRUTH' else music.harmonic_label_pair_evidence(upper,evidence,queries)
    alternatives=[]
    if joint is not None and joint['feasible_label_pairs'] is not None:
        partial=partial_path_possibilities(evidence,queries)
        for pair in joint['feasible_label_pairs']:
            labels=pair['labels'];contexts=[]
            for pitch,label in zip(pitches,labels):
                if label is None:contexts.append(None);continue
                interval=music.relation(anchor=label['root_pc'],pitch=pitch)['interval'] if pitch is not None else None
                membership=music._chord_membership(pitch,label)
                contexts.append(dict(chord=deepcopy(label),root_against_reference=reference_coordinate(reference,str(label['root_pc'])),
                    note_against_chord=None if interval is None else dict(unwrapped_semitones=interval,interval_pc=str(F(interval)%12),membership=membership,chord_member=None if membership=='unknown' else membership=='chord_member'),
                    chord_tone_pitch_classes_outside_reference=[(label['root_pc']+d)%12 for d in label['formula'] if (label['root_pc']+d-reference['tonic_pc'])%12 not in reference['reference_intervals']]))
            alternatives.append(dict(**deepcopy(pair),contexts=contexts,
                root_displacement_pc=None if any(l is None for l in labels) else str(F(music.relation(anchor=labels[0]['root_pc'],pitch=labels[1]['root_pc'])['interval'])%12),
                all_optimal_path_partial_possibilities=partial))
    status='SOURCE_SEQUENCE_REFUSED' if reasons else 'HARMONIC_RESOURCE_OR_EVIDENCE_UNAVAILABLE' if joint is None or joint['feasible_label_pairs'] is None else 'CONDITIONAL_CHORD_VOICE_RELATIONSHIPS'
    return dict(request=deepcopy(request),status=status,source_refusals=list(dict.fromkeys(reasons)),source_motion=source,
        reference=dict(candidate_ref=reference['id'],scope_ref=scope['id'],tonic_pc=reference['tonic_pc'],collection=reference['reference_collection'],score=reference['score'],score_type=reference['score_type']),
        note_reference_coordinates=coordinates,diatonic_displacement=diatonic,joint_label_context=joint,alternatives=alternatives,
        limitations=['Destination chord/root is not an established temporary tonic','No key, mode, modulation, intended resolution, preference or probability inferred','Consecutive written source occurrences; not acoustic sustain or verified picked attacks']),evidence
