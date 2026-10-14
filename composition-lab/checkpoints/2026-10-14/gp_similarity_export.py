"""V15: safe GP7 export of independent chord, melody and rhythm controls.

Rhythm uses duration exchanges within a voice/bar; this is deliberately a
restricted, meter-preserving subset of symbolic rhythmic transforms.
Unsupported/unplayable edits are skipped and explicitly counted.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
from pathlib import Path
import random
import shutil
import zipfile
from xml.etree import ElementTree as ET
from extract import extract_score
from automatic_harmony_control import infer_harmony, _position, _write_note
from contextual_harmony import supplement_anchors
from harmonic_continuity import expand_agreed_anchors, at_time
from harmonic_relative import analyze_note, map_note
from similarity_controls import Controls, transform
from learned_patterns_v16 import plan_melody, plan_rhythm
from relational_learning_v17 import plan_intervals
from gp_occurrence_writer import apply_occurrence_edits


def _events(score, track):
    return [e for m in score['tracks'][track]['measures'] for v in m['voices'] for e in v]


def _harmony(score, track):
    observed, stats = infer_harmony(score, track)
    added, context = supplement_anchors(score, track, observed, max_gap=4)
    spans, continuity = expand_agreed_anchors(added, max_gap=4)
    return spans, {**stats, **context, **continuity}


def _plan_pitches(score, track, windows, controls, seed, melody_offsets, learned=False, learned_melody_strength=None):
    source=_events(score, track)
    timing=[{'onset':Fraction(e['onset_q']),'duration':Fraction(e['duration_q']),
             'pitches':tuple(n['midi'] for n in e['notes'] if n['midi'] is not None)} for e in source]
    chosen=transform(timing, windows, controls=Controls(controls.chords,controls.melody,0),
                     melody_offsets=melody_offsets,seed=seed)
    variation_strength = (controls.melody if learned_melody_strength is None else learned_melody_strength)
    learned_map,learned_stats=plan_melody(score,track,windows,chosen['harmony'],variation_strength,seed) if learned else ({},{})
    # V17: all note sequences contribute interval relationships, whether or not
    # harmony is confidently known. Harmonic-role substitutions retain priority.
    relation_map, relation_stats = (plan_intervals(score, track, variation_strength, seed,
                                exclude_events=learned_map.keys()) if learned else ({}, {}))
    timing_by_identity={id(event):chosen['events'][j] for j,event in enumerate(source)}
    tuning=score['tracks'][track]['tunings'][0]
    skipped_unplayable=0
    occurrence_edits={}
    for mi,measure in enumerate(score['tracks'][track]['measures']):
        for vi,voice in enumerate(measure['voices']):
            for ei,event in enumerate(voice):
                # The model uses object identity to label event-specific proposals.
                # Respect each event's position even when its GPIF ID is shared.
                # Lookup by identity, never structural equality.
                result=timing_by_identity.get(id(event))
                if result is None:raise AssertionError('Source event identity lost')
                notes=[(ni,n) for ni,n in enumerate(event['notes']) if n['midi'] is not None]
                pitches=learned_map.get(id(event),relation_map.get(id(event),result['pitches']))
                if len(notes)!=len(pitches):raise AssertionError('Incorrect note count')
                positions=[];used=set()
                for (ni,n),pitch in zip(notes,pitches):
                    pos=_position(pitch,tuning,n.get('string'),used=used)
                    if pos is None:break
                    used.add(pos[0]);positions.append((ni,n,(pitch,*pos)))
                if len(positions)!=len(notes):
                    skipped_unplayable+=1;continue
                for ni,n,position in positions:
                    if position[0]!=n['midi']:
                        occurrence_edits[mi,vi,ei,ni]=position
    return occurrence_edits, chosen, {'unplayable_events_skipped':skipped_unplayable,
                             'shared_note_definitions_skipped':0,**learned_stats,**relation_stats}


def _rhythm_swaps(score,track,windows, strength,seed):
    """Swap adjacent beat durations only if note starts stay in same harmony.

    Beat IDs must be used exactly once in the WHOLE score to avoid edits leaking
    to other measures/tracks. Preserve measure totals and source note identity.
    """
    if strength==0:return [],{'rhythm_swaps':0,'rhythm_pairs_ineligible':0}
    rng=random.Random(seed+101);usage=Counter()
    for tr in score['tracks']:
        for m in tr['measures']:
            for voice in m['voices']:
                for e in voice:usage[e['beat_id']]+=1
    swaps=[];ineligible=0
    for m in score['tracks'][track]['measures']:
        for voice in m['voices']:
            i=0
            while i+1<len(voice):
                a,b=voice[i:i+2];i+=2
                da,db=Fraction(a['duration_q']),Fraction(b['duration_q'])
                if da==db:continue
                if usage[a['beat_id']]!=1 or usage[b['beat_id']]!=1:
                    ineligible+=1;continue
                if any(n['tie'] for e in (a,b) for n in e['notes']):
                    ineligible+=1;continue
                t=Fraction(a['onset_q']);span=at_time(windows,t)
                # Both beats and their NEW start positions must remain inside a
                # single harmonic span, including the last beat's entire duration.
                if span is None or t+da+db>Fraction(span['end']):
                    ineligible+=1;continue
                if rng.random()<strength/100:swaps.append((a['beat_id'],b['beat_id']))
    return swaps,{'rhythm_swaps':len(swaps),'rhythm_pairs_ineligible':ineligible}


def export(source, destination, *, chords=0,melody=0,rhythm=0,track=0,seed=17,
           melody_offsets=(-2,-1,1,2),learned=False):
    controls=Controls(chords,melody,rhythm)
    source=Path(source);destination=Path(destination)
    if source.resolve()==destination.resolve():raise ValueError('Cannot overwrite original GP')
    score=extract_score(source)
    if track not in range(len(score['tracks'])):raise ValueError('Track index out of bounds')
    spans,stats=_harmony(score,track)
    pitch_controls=Controls(chords,0 if learned else melody,0)
    pitches,chosen,safety=_plan_pitches(score,track,spans,pitch_controls,seed,melody_offsets,learned=learned,learned_melody_strength=melody)
    swaps,rstats=_rhythm_swaps(score,track,spans,rhythm,seed) if not learned else ([],{})
    learned_rhythm,learned_rstats=plan_rhythm(score,track,spans,rhythm,seed) if learned else ({},{})
    clone_stats={'changed_note_occurrences':0,'cloned_notes':0,'cloned_beats':0,'cloned_voices':0,'cloned_bars':0}
    if not pitches and not swaps and not learned_rhythm:
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    else:
        with zipfile.ZipFile(source) as zi:
            members=[(i,zi.read(i.filename)) for i in zi.infolist()]
            root=ET.fromstring(zi.read('Content/score.gpif'))
        lookup={b.get('id'):b for b in root.findall('./Beats/Beat')}
        original_rhythm_refs={bid:node.find('Rhythm').get('ref') for bid,node in lookup.items() if node.find('Rhythm') is not None}
        for bid,source_bid in learned_rhythm.items():
            lookup[bid].find('Rhythm').set('ref',original_rhythm_refs[source_bid])
        for aid,bid in swaps:
            a=lookup[aid].find('Rhythm');b=lookup[bid].find('Rhythm')
            if a is None or b is None:raise ValueError('Missing beat rhythm reference')
            old_a,old_b=a.get('ref'),b.get('ref')
            a.set('ref',old_b);b.set('ref',old_a)
        clone_stats=apply_occurrence_edits(root,score,track,pitches,_write_note)
        xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(destination,'w') as zo:
            for info,data in members:zo.writestr(info,xml if info.filename=='Content/score.gpif' else data)
    actual=extract_score(destination)
    if actual['measure_count']!=score['measure_count']:raise AssertionError('Structure changed')
    # Verify exact meter, unchanged rest/note order, unchanged other tracks,
    # and unchanged timing where rhythm is locked.
    for index,(old,new) in enumerate(zip(score['tracks'],actual['tracks'])):
        for om,nm in zip(old['measures'],new['measures']):
            if om['time_signature']!=nm['time_signature']:raise AssertionError('Meter changed')
            for ov,nv in zip(om['voices'],nm['voices']):
                if len(ov)!=len(nv):raise AssertionError('Event count changed')
                for a,b in zip(ov,nv):
                    if len(a['notes'])!=len(b['notes']):raise AssertionError('Note count changed')
                    if index!=track or rhythm==0:
                        if (a['onset_q'],a['duration_q'])!=(b['onset_q'],b['duration_q']):raise AssertionError('Locked timing changed')
                    if index!=track:
                        if [n['midi'] for n in a['notes']]!=[n['midi'] for n in b['notes']]:raise AssertionError('Other track changed')
    return {'source':source.name,'output':str(destination),'track':track,'seed':seed,
            'controls':{'chords':chords,'melody':melody,'rhythm':rhythm},
            'changed_note_definitions':clone_stats['cloned_notes'],**clone_stats,'harmonic_windows':len(spans),
            'transformation':chosen['report'],**stats,**safety,**rstats,**learned_rstats,'learned':learned,
            'limitations':('Learned mode substitutes source-observed 2–4 event patterns only where compatible and safely exportable; ' if learned else 'Rhythm uses adjacent swaps; ')+'unknown harmony is preserved; strengths are probabilities, not calibrated musical distances'}


def main():
    import json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--track',type=int,default=0);p.add_argument('--chords',type=float,default=0)
    p.add_argument('--melody',type=float,default=0);p.add_argument('--rhythm',type=float,default=0)
    p.add_argument('--seed',type=int,default=17)
    p.add_argument('--learned',action='store_true')
    a=p.parse_args();print(json.dumps(export(a.source,a.output,chords=a.chords,melody=a.melody,
                              rhythm=a.rhythm,track=a.track,seed=a.seed,learned=a.learned),indent=2,default=str))
if __name__=='__main__':main()