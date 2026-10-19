"""Frozen source-profile versus generated GP annotation rates, not style quality.

Source family-balanced attack rates and generated equal-piece rates have different
track mixes. Missing source performance labels remain notation absence, not sound
absence. Unsupported generated dimensions are unknown, never invented negatives.
"""
from collections import defaultdict,Counter
from fractions import Fraction as F
from pathlib import Path
import argparse,json
from xml.etree import ElementTree as ET
from artist_profiles import observations
from exact_score import extract_score,validate_events
from technique_analysis import analyze,enabled,classify_group

FEATURES=('bend','finger_vibrato','palm_mute','hammer_on_from_open','pull_off_to_open',
          'close_interval_texture','power_chord','extended_power_chord','double_stop')


def generated(score,artist):
    if validate_events(score):raise ValueError('Generated score clock discrepancies')
    analysis=analyze(score);tracks=[]
    for ti,t in enumerate(score['tracks']):
        groups=defaultdict(list);rows=[]
        for m in t['measures']:
            for vi,v in enumerate(m['voices']):
                for ei,e in enumerate(v):
                    for ni,n in enumerate(e['notes']):
                        if n.get('grace_type') or F(e['duration_q'])<=0:continue
                        if n.get('midi') is None or enabled(n['note_xml'],'Muted') or enabled(n['note_xml'],'Dead'):
                            raise ValueError('Generated annotation comparison requires known pitched, non-dead notes')
                        effects=[]
                        for prop,label in [('Bended','bend'),('PalmMuted','palmMute')]:
                            if enabled(n['note_xml'],prop):effects.append(label)
                        root=ET.fromstring(n['note_xml']);vibrato=root.findtext('Vibrato')
                        row=dict(occurrence=f'{ti}:{m["number"]}:{vi}:{ei}:{ni}',voice=vi,midi=n['midi'],fret=n['fret'],string=n['string'],
                            duration_q=e['duration_q'],onset_q=e['onset_q'],bar_offset_q=e['local_onset_q'],
                            tie_destination=(n.get('tie') or {}).get('destination')=='true',effects=effects,
                            raw_note=dict(vibrato=vibrato in ('Slight','Wide')),raw_beat_effects={})
                        rows.append(row)
                        if not row['tie_destination']:groups[F(e['onset_q'])].append(row)
        linked=analysis['tracks'][ti]['explicit_hopo']
        tracks.append(dict(part_id=ti,guitar_or_bass=isinstance(t.get('program'),int) and 24<=t['program']<=39,
            temporal_relationships_eligible=True,rows=rows,
            coattack_groups=[dict(onset_q=str(q),labels=classify_group(ns)) for q,ns in groups.items()],
            hopo_transition_candidates=[dict(origin=p['origin'],direction=p['direction'],context=p['context']) for p in linked]))
    song=dict(song_id=score['source_sha256'],artist=artist,provisional_partition='held_out',ai_generated=False,is_junk=False,
        notation_hash=score['source_sha256'],tracks=tracks)
    events,_=observations(dict(songs=[song]))
    for event in events:
        event['known']=[f for f in event['known'] if f in FEATURES];event['labels']=[f for f in event['labels'] if f in FEATURES]
    return events


def compare(source_model,paths,artist):
    if source_model.get('schema')!='artist-conditional-notation-v1' or source_model.get('weighting')!='family':
        raise ValueError('Expected family-weighted artist notation model')
    table=next((t for t in source_model['tables'] if t['artist']==artist and t['context']=='*'),None)
    if table is None:raise ValueError('No frozen source artist profile')
    pieces=[]
    for path in paths:
        events=generated(extract_score(path),artist);known=Counter();positive=Counter()
        for event in events:known.update(event['known']);positive.update(event['labels'])
        pieces.append(dict(file=path.name,events=len(events),known=dict(known),positive=dict(positive)))
    rates={}
    for f in FEATURES:
        denominator=F(table['known'].get(f,'0'));source=float(F(table['features'].get(f,'0'))/denominator) if denominator else None
        values=[p['positive'].get(f,0)/p['known'][f] for p in pieces if p['known'].get(f)]
        target=sum(values)/len(values) if values else None
        rates[f]=dict(source_family_balanced_attack_rate=source,generated_equal_piece_attack_rate=target,
            absolute_percentage_point_difference=100*abs(source-target) if source is not None and target is not None else None,
            known_generated_groups=sum(p['known'].get(f,0) for p in pieces),positive_generated_groups=sum(p['positive'].get(f,0) for p in pieces))
    return dict(schema='source-generated-annotation-rates-v1',artist=artist,pieces=pieces,features=rates,
        unknown_generated_dimensions=['pedal_call','pedal_response','slide','tapping','dead'],
        limitations=['Annotation distributions only, never a musical-style/quality score.',
            'Source all eligible guitar/bass tracks versus generated three-role arrangements: track-mix confounding.',
            'Only exact regular attacks; written pitches, not bend-adjusted/harmonic sounding constructions.',
            'Source marker absence does not establish absent physical performance.'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source_model','directory','out'):p.add_argument(name,type=Path)
    p.add_argument('--artist',default='Invent Animate');p.add_argument('--pattern',default='*-palm-100.gp');a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:p.error('Private report only')
    if a.out.exists():p.error('Output exists')
    paths=sorted(a.directory.glob(a.pattern))
    if not paths:p.error('No generated outputs')
    result=compare(json.loads(a.source_model.read_text(encoding='utf-8')),paths,a.artist)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result['features']))
