"""Multi-track harmonic context and structural novelty (standard library only)."""
from __future__ import annotations
import argparse,json,math
from collections import Counter
from pathlib import Path
from phrase_analysis import parsed_tracks
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def _guitar(t):
    n=t['track'].lower()
    return any(s in n for s in ('guitar','lead','rhythm'))
def _bass(t):
    return 'bass' in t['track'].lower()
def _signature(events):
    return tuple((round(start,2),round(duration,2),tuple(pitches))
                 for v,start,duration,pitches in events if v==0)
def _cosine_gap(a,b):
    keys=set(a)|set(b)
    if not keys:return 0.
    dot=sum(a[k]*b[k] for k in keys)
    aa=math.sqrt(sum(a[k]**2 for k in keys))
    bb=math.sqrt(sum(b[k]**2 for k in keys))
    return 1-dot/(aa*bb) if aa and bb else (1. if aa or bb else 0.)
def _pitched(events):
    c=Counter()
    for voice,onset,duration,pitches in events:
        for p in pitches:c[p%12]+=duration
    return c
def analyze(path,tolerance=1):
    score=parsed_tracks(path)
    tracks=score['tracks'];n=len(score['meter'])
    guitars=[i for i,t in enumerate(tracks) if _guitar(t)]
    bass=[i for i,t in enumerate(tracks) if _bass(t)]
    seen={};kept=[];doubled=[]
    for i in guitars:
        sig=tuple(_signature(m) for m in tracks[i]['measures'])
        if sig in seen:
            doubled.append({'track':tracks[i]['track'],'same_as':tracks[seen[sig]]['track']})
        else:
            kept.append(i);seen[sig]=i
    context=[]
    for j in range(n):
        histogram=Counter()
        for ti in kept+bass:histogram.update(_pitched(tracks[ti]['measures'][j]))
        bass_notes=[p for ti in bass for voice,start,duration,ps in tracks[ti]['measures'][j] for p in ps]
        context.append({'measure':j+1,'pitch_class_weights':{
            NAMES[k]:round(v,3) for k,v in histogram.most_common()},
            'bass_lowest_pitch_candidate':NAMES[min(bass_notes)%12] if bass_notes else None,
            'pitch_classes_top4':[NAMES[k] for k,_ in histogram.most_common(4)]})
    novelty=[]
    for j in range(1,n):
        before=Counter();after=Counter()
        for k in range(max(0,j-4),j):
            before.update({NAMES.index(name):v for name,v in context[k]['pitch_class_weights'].items()})
        for k in range(j,min(n,j+4)):
            after.update({NAMES.index(name):v for name,v in context[k]['pitch_class_weights'].items()})
        tonal=_cosine_gap(before,after)
        def density(start,end):
            return sum(sum(len(tracks[i]['measures'][k]) for i in kept)
                       for k in range(start,end))/max(1,end-start)
        left=density(max(0,j-4),j);right=density(j,min(n,j+4))
        change=abs(right-left)/max(1,left,right)
        novelty.append({'measure':j+1,'score':round(.7*tonal+.3*change,4),
            'harmonic_change':round(tonal,4),'density_change':round(change,4)})
    labels=sorted(set(i for i,label in score['sections'] if i>1))
    selected=[]
    for candidate in sorted(novelty,key=lambda item:-item['score']):
        if all(abs(candidate['measure']-other['measure'])>3 for other in selected):
            selected.append(candidate)
        if len(selected)>=max(len(labels),1):break
    selected.sort(key=lambda item:item['measure'])
    hits=sum(any(abs(c['measure']-label)<=tolerance for label in labels) for c in selected)
    return {'file':score['file'],'measures':n,
      'guitar_tracks_used':[tracks[i]['track'] for i in kept],
      'bass_tracks_used':[tracks[i]['track'] for i in bass],
      'exact_duplicate_guitar_tracks':doubled,
      'source_section_boundaries':labels,'boundary_candidates':selected,
      'boundary_check':{'within_one_measure':hits,'candidate_count':len(selected),
          'source_count':len(labels),'tolerance_measures':tolerance,
          'exact_overlaps':sorted(set(c['measure'] for c in selected)&set(labels)),
          'method':'in-sample annotation comparison; candidate count based on label count'},
      'pitch_context_by_measure':context,
      'limitations':['Pitch-class weights are not chord labels or inferred keys',
      'Bass lowest note is a root candidate only',
      'No drum analysis','Double tracks removed only when exactly identical',
      'Boundary candidate count uses annotations; results are not held-out accuracy',
      'Structural novelty is a heuristic, not confirmed phrase segmentation']}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('files',nargs='+',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();data=json.dumps([analyze(p) for p in args.files],indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(data,encoding='utf-8')
        print('Wrote '+str(args.output))
    else:print(data)
if __name__=='__main__':main()
