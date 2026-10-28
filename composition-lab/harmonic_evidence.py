"""Common conditional chord/degree evidence, referencing existing pitch owners.

No inferred source labels, preferred roots, new detector, or creative permission.
"""
from fractions import Fraction as F
from copy import deepcopy
import json
import musical_tier2 as music
from chord_degree_relations import note_role,pitch_from_degree
from chord_symbol_lexicon import parse,CURRENT_PROFILE,LEGACY_PROFILE
from declared_chord_ownership import attached,selection,label_values,capo_values


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def build(core,labels,capos,instruments,*,profile=CURRENT_PROFILE):
    music.validate(core)
    groups=[]
    for group in core['coattacks']:
        refs=attached(group,labels);declarations=[]
        for ref in refs:
            parsed=parse(labels[ref],profile=profile)
            declarations.append(dict(source_fact_ref=ref,parse_status=parsed['status'],interpretations=[dict(root_pc=h['root_pc'],kind=h['kind'],explicit_bass_pc=h['explicit_bass_pc']) for h in parsed.get('interpretations',[])]))
        written=selection(group,labels,capos,profile=profile)
        program=instruments.get(str(group['part_id']));values=[music.member_pitch(group,m) for m in group['members']];reasons=[]
        if type(program)is not int or not 0<=program<=127:reasons.append('NONPITCHED_OR_UNKNOWN_INSTRUMENT')
        if group['timing_uncertain']:reasons.append('UNCERTAIN_SOURCE_CLOCK')
        if any(F(m['duration_q'])<=0 for m in group['members']):reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
        if any(p is None for p in values):reasons.append('UNKNOWN_WRITTEN_PITCH')
        elif any(F(p).denominator!=1 for p in values):reasons.append('NONINTEGER_WRITTEN_PITCH')
        elif len({F(p)%12 for p in values})<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
        hypotheses=[]
        if not reasons:
            for label in music.interpreted(group)['chord_candidates']:
                members=[]
                for member,pitch in zip(group['members'],values):
                    roles=note_role(pitch,label)['degree_relationships']
                    if not roles:raise ValueError('Exact fit lacks a degree relationship')
                    if any(F(pitch_from_degree(label['root_pc'],label['kind'],r))!=F(pitch) for r in roles):raise ValueError('Degree relationship fails existing pitch equation')
                    members.append(dict(member_ref=member['id'],degree_relationships=roles))
                matches=[d['source_fact_ref'] for d in declarations if any(h['root_pc']==label['root_pc'] and h['kind']==label['kind'] for h in d['interpretations'])]
                hypotheses.append(dict(id=f"{group['id']}:root-{label['root_pc']}:{label['kind']}",evidence_class='exact_observed_pc_fit',root_pc=label['root_pc'],kind=label['kind'],formula=label['formula'],member_roles=members,matching_declared_root_kind_refs=matches))
        groups.append(dict(group_ref=group['id'],part_id=group['part_id'],onset_q=group['onset_q'],member_refs=[m['id'] for m in group['members']],
            status='REFUSED_COMPLETE_FIT' if reasons else 'EXACT_FIT_ALTERNATIVES' if hypotheses else 'NO_EXACT_FIT_IN_VOCABULARY',reasons=reasons,
            declarations=declarations,declared_admission_status=written['status'],hypotheses=hypotheses))
    return dict(schema='conditional-harmonic-evidence/1',scope='Complete coincident written starts; not acoustic harmony, sustained spans, key or musical intent',theory=deepcopy(music.THEORY_PROVENANCE),
        pitch_authority='Existing source-declared-degree or coattack owner; these are checked conditional relationships',groups=groups,
        uncertainty='Every exact fit in the pinned vocabulary is retained. A singleton is not established chord identity. Declared labels are separate source evidence.')


def validate(core,labels,capos,instruments,evidence,*,profile=CURRENT_PROFILE):
    expected=build(core,labels,capos,instruments,profile=profile)
    if encoded(expected)!=encoded(evidence):raise ValueError('Stale, incomplete or forged harmonic evidence')
    return expected


