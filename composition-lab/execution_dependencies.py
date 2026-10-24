"""Source-written execution dependencies, separate from sounding context.

Accepted occurrence/HOPO/slide/timing primitives are unchanged. Imports are lazy
because isolated workers compile this module before staging those primitives.
No acoustic onset, ringing end or unspecified slide endpoint is inferred.
"""
from copy import deepcopy
import json


def _value(value):
    if type(value)in(str,int,float,bool,type(None)):return value
    if type(value)is dict and set(value)<={'direction','duration','shift'} and all(type(v)in(str,int,float,bool,type(None))for v in value.values()):return deepcopy(value)
    return dict(unsupported_source_type=type(value).__name__)


def build(tier1):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    documents=project_documents(tier1)
    # Existing pure adapter validates source identity and initializes API imports.
    extract_documents(documents)
    from source_semantics import layout,rests
    from analyze_relationships import occurrences,hopo
    from source_relationship_details import relationship_details
    names=sorted((n for n in documents if n.startswith('track-')and n.endswith('.json')),key=lambda n:int(n[6:-5]))
    parts=[documents[n]for n in names];headers,shared_warnings=layout(parts)
    song=documents['metadata.json']['songId'];catalog=documents['metadata.json'].get('tracks')or[]
    edges=[];uncertainty=[];signatures=[];declarations=[]
    for name,part in zip(names,parts):
        pid=part['partId'];rows,grace,_,warnings=occurrences(part,headers)
        _,rest_warnings=rests(part,headers);warnings=warnings+rest_warnings
        lookup={r['occurrence']:r for r in rows+grace}
        def ref(ident):
            if ident is None:return None
            if ident not in lookup:raise ValueError('Dependency refers outside captured source occurrences')
            return f'event:{song}:{ident}'
        def convert(record):
            result=deepcopy(record)
            for k in ('origin','destination','occurrence','candidate_destination'):
                if k in result:result[k]=ref(result[k])
            if 'tied_members'in result:result['tied_members']=[ref(i)for i in result['tied_members']]
            if 'raw_value'in result:result['raw_value']=_value(result['raw_value'])
            return result
        def add(kind,status,members,semantics,reason=None):
            members=sorted(set(r for r in members if r is not None))
            item=dict(kind=kind,status=status,member_refs=members,semantics=semantics)
            edges.append(item)
            if reason is not None:uncertainty.append(dict(kind=kind,status=status,member_refs=members,reason=reason))
        flags=catalog[pid]if pid<len(catalog)else{}
        program=isinstance(part.get('instrumentId'),int)and 24<=part['instrumentId']<=39
        guitar=program and not flags.get('isVocalTrack')and not flags.get('isEmpty')
        temporal_valid=not warnings and not shared_warnings
        pairs,unresolved=hopo(rows,grace)if guitar and temporal_valid else([],[])
        hp_pairs=[convert(r)for r in pairs];hp_unresolved=[convert(r)for r in unresolved]
        for record in hp_pairs:
            add('hopo','source_transition_candidate',[record['origin'],record['destination']],record)
        for record in hp_unresolved:
            add('hopo','unresolved',[record['origin']],record,record['reason'])
        excluded=[]
        for row in rows+grace:
            if 'hp'not in row['effects']:continue
            if guitar and temporal_valid and row in rows:continue
            reason='outside_instrument_scope'if not guitar else'excluded_for_timing'if not temporal_valid else'grace_origin_not_analyzed'
            record=dict(origin=ref(row['occurrence']),reason=reason)
            excluded.append(record);add('hopo',reason,[record['origin']],record,reason)
        details=relationship_details(part,headers,rows,grace,warnings,shared_warnings,recover_groups=False)
        slides=[convert(r)for r in details['slides']['events']]
        for record in slides:
            members=[record.get(k)for k in ('occurrence','origin','destination','candidate_destination')]+record.get('tied_members',[])
            reason=None if record['status']=='resolved_written_target'else'candidate_or_unknown_written_endpoint_not_verified_execution'
            add('slide',record['status'],members,record,reason)
        signatures.append(dict(part_id=pid,hopo_eligible=bool(guitar and temporal_valid),hopo_pairs=hp_pairs,hopo_unresolved=hp_unresolved,hopo_excluded=excluded,slides=slides))
        for mi,measure in enumerate(part.get('measures',[]),1):
            for vi,voice in enumerate(measure.get('voices',[])):
                for bi,beat in enumerate(voice.get('beats',[])):
                    for field in ('arpeggio','brushStroke','letRing'):
                        if field not in beat:continue
                        source=f'{name}#/measures/{mi-1}/voices/{vi}/beats/{bi}/{field}'
                        members=[ref(f'{pid}:{mi}:{vi}:{bi}:{ni}')for ni,n in enumerate(beat.get('notes',[]))if not n.get('rest')]
                        record=dict(source_fact_ref=source,member_refs=sorted(members),value=_value(beat[field]))
                        declarations.append(record)
                        if beat[field]is False or beat[field]is None:continue
                        status='declaration_only_unknown_end'if field=='letRing'else'declaration_only_unknown_performed_offsets'
                        semantics=dict(source_fact_ref=source,declaration=_value(beat[field]),performed_end_q=None)if field=='letRing'else dict(source_fact_ref=source,declaration=_value(beat[field]),performed_note_offsets=None)
                        add(field,status,members,semantics,'sounding_end_unspecified'if field=='letRing'else'performed_roll_offsets_unspecified')
    signature=dict(parts=signatures,declarations=declarations)
    # Require a plain JSON payload; there are no live source objects or note rows.
    result=dict(edges=edges,pinned_members=sorted({r for e in edges for r in e['member_refs']}),signature=signature,uncertainty=uncertainty)
    return json.loads(json.dumps(result,allow_nan=False))
