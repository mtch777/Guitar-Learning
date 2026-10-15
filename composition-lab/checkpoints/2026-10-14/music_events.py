"""Canonical, non-stylistic GP7 event representation.

Beat durations and offsets use rational *quarter-note beats*. Keep score
identifiers and original XML descriptors so analysis does not erase evidence.
"""
from __future__ import annotations
from fractions import Fraction

VALUES = {'Whole':4,'Half':2,'Quarter':1,'Eighth':Fraction(1,2),
          '16th':Fraction(1,4),'32nd':Fraction(1,8),'64th':Fraction(1,16),
          '128th':Fraction(1,32),'256th':Fraction(1,64)}


def duration(rhythm):
    """Exact quarter-beat duration; raise, never invent, on unsupported rhythms."""
    if rhythm is None:
        raise ValueError('Beat missing rhythm')
    value = rhythm.findtext('NoteValue')
    if value not in VALUES:
        raise ValueError('Unsupported note value: '+str(value))
    base = Fraction(VALUES[value])
    dot = rhythm.find('AugmentationDot')
    if dot is not None:
        count = int(dot.get('count','1'))
        if count < 0: raise ValueError('Negative dot count')
        base *= sum((Fraction(1,2**i) for i in range(count+1)),Fraction(0))
    tup = rhythm.find('PrimaryTuplet')
    if tup is not None:
        num,den = int(tup.get('num')),int(tup.get('den'))
        if not num or not den:raise ValueError('Invalid tuplet')
        base *= Fraction(den,num)
    return base


def frac(value):
    return str(value.numerator)+'/'+str(value.denominator)


def meter_length(text):
    if not text or '/' not in text:raise ValueError('Unknown meter: '+str(text))
    numerator,denominator=map(int,text.split('/'))
    return Fraction(4*numerator,denominator)


def validate_events(score):
    """Check temporal consistency without rejecting intentional pickup/incomplete bars."""
    findings=[]
    for track in score['tracks']:
        for measure in track['measures']:
            expected=meter_length(measure['time_signature'])
            for vi,voice in enumerate(measure['voices']):
                if not voice: continue  # Absent GP voice slot, not an underfull voice.
                total=sum((Fraction(b['duration_q']) for b in voice),Fraction(0))
                if total != expected:
                    findings.append({'track':track['index'],'measure':measure['number'],
                                     'voice':vi,'duration_q':frac(total),'meter_q':frac(expected)})
    return findings
