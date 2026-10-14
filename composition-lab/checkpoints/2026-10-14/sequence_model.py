"""Generic conditional event-sequence learning from GP beat events.

No musical roles, harmonic roots, modes, genres, or fixed progressions.
Events keep duration, interval from previous sounded bass pitch, and simultaneous
pitch offsets. Statistical contexts are contiguous within one score voice.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import random
from extract import extract_score


def event_token(beat, previous):
    """Exact rational sixteenth-note units, pitch movement, and chord shape."""
    duration=Fraction(beat['duration_q'])
    if duration<=0:raise ValueError('Non-positive duration')
    notes=sorted(n['midi'] for n in beat['notes'] if n['midi'] is not None)
    units=duration*4
    if not notes:return (units,None,()),previous
    anchor=notes[0]
    shape=tuple(p-anchor for p in notes)
    delta=anchor-previous if previous is not None else None
    return (units,delta,shape),anchor

def track_sequences(score):
    """All supported meters and exact durations; split contexts at meter changes and invalid bars."""
    sequences=[];seen=set()
    for tr in score['tracks']:
        # This is a pitched-string GP exporter; percussion staves have no tuning.
        if not any(staff for staff in tr.get('tunings',[])):
            continue
        signature=tuple((m['time_signature'],tuple(tuple((b['duration_q'],tuple(n['midi'] for n in b['notes'])) for b in v) for v in m['voices'])) for m in tr['measures'])
        if signature in seen:continue
        seen.add(signature)
        for vi in range(max((len(m['voices']) for m in tr['measures']),default=0)):
            seq=[];start_pitch=None;prior=None
            for m in tr['measures']:
                if vi>=len(m['voices']):
                    if seq:sequences.append((seq,start_pitch))
                    seq=[];start_pitch=None;prior=None;continue
                bar=m['voices'][vi]
                from music_events import meter_length
                if sum((Fraction(b['duration_q']) for b in bar),Fraction(0))!=meter_length(m['time_signature']):
                    if seq:sequences.append((seq,start_pitch))
                    seq=[];start_pitch=None;prior=None;continue
                converted=[];tmp=prior
                for beat in bar:
                    tok,tmp=event_token(beat,tmp)
                    if tok is None:break
                    converted.append(tok)
                if len(converted)!=len(bar):
                    if seq:sequences.append((seq,start_pitch))
                    seq=[];start_pitch=None;prior=None;continue
                if start_pitch is None:
                    start_pitch=next((min(n['midi'] for n in b['notes'] if n['midi'] is not None) for b in bar if any(n['midi'] is not None for n in b['notes'])),None)
                seq.extend(converted);prior=tmp
            if seq and start_pitch is not None:sequences.append((seq,start_pitch))
    return sequences

class SequenceModel:
    def __init__(self,max_order=4):
        if max_order<0:raise ValueError('max_order must be >=0')
        self.max_order=max_order
        self.next_counts=[defaultdict(Counter) for _ in range(max_order+1)]
        self.starts=Counter();self.event_count=0;self.sequence_count=0
        self.pitch_starts=Counter()

    def add_sequence(self,sequence,start_pitch):
        if not sequence or start_pitch is None:return
        self.starts[tuple(sequence[:min(self.max_order,len(sequence))])]+=1
        self.pitch_starts[start_pitch]+=1
        self.sequence_count+=1
        for i,token in enumerate(sequence):
            for k in range(min(self.max_order,i)+1):
                context=tuple(sequence[i-k:i]) if k else ()
                self.next_counts[k][context][token]+=1
            self.event_count+=1

    @classmethod
    def from_scores(cls,scores,max_order=4):
        model=cls(max_order)
        for score in scores:
            for seq,pitch in track_sequences(score):model.add_sequence(seq,pitch)
        if not model.event_count:raise ValueError('No representable training events')
        return model

    @classmethod
    def from_paths(cls,paths,max_order=4):
        return cls.from_scores([extract_score(p) for p in paths],max_order)

    def distribution(self,history,valid=None):
        for k in range(min(len(history),self.max_order),-1,-1):
            counts=self.next_counts[k].get(tuple(history[-k:]) if k else (),{})
            options=Counter({tok:n for tok,n in counts.items() if valid is None or valid(tok)})
            if options:return options,k
        return Counter(),None

    def sample(self,rng,history,valid=None):
        counts,order=self.distribution(history,valid)
        if not counts:raise ValueError('No valid learned continuation')
        return rng.choices(list(counts),weights=list(counts.values()),k=1)[0],order