"""Higher-level hypotheses referencing immutable original occurrences."""
from collections import defaultdict
from fractions import Fraction as F


def interpret(score,sounding,boundary_model,threshold):
    hypotheses=[];sustains=sounding['sustains']
    for lane in sounding['lanes']:
        nodes=[sustains[sid] for sid in lane['members']];nodes=[n for n in nodes if n['midi'] is not None and F(n['duration_q'])>0]
        if not nodes:continue
        boundaries=[0];features_batch=[]
        for i,n in enumerate(nodes[:-1]):
            previous=nodes[i-1] if i else n;following=nodes[i+1]
            duration=float(F(n['duration_q']));next_duration=float(F(following['duration_q']))
            gap=float(max(F(0),F(following['onset_q'])-F(n['end_q'])))
            phase=F(n['onset_q'])%4;strength=1 if phase==0 else .5 if phase.denominator==1 else .25
            features=[duration,gap,abs(n['midi']-previous['midi']),abs(following['midi']-n['midi']),duration/max(.01,next_duration),strength]
            features_batch.append(features)
        raw=[float(p) for p in boundary_model.predict_proba(features_batch)[:,1]] if features_batch else []
        for i,probability in enumerate(raw):
            if probability>=threshold:boundaries.append(i+1)
        boundaries.append(len(nodes))
        for left,right in zip(boundaries,boundaries[1:]):
            group=nodes[left:right]
            hypotheses.append(dict(kind='phrase',lane=lane['id'],onset_q=group[0]['onset_q'],end_q=group[-1]['end_q'],
                members=[oid for n in group for oid in n['members']],confidence=None,
                boundary_score_before=raw[left-1] if left else None,
                provenance='MTC-trained local boundary model applied to inferred lane; GP transfer unvalidated'))
        seen={}
        for length in (4,8):
            for i in range(len(nodes)-length+1):
                group=nodes[i:i+length];anchor=group[0]['midi']
                signature=tuple((n['midi']-anchor,n['duration_q']) for n in group)
                if (length,signature) in seen:
                    hypotheses.append(dict(kind='motif',members=[oid for n in group for oid in n['members']],
                        related_members=seen[length,signature],confidence=None,provenance='exact relative interval/duration recurrence; not perceptual motif truth'))
                else:seen[length,signature]=[oid for n in group for oid in n['members']]
    pitched=[n for n in sustains.values() if n['midi'] is not None and not score['tracks'][n['track']].get('is_percussion')]
    for q in range(int(F(score['duration_q']))):
        active=[n for n in pitched if F(n['onset_q'])<=q<F(n['end_q'])]
        if active:hypotheses.append(dict(kind='harmony',onset_q=str(q),end_q=str(q+1),
            members=[oid for n in active for oid in n['members']],pitch_classes=sorted({n['midi']%12 for n in active}),
            bass_observation=min(n['midi'] for n in active),root=None,quality=None,inversion=None,non_chord_tones=None,
            confidence=None,provenance='joint sounding pitch observations only; harmonic interpretation unresolved'))
    allowed=set(sounding['occurrences'])
    for h in hypotheses:
        if not set(h['members'])<=allowed:raise AssertionError('Unknown occurrence reference')
    return hypotheses
