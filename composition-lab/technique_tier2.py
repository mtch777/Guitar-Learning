"""Connect retained technique relationships to complete preceding Tier1 only.

No raw-file reads, detector changes, generated notes or performed-sound claims.
"""
from copy import deepcopy
import json
from source_fact_tier1 import project_documents,fact_id
from freeze_technique_baseline import retained
from technique_observation_relations import lift,realize


TRACK_RELATION_FIELDS=(
    'name','guitar_or_bass','program_guitar_or_bass','catalog_flags',
    'summary','sections','examples','counterexamples',
    'rest_spans','technique_values','technique_value_histograms',
    'sustain_relationships','physical_notation_flags','relationship_details',
    'temporal_relationships_eligible','timing_warnings','identity_warnings',
    'coattack_groups','hopo_transition_candidates','unresolved_hp',
)


def occurrence_pointer(ident,documents):
    part,bar,voice,beat,note=map(int,ident.split(':'))
    document=f'track-{part}.json'
    if document not in documents:raise ValueError('Technique occurrence references absent source part')
    return fact_id(document,f'/measures/{bar-1}/voices/{voice}/beats/{beat}/notes/{note}')


def analyze(tier1):
    """Compatibility projection is ephemeral; persist references/relations only."""
    documents=project_documents(tier1)
    # JSON object keys are strings. Match the frozen persisted baseline,
    # including histogram keys emitted as Python integers by retained code.
    result=json.loads(json.dumps(retained(documents),allow_nan=False))
    tracks=[];known={r['id'] for r in tier1['facts']}
    for track in result['tracks']:
        original=track['analysis'];rows=original['rows']+original['grace_rows']
        if set(original)!=set(TRACK_RELATION_FIELDS)|{'part_id','rows','grace_rows','pedal_candidates'}:raise ValueError('Unmapped retained analysis field')
        references=[]
        for row in rows:
            ref=occurrence_pointer(row['occurrence'],documents)
            if ref not in known:raise ValueError('Invented technique source occurrence')
            references.append(dict(occurrence_ref=row['occurrence'],musical_occurrence_ref=f"event:{documents['metadata.json']['songId']}:{row['occurrence']}",source_fact_ref=ref,onset_q=row['onset_q'],duration_q=row['duration_q'],grace=row in original['grace_rows']))
        # Evidence event rows can contain the full legacy source row. Store only
        # event time + note IDs; exact full report remains a private QA baseline.
        sections=[]
        for section in track['approved_pedal_sections']:
            item=deepcopy(section)
            if 'evidence' in item:
                item['evidence']['events']=[dict(onset_q=e['onset_q'],note_refs=[n['occurrence'] for n in e['notes']]) for e in item['evidence'].get('events',[])]
            sections.append(item)
        tracks.append(dict(part_id=original['part_id'],source_occurrences=references,
                           retained_field_dispositions={k:('persisted_relationship' if k in TRACK_RELATION_FIELDS else 'part_identity' if k=='part_id' else 'replaced_by_approved_pedal_evidence_support_expansion' if k=='pedal_candidates' else 'recomputed_from_T1_with_source_time_occurrence_links') for k in original},
                           **{k:deepcopy(original[k]) for k in TRACK_RELATION_FIELDS},
                           dynamics=[dict(occurrence_ref=r['occurrence'],**r['dynamic']) for r in rows],
                           approved_pedal_sections=sections,
                           approved_pedal_seeds=deepcopy(track['approved_pedal_seeds']),
                           approved_pedal_phrases=deepcopy(track['approved_pedal_phrases'])))
    return dict(tier=2,schema='source-technique-relations/1',input=deepcopy(tier1),technique_observations=lift(tier1),tracks=tracks,headers=deepcopy(result['headers']),timeline=deepcopy(result['timeline']),playback_order=deepcopy(result['playback_order']),layout_warnings=result['layout_warnings'],scope='Retained source notation/technique relationships, no inferred performance, emotion or generation',inverse_status='REGISTERED_TECHNIQUE_DECLARATIONS_ONLY_NOT_COMPLETE_SOURCE')


def comparable_to_baseline(tier2,baseline):
    """Exact parity for persisted relationship fields and approved pedal outputs."""
    if len(tier2['tracks'])!=len(baseline['tracks']):return False
    for actual,old in zip(tier2['tracks'],baseline['tracks']):
        if actual['part_id']!=old['analysis']['part_id']:return False
        for key in TRACK_RELATION_FIELDS:
            if actual[key]!=old['analysis'][key]:return False
        rows=old['analysis']['rows']+old['analysis']['grace_rows']
        if actual['dynamics']!=[dict(occurrence_ref=r['occurrence'],**r['dynamic']) for r in rows]:return False
        expected=deepcopy(old['approved_pedal_sections'])
        for item in expected:
            if 'evidence' in item:
                item['evidence']['events']=[dict(onset_q=e['onset_q'],note_refs=[n['occurrence'] for n in e['notes']]) for e in item['evidence'].get('events',[])]
        if actual['approved_pedal_sections']!=expected or actual['approved_pedal_seeds']!=old['approved_pedal_seeds'] or actual['approved_pedal_phrases']!=old['approved_pedal_phrases']:return False
    return tier2['headers']==baseline['headers'] and tier2['timeline']==baseline['timeline'] and tier2['playback_order']==baseline['playback_order'] and tier2['layout_warnings']==baseline['layout_warnings']
