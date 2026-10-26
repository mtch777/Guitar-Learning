"""Independent mapping oracle for source execution-dependency views.

Uses retained track_analysis as the detector oracle, not execution_dependencies
or its mapping helpers. Source-fact roots independently enumerate declarations.
"""
import json
import re


def expected(tier1):
    from source_fact_tier1 import project_documents
    from source_tie_tier1 import extract_documents
    docs=project_documents(tier1);extract_documents(docs)
    from source_semantics import layout
    from analyze_relationships import track_analysis
    names=sorted([n for n in docs if re.fullmatch(r'track-\d+\.json',n)],key=lambda n:int(n[6:-5]))
    headers,warnings=layout([docs[n]for n in names]);song=docs['metadata.json']['songId'];flags=docs['metadata.json'].get('tracks')or[]
    all_edges=[];unknown=[];part_signatures=[];declarations=[]
    roots=[]
    for fact in tier1['facts']:
        m=re.fullmatch(r'/measures/(\d+)/voices/(\d+)/beats/(\d+)/(arpeggio|brushStroke|letRing|downArpeggio)',fact['pointer'])
        if m and fact['document']in names:roots.append((fact['document'],int(m[1]),int(m[2]),int(m[3]),m[4],fact['id']))
    roots.sort(key=lambda r:(names.index(r[0]),r[1],r[2],r[3],('arpeggio','brushStroke','letRing','downArpeggio').index(r[4])))
    def literal(value):
        if type(value)in(str,int,float,bool,type(None)):return value
        if isinstance(value,dict)and set(value)<={'direction','duration','shift'}and all(type(v)in(str,int,float,bool,type(None))for v in value.values()):return dict(value)
        return {'unsupported_source_type':type(value).__name__}
    for name in names:
        part=docs[name];pid=part['partId'];report=track_analysis(part,headers,catalog=flags[pid]if pid<len(flags)else{},shared_warnings=warnings)
        original_rows=report['rows']+report['grace_rows'];valid={r['occurrence']for r in original_rows}
        def global_ref(local):
            if local is None:return None
            if local not in valid:raise ValueError('Detector reference outside source note inventory')
            return f'event:{song}:{local}'
        def translated(record):
            out={}
            for key,value in record.items():
                if key in ('origin','destination','occurrence','candidate_destination'):out[key]=global_ref(value)
                elif key=='tied_members':out[key]=[global_ref(x)for x in value]
                elif key=='raw_value':out[key]=literal(value)
                else:out[key]=value
            return out
        def edge(kind,status,refs,semantics,reason=None):
            ids=sorted(set(r for r in refs if r is not None))
            all_edges.append({'kind':kind,'status':status,'member_refs':ids,'semantics':semantics})
            if reason is not None:unknown.append({'kind':kind,'status':status,'member_refs':ids,'reason':reason})
        hp=[translated(p)for p in report['hopo_transition_candidates']]
        un=[translated(p)for p in report['unresolved_hp']]
        for p in hp:edge('hopo','source_transition_candidate',[p['origin'],p['destination']],p)
        for p in un:edge('hopo','unresolved',[p['origin']],p,p['reason'])
        eligible=bool(report['guitar_or_bass']and report['temporal_relationships_eligible']);excluded=[]
        regular={r['occurrence']for r in report['rows']}
        for r in original_rows:
            if 'hp'not in r['effects']or(eligible and r['occurrence']in regular):continue
            reason='outside_instrument_scope'if not report['guitar_or_bass']else'excluded_for_timing'if not report['temporal_relationships_eligible']else'grace_origin_not_analyzed'
            record={'origin':global_ref(r['occurrence']),'reason':reason};excluded.append(record);edge('hopo',reason,[record['origin']],record,reason)
        slides=[translated(r)for r in report['relationship_details']['slides']['events']]
        for p in slides:
            refs=[p.get(k)for k in ('occurrence','origin','destination','candidate_destination')]+p.get('tied_members',[])
            edge('slide',p['status'],refs,p,None if p['status']=='resolved_written_target'else'candidate_or_unknown_written_endpoint_not_verified_execution')
        part_signatures.append(dict(part_id=pid,hopo_eligible=eligible,hopo_pairs=hp,hopo_unresolved=un,hopo_excluded=excluded,slides=slides))
        for document,mi,vi,bi,field,source in roots:
            if document!=name:continue
            beat=part['measures'][mi]['voices'][vi]['beats'][bi];value=beat[field]
            members=sorted(global_ref(r['occurrence'])for r in original_rows if r['bar']==mi+1 and r['voice']==vi and r['beat']==bi)
            declarations.append(dict(source_fact_ref=source,member_refs=members,value=literal(value)))
            if value is False or value is None:continue
            if field=='downArpeggio':
                if value==0:continue
                edge(field,'declaration_only_unknown_roll_execution',members,dict(source_fact_ref=source,declaration=literal(value),performed_note_offsets=None),'roll_execution_not_established')
            elif field=='letRing':
                edge(field,'declaration_only_unknown_end',members,dict(source_fact_ref=source,declaration=literal(value),performed_end_q=None),'sounding_end_unspecified')
            else:
                edge(field,'declaration_only_unknown_performed_offsets',members,dict(source_fact_ref=source,declaration=literal(value),performed_note_offsets=None),'performed_roll_offsets_unspecified')
    graph=dict(edges=all_edges,pinned_members=sorted({r for e in all_edges for r in e['member_refs']}),signature=dict(parts=part_signatures,declarations=declarations),uncertainty=unknown)
    return json.loads(json.dumps(graph,allow_nan=False))


def check(tier1,graph):
    issues=[]
    try:
        want=expected(tier1)
        if type(graph)is not dict or set(graph)!=set(want):issues.append('DEPENDENCY_GRAPH_SCHEMA_MISMATCH')
        else:
            for field in want:
                if json.dumps(graph[field],sort_keys=True,allow_nan=False)!=json.dumps(want[field],sort_keys=True,allow_nan=False):issues.append('DEPENDENCY_'+field.upper()+'_MISMATCH')
        return dict(status='PASS_INDEPENDENT_EXECUTION_DEPENDENCIES'if not issues else'FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES',issues=issues,
            expected_edges=len(want['edges']),expected_pinned_members=len(want['pinned_members']),expected_uncertainties=len(want['uncertainty']),
            scope='Retained detector semantics and source-fact declaration mapping; not acoustic or human execution certification')
    except Exception as error:
        return dict(status='FAIL_INDEPENDENT_EXECUTION_DEPENDENCIES',issues=[type(error).__name__+': '+str(error)])
