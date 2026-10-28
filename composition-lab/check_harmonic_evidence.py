"""Raw-source/native-theory oracle; no harmonic producer or proposal imports."""
from collections import defaultdict
from fractions import Fraction as F
from functools import lru_cache
import json
import hashlib
import re
from check_voicing_context import _nodes,_paths
from check_voicing_policy import _written_ties
from check_execution_dependencies import expected as execution_expected
from check_inner_voicing import _note,_plain_reasons,_overlap_index,_has_outside_overlap,_physical
from check_declared_chord_ownership import native_interpretations,CURRENT_PROFILE


def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)


@lru_cache(maxsize=1)
def native_forms():
    from music21 import harmony,pitch,scale,__version__
    if __version__!='9.9.2':raise ValueError('Pinned native theory required')
    out=[];major=scale.MajorScale('C')
    for kind,(formula,aliases) in harmony.CHORD_TYPES.items():
        definitions=[]
        for token in formula.split(','):
            m=re.fullmatch(r'([#-]*)(\d+)',token);acc,number=m.groups();degree=int(number)
            alteration=int(pitch.Accidental(acc).alter) if acc else 0
            # pitchFromDegree is periodic: request the simple degree explicitly,
            # then retain the compound octave encoded by the written degree.
            distance=int(major.pitchFromDegree((degree-1)%7+1).midi-60)+12*((degree-1)//7)+alteration
            definitions.append(dict(token=token,degree=degree,alteration=alteration,theoretical_semitones=distance,pitch_class=distance%12))
        pcs=sorted({p.pitchClass for p in harmony.ChordSymbol(root='C',kind=kind).pitches})
        if set(pcs)!={d['pitch_class'] for d in definitions}:raise ValueError('Native theory definitions disagree')
        out.append((kind,pcs,definitions))
    return tuple(out)


def declared_status(declarations,literals,refs,nodes,part,clock_uncertain):
    if len(declarations)!=1:return 'NO_DECLARATION'if not declarations else'MULTIPLE_DECLARATIONS'
    if len({tuple(r.split(':')[3:6])for r in refs})!=1:return 'MIXED_DECLARING_BEAT_SCOPE'
    capo=part.get('capo')
    if capo is not None and not(type(capo)in(int,float)and capo==0):return 'UNVERIFIED_CAPO_LABEL_CONVENTION'
    if any(nodes[r]['duration']<=0 for r in refs):return 'GRACE_OR_NONPOSITIVE_DURATION'
    ref=next(iter(declarations));choices=declarations[ref]
    if type(literals[ref])is not str:return 'UNSUPPORTED_LITERAL_TYPE'
    if len(choices)!=1:return 'AMBIGUOUS_SYMBOL'if choices else'UNSUPPORTED_SYMBOL'
    if clock_uncertain:return 'UNCERTAIN_SOURCE_CLOCK'
    values=[nodes[r]['pitch']for r in refs]
    if any(p is None or p.denominator!=1 for p in values):return 'UNKNOWN_WRITTEN_PITCH'
    pcs={int(p%12)for p in values};h=choices[0]
    if len(pcs)<2:return 'NOT_MULTIPLE_PITCH_CLASSES'
    if pcs!=set(h['pcs']):return 'SYMBOL_PITCH_SET_MISMATCH'
    if h['slash_bass_pc']is not None and int(min(values)%12)!=h['slash_bass_pc']:return 'EXPLICIT_SLASH_BASS_MISMATCH'
    if any(sum((p-h['root_pc']-distance)%12==0 for _,distance in h['degrees'])!=1 for p in values):return 'AMBIGUOUS_DEGREE_ASSIGNMENT'
    return 'SUPPORTED_DECLARED_WRITTEN_CHORD'


def check(tier1,view,catalog=None,profile=CURRENT_PROFILE):
    issues=[];hypothesis_count=0;member_coordinates=0;expected_units={};expected_refusals=[]
    try:
        if set(view)!={'schema','scope','theory','pitch_authority','groups','uncertainty'} or view['schema']!='conditional-harmonic-evidence/1':raise ValueError('Incorrect harmonic evidence schema')
        if view['scope']!='Complete coincident written starts; not acoustic harmony, sustained spans, key or musical intent' or view['pitch_authority']!='Existing source-declared-degree or coattack owner; these are checked conditional relationships' or view['uncertainty']!='Every exact fit in the pinned vocabulary is retained. A singleton is not established chord identity. Declared labels are separate source evidence.':raise ValueError('Unsupported semantic claim')
        native_hash=hashlib.sha256(json.dumps([(k,p)for k,p,_ in native_forms()],separators=(',',':')).encode()).hexdigest()
        provenance=dict(source='music21.harmony.CHORD_TYPES',version='9.9.2',forms_sha256=native_hash,vocabulary_scope='Published Western chord-kind definitions; not exhaustive musical harmony',candidate_rule='Exact observed pitch-class set; all twelve roots; singleton excluded')
        if encoded(view['theory'])!=encoded(provenance):raise ValueError('Native theory provenance differs')
        docs,lower,nodes,rests=_nodes(tier1);groups=defaultdict(list)
        for ref,n in nodes.items():groups[n['part'],int(ref.split(':')[3]),n['onset']].append(ref)
        order=sorted(groups,key=lambda k:(k[2],k[1],k[0]));rows=view['groups']
        if len(rows)!=len(order):raise ValueError('Missing/extra source groups')
        ties=_written_ties(docs,lower['events']);pinned={r for e in ties['links']for r in(e['origin'],e['destination'])}|{e['destination']for e in ties['unresolved']}|set(execution_expected(tier1)['pinned_members'])
        index=_overlap_index(nodes);neighbors=defaultdict(set)
        for path in _paths(nodes,rests,True).values():
            for ref in path['refs']:neighbors[ref].update(path['refs'])
        for ordinal,((pid,bar,onset),row) in enumerate(zip(order,rows)):
            refs=groups[pid,bar,onset];group_id=f'coattack:{ordinal}';part=docs[f'track-{pid}.json'];program=part.get('instrumentId')
            if row['group_ref']!=group_id or type(row['part_id'])is not int or row['part_id']!=pid or row['onset_q']!=str(onset) or row['member_refs']!=refs:raise ValueError('Group identity/time/member mismatch')
            values=[nodes[r]['pitch']for r in refs];reasons=[]
            if type(program)is not int or not 0<=program<=127:reasons.append('NONPITCHED_OR_UNKNOWN_INSTRUMENT')
            if any(w['bar']==bar for k in ('layout_warnings','timing_warnings')for w in lower['source_coverage'][k]):reasons.append('UNCERTAIN_SOURCE_CLOCK')
            if any(nodes[r]['duration']<=0 for r in refs):reasons.append('GRACE_OR_NONPOSITIVE_DURATION')
            if any(p is None for p in values):reasons.append('UNKNOWN_WRITTEN_PITCH')
            elif any(p.denominator!=1 for p in values):reasons.append('NONINTEGER_WRITTEN_PITCH')
            elif len({p%12 for p in values})<2:reasons.append('INSUFFICIENT_DISTINCT_PITCH_CLASSES')
            if row['reasons']!=reasons:raise ValueError('Complete-fit refusal differs from source')
            declarations={};literals={}
            for ref in refs:
                _,beat,_=_note(docs,ref);p,b,v,i,_=map(int,ref.split(':')[2:])
                if 'text'in beat.get('chord',{}):
                    fact_ref=f'track-{p}.json#/measures/{b-1}/voices/{v}/beats/{i}/chord/text';literals[fact_ref]=beat['chord']['text'];declarations[fact_ref]=native_interpretations(literals[fact_ref],profile)
            if [d['source_fact_ref']for d in row['declarations']]!=sorted(declarations):raise ValueError('Forged or missing source label provenance')
            for d in row['declarations']:
                choices=declarations[d['source_fact_ref']];parse_status='UNSUPPORTED_LITERAL_TYPE'if type(literals[d['source_fact_ref']])is not str else'UNIQUE_LIBRARY_SYMBOL'if len(choices)==1 else'AMBIGUOUS_SYMBOL'if choices else'UNSUPPORTED_SYMBOL'
                if d['parse_status']!=parse_status:raise ValueError('Forged declaration parse status')
                want=[dict(root_pc=h['root_pc'],kind=h['kind'],explicit_bass_pc=h['slash_bass_pc'])for h in declarations[d['source_fact_ref']]]
                if sorted(map(encoded,want))!=sorted(map(encoded,d['interpretations'])):raise ValueError('Native label interpretations differ')
            if row['declared_admission_status']!=declared_status(declarations,literals,refs,nodes,part,'UNCERTAIN_SOURCE_CLOCK'in reasons):raise ValueError('Forged declaration admission status')
            expected={}
            if not reasons:
                pcs={int(p%12)for p in values}
                for kind,formula,definitions in native_forms():
                    if len(formula)<2:continue
                    for root in range(12):
                        if {(root+p)%12 for p in formula}!=pcs:continue
                        ident=f'{group_id}:root-{root}:{kind}';members=[]
                        for ref,p in zip(refs,values):
                            matches=[dict(d,relative_octaves=int((p-root-d['theoretical_semitones'])/12))for d in definitions if(p-root-d['theoretical_semitones'])%12==0]
                            if not matches:raise ValueError('Native fit has no member degree')
                            members.append(dict(member_ref=ref,degree_relationships=matches));member_coordinates+=len(matches)
                        declared=[ref for ref,hh in sorted(declarations.items())if any(h['root_pc']==root and h['kind']==kind for h in hh)]
                        expected[ident]=dict(id=ident,evidence_class='exact_observed_pc_fit',root_pc=root,kind=kind,formula=formula,member_roles=members,matching_declared_root_kind_refs=declared)
            actual=row['hypotheses']
            if len(actual)!=len(expected) or {h['id']for h in actual}!=set(expected):raise ValueError('Missing, duplicate or extra exact-fit hypothesis')
            for h in actual:
                if encoded(h)!=encoded(expected[h['id']]):raise ValueError('Native formula, degree or provenance mismatch')
            hypothesis_count+=len(expected)
            expected_status='REFUSED_COMPLETE_FIT'if reasons else'EXACT_FIT_ALTERNATIVES'if expected else'NO_EXACT_FIT_IN_VOCABULARY'
            if row['status']!=expected_status:raise ValueError('Incorrect harmonic support status')
            if not expected:continue
            strings=[nodes[r]['string']for r in refs]
            component_reasons=[]
            if type(program)is not int or not 24<=program<=39:component_reasons.append('OUTSIDE_GUITAR_COMPONENT_SCOPE')
            if any(type(s)is not int or s<0 for s in strings)or len(set(strings))!=len(strings):component_reasons.append('NONUNIQUE_OR_UNKNOWN_STRING')
            if any(type(_note(docs,r)[2].get('fret'))not in(int,float)for r in refs):component_reasons.append('MISSING_NUMERIC_SOURCE_FRET')
            if component_reasons:
                expected_refusals.append(dict(group_ref=group_id,reasons=sorted(component_reasons)));continue
            base=_plain_reasons(docs,nodes,refs,pinned);lo,hi=min(values),max(values)
            inner=[r for r in refs if lo<nodes[r]['pitch']<hi];eligible=not base and bool(inner)and not _has_outside_overlap(nodes,refs,index)
            excluded=sorted(set(refs)|{x for r in refs for x in neighbors[r]})
            for h in expected.values():
                if any(len(m['degree_relationships'])!=1 for m in h['member_roles']):
                    expected_refusals.append(dict(group_ref=group_id,hypothesis_ref=h['id'],reasons=['AMBIGUOUS_DEGREE_ASSIGNMENT']));continue
                roles=[dict(degree_token=m['degree_relationships'][0]['token'],relative_octaves=m['degree_relationships'][0]['relative_octaves'])for m in h['member_roles']]
                expected_units[h['id']]=dict(group_ref=group_id,member_refs=refs,strings=strings,roles=roles,pitches=list(map(str,values)),family=[pid,h['root_pc'],h['kind']],inner_refs=inner,excluded_neighborhood=excluded,base_eligible=not base,eligible=eligible)
                expected_units[h['id']].update(part_id=pid,source_unit_ref=refs[0],hypothesis_ref=h['id'],evidence_class='exact_observed_pc_fit',outer_refs=[r for r in refs if r not in inner],inner_strings=[nodes[r]['string']for r in inner])
        if catalog is not None:
            if encoded(catalog['component_scope_refusals'])!=encoded(expected_refusals):raise ValueError('Component refusal inventory differs')
            units=catalog['units']
            if len(units)!=len(expected_units)or{u['id']for u in units}!=set(expected_units):raise ValueError('Component hypothesis denominator differs')
            for u in units:
                want=expected_units[u['id']]
                for field,value in want.items():
                    got=not u['base_reasons']if field=='base_eligible'else not u['reasons']if field=='eligible'else u[field]
                    if encoded(got)!=encoded(value):raise ValueError(f'Independent component {field} differs')
            physical_groups=defaultdict(list)
            for ref,n in nodes.items():physical_groups[n['part'],n['onset']].append(ref)
            native_geometry={}
            for refs in physical_groups.values():
                reasons=_plain_reasons(docs,nodes,refs,pinned)
                if _has_outside_overlap(nodes,refs,index):reasons.append('OVERLAP')
                key=None
                try:
                    settings,frets=_physical(docs,refs,nodes);ss=sorted(frets);base=min(frets.values())
                    key=encoded([*settings,ss,[str(frets[s]-base)for s in ss],[frets[s]==0 for s in ss]])
                except (ValueError,TypeError,KeyError):reasons.append('PHYSICAL_UNAVAILABLE')
                native_geometry[refs[0]]=(refs,not reasons,key)
            geometries=catalog['geometries']
            if len(geometries)!=len(native_geometry)or{g['id']for g in geometries}!=set(native_geometry):raise ValueError('Whole geometry denominator differs')
            for g in geometries:
                refs,eligible,key=native_geometry[g['id']]
                if g['member_refs']!=refs or bool(g['reasons'])==eligible or eligible and g['key']!=key:raise ValueError('Whole source geometry differs')
    except Exception as error:issues.append(str(error))
    return dict(status='PASS_NATIVE_HARMONIC_EVIDENCE'if not issues else'FAIL',issues=issues,groups=len(view.get('groups',[])),hypotheses=hypothesis_count,degree_coordinates=member_coordinates,component_hypotheses=len(expected_units),scope='Exact finite-vocabulary source compatibility and catalog guards, not identified harmonic truth or creative admission')
