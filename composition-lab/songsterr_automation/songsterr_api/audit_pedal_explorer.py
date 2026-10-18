"""Compare displayed evidence with fresh clip-local detection; never edit cases.

This is a diagnostic experiment, not a replacement pedal classifier. Source
occurrences and musical feedback stay in ignored local-artifacts directories.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pedal_regions import detect_regions


def audit_case(case, track):
    base, stop = F(case['base_q']), F(case['end_q'])
    rows = [n for n in track['rows'] if base <= F(n['onset_q']) < stop]
    attacks = [n for n in rows if not n['tie_destination'] and n['midi'] is not None]
    byid = {n['occurrence']: n for n in attacks}
    displayed = {n['id']: n['role'] for n in case['notes']}
    groups = defaultdict(list)
    for n in attacks:
        groups[F(n['onset_q'])].append(n)
    local = detect_regions(rows)
    local_members = {n for r in local for n in r['anchor_occurrences']}
    marked = {ident for ident, role in displayed.items() if role == 'call'}
    mixed = {ident for ident, role in displayed.items() if role == 'mixed'}
    anchor = set(case['anchor'])
    parent_dyad_without_higher_answer = bool(len(anchor) > 1 and
        not any(n['midi'] > max(anchor) for n in attacks))
    return dict(id=case['id'], song_id=case['song_id'], part_id=track['part_id'],
                bars=[case['start_bar'], case['end_bar']],
                written_notes=len(rows), attack_notes=len(attacks),
                tie_segments_excluded=len(rows)-len([n for n in rows if not n['tie_destination']]),
                displayed_call_attacks=len({F(byid[i]['onset_q']) for i in marked if i in byid}),
                selected_cycles=len(case['cycles']),
                selected_closed_cycles=sum(c['closed_by_anchor_return'] for c in case['cycles']),
                singleton_cycle_selection=len(case['cycles']) == 1,
                parent_dyad_without_higher_answer=parent_dyad_without_higher_answer,
                mixed_notes_at_anchor_pitch=sum(i in byid and byid[i]['midi'] in anchor for i in mixed),
                mixed_notes_outside_anchor=sum(i in byid and byid[i]['midi'] not in anchor for i in mixed),
                context_notes_at_anchor_pitch=sum(displayed.get(n['occurrence']) == 'context' and n['midi'] in anchor for n in attacks),
                clip_local_regions=local,
                alternatives={name:detect_regions(rows, **policy) for name,policy in POLICIES.items()},
                local_anchor_occurrences_unmarked=sorted(local_members-marked),
                local_marked_overlap=len(local_members & marked),
                event_signatures=[dict(onset_q=str(q), pitches=sorted({n['midi'] for n in ns}),
                    ids=[n['occurrence'] for n in ns]) for q, ns in sorted(groups.items())])


POLICIES={
    'two_returns':dict(minimum_return_pairs=2),
    'higher_than_whole_anchor':dict(contrast_above_entire_anchor=True),
    'combined':dict(minimum_return_pairs=2,contrast_above_entire_anchor=True),
}


def run(report, cases):
    songs = {s['song_id']: s for s in report['songs']}
    records = []
    for case in cases:
        part = int(case['notes'][0]['id'].split(':')[0])
        track = next(t for t in songs[case['song_id']]['tracks'] if t['part_id'] == part)
        records.append(audit_case(case, track))
    corpus={name:dict(regions=0,changed_tracks=0,removed_anchor_section_keys=0,
                     added_anchor_section_keys=0) for name in dict(baseline={},**POLICIES)}
    for song in report['songs']:
        for track in song['tracks']:
            if not track['guitar_or_bass'] or not track['temporal_relationships_eligible']:continue
            baseline=detect_regions(track['rows'])
            before={tuple(r['anchor_pitches'])+(r['section_start'],) for r in baseline}
            for name,policy in dict(baseline={},**POLICIES).items():
                alternative=detect_regions(track['rows'],**policy)
                after={tuple(r['anchor_pitches'])+(r['section_start'],) for r in alternative}
                counts=corpus[name]
                counts['regions']+=len(alternative);counts['changed_tracks']+=alternative!=baseline
                counts['removed_anchor_section_keys']+=len(before-after)
                counts['added_anchor_section_keys']+=len(after-before)
    return dict(schema='pedal-explorer-audit-v1', records=records,corpus_experiments=corpus,
        summary=dict(cases=len(records), singleton_selections=sum(r['singleton_cycle_selection'] for r in records),
            dyad_without_higher_answer=sum(r['parent_dyad_without_higher_answer'] for r in records),
            mixed_anchor_notes=sum(r['mixed_notes_at_anchor_pitch'] for r in records),
            mixed_nonanchor_notes=sum(r['mixed_notes_outside_anchor'] for r in records)),
        limitations=['Clip-local detection is an alternative experiment, not adjudicated truth.',
            'Ties are excluded from attack counts; written segments remain preserved.',
            'Unmarked notes are not automatically false negatives; human judgments remain separate.',
            'Current mixed event labels conflate individual note roles; counts expose this without changing semantics.'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('report', type=Path); p.add_argument('cases', type=Path); p.add_argument('out', type=Path)
    a=p.parse_args()
    if 'local-artifacts' not in a.out.resolve().parts:
        p.error('Occurrence evidence stays private')
    result=run(json.loads(a.report.read_text(encoding='utf-8-sig')), json.loads(a.cases.read_text(encoding='utf-8-sig')))
    result['inputs']={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in [('report',a.report),('cases',a.cases)]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['summary']))