def context(upper):
    from connected_tier2 import realize
    from source_fact_tier1 import project_documents
    from declared_chord_ownership import validate as normalize_degrees
    from voicing_families import validate as normalize_families
    before=realize(upper);docs=project_documents(before);facts=upper['source_structure']['facts'];choices=upper['owned_parameters']['source_choices']
    labels=label_values(choices,facts);capos=capo_values(choices,facts);core=upper['musical_relationships']
    profile=core.get('admission_profile',LEGACY_PROFILE if core.get('schema')=='source-declared-chord-degrees/1' else CURRENT_PROFILE)
    if core.get('schema')=='source-declared-chord-degrees/1':core=normalize_degrees(core,labels,capos)
    elif core.get('schema')=='source-voicing-families/1':core=normalize_families(core)
    instruments={str(p['partId']):p.get('instrumentId') for name,p in docs.items() if name.startswith('track-')}
    return dict(before=before,documents=docs,core=core,labels=labels,capos=capos,instruments=instruments,profile=profile)


def from_context(c):return build(c['core'],c['labels'],c['capos'],c['instruments'],profile=c['profile'])


def source_patterns(upper):
    """Feed all exact-fit assumptions through the existing source unit guards."""
    from source_tie_tier1 import extract_documents
    from voicing_register import tie_relationships,notation
    from voicing_context_relations import graph
    from execution_dependencies import build as execution
    from declared_degree_choices import source_unit
    from inner_voicing import decorate
    c=context(upper);view=from_context(c);lower=extract_documents(c['documents']);nodes=graph(c['before'],typed_nominal=True)
    events={e['id']:e for e in lower['events']};ties=tie_relationships(lower)
    pinned=set(execution(c['before'])['pinned_members'])|{r for e in ties['links'] for r in (e['origin'],e['destination'])}|{e['destination'] for e in ties['unresolved']}
    groups={g['id']:g for g in c['core']['coattacks']};units=[];refusals=[]
    for row in view['groups']:
        if not row['hypotheses']:continue
        group=groups[row['group_ref']];reasons=[];program=c['instruments'].get(str(group['part_id']))
        if type(program)is not int or not 24<=program<=39:reasons.append('OUTSIDE_GUITAR_COMPONENT_SCOPE')
        strings=[nodes['nodes'][r]['string'] for r in row['member_refs']]
        if any(type(s)is not int or s<0 for s in strings) or len(set(strings))!=len(strings):reasons.append('NONUNIQUE_OR_UNKNOWN_STRING')
        for ref in row['member_refs']:
            _,_,note=notation(c['documents'],events[ref])
            if type(note.get('fret'))not in(int,float):reasons.append('MISSING_NUMERIC_SOURCE_FRET')
        if reasons:
            refusals.append(dict(group_ref=row['group_ref'],reasons=sorted(set(reasons))));continue
        for h in row['hypotheses']:
            if any(len(m['degree_relationships'])!=1 for m in h['member_roles']):
                refusals.append(dict(group_ref=row['group_ref'],hypothesis_ref=h['id'],reasons=['AMBIGUOUS_DEGREE_ASSIGNMENT']));continue
            roles=[dict(degree_token=m['degree_relationships'][0]['token'],relative_octaves=m['degree_relationships'][0]['relative_octaves']) for m in h['member_roles']]
            unit=source_unit(group,h,roles,c['documents'],nodes,events,pinned)
            unit['source_unit_ref']=unit['id'];unit['id']=h['id'];unit['hypothesis_ref']=h['id'];unit['evidence_class']=h['evidence_class']
            units.append(unit)
    decorated=decorate(dict(before=c['before'],documents=c['documents'],units=units,lane_graph=nodes,typed_nominal=True))
    decorated['harmonic_evidence']=view;decorated['component_scope_refusals']=refusals
    decorated['profile']=c['profile']
    return decorated
