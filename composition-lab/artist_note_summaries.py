"""Individual-note notation inventory; attack-group rates remain separate.

No detector, inference or generation changes. Written duration mass sums every
note segment (including ties and simultaneous notes); it is not occupied time,
acoustic sustain, performed duration or a listening judgment.
"""
from collections import Counter, defaultdict
from fractions import Fraction as F

from artist_profiles import connected_families
from artist_relationship_profiles import validate_profile_inputs

MARKERS={
    'bend':('note',('bend',)), 'slide':('note',('slide',)),
    'palm_mute':('beat',('palmMute',)), 'tapping':('beat',('tapping',)),
    'dead':('note',('dead',)), 'ghost':('note',('ghost',)),
    'harmonic':('either',('harmonic',)), 'staccato':('note',('staccato',)),
    'accent':('note',('accentuated',)),
    'finger_vibrato':('note',('leftHandVibrato','vibrato','wideVibrato')),
}
VIEWS=('written_regular_segments','fresh_note_attacks','written_note_duration_mass')


def _raw_state(mapping,keys):
    if mapping is None:return None
    if not isinstance(mapping,dict):raise ValueError('Raw marker coverage must be an object or missing')
    values=[mapping[k] for k in keys if k in mapping]
    if any(v is not None and bool(v) for v in values):return True
    if any(v is None for v in values):return None
    return False


def marker_state(row,feature):
    """Return True/False/None plus positive evidence scope.

    An explicit effects list establishes recorded-marker coverage. Missing both
    effects and raw objects does not. Note vibrato requires note-scope evidence;
    a beat vibrato flag is never relabelled finger vibrato.
    """
    scope,keys=MARKERS[feature]
    effects=row.get('effects')
    if effects is not None and (not isinstance(effects,list) or any(not isinstance(x,str) for x in effects)):
        raise ValueError('Covered effects must be a list of marker names')
    raw_note=row.get('raw_note');raw_beat=row.get('raw_beat_effects')
    mappings=[('note',raw_note)] if scope=='note' else [('beat',raw_beat)] if scope=='beat' else [('note',raw_note),('beat',raw_beat)]
    states=[(name,_raw_state(mapping,keys)) for name,mapping in mappings]
    positive=[name for name,state in states if state is True]
    if positive:
        if effects is not None and not any(k in effects for k in keys):
            return None,'raw_effects_conflict'
        return True,'+'.join(positive)
    explicit_null=any(isinstance(mapping,dict) and any(mapping.get(k,'absent') is None for k in keys) for _,mapping in mappings)
    if explicit_null:return None,'explicit_null_marker'
    covered=[state for _,state in states if state is not None]
    active=effects is not None and any(k in effects for k in keys)
    if feature=='finger_vibrato':
        if raw_note is not None:return False,'note_marker_absent'
        if active:return None,'vibrato_scope_unknown'
    elif active:
        if all(mapping is not None for _,mapping in mappings):return None,'raw_effects_conflict'
        return True,scope+'_from_covered_effects'
    if effects is not None:return False,'covered_marker_absent'
    if len(covered)==len(mappings):return False,'raw_marker_absent'
    return None,'marker_coverage_unknown'


def _empty():
    return {feature:{
        'written_regular_segments':Counter(), 'fresh_note_attacks':Counter(),
        'written_note_duration_mass':dict(known_q=F(0),positive_q=F(0),unknown_marker_q=F(0),unknown_duration_count=0),
        'positive_evidence_scopes':Counter(), 'unknown_reasons':Counter(),
    } for feature in MARKERS}


def _add(target,row,duration,attack):
    for feature,views in target.items():
        state,provenance=marker_state(row,feature)
        for view,eligible in [('written_regular_segments',True),('fresh_note_attacks',attack is True)]:
            if not eligible:continue
            counts=views[view];counts['candidates']+=1
            counts['unknown' if state is None else 'known']+=1
            if state is True:counts['positive']+=1
        mass=views['written_note_duration_mass']
        if duration is None:mass['unknown_duration_count']+=1
        elif state is None:mass['unknown_marker_q']+=duration
        else:
            mass['known_q']+=duration
            if state:mass['positive_q']+=duration
        if state is True:views['positive_evidence_scopes'][provenance]+=1
        elif state is None:views['unknown_reasons'][provenance]+=1


def _merge(target,other):
    for feature,views in other.items():
        for view in ('written_regular_segments','fresh_note_attacks','positive_evidence_scopes','unknown_reasons'):
            target[feature][view].update(views[view])
        for key,value in views['written_note_duration_mass'].items():target[feature]['written_note_duration_mass'][key]+=value


def _serialize(table):
    result={}
    for feature,views in table.items():
        out={}
        for view in ('written_regular_segments','fresh_note_attacks'):
            counts=views[view]
            out[view]={key:counts[key] for key in ('candidates','known','positive','unknown')}
            out[view]['rate']=counts['positive']/counts['known'] if counts['known'] else None
        mass=views['written_note_duration_mass']
        out['written_note_duration_mass']={key:str(value) if isinstance(value,F) else value for key,value in mass.items()}
        out['written_note_duration_mass']['rate']=float(mass['positive_q']/mass['known_q']) if mass['known_q'] else None
        out['positive_evidence_scopes']=dict(views['positive_evidence_scopes'])
        out['unknown_reasons']=dict(views['unknown_reasons'])
        result[feature]=out
    return result


