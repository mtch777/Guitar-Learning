"""Lossless occurrence membership plus explicit-tie sustains and inferred lanes.

Lanes are an interval-partition hypothesis, never asserted original voices.
Nothing is removed: tied written occurrences, ornaments, unknown pitches and
raw technique metadata remain addressable in the canonical score.
"""
from collections import defaultdict
from fractions import Fraction as F


def build_sounding(score):
    occurrences={};items=[];warnings=[]
    for track in score['tracks']:
        for mi,m in enumerate(track['measures']):
            for vi,voice in enumerate(m['voices']):
                for ei,e in enumerate(voice):
                    for ni,n in enumerate(e['notes']):
                        ident=f"t{track['index']}:m{mi}:v{vi}:b{ei}:n{ni}"
                        row=dict(id=ident,track=track['index'],voice=vi,measure=mi,beat=ei,note_index=ni,
                            onset_q=str(F(e['onset_q'])),duration_q=str(F(e['duration_q'])),
                            midi=n['midi'],string=n.get('string'),tie=n.get('tie'),grace_type=e.get('grace_type'),
                            technique_tags=list(n.get('technique_tags',[])),source_note_id=n.get('note_id'))
                        occurrences[ident]=row;items.append(row)
    pending=defaultdict(list);sustains={};membership={}
    for row in sorted(items,key=lambda r:(F(r['onset_q']),r['track'],r['voice'],r['id'])):
        onset=F(row['onset_q']);end=onset+F(row['duration_q']);tie=row['tie'] or {}
        key=(row['track'],row['voice'],row['string'],row['midi'])
        candidates=[sid for boundary,sid in pending[key] if boundary==onset]
        sid=None
        if tie.get('destination')=='true':
            if len(candidates)==1:
                sid=candidates[0];pending[key]=[(t,s) for t,s in pending[key] if s!=sid]
            else:warnings.append(dict(occurrence=row['id'],type='unresolved_tie_destination',candidates=len(candidates)))
        if sid is None:
            sid='sustain:'+row['id'];sustains[sid]=dict(id=sid,track=row['track'],voice=row['voice'],midi=row['midi'],string=row['string'],
                onset_q=str(onset),end_q=str(end),duration_q=str(end-onset),members=[],grace_type=row['grace_type'])
        node=sustains[sid];node['members'].append(row['id']);membership[row['id']]=sid
        node['end_q']=str(max(F(node['end_q']),end));node['duration_q']=str(F(node['end_q'])-F(node['onset_q']))
        if tie.get('origin')=='true':pending[key].append((end,sid))
    for entries in pending.values():
        for end,sid in entries:warnings.append(dict(sustain=sid,type='unresolved_tie_origin',end_q=str(end)))
    # Greedy interval partition with nearest-pitch tie-break. Original voice IDs
    # are retained separately; this is a reproducible melodic-lane hypothesis.
    groups=defaultdict(list);lanes=[]
    for node in sustains.values():groups[node['track'],node['voice']].append(node)
    for (ti,vi),nodes in groups.items():
        local=[]
        for n in sorted(nodes,key=lambda n:(F(n['onset_q']),n['id'])):
            free=[lane for lane in local if F(lane['end_q'])<=F(n['onset_q'])]
            if free:
                lane=min(free,key=lambda l:abs((n['midi'] or 0)-(l['last_pitch'] or 0)))
            else:
                lane=dict(id=f'lane:{ti}:{vi}:{len(local)}',track=ti,source_voice=vi,members=[],end_q='0',last_pitch=None,
                    provenance='interval_partition_nearest_pitch_hypothesis');local.append(lane)
            lane['members'].append(n['id']);lane['end_q']=n['end_q'];lane['last_pitch']=n['midi']
        lanes+=local
    assert len(membership)==len(occurrences)
    return dict(format='sounding-graph-v1',occurrences=occurrences,sustains=sustains,lanes=lanes,warnings=warnings,
        semantics='written rational time; original voices retained; lanes inferred; grace performance scheduling not inferred')


def audit_sounding(score,graph):
    expected=sum(len(e['notes']) for t in score['tracks'] for m in t['measures'] for v in m['voices'] for e in v)
    members=[oid for n in graph['sustains'].values() for oid in n['members']]
    assert len(members)==len(set(members))==expected==len(graph['occurrences'])
    lane_members=[sid for l in graph['lanes'] for sid in l['members']]
    assert len(lane_members)==len(set(lane_members))==len(graph['sustains'])
    for lane in graph['lanes']:
        nodes=[graph['sustains'][sid] for sid in lane['members']]
        for a,b in zip(nodes,nodes[1:]):assert F(a['end_q'])<=F(b['onset_q'])
    return dict(written_occurrences=expected,sounding_events=len(graph['sustains']),lane_count=len(graph['lanes']),
        merged_tie_occurrences=expected-len(graph['sustains']),unresolved_tie_markings=len(graph['warnings']),
        occurrence_coverage=1.0,no_lane_overlaps=True)
