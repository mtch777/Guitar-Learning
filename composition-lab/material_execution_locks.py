"""Preserve unresolved execution context without keeping a second note stream.

These locks describe an edit boundary, not a performed gesture or its endpoint.
Every check is rebuilt from the current authoritative owners. Saved fingerprints
are never updated to make an edited result pass.
"""
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json

import backing_execution_constraints as execution

SCHEMA='material-unresolved-execution-locks/1'
SUCCESSOR_SCHEMA='material-unresolved-execution-locks/2'
CLOCK_SCHEMA='material-unresolved-execution-locks/3'
_REF_FIELDS=('origin_ref','destination_ref','candidate_destination_ref')
_LIST_FIELDS=('member_refs','tied_member_refs')


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _digest(value):
    return type(value)is str and len(value)==64 and all(c in '0123456789abcdef'for c in value)


def _origin(value):
    if type(value)is not str or str(F(value))!=value:
        raise ValueError('Canonical material clock origin required')
    return F(value)


def _maps(nodes,identity_map,fact_identity_map):
    mapping={} if identity_map is None else identity_map
    facts={} if fact_identity_map is None else fact_identity_map
    if any(type(m)is not dict or any(type(k)is not str or type(v)is not str or not v for k,v in m.items())for m in (mapping,facts)):
        raise ValueError('Explicit current-to-stable identity maps required')
    if set(mapping)-set(nodes):raise ValueError('Identity map names absent current occurrences')
    identities={ref:mapping.get(ref,ref)for ref in nodes}
    if len(set(identities.values()))!=len(identities):raise ValueError('Noninjective execution identity mapping')
    return identities,{ident:ref for ref,ident in identities.items()},facts


def _record(row,identities,facts):
    if type(row)is not dict or set(row)!=execution.FIELDS or row['id']!=execution.identity(row):
        raise ValueError('Complete authoritative execution record required')
    result={k:v for k,v in row.items()if k!='id'}
    for key in _LIST_FIELDS:
        if type(row[key])is not list or len(set(row[key]))!=len(row[key]):raise ValueError('Unique execution members required')
        try:result[key]=sorted(identities[ref]for ref in row[key])
        except KeyError as error:raise ValueError('Execution member is absent')from error
    for key in _REF_FIELDS:
        ref=row[key]
        if ref is not None:
            if ref not in identities:raise ValueError('Execution endpoint is absent')
            result[key]=identities[ref]
    source=row['source_fact_ref']
    if source is not None and type(source)is not str:raise ValueError('Optional execution fact reference must be string or null')
    result['source_fact_ref']=facts.get(source,source)
    return result


def _unresolved(row):
    return not ((row['kind']=='hopo'and row['status']=='source_transition_candidate')or
                (row['kind']=='slide'and row['status']=='resolved_written_target'))


def _touched(row):
    refs=set(row['member_refs'])|set(row['tied_member_refs'])
    refs.update(row[k]for k in _REF_FIELDS if row[k]is not None)
    return refs


def _context(tier1,observed,owned_refs,identity_map,fact_identity_map,origin_q):
    data=execution._snapshot(execution.encoded(tier1));nodes=data['nodes']
    if type(owned_refs)is not list or len(set(owned_refs))!=len(owned_refs)or set(owned_refs)-set(nodes):
        raise ValueError('Unique current owned execution occurrences required')
    if type(observed)is not list:raise ValueError('Explicit observed execution records required')
    identities,inverse,facts=_maps(nodes,identity_map,fact_identity_map)
    expected={}
    for row in observed:
        normalized=_record(row,identities,facts)
        if _unresolved(row):
            if not _touched(row)&set(owned_refs):raise ValueError('Unresolved record is outside this owner')
            key=_hash(normalized)
            if key in expected:raise ValueError('Duplicate unresolved execution record')
            expected[key]=row
    actual={}
    for row in data['records']:
        if _unresolved(row) and _touched(row)&set(owned_refs):
            actual[_hash(_record(row,identities,facts))]=row
    if set(actual)!=set(expected):raise ValueError('Unresolved execution metadata or membership changed')
    return data,actual,identities,inverse,_origin(origin_q)


def _policy(row):
    if row['kind']=='hopo' or row['kind']=='slide'and row['slide_type']in ('shift','legato'):
        return 'approved_written_successor_inputs'
    if row['kind']=='slide'and row['status']=='exit_target_unspecified':
        return 'next_written_contact_context'
    if row['kind']=='letRing'and row['status']=='declaration_only_unknown_end':
        return 'next_written_contact_context'
    raise ValueError('Unsupported unresolved execution lock: '+str(row['kind'])+'/'+str(row['status']))


