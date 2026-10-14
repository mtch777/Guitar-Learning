"""Source-derived, chord-relative phrase substitutions with independent locks.

Uses only observed event groups: no hardcoded scales, genres, or pitch offsets.
No claim of calibrated 0-100 perceptual difference is made.
"""
from collections import Counter
from fractions import Fraction as F
import random
from harmonic_relative import analyze_note, map_note
from harmonic_continuity import at_time


def phrases(score, track, spans, sizes=(4,3,2), require_span=True):
    """Yield non-overlapping-per-voice contiguous blocks within one chord span."""
    for measure in score['tracks'][track]['measures']:
        for voice in measure['voices']:
            for size in sizes:
                for i in range(len(voice)-size+1):
                    group=voice[i:i+size]
                    if any(any(n['tie'] for n in e['notes']) for e in group):continue
                    if any(F(b['onset_q']) != F(a['onset_q'])+F(a['duration_q']) for a,b in zip(group,group[1:])):continue
                    start=F(group[0]['onset_q']);end=F(group[-1]['onset_q'])+F(group[-1]['duration_q'])
                    span=at_time(spans,start)
                    if require_span and (span is None or end>F(span['end'])):continue
                    yield group,span


def _shape(group):
    return tuple(len([n for n in e['notes'] if n['midi'] is not None]) for e in group)


def _durations(group):return tuple(F(e['duration_q']) for e in group)


def learn(score,track,spans):
    melody=Counter();rhythm=Counter()
    for group,_ in phrases(score,track,spans,require_span=False):
        key=_shape(group)
        assignments=[at_time(spans,F(e['onset_q'])) for e in group]
        if all(assignments):
            roles=tuple(tuple(analyze_note(n['midi'],chord['chord']) for n in e['notes'] if n['midi'] is not None) for e,chord in zip(group,assignments))
            melody[(key,tuple(tuple((n.interval_from_root,n.degree,n.octave_displacement) for n in notes) for notes in roles))]+=1
        rhythm[(key,_durations(group))]+=1
    return melody,rhythm


def plan_melody(score,track,spans,chosen_windows,strength,seed=17):
    """Map learned phrase roles into each target chord, with no event/timing edits."""
    if strength==0:return {},{'learned_melody_phrases':0,'melody_candidates_unavailable':0}
    pool,_=learn(score,track,spans)
    by_shape={}
    for (shape,roles),weight in pool.items():by_shape.setdefault(shape,[]).append((roles,weight))
    rng=random.Random(seed+503);planned={};changed=0;unavailable=0;occupied=set()
    for group,span in phrases(score,track,spans,require_span=False):
        if any(at_time(spans,F(e['onset_q'])) is None for e in group):continue
        ids=tuple(id(e) for e in group)
        if any(x in occupied for x in ids):continue
        if rng.random()>=strength/100:continue
        shape=_shape(group);existing=tuple(tuple((x.interval_from_root,x.degree,x.octave_displacement) for x in [analyze_note(n['midi'],at_time(spans,F(e['onset_q']))['chord']) for n in e['notes'] if n['midi'] is not None]) for e in group)
        candidates=[(roles,weight) for roles,weight in by_shape.get(shape,()) if roles!=existing]
        if not candidates:unavailable+=1;continue
        selection=rng.choices([v[0] for v in candidates],weights=[v[1] for v in candidates])[0]
        target=at_time(chosen_windows,F(group[0]['onset_q']))
        if target is None:unavailable+=1;continue
        from harmonic_relative import RelativeNote
        for event,notes in zip(group,selection):
            target=at_time(chosen_windows,F(event['onset_q']))
            if target is None:raise AssertionError('Source harmonic match lost')
            mapped=[]
            for interval,degree,octave in notes:
                rel=RelativeNote(0,interval,degree,octave)
                mapped.append(map_note(rel,target['target']))
            planned[id(event)]=tuple(mapped)
        occupied.update(ids);changed+=1
    return planned,{'learned_melody_phrases':changed,'melody_candidates_unavailable':unavailable,'learned_melody_vocabulary':len(pool)}


def plan_rhythm(score,track,spans,strength,seed=17):
    """Swap complete observed duration sequences with equal length/total and event types.

    Cannot change note attacks across ambiguous chords; each replacement uses
    existing GPIF Rhythm references and unique beat definitions.
    """
    if strength==0:return {},{'learned_rhythm_phrases':0,'rhythm_candidates_unavailable':0}
    _,pool=learn(score,track,spans)
    lookup={}
    for (shape,durations),weight in pool.items():lookup.setdefault((shape,sum(durations,F(0))),[]).append((durations,weight))
    uses=Counter(e['beat_id'] for t in score['tracks'] for m in t['measures'] for v in m['voices'] for e in v)
    ref_by_duration={}
    for t in score['tracks']:
        for m in t['measures']:
            for v in m['voices']:
                for e in v:ref_by_duration.setdefault(F(e['duration_q']),e['beat_id'])
    rng=random.Random(seed+907);planned={};changed=0;unavailable=0;occupied=set()
    for group,span in phrases(score,track,spans,require_span=False):
        ids=tuple(e['beat_id'] for e in group)
        if any(x in occupied for x in ids):continue
        if rng.random()>=strength/100:continue
        if any(uses[x]!=1 for x in ids):unavailable+=1;continue
        original=_durations(group)
        choices=[]
        start=F(group[0]['onset_q'])
        for p,w in lookup.get((_shape(group),sum(original,F(0))),()):
            if p==original or not all(d in ref_by_duration for d in p):continue
            onset=start;valid=True
            for ev,d in zip(group,p):
                old_h=at_time(spans,F(ev['onset_q']))
                new_h=at_time(spans,onset)
                if old_h is not new_h:valid=False;break
                onset+=d
            if valid:choices.append((p,w))
        if not choices:unavailable+=1;continue
        pattern=rng.choices([p for p,w in choices],weights=[w for p,w in choices])[0]
        for event,d in zip(group,pattern):planned[event['beat_id']]=ref_by_duration[d]
        occupied.update(ids);changed+=1
    return planned,{'learned_rhythm_phrases':changed,'rhythm_candidates_unavailable':unavailable,'learned_rhythm_vocabulary':len(pool)}