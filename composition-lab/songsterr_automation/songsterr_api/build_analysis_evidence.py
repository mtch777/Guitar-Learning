"""Build a small private, source-located evidence pack from the full analysis.

Every selected occurrence is checked against cached raw JSON, not a generated GP.
"""
import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=32)
def load_part(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check_occurrence(root, song_id, track, row):
    p=root/str(song_id)/f'track-{track["part_id"]}.json'
    part=load_part(p)
    m=part['measures'][row['bar']-1]
    beat=m['voices'][row['voice']]['beats'][row['beat']]
    note=beat['notes'][row['note']]
    if row['raw_note']!=note or row['raw_beat_effects']!={k:v for k,v in beat.items() if k!='notes'}:
        raise ValueError('Occurrence does not match raw source: '+row['occurrence'])
    return p


def build(report, root):
    selected=[];used=Counter();families={};verified=0
    for song in report['songs']:
        if song['ai_generated'] is not False or song['is_junk'] is not False:continue
        for track in song['tracks']:
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
            lookup={r['occurrence']:r for r in track['rows']}
            candidates=[]
            for k,ids in track['examples'].items():candidates.append((k,ids[:1]))
            for g in track['coattack_groups']:
                for k in g['labels']:
                    if k not in {c[0] for c in candidates}:candidates.append((k,g['members']))
            for g in track['hopo_transition_candidates']:
                k=g['direction']+'_'+g['context']
                if k not in {c[0] for c in candidates}:candidates.append((k,[g['origin'],g['destination']]))
            if track['pedal_candidates']:
                g=track['pedal_candidates'][0]
                candidates.append(('pedal_burst_candidate',[ident for run in g['members'] for group in run for ident in group]))
            if track['counterexamples']:candidates.append(('whole_step_counterexample',track['counterexamples'][0]['members']))
            for label,ids in candidates:
                key=(label,song['candidate_work_family'])
                if used[label]>=3 or key in families:continue
                target=[lookup[ident] for ident in ids]
                start=min(r['bar'] for r in target);end=max(r['bar'] for r in target)
                context=[r for r in track['rows'] if start-1<=r['bar']<=end+1]
                for r in context:check_occurrence(root,song['song_id'],track,r);verified+=1
                # Matched notation control: same track and written duration, unmarked.
                control=None
                if label in track['examples']:
                    control=next((r for r in track['rows'] if label not in r['effects'] and r['duration_q']==target[0]['duration_q'] and r['tie_destination']==target[0]['tie_destination']),None)
                    if control:check_occurrence(root,song['song_id'],track,control);verified+=1
                validation_path=root/str(song['song_id'])/'gp7-validation.json'
                validation=json.loads(validation_path.read_text(encoding='utf-8-sig')) if validation_path.exists() else {}
                selected.append(dict(label=label,song_id=song['song_id'],revision_id=song['revision_id'],title=song['title'],
                                     track_id=track['part_id'],track_name=track['name'],start_bar=start,end_bar=end,
                                     target_occurrences=ids,source_context=context,unmarked_duration_matched_control=control,
                                     source_gp=str((root/str(song['song_id'])/'score.gp').resolve()),
                                     gp_snapshot_roundtrip_pass=validation.get('roundtripPass'),
                                     gp_direct_regular_notation_differences=validation.get('directSource',{}).get('differences'),
                                     status='source-notation evidence; musical function and feel unadjudicated'))
                used[label]+=1;families[key]=True
    return dict(schema='source-technique-evidence-v1',examples=selected,by_label=dict(used),raw_occurrences_verified=verified,
                limitations=['No accuracy estimate from self-selected source examples','Unmarked controls do not prove the technique was absent in performance',
                             'Some rare markers have fewer than three eligible source families','No synthesized listening substitutes or generation-quality verdict'])


def markdown(report, pack):
    rows=['# Private corpus analysis','',
          'Written notation observations. No new listening judgment or artist-feel claim. See `relationships.json` for exact occurrences and conditional distributions.',
          '', '| Technique marker | Entries with marker / all entries | Pooled note-segment share |', '|---|---:|---:|']
    counts=Counter();segments=0
    for s in report['songs']:
        segments+=s['summary']['note_segments']
        counts.update({k:v['numerator'] for k,v in s['summary']['marker_shares'].items()})
    for k,n in counts.most_common():
        entries=sum(k in s['summary']['marker_shares'] for s in report['songs'])
        rows.append(f'| {k} | {entries}/{len(report["songs"])} | {100*n/segments:.3f}% ({n}/{segments}) |')
    rows+=['','## Traceable examples','', 'All examples below come from entries without AI/junk flags and tracks without detected bar overflow. These flags do not establish transcription correctness. Exact raw source context and duration-matched unmarked controls are in `analysis-evidence.json`.','']
    for e in pack['examples']:
        rows.append(f'- **{e["label"]}** — {e["title"]}; track {e["track_id"]}: {e["track_name"]}; bars {e["start_bar"]}–{e["end_bar"]}; Songsterr {e["song_id"]}, revision {e["revision_id"]}. [GP](<{e["source_gp"]}>); tested GP snapshot roundtrip: {e["gp_snapshot_roundtrip_pass"]} (not proof of complete source fidelity).')
    return '\n'.join(rows)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--aggregate',type=Path);a=p.parse_args();root=a.corpus.resolve()
    if 'local-artifacts' not in root.parts:p.error('Evidence must remain private in local-artifacts')
    report_path=root/('relationships-v2.json' if (root/'relationships-v2.json').exists() else 'relationships.json')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    suffix='-v2' if report['schema'].endswith('-v2') else ''
    pack=build(report,root/'songs')
    (root/('analysis-evidence'+suffix+'.json')).write_text(json.dumps(pack,indent=2),encoding='utf-8')
    (root/('ANALYSIS_V2.md' if suffix else 'ANALYSIS.md')).write_text(markdown(report,pack),encoding='utf-8')
    if a.aggregate:
        public=json.loads(a.aggregate.read_text(encoding='utf-8'))
        if public.get('schema')!=report['schema']:raise ValueError('Aggregate schema mismatch')
        public['evidence_validation']=dict(examples=len(pack['examples']),by_label=pack['by_label'],raw_occurrences_verified=pack['raw_occurrences_verified'])
        a.aggregate.write_text(json.dumps(public,indent=2),encoding='utf-8')
    print(json.dumps(dict(examples=len(pack['examples']),by_label=pack['by_label'],raw_occurrences_verified=pack['raw_occurrences_verified'])))
