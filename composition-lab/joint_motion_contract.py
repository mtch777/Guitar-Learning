"""Bounded relationship record/permission validator; no generator or GP writer.

Within-bar main-voice written minima only. Harmony remains fixed. Zero locks
signed interval CHANGES, not absolute pitches; disconnected components have no
implied connecting edge. This is not a finished lever or functional harmony.
"""
from fractions import Fraction as F
from copy import deepcopy
from aligned_relationship_audit import interval_stream
from engine_contract import digest
from generation_freedom import validate,facets

FEATURE='within_bar_written_minimum_interval_change'
ROLES=['harmony','melody','bass']


def observe(score,bar):
    try:
        validate(score)
        if [t['name'] for t in score['tracks']]!=ROLES or type(bar)is not int or not 1<=bar<=len(score['tracks'][0]['measures']):raise ValueError('Explicit three-role bar required')
        if any(len(t['measures'][bar-1]['voices'])!=1 for t in score['tracks']):raise ValueError('Main voice only')
        def roots(ti):
            return [dict(local_q=e['local_onset_q'],duration_q=e['duration_q'],root=min(n['midi'] for n in e['notes'])) for e in score['tracks'][ti]['measures'][bar-1]['voices'][0] if e['notes']]
        stream=interval_stream(roots(0),roots(1))
    except (ValueError,KeyError,TypeError,IndexError,ZeroDivisionError) as error:
        return dict(feature=FEATURE,status='unknown',reason=str(error))
    edges=[dict(from_q=a['q'],to_q=b['q'],delta=b['interval']-a['interval']) for a,b in zip(stream,stream[1:]) if F(b['q'])<=F(a['until'])]
    record=dict(feature=FEATURE,status='known' if edges else 'not_applicable',reason=None if edges else 'no_eligible_transition',bar=bar,
        clocks=[dict(q=x['q'],until=x['until']) for x in stream],edges=edges)
    record['evidence_digest']=digest(record)
    return record


def permission(record,freedom,support=None,*,literal_melody_lock=False,function_lock=False,octave_lock=False):
    if type(freedom)is not int or freedom not in (0,100):return dict(status='refused',reason='unsupported_partial_control')
    if function_lock or octave_lock:return dict(status='refused',reason='unsupported_function_or_octave_lock')
    if record.get('feature')!=FEATURE or record.get('status')!='known':return dict(status='refused',reason=record.get('status','unknown_relationship'))
    if freedom==100 and literal_melody_lock:return dict(status='refused',reason='target_determined_by_literal_pitch_lock')
    if freedom==100:
        if not isinstance(support,dict) or support.get('known') is not True:return dict(status='refused',reason='unknown_support')
        try:
            mass=support['eligible_mass_q']
            if type(mass) not in (int,str) or F(mass)<=0:raise ValueError()
            if not support.get('denominator_unit') or not support.get('model_sha256'):raise ValueError()
        except (KeyError,ValueError,ZeroDivisionError):return dict(status='refused',reason='unsupported_evidence')
    return dict(status='validation_only',freedom=freedom,literal_melody_lock=literal_melody_lock,
        editable=['melody.midi','melody.string','melody.fret'],gp_consumer=False)


def proposal_view(reference,bar,freedom,support=None,**locks):
    """No original pitches, feature deltas, source digests or support payload."""
    record=observe(reference,bar);grant=permission(record,freedom,support,**locks)
    if grant['status']=='refused':return grant
    if freedom!=100:return dict(status='refused',reason='zero_lock_uses_protected_validator_only')
    tracks=[]
    for track in reference['tracks']:
        m=track['measures'][bar-1]
        tracks.append(dict(role=track['name'],tuning=deepcopy(track['tunings'][0]),meter=m['time_signature'],
            events=[dict(local_q=e['local_onset_q'],duration_q=e['duration_q'],cardinality=len(e['notes'])) for e in m['voices'][0]]))
    return dict(status='validation_only',feature=FEATURE,bar=bar,tracks=tracks,editable=grant['editable'])


def verify(reference,candidate,bar,freedom,support=None,**locks):
    old=observe(reference,bar);grant=permission(old,freedom,support,**locks)
    if grant['status']=='refused':return grant
    new=observe(candidate,bar)
    if new['status']!='known':return dict(status='refused',reason='candidate_relationship_unavailable')
    a,b=facets(reference,ROLES),facets(candidate,ROLES)
    if any(a[k]!=b[k] for k in a if k!='melody'):return dict(status='refused',reason='non_target_dimension_changed')
    # Melody changes are limited to the selected bar, never a whole-score grant.
    for key,value in a['melody'].items():
        if int(key.split(':')[1])!=bar-1 and value!=b['melody'][key]:return dict(status='refused',reason='outside_selected_bar')
    def protected(score):
        copy=deepcopy(score)
        for voice in copy['tracks'][1]['measures'][bar-1]['voices']:
            for event in voice:
                for note in event['notes']:
                    for key in ('midi','string','fret'):note.pop(key)
        return copy
    if protected(reference)!=protected(candidate):return dict(status='refused',reason='protected_metadata_or_topology_changed')
    if old['clocks']!=new['clocks']:return dict(status='refused',reason='joint_activity_changed')
    if locks.get('literal_melody_lock') and a['melody']!=b['melody']:return dict(status='refused',reason='literal_melody_lock_changed')
    if freedom==0 and old['edges']!=new['edges']:return dict(status='refused',reason='literal_relationship_changed')
    return dict(status='verified_contract_only',freedom=freedom,relationship_equal=old['edges']==new['edges'],
        forced_difference=False,gp_checked=False,musical_acceptance=False)