def _numeric_successor_choices(row):
    """These accepted declarations do not inspect numeric pitch/fret values.

    Their unknown performed end/target stays unknown. This permission does not
    apply to HP or shift/legato successor predicates, which inspect pitch/fret.
    """
    return ((row['kind']=='letRing'and row['status']=='declaration_only_unknown_end')or
            (row['kind']=='slide'and row['status']=='exit_target_unspecified'
             and row['slide_type']in('downwards','upwards')))


def _part_end(tier1,part):
    from source_fact_tier1 import project_documents
    from source_key_tier1 import extract_documents
    documents=project_documents(tier1)
    count=len(documents[f'track-{part}.json']['measures'])
    frames=extract_documents(documents)['measure_geometry']['frames']
    if not count or count>len(frames):raise ValueError('Unknown part-end clock boundary')
    frame=frames[count-1]
    return F(frame['start_q'])+F(frame['span_q'])


def _node(node,identity,origin,*,release_numeric=False):
    result=dict(identity=identity,part=node['part'],voice=node['voice'],string=node['string'],
        string_valid=node['string_valid'],onset_q=str(node['onset']-origin),duration_q=str(node['duration']),
        grace=node['grace'],tie_destination=node['tie_destination'],pitch=node['pitch'],fret=node['fret'])
    if release_numeric:
        # Release numeric values, not the distinction between a pitched contact
        # and dead/unknown notation. The values remain owned by the existing
        # degree/physical equations, never duplicated in this relationship.
        result['pitch_known']=result.pop('pitch')is not None
        result['fret_known']=result.pop('fret')is not None
    return result


def _fences(row,nodes,identities):
    result=[]
    for ref in sorted(_touched(row)):
        focal=nodes[ref]
        if not focal['string_valid'] or focal['grace'] or focal['duration']<=0:
            raise ValueError('Unresolved contact context requires a known positive written string contact')
        following=[n for n in nodes.values()if n['part']==focal['part'] and n['string']==focal['string']
                   and not n['grace'] and n['onset']>focal['onset']]
        next_time=min((n['onset']for n in following),default=None)
        ends=sorted(identities[n['ref']]for n in following if n['onset']==next_time)
        result.append(dict(anchor=identities[ref],next_contact_ids=ends,
            boundary='next_written_contact'if ends else'part_end'))
    return sorted(result,key=lambda r:r['anchor'])


def _incoming_ties(refs,nodes):
    """Keep written predecessor identities and validate their current equality.

    A tied destination on a contact boundary can depend on a note outside that
    boundary. Its incoming chain must remain part of the relationship proof.
    This is written continuity, not an estimate of an acoustic release time.
    """
    result=set(refs);pending=list(refs)
    while pending:
        current=nodes[pending.pop()]
        if not current['tie_destination']:continue
        lane=[n for n in nodes.values()if n['part']==current['part']and n['voice']==current['voice']
              and n['string']==current['string']and not n['grace']and n['onset']<current['onset']]
        last=max((n['onset']for n in lane),default=None)
        previous=[n for n in lane if n['onset']==last]
        if (len(previous)!=1 or current['grace']or not current['string_valid']
                or current['pitch']is None or current['fret']is None):
            raise ValueError('Protected incoming written tie is unresolved')
        previous=previous[0]
        if (previous['onset']+previous['duration']!=current['onset']
                or previous['pitch']!=current['pitch']or previous['fret']!=current['fret']):
            raise ValueError('Protected incoming written tie changed')
        if previous['ref']not in result:
            result.add(previous['ref']);pending.append(previous['ref'])
        # Extending the proof to an incoming predecessor also extends its
        # physical contact window. Inspect ALL current voices: an added contact
        # during that written hold cannot hide just before the main window.
        for ref,node in nodes.items():
            if node['part']!=previous['part']or node['string']!=previous['string']:continue
            intersects=(previous['onset']<=node['onset']<=current['onset']or
                (not node['grace']and node['onset']<previous['onset']<node['onset']+node['duration']))
            if intersects and ref not in result:
                result.add(ref);pending.append(ref)
    return result


