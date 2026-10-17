"""Multiscale descriptive technique report. No inferred artist/phrase truth."""
from collections import Counter, defaultdict
from fractions import Fraction as F
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile
from exact_score import extract_score
from technique_analysis import analyze
from technique_effects import normalize_report


def rate(n,d):return dict(numerator=n,denominator=d,percent=100*n/d if d else None)


def summarize(score):
    report=normalize_report(analyze(score));tracks=[]
    for source,track in zip(score['tracks'],report['tracks']):
        notes={};sections=defaultdict(set);section='Unannotated';section_start=1
        for m in source['measures']:
            if m['section']:section=m['section'];section_start=m['number']
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    for ni,n in enumerate(e['notes']):
                        key=f"{source['index']}:{m['number']}:{vi}:{ei}:{ni}"
                        notes[key]=dict(n,section=f'{section_start}:{section}')
                        sections[f'{section_start}:{section}'].add(key)
        observed=Counter();eligible=Counter();conditions=defaultdict(Counter)
        for pair in track['eligible_transitions']:
            family=pair['direction']+'_'+pair['context'];eligible[family]+=1
        for pair in track['explicit_hopo']:
            family=pair['direction']+'_'+pair['context'];observed[family]+=1
            a,b=notes[pair['origin']],notes[pair['destination']]
            c=conditions[family];c['fret_distance:'+str(pair['fret_distance'])]+=1
            c['destination_duration_q:'+str(F(b['duration_q']))]+=1
            c['origin_fret:'+str(a['fret'])]+=1;c['section:'+a['section']]+=1
            c['destination_longer_or_equal' if F(b['duration_q'])>=F(a['duration_q']) else 'destination_shorter']+=1
        section_rows=[]
        for name,members in sections.items():
            pairs=[p for p in track['explicit_hopo'] if p['origin'] in members]
            candidates=[p for p in track['eligible_transitions'] if p['origin'] in members]
            section_rows.append(dict(section=name,note_occurrences=len(members),marked_hopo=rate(len(pairs),len(candidates)),families=dict(Counter(p['direction']+'_'+p['context'] for p in pairs))))
        groups=defaultdict(lambda:dict(intervals=0,coattacks=0,duration_q=F(0),pitch_effect_unresolved=0))
        for group in track['simultaneous_groups']:
            for family in group['labels']:
                g=groups[family];g['intervals']+=1;g['coattacks']+=int(group['coattack']);g['duration_q']+=F(group['end_q'])-F(group['onset_q']);g['pitch_effect_unresolved']+=int(group['requires_pitch_effect_resolution'])
        for g in groups.values():g['duration_q']=str(g['duration_q'])
        effects=Counter(e['family'] for e in track['normalized_effects'])
        tracks.append(dict(index=track['index'],scope=track['technique_scope'],note_occurrences=len(notes),attacks=track['attack_count'],
                           hopo_rates={f:rate(observed[f],eligible[f]) for f in sorted(set(observed)|set(eligible))},
                           hopo_conditions={f:dict(c) for f,c in conditions.items()},source_sections=section_rows,
                           simultaneous_groups=dict(groups),explicit_effect_occurrences=dict(effects),
                           pedal_candidates=dict(alternating=len(track['polyphonic_pedal_candidates']),bursts=len(track['pedal_burst_candidates']),recurrence_groups=len(track['polyphonic_pedal_recurrence_groups']),transformation_groups=len(track['pedal_transformation_groups']),period_sensitivity=track['pedal_period_sensitivity']),
                           phrase_metrics=None,phrase_reason='No independently validated phrase boundaries supplied',
                           source_marker_coverage='Observed notation only; unmarked does not establish an unperformed technique'))
    return dict(schema='gp-technique-multiscale-v1',source_sha256=score['source_sha256'],tracks=tracks,
                phrase_inference_used=False,artist_inference_used=False,
                limitations=['Written order, repeats not unfolded','Counts describe annotation and deterministic candidates, not technique prevalence in recorded audio','No musical-purpose, emotional-meaning or physical-playability labels inferred'])


def coverage(source):
    with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    return dict(staff_properties=dict(Counter(p.get('name') for p in root.findall('./Tracks/Track/Staves/Staff/Properties/Property'))),
                track_properties=dict(Counter(p.get('name') for p in root.findall('./Tracks/Track/Properties/Property'))),
                policy='Staff/track properties inventoried and preserved; unmodeled properties are unsupported interpretation, not discarded',
                raw_staff_semantics_certified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    result=dict(schema='gp-technique-corpus-v1',songs=[dict(**summarize(extract_score(s)),coverage=coverage(s)) for s in a.sources],
                corpus_artist=None,artist_reason='Input collection is not asserted to represent one artist')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2));print(json.dumps(dict(songs=len(result['songs']),phrase_labels_fabricated=0)))
