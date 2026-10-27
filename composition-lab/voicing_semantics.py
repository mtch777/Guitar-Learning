"""Checked conditional voicing semantics over the authoritative musical core.

This is a lock checker, not another pitch owner, hypothesis selector or generator.
Formula compatibility does NOT establish a root. Exact degree spelling is unknown
in the pinned pitch-class vocabulary, so semitone roles are named honestly.
"""
from collections import Counter
from fractions import Fraction as F
import hashlib
import json
import musical_tier2 as music

LOCKS={'harmonic_hypotheses','occurrence_ids','member_pitch_classes','doubling',
       'inversion','bass_pitch','spacing','member_register','pitches','observed_formula_support','formula_membership'}


def token(value):return json.dumps(value,sort_keys=True,separators=(',',':'))


def pitch_coordinate(*,root_pc,pitch=None,coordinates=None):
    """SAME p=root_pc+role_pc+12*register, canonical 0<=role_pc<12."""
    if type(root_pc)is not int or not 0<=root_pc<12:raise ValueError('Root pitch-class coordinate required')
    if (pitch is None)==(coordinates is None):raise ValueError('Supply one side of shared relation')
    if pitch is not None:
        distance=F(music.relation(anchor=str(root_pc),pitch=pitch)['interval'])
        coordinates=dict(semitone_role=str(distance%12),register=distance//12)
    if type(coordinates)is not dict or set(coordinates)!={'semitone_role','register'}:raise ValueError('Exact coordinate fields required')
    role=coordinates['semitone_role'];register=coordinates['register']
    if type(role)is not str or str(F(role))!=role or not 0<=F(role)<12 or type(register)is not int:raise ValueError('Noncanonical role/register')
    recovered=music.relation(anchor=str(root_pc),interval=str(F(role)+12*register))['pitch']
    if pitch is not None and recovered!=str(F(pitch)):raise ValueError('Conflicting pitch coordinates')
    return dict(pitch=recovered,coordinates=coordinates)


def hypothesis(value):
    """Identity excludes derived bass/inversion; meaning remains conditional."""
    allowed={'root_pc','kind','formula','bass_interval_pc','root_is_observed','status'}
    if type(value)is not dict or not {'root_pc','kind','formula'}<=set(value) or set(value)-allowed:raise ValueError('Explicit harmonic hypothesis required')
    root=value['root_pc'];kind=value['kind'];formula=value['formula']
    if type(root)is not int or not 0<=root<12 or type(kind)is not str or kind not in dict(music.THEORY_FORMS) or type(formula)is not list or any(type(v)is not int for v in formula)or formula!=list(dict(music.THEORY_FORMS)[kind]):raise ValueError('Pinned theory hypothesis required')
    identity=dict(root_pc=root,kind=kind,formula=list(formula))
    return dict(id='harmony:'+hashlib.sha256(token(identity).encode()).hexdigest(),**identity,
        status='conditional_theory_hypothesis_not_established_harmony',spelling='diatonic_degree_and_alteration_not_established')


def describe(group,hypotheses):
    if len({m['id']for m in group['members']})!=len(group['members']):raise ValueError('Duplicate source occurrence')
    identities=[hypothesis(h)for h in hypotheses]
    if len({h['id']for h in identities})!=len(identities):raise ValueError('Duplicate harmonic hypothesis')
    pitches={m['id']:music.member_pitch(group,m)for m in group['members']}
    known=[F(p)for p in pitches.values()if p is not None];complete=len(known)==len(pitches)and bool(known)
    bass=min(known)if complete else None;views=[]
    for h in sorted(identities,key=lambda h:h['id']):
        members=[];doubling=Counter()
        for ident,p in pitches.items():
            if p is None:
                members.append(dict(id=ident,coordinates=None,formula_slot=None,membership='unknown'));continue
            coord=pitch_coordinate(root_pc=h['root_pc'],pitch=p)['coordinates'];role=F(coord['semitone_role'])
            slot=h['formula'].index(int(role))if role.denominator==1 and int(role)in h['formula']else None
            members.append(dict(id=ident,coordinates=coord,formula_slot=slot,membership='formula_member'if slot is not None else'nonmember_under_hypothesis'))
            doubling[coord['semitone_role']]+=1
        bass_role=None if bass is None else str((bass-h['root_pc'])%12)
        bass_slot=None if bass_role is None or F(bass_role).denominator!=1 or int(F(bass_role))not in h['formula']else h['formula'].index(int(F(bass_role)))
        views.append(dict(hypothesis=h,members=members,realized_semitone_multiplicity=dict(sorted(doubling.items())),
            unplayed_formula_roles=[str(step)for step in h['formula']if str(step)not in doubling],
            bass_semitone_role=bass_role,bass_formula_slot=bass_slot,
            inversion_status='unknown_incomplete_pitch'if not complete else'nonchord_bass_under_hypothesis'if bass_slot is None else'conditional_bass_formula_slot_not_established_root'))
    return dict(group_ref=group['id'],occurrence_ids=list(pitches),pitch_domain='written_base_not_sounding',
        complete=complete,bass_pitch=None if bass is None else str(bass),hypotheses=views,
        evidence='Explicit conditional hypotheses only; theoretical compatibility is not musical adjudication')


def validate_view(group,hypotheses,view):
    if token(describe(group,hypotheses))!=token(view):raise ValueError('Stale or tampered semantic view')
    return True


def check(before,after,before_hypotheses,after_hypotheses,locks,*,pinned_occurrences=()):
    """Recompute claims from actual inverse groups; never trust cached labels."""
    if type(locks)is not list or len(set(locks))!=len(locks) or set(locks)-LOCKS:raise ValueError('Explicit distinct semantic locks required')
    a=describe(before,before_hypotheses);b=describe(after,after_hypotheses);issues=[]
    ap={m['id']:music.member_pitch(before,m)for m in before['members']};bp={m['id']:music.member_pitch(after,m)for m in after['members']}
    ah={h['hypothesis']['id']:h for h in a['hypotheses']};bh={h['hypothesis']['id']:h for h in b['hypotheses']}
    semantic={'harmonic_hypotheses','doubling','inversion','member_register','observed_formula_support','formula_membership'}&set(locks)
    if semantic and(not ah or not bh):issues.append('INSUFFICIENT_HARMONIC_HYPOTHESIS')
    if semantic and set(ah)!=set(bh):issues.append('HARMONIC_HYPOTHESIS_SET_CHANGED')
    if set(locks)-{'occurrence_ids'} and(not a['complete']or not b['complete']):issues.append('INCOMPLETE_WRITTEN_PITCH')
    def pcs(values):return {k:None if p is None else str(F(p)%12)for k,p in values.items()}
    if 'occurrence_ids'in locks and set(ap)!=set(bp):issues.append('OCCURRENCE_IDENTITIES_CHANGED')
    if 'pitches'in locks and ap!=bp:issues.append('LITERAL_PITCH_CHANGED')
    if 'member_pitch_classes'in locks and pcs(ap)!=pcs(bp):issues.append('MEMBER_PITCH_CLASS_CHANGED')
    if 'bass_pitch'in locks and a['bass_pitch']!=b['bass_pitch']:issues.append('LOWEST_WRITTEN_PITCH_CHANGED')
    if 'spacing'in locks:
        def spacing(values,bass):return {k:None if p is None or bass is None else str(F(p)-F(bass))for k,p in values.items()}
        if spacing(ap,a['bass_pitch'])!=spacing(bp,b['bass_pitch']):issues.append('SPACING_CHANGED')
    for ident in sorted(set(ah)&set(bh)):
        x,y=ah[ident],bh[ident]
        if 'observed_formula_support'in locks and x['unplayed_formula_roles']!=y['unplayed_formula_roles']:issues.append('OBSERVED_FORMULA_SUPPORT_CHANGED:'+ident)
        if 'formula_membership'in locks:
            if {m['id']:m['membership']for m in x['members']}!={m['id']:m['membership']for m in y['members']}:issues.append('FORMULA_MEMBERSHIP_CHANGED:'+ident)
        if 'doubling'in locks and x['realized_semitone_multiplicity']!=y['realized_semitone_multiplicity']:issues.append('REALIZED_DOUBLING_CHANGED:'+ident)
        if 'inversion'in locks:
            if x['bass_formula_slot']is None or y['bass_formula_slot']is None:issues.append('INVERSION_UNESTABLISHED_UNDER_HYPOTHESIS:'+ident)
            elif x['bass_semitone_role']!=y['bass_semitone_role']:issues.append('CONDITIONAL_INVERSION_CHANGED:'+ident)
        if 'member_register'in locks:
            def registers(v):return {m['id']:None if m['coordinates']is None else m['coordinates']['register']for m in v['members']}
            if registers(x)!=registers(y):issues.append('MEMBER_REGISTER_CHANGED:'+ident)
    if any(ref not in ap or ref not in bp or ap[ref]!=bp[ref]for ref in pinned_occurrences):issues.append('PINNED_EXECUTION_PITCH_CHANGED')
    return dict(status='PASS_CONDITIONAL_SEMANTIC_LOCKS'if not issues else'REFUSED_SEMANTIC_LOCKS',issues=sorted(set(issues)),
        scope='harmonic_hypotheses means assumption-set equality ONLY; observed_formula_support and formula_membership are separate evidence locks. No established harmony. Physical/timing/technique locks require existing independent source checker; no artist or acoustic claim')