def _clock_topology(rows,boundaries):
    """Hash endpoint order/equality, delegating magnitudes to the pulse owner.

    Labels carry stable occurrence identity. Equal endpoint groups distinguish
    contiguous contacts from gaps and overlaps without storing a note stream.
    The complete current neighborhood is recomputed before this projection.
    """
    endpoints={}
    for node in rows:
        start=F(node.pop('onset_q'));duration=F(node.pop('duration_q'))
        for kind,value in (('start',start),('end',start+duration)):
            endpoints.setdefault(value,[]).append([node['identity'],kind])
    for boundary in boundaries:
        end=F(boundary.pop('end_q'))
        endpoints.setdefault(end,[]).append([boundary['anchor'],'window_end'])
    return [sorted(endpoints[value])for value in sorted(endpoints)]


def _projection(tier1,row,policy,fences,data,identities,inverse,origin,*,release_numeric=False,release_clock=False):
    if release_numeric and not _numeric_successor_choices(row):
        raise ValueError('Numeric choices are not supported by this accepted execution predicate')
    if release_clock and (not release_numeric or not _numeric_successor_choices(row)):
        raise ValueError('Clock choices require a declaration-only written contact')
    nodes=data['nodes'];refs=execution._neighborhood(row,nodes);boundaries=[]
    if policy=='next_written_contact_context':
        for fence in fences:
            if (type(fence)is not dict or set(fence)!={'anchor','next_contact_ids','boundary'}
                    or type(fence['next_contact_ids'])is not list or len(set(fence['next_contact_ids']))!=len(fence['next_contact_ids'])
                    or fence['boundary']!=('next_written_contact'if fence['next_contact_ids']else'part_end')):
                raise ValueError('Closed written-contact boundary required')
            try:focal=nodes[inverse[fence['anchor']]]
            except (KeyError,TypeError)as error:raise ValueError('Protected anchor identity is missing')from error
            if not focal['string_valid']:raise ValueError('Protected contact string is unresolved')
            endpoints=[]
            for stable in fence['next_contact_ids']:
                if stable not in inverse:raise ValueError('Protected next-contact identity is missing')
                endpoints.append(nodes[inverse[stable]])
            if endpoints:
                if len({r['onset']for r in endpoints})!=1:raise ValueError('Protected next-contact clock diverged')
                end=endpoints[0]['onset']
                if any(r['part']!=focal['part']or r['string']!=focal['string']or r['grace']for r in endpoints):
                    raise ValueError('Protected next contact changed lane or kind')
            else:end=_part_end(tier1,focal['part'])
            if end<=focal['onset']:raise ValueError('Protected contact ordering changed')
            # Same physical string, ALL voices. Include added contacts, grace
            # points and earlier notes whose written holds overlap the window.
            for ref,node in nodes.items():
                if node['part']!=focal['part']or node['string']!=focal['string']:continue
                intersects=(focal['onset']<=node['onset']<=end or
                    (not node['grace']and node['onset']<focal['onset']<node['onset']+node['duration']))
                if intersects:refs.add(ref)
            boundaries.append(dict(anchor=fence['anchor'],end_q=str(end-origin),boundary=fence['boundary']))
    elif fences:raise ValueError('Unexpected context boundaries for written successor policy')
    if release_clock:refs=_incoming_ties(refs,nodes)
    if not refs:raise ValueError('Unresolved execution has no protected occurrence')
    if {nodes[r]['part']for r in refs}&set(data['uncertain_parts']):
        raise ValueError('Unverified execution clock cannot establish a context lock')
    rows=sorted((_node(nodes[r],identities[r],origin,release_numeric=release_numeric)for r in refs),key=lambda r:r['identity'])
    projection=dict(nodes=rows,boundaries=boundaries)
    if release_clock:projection['endpoint_order']=_clock_topology(rows,boundaries)
    return _hash(projection),refs


