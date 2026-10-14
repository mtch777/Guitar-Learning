"""Evidence-based *candidate* gesture segmentation, independent of chord labels.

Boundaries use observations (silence, rests, pitch discontinuity and explicit
section changes), never a fixed number of bars or genre templates. The resulting
segments are hypotheses, not verified musical phrases.
"""
from fractions import Fraction as F
from statistics import median


def pitched(event):
    return [n['midi'] for n in event['notes'] if n['midi'] is not None]


def discover(score, track, *, jump_factor=2.5, min_jump=12, gap_factor=1.5,
             max_events=32):
    """Return per-voice segments of events, allowing spans across measure lines.

    Silent rests are explicit boundaries; unusually large melodic jumps and
    significant silence split gestures. Section labels enforce a boundary.
    max_events only caps computation; does not set a preferred phrase length.
    """
    if max_events < 2 or min_jump < 0 or jump_factor <= 0 or gap_factor <= 0:
        raise ValueError('Invalid segmentation parameters')
    measures = score['tracks'][track]['measures']
    streams = {}
    sections = set()
    for m in measures:
        if m.get('section'):
            sections.add(F(m['onset_q']))
        for vi,voice in enumerate(m['voices']):
            streams.setdefault(vi, []).extend(voice)
    output=[]
    for vi, stream in sorted(streams.items()):
        events=sorted(stream,key=lambda e:F(e['onset_q']))
        usable=[e for e in events if pitched(e) and not any(n.get('tie') for n in e['notes'])]
        gaps=[max(F(0),F(b['onset_q'])-F(a['onset_q'])-F(a['duration_q'])) for a,b in zip(usable,usable[1:])]
        positive=[g for g in gaps if g>0]
        typical_gap=median(positive) if positive else F(0)
        jumps=[abs(pitched(b)[0]-pitched(a)[0]) for a,b in zip(usable,usable[1:])]
        typical_jump=median(jumps) if jumps else 0
        threshold=max(min_jump,typical_jump*jump_factor)
        gap_threshold=typical_gap*gap_factor if typical_gap else F(0)
        chunk=[]
        for e in events:
            pitches=pitched(e)
            if not pitches or any(n.get('tie') for n in e['notes']):
                if chunk:output.append((vi,chunk));chunk=[]
                continue
            if chunk:
                prev=chunk[-1]
                prev_end=F(prev['onset_q'])+F(prev['duration_q'])
                gap=F(e['onset_q'])-prev_end
                jump=abs(pitches[0]-pitched(prev)[0])
                discontinuity=(gap<0 or (gap>0 and (not typical_gap or gap>gap_threshold))
                               or jump>threshold or F(e['onset_q']) in sections
                               or len(chunk)>=max_events)
                if discontinuity:
                    output.append((vi,chunk));chunk=[]
            chunk.append(e)
        if chunk:output.append((vi,chunk))
    return output


def phrase_windows(score,track,*,min_size=2,max_size=8):
    """All contiguous melodic training subphrases inside candidate gestures.

    Not fixed-size segmentation: gesture boundaries are inferred independently,
    then variable-length examples are extracted for compatible GP edits.
    """
    if min_size<2 or max_size<min_size:raise ValueError('Invalid window sizes')
    for _,segment in discover(score,track):
        for size in range(min(max_size,len(segment)),min_size-1,-1):
            for i in range(len(segment)-size+1):
                group=segment[i:i+size]
                if any(len(pitched(e))!=1 for e in group):continue
                if any(F(a['onset_q'])+F(a['duration_q'])!=F(b['onset_q'])
                       for a,b in zip(group,group[1:])):continue
                yield group