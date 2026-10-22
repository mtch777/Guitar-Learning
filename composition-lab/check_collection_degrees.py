"""Independent native-scale oracle; explicit reference only, never inferred key."""
from fractions import Fraction as F


def native_reference(tonic,quality):
    from music21 import scale,pitch
    if quality not in ('major','minor'):raise ValueError('Major or explicit natural minor only')
    native=(scale.MajorScale if quality=='major' else scale.MinorScale)(pitch.Pitch(midi=60+tonic))
    degrees={pc:native.getScaleDegreeFromPitch(pitch.Pitch(midi=60+pc),comparisonAttribute='pitchClass') for pc in range(12)}
    intervals={degree:(pc-tonic)%12 for pc,degree in degrees.items() if degree is not None}
    return degrees,intervals


def equations():
    from musical_tier2 import collection_degree_relation
    comparisons=0;errors=[]
    for tonic in range(12):
        for quality in ('major','minor'):
            degrees,intervals=native_reference(tonic,quality);reference=[intervals[i] for i in range(1,8)]
            for midi in range(128):
                degree=degrees[midi%12];comparisons+=1
                if degree is None:
                    try:collection_degree_relation(tonic,reference,pitch=str(midi))
                    except ValueError:pass
                    else:errors.append('Outside native collection mapped')
                    continue
                actual=collection_degree_relation(tonic,reference,pitch=str(midi));octave=(midi-tonic)//12
                if actual['degree']!=degree or actual['relative_octaves']!=octave:errors.append('Native degree/register differs')
                inverse=collection_degree_relation(tonic,reference,degree=degree,relative_octaves=octave)
                if inverse['pitch']!=str(midi):errors.append('Same degree equation did not restore MIDI pitch')
    return dict(status='PASS' if not errors else 'FAIL',native_pitch_class_comparisons=comparisons,errors=errors,scope='Native major/natural-minor reference, all12tonics and MIDI0..127; no source spelling or key accuracy claim')


def check(raw,context,candidate,inverses):
    degrees,intervals=native_reference(candidate['tonic_pc'],candidate['quality']);errors=[];expected_inverse=[];expected_coordinates=[]
    if context['candidate_ref']!=candidate['id']:errors.append('Candidate reference differs')
    for note in context['note_contexts']:
        ident=note['occurrence_ref'];pitch=None if raw[ident]['pitch'] is None else F(raw[ident]['pitch']);coordinate=note['interval_of_note_base_key_candidate']
        degree=degrees[int(pitch)%12] if pitch is not None and pitch.denominator==1 else None
        octave=int((pitch-candidate['tonic_pc'])//12) if pitch is not None else None
        expected_coordinates.append(None if degree is None else 7*octave+degree-1)
        if pitch is None:
            if coordinate is not None:errors.append('Unknown source pitch received coordinates')
            continue
        if coordinate is None or coordinate['reference_collection_degree']!=degree or coordinate['relative_octaves']!=octave or coordinate['in_reference_collection']!=(degree is not None):errors.append('Raw/native source degree or register differs')
        if degree is not None:
            if coordinate['diatonic_coordinate']!=7*octave+degree-1:errors.append('Signed native diatonic coordinate differs')
            expected_inverse.append(dict(occurrence_ref=ident,pitch=str(candidate['tonic_pc']+12*octave+intervals[degree])))
        elif coordinate['diatonic_coordinate'] is not None:errors.append('Outside collection gained diatonic coordinate')
    if inverses!=expected_inverse:errors.append('Shared degree inverse differs from raw/native pitches')
    eligible=context['source_motion']['eligibility']=='eligible_owned_written_sequence'
    refs=context['source_motion']['occurrence_refs']
    for i,pair in enumerate(context['pairs']):
        a,b=raw[refs[i]]['pitch'],raw[refs[i+1]]['pitch'];chromatic=str(F(b)-F(a)) if a is not None and b is not None else None
        displacement=expected_coordinates[i+1]-expected_coordinates[i] if eligible and expected_coordinates[i] is not None and expected_coordinates[i+1] is not None else None
        if pair['from_ref']!=refs[i] or pair['to_ref']!=refs[i+1] or pair['chromatic_distance_semitones']!=chromatic or pair['signed_diatonic_displacement']!=displacement or pair['adjacent_degree_movement']!=(abs(displacement)==1 if displacement is not None else None):errors.append('Source chromatic/native degree movement differs')
    return dict(status='PASS' if not errors else 'FAIL',errors=errors,queried_source_occurrences=len(context['note_contexts']),mapped_degree_inverse_occurrences=len(expected_inverse),scope='Raw source pitches and native explicit-reference degrees; sequence eligibility separately retained, not independent note-function truth')