def capture(tier1,observed_execution,owned_refs,*,identity_map=None,fact_identity_map=None,origin_q='0'):
    data,records,identities,inverse,origin=_context(tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    locks=[]
    for key,row in sorted(records.items()):
        policy=_policy(row)
        fences=_fences(row,data['nodes'],identities)if policy=='next_written_contact_context'else[]
        fingerprint,_=_projection(tier1,row,policy,fences,data,identities,inverse,origin)
        locks.append(dict(record_identity=key,policy=policy,context_boundaries=fences,fingerprint=fingerprint))
    return dict(schema=SCHEMA,locks=locks)


def _legacy_guard(guard):
    return dict(schema=SCHEMA,locks=[{k:v for k,v in row.items()if k not in('successor_fingerprint','clock_fingerprint')}
                                   for row in guard['locks']])


def _successor_guard(guard):
    return dict(schema=SUCCESSOR_SCHEMA,legacy_guard_sha256=guard['legacy_guard_sha256'],
        locks=[{k:v for k,v in row.items()if k!='clock_fingerprint'}for row in guard['locks']])


def upgrade_successor_choices(legacy_guard,tier1,observed_execution,owned_refs,*,
                              identity_map=None,fact_identity_map=None,origin_q='0'):
    """Explicitly migrate a VALID v1 guard; never rebaseline an edited v2 guard.

    Original lock fields/fingerprints stay byte-for-byte values, committed by
    legacy_guard_sha256. New fingerprints describe the same written contact
    context with only numeric pitch/fret values delegated to existing owners.
    This constructor adds no observation or performed duration/slide endpoint.
    """
    if type(legacy_guard)is not dict or legacy_guard.get('schema')!=SCHEMA:
        raise ValueError('Successor-choice upgrade requires an original v1 guard')
    validate(legacy_guard,tier1,observed_execution,owned_refs,identity_map=identity_map,
             fact_identity_map=fact_identity_map,origin_q=origin_q)
    data,records,identities,inverse,origin=_context(
        tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    out=deepcopy(legacy_guard);out['schema']=SUCCESSOR_SCHEMA
    out['legacy_guard_sha256']=_hash(legacy_guard)
    upgraded=0
    for lock in out['locks']:
        row=records[lock['record_identity']]
        if not _numeric_successor_choices(row):continue
        lock['successor_fingerprint'],_=_projection(tier1,row,lock['policy'],
            lock['context_boundaries'],data,identities,inverse,origin,release_numeric=True)
        upgraded+=1
    if not upgraded:raise ValueError('No eligible declaration-only written successor context')
    validate(out,tier1,observed_execution,owned_refs,identity_map=identity_map,
             fact_identity_map=fact_identity_map,origin_q=origin_q)
    return out


def upgrade_clock_choices(successor_guard,tier1,observed_execution,owned_refs,*,
                          identity_map=None,fact_identity_map=None,origin_q='0'):
    """Migrate a valid CURRENT v2, retaining every v1/v2 field and commitment.

    Only declaration-only ringing/exit-slide contexts delegate numeric timing
    to the existing pulse relationships. Contact identities, written ties and
    endpoint ordering/equality remain required. No performed end is inferred.
    An already edited/stale guard cannot be recaptured through this operation.
    """
    if type(successor_guard)is not dict or successor_guard.get('schema')!=SUCCESSOR_SCHEMA:
        raise ValueError('Clock-choice upgrade requires an existing v2 guard')
    validate(successor_guard,tier1,observed_execution,owned_refs,identity_map=identity_map,
             fact_identity_map=fact_identity_map,origin_q=origin_q)
    data,records,identities,inverse,origin=_context(
        tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    out=deepcopy(successor_guard);out['schema']=CLOCK_SCHEMA
    out['successor_guard_sha256']=_hash(successor_guard)
    for lock in out['locks']:
        row=records[lock['record_identity']]
        if not _numeric_successor_choices(row):continue
        lock['clock_fingerprint'],_=_projection(tier1,row,lock['policy'],
            lock['context_boundaries'],data,identities,inverse,origin,release_numeric=True,release_clock=True)
    validate(out,tier1,observed_execution,owned_refs,identity_map=identity_map,
             fact_identity_map=fact_identity_map,origin_q=origin_q)
    return out


def choice_scope(guard,tier1,observed_execution,owned_refs,*,identity_map=None,fact_identity_map=None,origin_q='0'):
    """Validate and distinguish numeric choice permission from protected context.

    String and successor membership stay protected even for numerically
    flexible refs. V3 alone delegates numeric clock while protecting contact
    topology. When combining guards, union strict_refs across ALL guards
    before subtracting them from the union of permitted refs.
    """
    if type(guard)is not dict:raise ValueError('Closed unresolved execution locks required')
    clock_upgraded=guard.get('schema')==CLOCK_SCHEMA
    upgraded=guard.get('schema')in(SUCCESSOR_SCHEMA,CLOCK_SCHEMA)
    fields={'schema','locks','legacy_guard_sha256'}if upgraded else{'schema','locks'}
    if clock_upgraded:fields.add('successor_guard_sha256')
    if set(guard)!=fields or guard['schema']not in(SCHEMA,SUCCESSOR_SCHEMA,CLOCK_SCHEMA)or type(guard['locks'])is not list:
        raise ValueError('Closed unresolved execution locks required')
    if upgraded and (any(type(row)is not dict for row in guard['locks'])or
                     not _digest(guard['legacy_guard_sha256'])or
                     _hash(_legacy_guard(guard))!=guard['legacy_guard_sha256']):
        raise ValueError('Immutable legacy execution commitment changed')
    if clock_upgraded and (not _digest(guard['successor_guard_sha256'])or
                           _hash(_successor_guard(guard))!=guard['successor_guard_sha256']):
        raise ValueError('Immutable successor execution commitment changed')
    data,records,identities,inverse,origin=_context(tier1,observed_execution,owned_refs,identity_map,fact_identity_map,origin_q)
    locked=set();strict=set();flexible=set();seen=set();released=0
    for lock in guard['locks']:
        if type(lock)is not dict or 'record_identity'not in lock:
            raise ValueError('Closed execution lock without note payload required')
        key=lock['record_identity']
        if not _digest(key)or key not in records or key in seen:raise ValueError('Unknown or duplicate unresolved record lock')
        row=records[key];release_numeric=upgraded and _numeric_successor_choices(row)
        release_clock=clock_upgraded and release_numeric
        expected={'record_identity','policy','context_boundaries','fingerprint'}
        if release_numeric:expected.add('successor_fingerprint');released+=1
        if release_clock:expected.add('clock_fingerprint')
        if set(lock)!=expected:raise ValueError('Closed execution lock without note payload required')
        if not _digest(key) or not _digest(lock['fingerprint']):raise ValueError('Exact execution commitment digests required')
        if release_numeric and not _digest(lock['successor_fingerprint']):raise ValueError('Exact successor commitment required')
        if release_clock and not _digest(lock['clock_fingerprint']):raise ValueError('Exact clock commitment required')
        seen.add(key)
        if lock['policy']!=_policy(row):raise ValueError('Execution lock policy changed')
        if type(lock['context_boundaries'])is not list:raise ValueError('Explicit execution context boundaries required')
        if lock['policy']=='next_written_contact_context':
            if any(type(f)is not dict or set(f)!={'anchor','next_contact_ids','boundary'} or type(f['anchor'])is not str
                   for f in lock['context_boundaries']):raise ValueError('Closed written-contact boundary required')
            anchors=sorted(identities[r]for r in _touched(row))
            if sorted(f.get('anchor')for f in lock['context_boundaries'])!=anchors:
                raise ValueError('Incomplete protected contact boundaries')
        fingerprint,refs=_projection(tier1,row,lock['policy'],lock['context_boundaries'],data,identities,inverse,origin,
                                    release_numeric=release_numeric,release_clock=release_clock)
        expected_fingerprint=(lock['clock_fingerprint']if release_clock else
                              lock['successor_fingerprint']if release_numeric else lock['fingerprint'])
        if fingerprint!=expected_fingerprint:raise ValueError('Protected unresolved execution context changed')
        locked.update(refs)
        (flexible if release_numeric else strict).update(refs)
    if seen!=set(records):raise ValueError('Missing unresolved execution lock')
    if upgraded and not released:raise ValueError('No eligible declaration-only written successor context')
    result=dict(covered_refs=execution.ordered(locked),strict_refs=execution.ordered(strict),
                pitch_flexible_refs=execution.ordered(flexible-strict))
    if clock_upgraded:result['clock_flexible_refs']=execution.ordered(flexible-strict)
    return result


def validate(guard,tier1,observed_execution,owned_refs,*,identity_map=None,fact_identity_map=None,origin_q='0'):
    """Keep the existing return contract: all protected-context occurrences."""
    return choice_scope(guard,tier1,observed_execution,owned_refs,identity_map=identity_map,
        fact_identity_map=fact_identity_map,origin_q=origin_q)['covered_refs']


def pitch_flexible_refs(guard,tier1,observed_execution,owned_refs,*,identity_map=None,fact_identity_map=None,origin_q='0'):
    return choice_scope(guard,tier1,observed_execution,owned_refs,identity_map=identity_map,
        fact_identity_map=fact_identity_map,origin_q=origin_q)['pitch_flexible_refs']
