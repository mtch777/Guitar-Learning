"""Descriptive generation metrics and leakage guards, never quality verdicts."""
from collections import Counter
from fractions import Fraction
import hashlib
from pathlib import Path


def validate_split(training, held_out):
    """Fail on identical bytes even when copied under another filename."""
    def hashes(paths):
        return {hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    if not training or not held_out: raise ValueError('Both training and held-out source lists are required')
    a,b=hashes(training),hashes(held_out)
    if a & b: raise ValueError('Source leakage: identical score in training and held-out split')
    return dict(training_sha256=sorted(a),held_out_sha256=sorted(b),byte_duplicate_leakage=False,
                limitation='Distinct arrangements/editions of the same song still need song-level identity adjudication')


def track_metrics(score):
    result=[]
    for track in score['tracks']:
        events=[e for m in track['measures'] for v in m['voices'] for e in v]
        notes=[n for e in events for n in e['notes']]
        durations=[Fraction(e['duration_q']) for e in events]
        # Continuity is defined separately within each actual voice.
        leaps=[]; gaps=[]
        voice_count=max((len(m['voices']) for m in track['measures']),default=0)
        for vi in range(voice_count):
            sounding=[e for m in track['measures'] if vi<len(m['voices']) for e in m['voices'][vi] if e['notes']]
            for a,b in zip(sounding,sounding[1:]):
                if len(a['notes'])==len(b['notes'])==1 and all(n['midi'] is not None for n in a['notes']+b['notes']):
                    leaps.append(abs(a['notes'][0]['midi']-b['notes'][0]['midi']))
                gaps.append(max(Fraction(0),Fraction(b['onset_q'])-Fraction(a['onset_q'])-Fraction(a['duration_q'])))
        total=sum(durations,Fraction(0))
        result.append(dict(track=track['index'],name=track['name'],notes=len(notes),
            monophonic_sounding_events=sum(len(e['notes'])==1 for e in events),
            polyphonic_events=sum(len(e['notes'])>1 for e in events),
            tie_destinations=sum((n.get('tie') or {}).get('destination')=='true' for n in notes),
            long_event_duration_share=float(sum((Fraction(e['duration_q']) for e in events if e['notes'] and Fraction(e['duration_q'])>=1),Fraction(0))/total) if total else None,
            mean_monophonic_leap=sum(leaps)/len(leaps) if leaps else None,
            max_monophonic_leap=max(leaps) if leaps else None,
            total_between_event_gap_q=str(sum(gaps,Fraction(0))),
            duration_histogram=dict(Counter(str(d) for d in durations)),
            interpretation='descriptive statistics; neither role inference nor musical quality'))
    return result


def copying_ngrams(reference, candidate, length=8):
    """Transposition-invariant within-voice note/rhythm windows, including chords.

No windows cross voice/track boundaries. This detects exact relative copying,
not approximate infringement, authorship or musical originality.
"""
    if length<2: raise ValueError('Window length must be at least two events')
    def windows(score):
        out=[]
        for track in score['tracks']:
            streams={}
            for m in track['measures']:
                for vi,voice in enumerate(m['voices']): streams.setdefault(vi,[]).extend(voice)
            for stream in streams.values():
                for i in range(max(0,len(stream)-length+1)):
                    window=stream[i:i+length]
                    pitches=[n['midi'] for e in window for n in e['notes']]
                    if not pitches or any(p is None for p in pitches): continue
                    anchor=pitches[0]
                    out.append(tuple((str(Fraction(e['duration_q'])),tuple(n['midi']-anchor for n in e['notes'])) for e in window))
        return out
    original=set(windows(reference)); output=windows(candidate)
    return dict(window_events=length,candidate_windows=len(output),
                exact_relative_match_share=sum(w in original for w in output)/len(output) if output else None,
                scope='supplied reference only; not an originality or copyright determination')
