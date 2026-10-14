"""Candidate phrase segmentation and musical development from GP7 symbolic tracks.

Section markers are imported from the score. Internal phrase ends are inferred
from rhythm, pitch activity and phrase-length preferences, not ground truth.
"""
from __future__ import annotations
import argparse
import json
import math
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

RHYTHMS = {'Whole':4., 'Half':2., 'Quarter':1., 'Eighth':.5,
           '16th':.25, '32nd':.125, '64th':.0625, '128th':.03125}


def refs(node, child):
    return (node.findtext(child) or '').split()


def parse(path):
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read('Content/score.gpif'))
    def indexed(parent, item):
        return {x.get('id'): x for x in root.findall('./%s/%s' % (parent, item))}
    bars, voices, beats, notes, rhythms = [indexed(a,b) for a,b in
        (('Bars','Bar'),('Voices','Voice'),('Beats','Beat'),('Notes','Note'),('Rhythms','Rhythm'))]
    masters = root.findall('./MasterBars/MasterBar')
    section_starts = [(i + 1, m.findtext('./Section/Text')) for i,m in enumerate(masters)
                      if m.findtext('./Section/Text')]
    tracks=[]
    for track_i, track in enumerate(root.findall('./Tracks/Track')):
        measures=[]
        for master in masters:
            bar_refs=refs(master,'Bars')
            if track_i >= len(bar_refs):
                raise ValueError('Missing bar for track '+str(track_i))
            events=[]
            for voice_i, voice_id in enumerate(refs(bars[bar_refs[track_i]], 'Voices')):
                if voice_id=='-1':continue
                clock=0.
                for beat_id in refs(voices[voice_id],'Beats'):
                    beat=beats[beat_id]
                    rhythm_ref=beat.find('Rhythm')
                    rhythm=rhythms.get(rhythm_ref.get('ref')) if rhythm_ref is not None else None
                    name=rhythm.findtext('NoteValue') if rhythm is not None else None
                    if name not in RHYTHMS:raise ValueError('Unsupported rhythm '+str(name))
                    duration=RHYTHMS[name]
                    dot=rhythm.find('AugmentationDot')
                    if dot is not None:duration *= 2-0.5**int(dot.get('count','1'))
                    tuplet=rhythm.find('PrimaryTuplet')
                    if tuplet is not None and tuplet.findtext('Num') and tuplet.findtext('Den'):
                        duration *= int(tuplet.findtext('Den'))/int(tuplet.findtext('Num'))
                    pitches=[]
                    for nid in refs(beat,'Notes'):
                        note=notes[nid]
                        midi=note.findtext("./Properties/Property[@name='Midi']/Number")
                        fret=note.findtext("./Properties/Property[@name='Fret']/Fret")
                        string=note.findtext("./Properties/Property[@name='String']/String")
                        if all(v is not None for v in (midi,fret,string)):
                            pitches.append(int(midi))
                    if pitches:events.append((voice_i, round(clock,5),round(duration,5),tuple(sorted(pitches))))
                    clock+=duration
            measures.append(events)
        tracks.append({'name':track.findtext('Name') or 'unnamed', 'measures':measures})
    return {'song':Path(path).name,'measures':len(masters),'sections':section_starts,'tracks':tracks}


def primary_notes(measure):
    # Keep first written voice only; lowest note of chords for a monophonic outline.
    return [(onset,duration,pitches[0]) for v,onset,duration,pitches in measure if v==0 and pitches]


def boundary_strength(measures, boundary):
    """Evidence that measure boundary (0-based index) starts a new phrase."""
    before=measures[max(0,boundary-2):boundary]
    after=measures[boundary:min(len(measures),boundary+2)]
    if not before or not after:return 0.
    counts_a=[len(primary_notes(m)) for m in before]
    counts_b=[len(primary_notes(m)) for m in after]
    density=abs(sum(counts_a)/len(counts_a)-sum(counts_b)/len(counts_b)) / max(1.,max(counts_a+counts_b))
    previous=primary_notes(measures[boundary-1]); following=primary_notes(measures[boundary])
    silence=float(not previous or not following)
    pcs_a=Counter(p%12 for m in before for _,_,p in primary_notes(m))
    pcs_b=Counter(p%12 for m in after for _,_,p in primary_notes(m))
    dot=sum(pcs_a[p]*pcs_b[p] for p in set(pcs_a)|set(pcs_b))
    norm=math.sqrt(sum(x*x for x in pcs_a.values())*sum(x*x for x in pcs_b.values()))
    pc_change=1-dot/norm if norm else float(bool(pcs_a)!=bool(pcs_b))
    return round(.45*density+.4*pc_change+.15*silence,4)


def segment_section(measures, start, end):
    """Dynamic-programming boundaries within [start,end), zero-based measures.

    Favors 4-bar units but permits 2, 3, 6 and 8 when phrase boundary evidence
    supports them. Section edges are hard constraints, not predictions.
    """
    if start>=end:return []
    lengths=(2,3,4,6,8)
    n=end-start
    dp=[-float('inf')]*(n+1)
    preceding=[None]*(n+1)
    dp[0]=0.
    for i in range(1,n+1):
        for length in lengths+(1,):
            if i-length<0:continue
            edge=start+i
            reward={1:-2.2,2:-.55,3:-.32,4:.42,6:-.15,8:0.}.get(length,-2.)
            evidence=boundary_strength(measures,edge) if edge<end else 0.
            score=dp[i-length]+reward+1.6*evidence-.08
            if score>dp[i]:dp[i]=score;preceding[i]=i-length
    spans=[];cursor=n
    while cursor>0:
        prev=preceding[cursor]
        if prev is None:raise ValueError('Could not segment section')
        spans.append((start+prev,start+cursor))
        cursor=prev
    return list(reversed(spans))


