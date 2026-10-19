"""Additional source relationships with explicit local timing gates.

Existing whole-track detectors and eligibility flags are intentionally separate.
No region boundary grants permission to bridge an uncertain tie or slide.
"""
from collections import Counter, defaultdict
from source_semantics import unpitched_tie_continuity
from source_slides import resolve_slides
from source_timing_regions import local_timing_regions, relationship_region
from technique_analysis import classify_group


def relationship_details(part, headers, rows, grace=(), timing_warnings=(),
                         other_warnings=(), recover_groups=False):
    regions=local_timing_regions(part,headers,timing_warnings,other_warnings)
    by_id={r['occurrence']:r for r in [*rows,*grace]}
    grace_ids={r['occurrence'] for r in grace}
    slides=resolve_slides(rows,grace)
    for event in slides['events']:
        identifiers={event['occurrence'],*event.get('tied_members',[])}
        identifiers.update(event[k] for k in ('origin','destination','candidate_destination') if event.get(k))
        members=[by_id[i] for i in identifiers]
        lane=regions['voice_regions'].get(str(event['voice']),[])
        index=None if identifiers & grace_ids else relationship_region(lane,members)
        event['timing_region']=index
        event['timing_eligible']=index is not None
        if index is None and event['status'] in ('resolved_written_target','target_after_tie_candidate'):
            event['candidate_destination']=event['destination']
            event['status_before_timing_gate']=event['status']
            event.update(status='excluded_for_timing',destination=None,
                         interval_semitones=None,direction=None,transition_q=None)
    slides['status_counts']=dict(Counter(e['status'] for e in slides['events']))
    ties=dict(schema='source-local-unpitched-ties-v1',links=[],chains=[],unresolved=[])
    for voice,lane in regions['voice_regions'].items():
        for index,region in enumerate(lane):
            subset=[r for r in rows if str(r['voice'])==voice and relationship_region([region],[r]) is not None]
            result=unpitched_tie_continuity(subset)
            for key in ('links','chains','unresolved'):
                ties[key].extend(dict(item,timing_region=index) for item in result[key])
    ties['limitation']='Explicit unpitched written continuity only; no sounding sustain; no crossing unsafe regions'
    groups=[]
    if recover_groups:
        attacks=defaultdict(list)
        for row in rows:
            if not row['tie_destination']:attacks[row['onset_q']].append(row)
        for onset,notes in attacks.items():
            region=relationship_region(regions['all_voice_regions'],notes)
            if region is None:continue
            labels=classify_group(notes)
            if labels:groups.append(dict(onset_q=onset,members=[r['occurrence'] for r in notes],
                                         labels=labels,timing_region=region,
                                         pitch_effects_unresolved=any(r.get('pitch_effects') for r in notes)))
    return dict(local_timing=regions,slides=slides,unpitched_ties=ties,
                recovered_coattack_groups=groups,
                policy='Additional analysis only; original detector fields and global eligibility unchanged')
