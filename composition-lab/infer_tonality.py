"""Explainable, configurable tonal-center and mode hypotheses for GP7 scores.

Standard library only. Does not equate key signature with tonal center, or bass
pitch with chord root. Hypothesis scores are heuristic, NOT probabilities.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from phrase_development import parse

NAMES = ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')
MODES = {
    'Ionian': (0,2,4,5,7,9,11), 'Dorian': (0,2,3,5,7,9,10),
    'Phrygian': (0,1,3,5,7,8,10), 'Lydian': (0,2,4,6,7,9,11),
    'Mixolydian': (0,2,4,5,7,9,10), 'Aeolian': (0,2,3,5,7,8,10),
    'Locrian': (0,1,3,5,6,8,10),
}
CHORD_TYPES = {'power':(0,7),'major':(0,4,7),'minor':(0,3,7),
               'sus2':(0,2,7),'sus4':(0,5,7),'dim':(0,3,6),
               'aug':(0,4,8),'major7':(0,4,7,11),'minor7':(0,3,7,10),
               'dom7':(0,4,7,10)}

@dataclass(frozen=True)
class Settings:
    # Exposed to the CLI as a JSON object so parameters can be tuned on held-out data.
    note: float = 0.7
    sustained: float = 1.0
    bass: float = 1.8
    strong_bass: float = 1.2
    chord_root: float = 2.0
    bass_chord_agreement: float = 2.8
    cadence: float = 2.4
    ending: float = 2.5
    pitch_collection: float = 1.8
    prior: float = 0.12
    mode_margin: float = 0.08
    center_margin: float = 0.10
    minimum_evidence: float = 2.0
    mode_min_coverage: float = 0.73

    @classmethod
    def load(cls, values=None):
        if values is None:return cls()
        unknown=set(values)-set(cls.__dataclass_fields__)
        if unknown:raise ValueError('Unknown weights: '+', '.join(sorted(unknown)))
        if any(not isinstance(v,(float,int)) or v<0 for v in values.values()):
            raise ValueError('All weights must be nonnegative numbers')
        return cls(**values)


def track_type(name):
    lower=name.lower()
    if 'drum' in lower or 'percussion' in lower:return 'percussion'
    if 'bass' in lower:return 'bass'
    if any(x in lower for x in ('guitar','lead','rhythm','clean','distortion')):return 'guitar'
    return 'other'


def chord_hypotheses(pitches, bass=None):
    """Chord fit with inversion/slash-bass status. May return competing candidates."""
    pcs={int(p)%12 for p in pitches}
    if len(pcs)<2:return []
    choices=[]
    for root in range(12):
        for quality,intervals in CHORD_TYPES.items():
            chord={(root+i)%12 for i in intervals}
            matched=pcs & chord
            if len(matched)<2:continue
            precision=len(matched)/len(pcs)
            coverage=len(matched)/len(chord)
            fit=0.7*precision+0.3*coverage
            if bass is None: bass_relation='absent'
            elif bass%12==root:bass_relation='root'
            elif bass%12 in chord:bass_relation='inversion'
            else:bass_relation='nonchord_or_pedal'
            # Do not discard an explicit chord because the bass disagrees.
            if bass_relation=='root':fit+=.08
            if bass_relation=='inversion':fit+=.02
            choices.append({'root':root,'quality':quality,'score':round(fit,4),
                            'bass_relation':bass_relation,'matched':sorted(matched),
                            'extra_notes':sorted(pcs-chord)})
    return sorted(choices,key=lambda c:(-c['score'],-len(c['matched']),c['root'],c['quality']))[:8]


def collect(score):
    """Use primary guitar/bass tracks; avoid doubled identical arrangements.

    GP phrase extractor only emits fretted pitched events. Chord roots are
    evidenced by synchronous pitch clusters, not all notes in a measure.
    """
    tracks=[];dedup=set();excluded=[]
    for track in score['tracks']:
        kind=track_type(track['name'])
        if kind not in ('guitar','bass'):continue
        signature=tuple(tuple((v,t,d,p) for v,t,d,p in bar) for bar in track['measures'])
        if kind=='guitar' and signature in dedup:
            excluded.append(track['name']);continue
        if kind=='guitar':dedup.add(signature)
        tracks.append((kind,track))
    measures=[]
    for i in range(score['measures']):
        notes=Counter();bass=Counter();chords=[];melody=[]
        for kind,track in tracks:
            events=track['measures'][i]
            if kind=='bass':
                for voice,onset,duration,pitches in events:
                    for pitch in pitches:
                        bass[pitch%12]+=duration
            else:
                for voice,onset,duration,pitches in events:
                    # Deduplicate same-time layered notes, but preserve repeated attacks.
                    for pitch in pitches:notes[pitch%12]+=duration
                    if len(set(p%12 for p in pitches))>=2:
                        chords.append({'onset':onset,'duration':duration,
                                       'pitches':[p%12 for p in pitches],
                                       'lowest_pitch':min(pitches)%12})
                    if voice==0 and len(pitches)==1:
                        melody.append((onset,duration,pitches[0]%12))
        first=melody[0][2] if melody else None
        last=melody[-1][2] if melody else None
        measures.append({'number':i+1,'notes':notes,'bass':bass,'chords':chords,
                         'melody_first':first,'melody_last':last})
    return measures,excluded


def candidate_evidence(measures,settings,section_starts=(),key_signature=None):
    """Return a ranked profile for every tonic/mode pair plus evidence traces."""
    tonic=Counter();collection=Counter();support=defaultdict(Counter)
    section_starts={int(x) for x in section_starts}
    end_bars={m-1 for m in section_starts if m>1}
    end_bars.add(len(measures))
    for m in measures:
        weight=1+float(m['number'] in end_bars)*settings.ending
        # Note distribution is secondary: it mainly establishes a pitch collection.
        for pc,dur in m['notes'].items():
            collection[pc]+=dur*settings.note
        for pc,dur in m['bass'].items():
            collection[pc]+=dur*.6
            val=dur*(settings.bass+settings.strong_bass*float(m['number'] in section_starts))
            tonic[pc]+=val;support[pc]['bass']+=val
        if m['melody_last'] is not None and m['number'] in end_bars:
            pc=m['melody_last'];val=settings.cadence*weight
            tonic[pc]+=val;support[pc]['structural_melody_ending']+=val
        for chord in m['chords']:
            bass_pc=m['bass'].most_common(1)[0][0] if m['bass'] else None
            candidates=chord_hypotheses(chord['pitches'],bass=bass_pc)
            if not candidates:continue
            best=candidates[0]['score'];plausible=[c for c in candidates if best-c['score']<.055]
            if not plausible:continue
            for c in plausible:
                # Distribute ambiguous chord evidence across alternatives, not assert one root.
                val=settings.chord_root*chord['duration']*c['score']/len(plausible)
                tonic[c['root']]+=val;support[c['root']]['explicit_chord']+=val
                if c['bass_relation']=='root':
                    joint=settings.bass_chord_agreement*chord['duration']/len(plausible)
                    tonic[c['root']]+=joint
                    support[c['root']]['bass_chord_agreement']+=joint
    if key_signature is not None:
        # Input metadata is a weak hint for pitch collection, never proof of tonic.
        # Specifying this explicitly requires an external reliable parser.
        for pc in key_signature:collection[pc]+=settings.prior
    total_tonic=sum(tonic.values());total_pitch=sum(collection.values())
    if not total_tonic or not total_pitch:
        return {'ranked':[],'tonic_candidates':[],'evidence_amount':total_tonic,
                'status':'insufficient_evidence'}
    centers=[]
    for pc in range(12):
        centers.append({'tonic':NAMES[pc], 'pc':pc,
                        'relative_support':round(tonic[pc]/total_tonic,4),
                        'evidence':{k:round(v,3) for k,v in support[pc].items()}})
    centers.sort(key=lambda x:-x['relative_support'])
    candidates=[]
    for pc in range(12):
        center_part=tonic[pc]/total_tonic
        for mode,intervals in MODES.items():
            scale={(pc+x)%12 for x in intervals}
            in_scale=sum(collection[n] for n in scale)
            coverage=in_scale/total_pitch
            score=center_part+settings.pitch_collection*coverage
            candidates.append({'tonic':NAMES[pc],'mode':mode,'score':round(score,5),
                               'center_score':round(center_part,5),
                               'pitch_collection_coverage':round(coverage,4),
                               'out_of_scale_notes':[NAMES[x] for x in range(12) if collection[x] and x not in scale]})
    candidates.sort(key=lambda x:-x['score'])
    best=candidates[0];second=candidates[1]
    tonic_margin=centers[0]['relative_support']-centers[1]['relative_support']
    same_tonic=sorted((c for c in candidates if c['tonic']==best['tonic']),key=lambda x:-x['score'])
    mode_margin=same_tonic[0]['score']-same_tonic[1]['score']
    source_kinds={k for items in support.values() for k in items}
    if total_tonic<settings.minimum_evidence or best['pitch_collection_coverage']<settings.mode_min_coverage:
        status='insufficient_evidence'
    elif not source_kinds.intersection({'bass','explicit_chord','bass_chord_agreement'}):
        status='melody_only_weak_evidence'
    elif tonic_margin<settings.center_margin:
        status='tonic_ambiguous'
    elif mode_margin<settings.mode_margin:
        status='mode_ambiguous'
    else:status='tentative_tonic_and_mode'
    return {'status':status,'ranked':candidates[:12],
            'tonic_candidates':centers[:6],
            'evidence_amount':round(total_tonic,3),
            'margins':{'tonic':round(tonic_margin,4),'mode':round(mode_margin,4)},
            'interpretation':'Heuristic rankings, NOT calibrated probabilities or validated keys'}


def infer(path,settings=None):
    settings=settings or Settings()
    score=parse(path)
    measures,excluded=collect(score)
    starts=[m for m,_ in score['sections']]
    overall=candidate_evidence(measures,settings,starts)
    boundaries=sorted({1,score['measures']+1}|set(starts))
    sections=[]
    for a,b in zip(boundaries,boundaries[1:]):
        label=next((name for measure,name in score['sections'] if measure==a),None)
        sections.append({'label':label,'start_measure':a,'end_measure':b-1,
                         'inference':candidate_evidence(measures[a-1:b-1],settings,(1,b-a+1))})
    return {'song':score['song'],'written_key_signature':'not_read_by_this_module',
            'overall':overall,'sections':sections,'excluded_exact_double_tracks':excluded,
            'parameters':asdict(settings),
            'limitations':['Tonality is not verified by audio or human annotation',
                'No reliable GP key metadata parsed; not assumed to be actual key',
                'Missing rests and ties in the upstream parser may affect timing',
                'Chords are inferred from simultaneous notes and may be inversions or pedals',
                'Melody endings are heuristic and include ordinary measure endings',
                'Pitch collection may support several relative modes; model preserves ambiguity',
                'No automatic modulation detection outside annotated sections']}


def main():
    p=argparse.ArgumentParser(description='Rank tonal centers/modes without forcing a key')
    p.add_argument('files',nargs='+',type=Path)
    p.add_argument('--settings',type=Path,help='Optional JSON dictionary of weights')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    settings=Settings.load(json.loads(args.settings.read_text()) if args.settings else None)
    report=[infer(path,settings) for path in args.files]
    result=json.dumps(report,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(result,encoding='utf-8')
        print('Wrote',args.output)
    else:print(result)
if __name__=='__main__':main()