def phrase_events(measures,start,end):
    return [(bar-start,round(onset,3),round(duration,3),pitch)
            for bar in range(start,end)
            for onset,duration,pitch in primary_notes(measures[bar])]


def normalized_distance(a,b):
    """Pitch-transposition-invariant normalized edit distance over notes and timing."""
    if not a or not b:return 1.
    x0=a[0][3];y0=b[0][3]
    x=[(p-x0,bar+onset,duration) for bar,onset,duration,p in a]
    y=[(p-y0,bar+onset,duration) for bar,onset,duration,p in b]
    prev=[float(j) for j in range(len(y)+1)]
    for i,(pitch,time,duration) in enumerate(x,1):
        row=[float(i)]
        for j,(p,t,d) in enumerate(y,1):
            cost=(0. if pitch==p else .8)+(.15 if abs(time-t)>.125 else 0.)+(.05 if abs(duration-d)>.125 else 0.)
            row.append(min(prev[j]+1.,row[j-1]+1.,prev[j-1]+cost))
        prev=row
    return round(min(1.,prev[-1]/max(len(x),len(y))),4)


def classify(distance,shift,a,b):
    if distance==0.:return 'transposed_exact' if shift else 'identical'
    if distance<=.22:return 'varied'
    return 'contrasting'


def analyze_track(track,sections,measure_count,similarity=.22):
    measures=track['measures']
    boundaries=sorted({1,measure_count+1}|{m for m,_ in sections if 1<=m<=measure_count})
    segments=[]
    for a,b in zip(boundaries,boundaries[1:]):
        segments.extend(segment_section(measures,a-1,b-1))
    phrases=[];families=[]
    for first,last in segments:
        notes=phrase_events(measures,first,last)
        item={'start_measure':first+1,'end_measure':last,'bars':last-first,'note_count':len(notes),
              'boundary_cue':boundary_strength(measures,first) if first>0 else 0.,
              'section':next((label for m,label in reversed(sections) if m<=first+1),None)}
        candidates=[]
        if len(notes)>=4:
            for previous_index,previous in enumerate(phrases):
                older=previous['_events']
                if len(older)<4 or abs((last-first)-previous['bars'])>1:continue
                score=normalized_distance(notes,older)
                if score<=similarity:
                    candidates.append((score,previous_index))
        if candidates:
            distance,index=min(candidates)
            predecessor=phrases[index]
            item['motif_family']=predecessor['motif_family']
            item['develops_phrase_at']=predecessor['start_measure']
            item['similarity_distance']=distance
            item['relationship']=classify(distance,notes[0][3]-predecessor['_events'][0][3],notes,predecessor['_events'])
            item['pitch_shift_semitones']=notes[0][3]-predecessor['_events'][0][3]
        elif len(notes)>=4:
            item['motif_family']='F'+str(len(families)+1)
            families.append(item['motif_family'])
            item['relationship']='new_candidate'
        else:
            item['motif_family']=None
            item['relationship']='sparse_or_silent'
        item['_events']=notes
        phrases.append(item)
    output=[{k:v for k,v in phrase.items() if k!='_events'} for phrase in phrases]
    transitions=Counter()
    for a,b in zip(output,output[1:]):
        transitions[a['relationship']+' → '+b['relationship']]+=1
    return {'track':track['name'],'phrases':output,'unique_motif_families':len(families),
            'related_phrase_count':sum(bool(p.get('develops_phrase_at')) for p in output),
            'development_transitions':dict(transitions)}


def analyze(path):
    score=parse(path)
    seen=set();results=[];duplicates=[]
    for track in score['tracks']:
        if not any(word in track['name'].lower() for word in ('guitar','lead','rhythm','clean','distortion')):
            continue
        signature=tuple(tuple(bar) for bar in track['measures'])
        if signature in seen:
            duplicates.append(track['name']);continue
        seen.add(signature)
        results.append(analyze_track(track,score['sections'],score['measures']))
    return {'song':score['song'],'measure_count':score['measures'],
            'annotated_sections':[{'measure':m,'label':label} for m,label in score['sections']],
            'guitar_tracks':results,'duplicate_guitar_tracks_excluded':duplicates,
            'method':{'phrase_lengths':[1,2,3,4,6,8],
                      'phrase_segmentation':'4-bar preference plus local density/pitch change; section markers forced',
                      'development':'relative-pitch/timing edit-distance among earlier nonoverlapping phrases',
                      'similarity_threshold':.22,
                      'caveats':['Phrase boundaries are candidate estimates, not verified annotations',
                                 'Source tab section labels force section boundaries',
                                 'Only primary voice and bottom note of chords compared',
                                 'Some repetitions may be missed if phrase segmentation differs',
                                 'Families are greedy; similarity is not necessarily transitive',
                                 'No percussion or full chord-voicing relationships']}}


def main():
    ap=argparse.ArgumentParser(description='Map estimated phrases and their musical development')
    ap.add_argument('files',nargs='+',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    data=[analyze(file) for file in args.files]
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(data,indent=2),encoding='utf-8')
        print('Wrote '+str(args.output))
    else:print(json.dumps(data,indent=2))

if __name__=='__main__':main()