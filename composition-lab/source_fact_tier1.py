"""Complete typed extraction of captured JSON; no musical interpretation.

One owner per source path, including empty containers. No duplicate raw document
or normalized note stream is stored. This is Tier1, NOT a Tier2 abstraction.
"""
from copy import deepcopy
import json
import math
from pathlib import Path


def escape(key):
    return key.replace('~','~0').replace('/','~1')


def fact_id(document,pointer):
    return document+'#'+pointer


def kind(value):
    result={dict:'object',list:'array',str:'string',int:'integer',float:'float',bool:'boolean',type(None):'null'}.get(type(value))
    if result is None or type(value) is float and not math.isfinite(value):raise ValueError('Unsupported non-JSON value')
    return result


def extract_documents(documents):
    facts=[];roots=[]
    def visit(document,pointer,value,parent,slot):
        ident=fact_id(document,pointer);tag=kind(value)
        record=dict(id=ident,document=document,pointer=pointer,parent=parent,slot=slot,type=tag)
        if tag=='object':
            if any(type(k) is not str for k in value):raise ValueError('JSON object keys must be strings')
            record['children']=[fact_id(document,pointer+'/'+escape(k)) for k in value]
        elif tag=='array':record['children']=[fact_id(document,pointer+'/'+str(i)) for i in range(len(value))]
        else:record['value']=deepcopy(value)
        facts.append(record)
        if tag=='object':
            for k,v in value.items():visit(document,pointer+'/'+escape(k),v,ident,k)
        elif tag=='array':
            for i,v in enumerate(value):visit(document,pointer+'/'+str(i),v,ident,i)
    if type(documents) is not dict or not documents:raise ValueError('Nonempty captured document map required')
    for name,value in documents.items():
        if type(name) is not str or not name or '#' in name:raise ValueError('Invalid source document identity')
        roots.append(dict(document=name,fact_ref=fact_id(name,'')))
        visit(name,'',value,None,None)
    result=dict(tier=1,schema='complete-source-facts/1',documents=roots,facts=facts,scope='All captured JSON typed values and topology; not source byte formatting or musical analysis')
    validate(result)
    return result


def extract(capture):
    files=[capture/'metadata.json']+sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
    return extract_documents({p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in files})


def validate(tier1):
    if type(tier1) is not dict or set(tier1)!={'tier','schema','documents','facts','scope'} or type(tier1['tier']) is not int or tier1['tier']!=1 or tier1['schema']!='complete-source-facts/1':raise ValueError('Unsupported complete Tier1')
    facts=tier1['facts'];index={r['id']:r for r in facts}
    if len(index)!=len(facts):raise ValueError('Duplicate source ownership')
    if tier1['scope']!='All captured JSON typed values and topology; not source byte formatting or musical analysis':raise ValueError('Undeclared source scope')
    visited=[];seen=set();document_names=[]
    def walk(ident,document,pointer,parent,slot):
        if ident not in index or ident in seen:raise ValueError('Missing/duplicated/cyclic source ownership')
        row=index[ident];visited.append(ident);seen.add(ident)
        if row.get('id')!=fact_id(document,pointer) or row.get('document')!=document or row.get('pointer')!=pointer or row.get('parent')!=parent or type(row.get('slot')) is not type(slot) or row.get('slot')!=slot:raise ValueError('Source address ownership differs')
        base={'id','document','pointer','parent','slot','type'};tag=row['type']
        if tag in ('object','array'):
            if set(row)!=base|{'children'} or type(row['children']) is not list:raise ValueError('Invalid source container')
            slots=[]
            for i,child in enumerate(row['children']):
                if child not in index:raise ValueError('Missing source child')
                key=index[child]['slot']
                if tag=='object' and type(key) is not str or tag=='array' and (type(key) is not int or key!=i):raise ValueError('Invalid source child slot/order')
                if key in slots:raise ValueError('Duplicate source key')
                slots.append(key);walk(child,document,pointer+'/'+(escape(key) if tag=='object' else str(i)),ident,key)
        elif set(row)!=base|{'value'} or kind(row['value'])!=tag:raise ValueError('Typed source value differs')
    for root in tier1['documents']:
        if set(root)!={'document','fact_ref'} or root['document'] in document_names:raise ValueError('Duplicate/invalid source document')
        document_names.append(root['document']);walk(root['fact_ref'],root['document'],'',None,None)
    if visited!=[r['id'] for r in facts]:raise ValueError('Unowned facts or original source traversal order differs')


def project_documents(tier1):
    """Ephemeral preceding-tier compatibility view; no files/caches/source reads."""
    validate(tier1);index={r['id']:r for r in tier1['facts']}
    def value(ident):
        row=index[ident]
        if row['type']=='object':return {index[i]['slot']:value(i) for i in row['children']}
        if row['type']=='array':return [value(i) for i in row['children']]
        return deepcopy(row['value'])
    return {r['document']:value(r['fact_ref']) for r in tier1['documents']}


def ownership_ledger(tier1):
    validate(tier1)
    return [dict(fact_ref=r['id'],source_document=r['document'],source_pointer=r['pointer'],type=r['type'],owner='T1',disposition='exact_source_fact_not_yet_lifted') for r in tier1['facts']]