def summarize_notes(report,artist,*,partition='development'):
    """Descriptive inventory of ONE artist/partition, with explicit units.

    Development and held-out inventories are never implicitly combined. Original
    global temporal eligibility is retained, despite these being descriptive
    counts, so this inventory has the same declared eligible source population.
    """
    if partition not in ('development','held_out'):raise ValueError('Explicit development or held_out partition required')
    audit=validate_profile_inputs(report,{})
    families=connected_families(report['songs'])
    local={};songs={};coverage=Counter();source_song_ids=[]
    for song in report['songs']:
        if song.get('artist')!=artist or song['provisional_partition']!=partition:continue
        if song.get('ai_generated') is not False or song.get('is_junk') is not False:
            coverage['flagged_songs_excluded']+=1;continue
        sid=song['song_id'];source_song_ids.append(sid)
        for track in song['tracks']:
            if not track.get('guitar_or_bass'):continue
            if not track.get('temporal_relationships_eligible'):
                coverage['temporal_ineligible_tracks_excluded']+=1;continue
            coverage['eligible_tracks']+=1;coverage['grace_occurrences_excluded']+=len(track.get('grace_rows',[]))
            for row in track['rows']:
                beat_raw=row.get('raw_beat_effects')
                if beat_raw is not None and not isinstance(beat_raw,dict):raise ValueError('Raw beat coverage must be an object or missing')
                if row.get('grace') or row.get('grace_type') or (beat_raw or {}).get('graceNote'):
                    coverage['unexpected_grace_in_regular_rows_excluded']+=1;continue
                coverage['written_regular_segments']+=1
                coverage['unknown_base_pitch_segments']+=row.get('midi') is None
                tied=row.get('tie_destination')
                if tied is not None and not isinstance(tied,bool):raise ValueError('Tie destination must be explicit Boolean or unknown')
                attack=None if tied is None else not tied
                coverage['fresh_note_attacks']+=attack is True
                coverage['unknown_attack_eligibility_segments']+=attack is None
                if row.get('duration_q') is not None and type(row['duration_q']) not in (str,int):
                    raise ValueError('Written duration must be an exact rational string or integer')
                duration=None if row.get('duration_q') is None else F(row['duration_q'])
                if duration is not None and duration<=0:raise ValueError('Nonpositive regular written duration')
                coverage['unknown_written_duration_segments']+=duration is None
                key=(sid,track['part_id'],row.get('section_start'))
                if key not in local:local[key]=_empty()
                _add(local[key],row,duration,attack)
    for (sid,_,_),table in local.items():
        if sid not in songs:songs[sid]=_empty()
        _merge(songs[sid],table)
    aggregate=_empty()
    for table in songs.values():_merge(aggregate,table)
    artist_aggregate=_serialize(aggregate)
    for feature in MARKERS:
        for view in VIEWS:
            eligible=[]
            for sid,table in songs.items():
                metric=table[feature][view]
                den=metric['known_q'] if view=='written_note_duration_mass' else metric['known']
                pos=metric['positive_q'] if view=='written_note_duration_mass' else metric['positive']
                if den:eligible.append((sid,float(F(pos)/F(den)),bool(pos)))
            by_family=defaultdict(list)
            for sid,rate,positive in eligible:by_family[families[sid]].append((rate,positive))
            values=[rate for sid,rate,positive in eligible]
            summary=artist_aggregate[feature][view]
            summary.update(pooled_rate=summary.pop('rate'),
                equal_song_rate=sum(values)/len(values) if values else None,
                family_balanced_rate=sum(sum(v for v,p in rows)/len(rows) for rows in by_family.values())/len(by_family) if by_family else None,
                eligible_songs=len(eligible),songs_with_annotation=sum(p for _,_,p in eligible),
                eligible_families=len(by_family),families_with_annotation=sum(any(p for _,p in rows) for rows in by_family.values()),
                minimum_song_rate=min(values) if values else None,maximum_song_rate=max(values) if values else None,
                songs_without_known_denominator=len(source_song_ids)-len(eligible))
    return dict(schema='artist-individual-note-inventory-v1',artist=artist,partition=partition,
        scope='descriptive_'+partition,source_songs=sorted(source_song_ids,key=str),
        source_families=sorted({families[s] for s in source_song_ids}),input_audit=audit,coverage=dict(coverage),
        artist_aggregate=artist_aggregate,
        songs=[dict(song_id=sid,family=families[sid],metrics=_serialize(table)) for sid,table in sorted(songs.items(),key=lambda x:str(x[0]))],
        track_sections=[dict(song_id=sid,family=families[sid],part_id=tid,source_section_instance=section,metrics=_serialize(table))
                        for (sid,tid,section),table in sorted(local.items(),key=lambda x:str(x[0]))],
        definitions=dict(written_regular_segments='Individual regular note occurrences, including tied destinations',
            fresh_note_attacks='Individual regular notes explicitly not tied destinations; unknown tie status excluded',
            written_note_duration_mass='Exact sum of notated quarter-note duration over individual regular segments, including ties/polyphony; not occupied or acoustic time',
            beat_markers='Palm mute/tapping and beat harmonic tags describe notes carrying a shared beat annotation; not independent technique gestures',
            finger_vibrato='Note-scope flags only; beat vibrato and whammy are not finger vibrato',
            annotation_absence='Known absent notation is not proof of absent performance'),
        limitations=['No chord/pedal group labels copied onto individual notes',
            'Written-marker coverage is distinct from base-pitch knowledge and performed execution',
            'Grace is separately counted and excluded, never given metrical duration mass',
            'Track/source-section scopes are not inferred phrases, functions or emotional intent',
            'No generation quotas or artist-style correctness inferred from these descriptive rates'])
