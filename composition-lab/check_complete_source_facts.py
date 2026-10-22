"""Independent captured-JSON walker; no Tier1 producer imports."""
import json
import math
from pathlib import Path


def check(capture,tier1):
    files=[capture/'metadata.json']+sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
    expected=[]
    def pointer_token(key):return key.replace('~','~0').replace('/','~1')
    def walk(filename,path,value,parent,slot):
        name=filename+'#'+path
        tag={dict:'object',list:'array',str:'string',int:'integer',float:'float',bool:'boolean',type(None):'null'}[type(value)]
        record={'id':name,'document':filename,'pointer':path,'parent':parent,'slot':slot,'type':tag}
        if type(value) is dict:record['children']=[filename+'#'+path+'/'+pointer_token(k) for k in value]
        elif type(value) is list:record['children']=[filename+'#'+path+'/'+str(i) for i in range(len(value))]
        else:record['value']=value
        expected.append(record)
        if type(value) is dict:
            for key,child in value.items():walk(filename,path+'/'+pointer_token(key),child,name,key)
        elif type(value) is list:
            for i,child in enumerate(value):walk(filename,path+'/'+str(i),child,name,i)
    for file in files:walk(file.name,'',json.loads(file.read_text(encoding='utf-8-sig')),None,None)
    # JSON spelling distinguishes bool/int/float/-0.0; it also checks ordered
    # container child lists and every explicit empty object/array owner.
    actual=tier1.get('facts',[]);issues=[]
    if len(actual)!=len(expected):issues.append('Complete captured path denominator differs')
    mismatches=[i for i,(a,b) in enumerate(zip(actual,expected)) if json.dumps(a,sort_keys=True,allow_nan=False)!=json.dumps(b,sort_keys=True,allow_nan=False)]
    if mismatches:issues.append('Typed source value/order/pointer differs')
    roots=[dict(document=p.name,fact_ref=p.name+'#') for p in files]
    if tier1.get('documents')!=roots:issues.append('Captured document inventory differs')
    return dict(status='PASS_COMPLETE_CAPTURED_JSON_FACTS' if not issues else 'FAIL',expected_paths=len(expected),actual_paths=len(actual),issues=issues,mismatch_indices=mismatches[:20],scope='Every captured JSON field/container/type/order; no byte formatting or musical-abstraction claim')
