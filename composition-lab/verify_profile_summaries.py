"""Reconcile descriptive summary denominators against the frozen source report.

Output includes private inventories: keep it outside Git. This does not verify
source performance, detection recall or musical meaning.
"""
from collections import defaultdict
from fractions import Fraction as F
import argparse
import json
from pathlib import Path

from artist_note_summaries import summarize_notes, marker_state, MARKERS
from relationship_profile_summary import summarize
from engine_contract import sha


def verify(report, model, artist):
    inventories={}
    for partition in ('development','held_out'):
        result=summarize_notes(report,artist,partition=partition)
        counts={f:dict(segments=0,known=0,positive=0,attacks=0,attack_known=0,
                      attack_positive=0,mass=F(0),positive_mass=F(0),unknown_mass=F(0),
                      unknown_duration=0) for f in MARKERS}
        for song in report['songs']:
            if (song.get('artist') != artist or song['provisional_partition'] != partition
                or song.get('ai_generated') is not False or song.get('is_junk') is not False):continue
            for track in song['tracks']:
                if not track.get('guitar_or_bass') or not track.get('temporal_relationships_eligible'):continue
                for row in track['rows']:
                    if row.get('grace') or row.get('grace_type') or (row.get('raw_beat_effects') or {}).get('graceNote'):continue
                    for feature,c in counts.items():
                        state,_=marker_state(row,feature)
                        attack=row.get('tie_destination') is False
                        c['segments']+=1;c['known']+=state is not None;c['positive']+=state is True
                        c['attacks']+=attack;c['attack_known']+=attack and state is not None
                        c['attack_positive']+=attack and state is True
                        if row.get('duration_q') is None:c['unknown_duration']+=1
                        elif state is None:c['unknown_mass']+=F(row['duration_q'])
                        else:
                            c['mass']+=F(row['duration_q'])
                            if state:c['positive_mass']+=F(row['duration_q'])
        for feature,c in counts.items():
            aggregate=result['artist_aggregate'][feature]
            for view,keys in [('written_regular_segments',('segments','known','positive')),
                              ('fresh_note_attacks',('attacks','attack_known','attack_positive'))]:
                for field,key in zip(('candidates','known','positive'),keys):
                    assert aggregate[view][field]==c[key],(partition,feature,view,field)
                    assert sum(s['metrics'][feature][view][field] for s in result['songs'])==c[key]
                    assert sum(s['metrics'][feature][view][field] for s in result['track_sections'])==c[key]
            mass=aggregate['written_note_duration_mass']
            for field,key in [('known_q','mass'),('positive_q','positive_mass'),('unknown_marker_q','unknown_mass')]:
                assert F(mass[field])==c[key]
                assert sum((F(s['metrics'][feature]['written_note_duration_mass'][field]) for s in result['track_sections']),F(0))==c[key]
            assert mass['unknown_duration_count']==c['unknown_duration']
            for view in ('written_regular_segments','fresh_note_attacks','written_note_duration_mass'):
                families=defaultdict(list);rates=[];positives=0
                for song in result['songs']:
                    metric=song['metrics'][feature][view]
                    den=F(metric['known_q']) if view=='written_note_duration_mass' else metric['known']
                    pos=F(metric['positive_q']) if view=='written_note_duration_mass' else metric['positive']
                    if not den:continue
                    rate=F(pos)/F(den);rates.append(rate);positives+=pos>0
                    families[song['family']].append(rate)
                actual=aggregate[view]
                for key,value in [('equal_song_rate',sum(rates)/len(rates) if rates else None),
                                  ('family_balanced_rate',sum(sum(v)/len(v) for v in families.values())/len(families) if families else None)]:
                    assert actual[key] is None if value is None else abs(actual[key]-float(value))<1e-12
                assert actual['eligible_songs']==len(rates) and actual['songs_with_annotation']==positives
                assert actual['eligible_families']==len(families)
                assert actual['families_with_annotation']==sum(any(v>0 for v in rates) for rates in families.values())
        inventories[partition]=result
    aggregate=summarize(model)
    grouped=defaultdict(list)
    for row in model['technique_song_summaries']:grouped[row['feature']].append(row)
    for feature,rows in grouped.items():
        metric=aggregate['features'][feature]
        n=sum(r['eligible_attack_groups'] for r in rows);y=sum(r['positive_attack_groups'] for r in rows)
        rates=[F(r['positive_attack_groups'],r['eligible_attack_groups']) for r in rows]
        families=defaultdict(list)
        for r,rate in zip(rows,rates):families[r['family']].append(rate)
        checks=dict(pooled_rate=F(y,n),equal_score_rate=sum(rates)/len(rates),
                    equal_family_rate=sum(sum(v)/len(v) for v in families.values())/len(families))
        for key,value in checks.items():assert abs(metric[key]-float(value))<1e-12,(feature,key)
        assert metric['eligible_groups']==n and metric['positive_groups']==y
    return dict(schema='summary-reconciliation-v1',inventories=inventories,aggregate=aggregate,
                checks=dict(partitions=2,note_features=len(MARKERS),group_features=len(grouped),
                            denominator_reconciliation=True),
                limitations=['Marker classification reused, not independent detector validation',
                             'Frozen global temporal eligibility unchanged; no recovered-track expansion',
                             'Notation inventory, not performed technique or musical acceptance'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--artist',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=verify(json.loads(args.report.read_text(encoding='utf-8')),
                  json.loads(args.model.read_text(encoding='utf-8')),args.artist)
    result['input_seals']=dict(report=sha(args.report),model=sha(args.model))
    with args.output.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2)
    print(json.dumps(result['checks']))
