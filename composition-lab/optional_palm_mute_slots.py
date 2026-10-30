"""A beat's optional Boolean palm-mute flag has one reversible owner.

The owner retains only container references and the typed optional state. Other
beat children, including notes and timing, remain with their existing owners.
"""
from copy import deepcopy
import re
from source_fact_tier1 import validate as validate_source

SCHEMA='source-beat-palm-mute-slots/1'
OWNER='optional_beat_palm_mute'
_N=r'(?:0|[1-9][0-9]*)'
_BEAT=re.compile(r'(track-'+_N+r'\.json)#(/measures/'+_N+r'/voices/'+_N+r'/beats/('+_N+r'))')
_META={'id','document','pointer','parent','slot','type'}


def _structure(beat):
    if type(beat)is not dict or set(beat)!=_META|{'children'}:raise ValueError('Exact beat-container structure required')
    if any(type(beat[k])is not str for k in('id','document','pointer','parent','type')):raise ValueError('Typed beat address required')
    match=_BEAT.fullmatch(beat['id'])
    if match is None:raise ValueError('Registered beat-array address required')
    document,pointer,index=match.groups()
    if beat['document']!=document or beat['pointer']!=pointer or beat['parent']!=document+'#'+pointer.rsplit('/',1)[0]or type(beat['slot'])is not int or beat['slot']!=int(index)or beat['type']!='object':raise ValueError('Beat-container address conflict')
    children=beat['children'];prefix=beat['id']+'/'
    if type(children)is not list or any(type(c)is not str for c in children)or len(set(children))!=len(children):raise ValueError('Unique ordered beat child references required')
    for child in children:
        tail=child[len(prefix):]if child.startswith(prefix)else None
        if tail is None or '/'in tail or re.search(r'~(?![01])',tail):raise ValueError('Child escaped its immediate beat scope')
        if tail=='palmMute':raise ValueError('Palm-mute child has duplicate structural ownership')


def expand(group):
    if type(group)is not dict or set(group)!={'id','beat_structure','state'}:raise ValueError('Exact optional palm-mute group required')
    beat=group['beat_structure'];_structure(beat)
    if group['id']!='palm-mute-slot:'+beat['id']:raise ValueError('Palm-mute-slot identity conflict')
    state=group['state'];result=deepcopy(beat)
    if type(state)is not dict:raise ValueError('Typed optional state required')
    if state=={'kind':'absent'}and set(state)=={'kind'}:return[result]
    if set(state)!={'kind','value','child_index'}or state['kind']!='explicit'or type(state['value'])is not bool or type(state['child_index'])is not int or not 0<=state['child_index']<=len(beat['children']):raise ValueError('Known exact Boolean and insertion index required')
    ident=beat['id']+'/palmMute';result['children'].insert(state['child_index'],ident)
    flag=dict(id=ident,document=beat['document'],pointer=beat['pointer']+'/palmMute',parent=beat['id'],slot='palmMute',type='boolean',value=state['value'])
    return[result,flag]


def build(source_beat,source_flag=None):
    if type(source_beat)is not dict:raise ValueError('Beat structure required')
    beat=deepcopy(source_beat)
    if set(beat)!=_META|{'children'}or type(beat['children'])is not list:raise ValueError('Exact beat descriptor required')
    if any(type(beat[k])is not str for k in('id','document','pointer','parent','type')):raise ValueError('Typed source beat address required')
    ident=beat['id']+'/palmMute'
    if source_flag is None:state={'kind':'absent'}
    else:
        if type(source_flag)is not dict or set(source_flag)!=_META|{'value'}:raise ValueError('Exact source palm-mute scalar required')
        wanted=dict(id=ident,document=beat['document'],pointer=beat['pointer']+'/palmMute',parent=beat['id'],slot='palmMute',type='boolean',value=source_flag['value'])
        if source_flag!=wanted or type(source_flag['value'])is not bool or beat['children'].count(ident)!=1:raise ValueError('Known Boolean/address membership required')
        state=dict(kind='explicit',value=source_flag['value'],child_index=beat['children'].index(ident));beat['children'].remove(ident)
    group=dict(id='palm-mute-slot:'+beat['id'],beat_structure=beat,state=state);expand(group);return group


def lift(tier1):
    validate_source(tier1);index={r['id']:r for r in tier1['facts']};groups=[]
    for beat in tier1['facts']:
        if beat['type']!='object'or _BEAT.fullmatch(beat['id'])is None:continue
        flag=index.get(beat['id']+'/palmMute')
        if flag is not None and(flag['type']!='boolean'or type(flag['value'])is not bool):continue
        groups.append(build(beat,flag))
    return dict(schema=SCHEMA,groups=sorted(groups,key=lambda g:g['id']))


def realize(model):
    if type(model)is not dict or set(model)!={'schema','groups'}or model['schema']!=SCHEMA or type(model['groups'])is not list:raise ValueError('Registered optional palm-mute model required')
    rows=[];seen=set();ids=[]
    for group in model['groups']:
        values=expand(group);ids.append(group['id'])
        for row in values:
            if row['id']in seen:raise ValueError('Duplicate optional source ownership')
            seen.add(row['id']);rows.append(row)
    if ids!=sorted(ids):raise ValueError('Canonical palm-mute group order required')
    return rows


def coverage(model):return[dict(fact_ref=r['id'],owner=OWNER)for r in realize(model)]
