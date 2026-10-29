"""One typed relation owns note child membership and its optional accent.

Other note children remain references to their existing owners. No source note
values or original accent backup are retained. Unknown accents are not lifted.
"""
from copy import deepcopy
import re
from source_fact_tier1 import validate as validate_source

SCHEMA='source-note-accent-slots/1'
OWNER='optional_note_accent'
_N=r'(?:0|[1-9][0-9]*)'
_NOTE=re.compile(r'(track-'+_N+r'\.json)#(/measures/'+_N+r'/voices/'+_N+r'/beats/'+_N+r'/notes/('+_N+r'))')
_META={'id','document','pointer','parent','slot','type'}


def _structure(note):
    if type(note)is not dict or set(note)!=_META|{'children'}:
        raise ValueError('Exact note-container structure required')
    if any(type(note[k])is not str for k in ('id','document','pointer','parent','type')):
        raise ValueError('Typed note address required')
    match=_NOTE.fullmatch(note['id'])
    if match is None:raise ValueError('Registered note-array address required')
    document,pointer,ordinal=match.groups()
    if note['document']!=document or note['pointer']!=pointer or note['parent']!=document+'#'+pointer.rsplit('/',1)[0] or type(note['slot'])is not int or note['slot']!=int(ordinal) or note['type']!='object':
        raise ValueError('Note-container address conflict')
    children=note['children'];prefix=note['id']+'/'
    if type(children)is not list or any(type(c)is not str for c in children) or len(set(children))!=len(children):
        raise ValueError('Unique ordered note child references required')
    for child in children:
        tail=child[len(prefix):] if child.startswith(prefix) else None
        if tail is None or '/'in tail or re.search(r'~(?![01])',tail):
            raise ValueError('Child escaped its immediate note-container scope')
        if tail=='accentuated':raise ValueError('Accent child has duplicate structural ownership')


def expand(group):
    """SAME relation emits both the container membership and optional scalar."""
    if type(group)is not dict or set(group)!={'id','note_structure','state'}:
        raise ValueError('Exact optional-accent group required')
    note=group['note_structure'];_structure(note)
    if group['id']!='accent-slot:'+note['id']:raise ValueError('Accent-slot identity conflict')
    state=group['state']
    if type(state)is not dict:raise ValueError('Typed optional state required')
    result=deepcopy(note)
    if state=={'kind':'absent'} and set(state)=={'kind'}:return [result]
    if set(state)!={'kind','value','child_index'} or state['kind']!='explicit' or type(state['value'])is not int or state['value']not in(0,1,2) or type(state['child_index'])is not int or not 0<=state['child_index']<=len(note['children']):
        raise ValueError('Known exact integer accent and insertion index required')
    ident=note['id']+'/accentuated'
    result['children'].insert(state['child_index'],ident)
    accent=dict(id=ident,document=note['document'],pointer=note['pointer']+'/accentuated',parent=note['id'],slot='accentuated',type='integer',value=state['value'])
    return [result,accent]


def build(source_note,source_accent=None):
    """Lift one validated note descriptor and optional known scalar fact."""
    if type(source_note)is not dict:raise ValueError('Note structure required')
    note=deepcopy(source_note)
    if set(note)!=_META|{'children'} or type(note['children'])is not list:
        raise ValueError('Exact note descriptor required')
    if any(type(note[k])is not str for k in ('id','document','pointer','parent','type')):
        raise ValueError('Typed source note address required')
    ident=note.get('id','')+'/accentuated'
    if source_accent is None:
        state={'kind':'absent'}
    else:
        if type(source_accent)is not dict or set(source_accent)!=_META|{'value'}:
            raise ValueError('Exact source accent scalar required')
        wanted=dict(id=ident,document=note.get('document'),pointer=note.get('pointer','')+'/accentuated',parent=note.get('id'),slot='accentuated',type='integer',value=source_accent['value'])
        if source_accent!=wanted or type(source_accent['value'])is not int or source_accent['value']not in(0,1,2) or note['children'].count(ident)!=1:
            raise ValueError('Known source accent/address membership required')
        state=dict(kind='explicit',value=source_accent['value'],child_index=note['children'].index(ident))
        note['children'].remove(ident)
    group=dict(id='accent-slot:'+note.get('id',''),note_structure=note,state=state)
    expand(group)
    return group


def lift(tier1):
    validate_source(tier1);index={r['id']:r for r in tier1['facts']};groups=[]
    for note in tier1['facts']:
        if note['type']!='object' or _NOTE.fullmatch(note['id'])is None:continue
        accent=index.get(note['id']+'/accentuated')
        if accent is not None and (accent['type']!='integer' or type(accent['value'])is not int or accent['value']not in(0,1,2)):continue
        # validate_source has authenticated the actual parent-array membership.
        groups.append(build(note,accent))
    return dict(schema=SCHEMA,groups=sorted(groups,key=lambda g:g['id']))


def realize(model):
    if type(model)is not dict or set(model)!={'schema','groups'} or model['schema']!=SCHEMA or type(model['groups'])is not list:
        raise ValueError('Registered optional-accent model required')
    rows=[];seen=set();ids=[]
    for group in model['groups']:
        emitted=expand(group);ids.append(group['id'])
        for row in emitted:
            if row['id']in seen:raise ValueError('Duplicate optional source ownership')
            seen.add(row['id']);rows.append(row)
    if ids!=sorted(ids):raise ValueError('Canonical optional-accent group order required')
    return rows


def coverage(model):
    """Current materialized fact denominator comes from the SAME expansion."""
    return [dict(fact_ref=r['id'],owner=OWNER)for r in realize(model)]
