"""Preregistered offline A/B/C voicing diagnostic; never admits a change."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
from inner_voicing import component_links,encoded
from voicing_frames import relationship,pitches


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def links(c,target,arm):
    if arm=='A':return component_links(c,target)
    if arm not in ('B','C'):raise ValueError('Unknown arm')
    if target['reasons']:return []
    selected=set(target['inner_strings']);excluded=set(target['excluded_neighborhood']);out=[]
    target_frame=relationship(*target['family'][1:],roles=target['roles'])['frame_octave']
    for donor in c['units']:
        same=donor['family']==target['family'] if arm=='B' else donor['family'][::2]==target['family'][::2]
        if donor['base_reasons'] or not same or excluded.intersection(donor['member_refs']) or not selected<=set(donor['inner_strings']):continue
        frame=relationship(*donor['family'][1:],roles=donor['roles'])
        source=dict(zip(donor['strings'],frame['components']));new=[]
        for ref,string,role in zip(target['member_refs'],target['strings'],target['roles']):
            if ref not in target['inner_refs']:new.append(deepcopy(role));continue
            component=source[string]
            new.append(dict(degree_token=component['degree_token'],relative_octaves=target_frame+component['octave_offset']))
        out.append(dict(donor=donor,roles=new,changed=new!=target['roles']))
    return out


def preflight(c,target,roles):
    old=list(map(F,target['pitches']));new=pitches(*target['family'][1:],roles);lo,hi=min(old),max(old)
    inner=[i for i,r in enumerate(target['member_refs']) if r in target['inner_refs']]
    if any(a!=b for i,(a,b) in enumerate(zip(old,new)) if i not in inner):raise ValueError('Protected outer changed')
    if any(not lo<new[i]<hi for i in inner):return dict(stage='INNER_PITCH_OUTSIDE_PROTECTED_ENVELOPE')
    if any((old[i]-old[j])*(new[i]-new[j])<0 for i in inner for j in inner):return dict(stage='INNER_STRING_PITCH_ORDER_REVERSED')
    if {p%12 for p in old}!={p%12 for p in new}:return dict(stage='CHORD_FORMULA_SUPPORT_CHANGED')
    source=next((g for g in c['geometries'] if set(g['member_refs'])==set(target['member_refs'])),None)
    if source is None or source['reasons']:return dict(stage='SOURCE_GEOMETRY_UNAVAILABLE')
    instrument,tuning,capo,strings,_,_=json.loads(source['key'])
    bystring=dict(zip(target['strings'],new));frets={s:bystring[s]-F(tuning[s])-F(capo) for s in strings}
    if any(f<0 or f.denominator!=1 for f in frets.values()):return dict(stage='INVALID_NOMINAL_FRET')
    base=min(frets.values());key=encoded([instrument,tuning,capo,strings,[str(frets[s]-base) for s in strings],[frets[s]==0 for s in strings]])
    excluded=set(target['excluded_neighborhood']);witnesses=[g['id'] for g in c['geometries'] if not g['reasons'] and g['key']==key and not excluded.intersection(g['member_refs'])]
    return dict(stage='WHOLE_GEOMETRY_PREFLIGHT_ONLY' if witnesses else 'NO_INDEPENDENT_WHOLE_GEOMETRY',geometry_key=key,witnesses=witnesses,
        remaining=['Actual inverse and whole fact equality outside release','Target fret limit','Execution and ties','Incident paths','Technique classes','Approved pedals','Artist fit and listening'])


def run_case(path):
    c=json.loads(path.read_text());frames=[];baseline=[];arms={};allkeys={}
    for unit in c['units']:
        if unit['base_reasons']:continue
        f=relationship(*unit['family'][1:],roles=unit['roles'])
        recovered=relationship(*unit['family'][1:],framed=f)
        if recovered!=unit['roles'] or pitches(*unit['family'][1:],recovered)!=list(map(F,unit['pitches'])):raise ValueError('Source frame reversal failed')
        frames.append(dict(id=unit['id'],family=unit['family'],frame=f))
    for arm in ('A','B','C'):
        counts=Counter();rows=[];keys=set()
        for target in c['units']:
            if target['reasons']:counts['refused_targets']+=1;continue
            counts['eligible_targets']+=1;buckets=defaultdict(list)
            for link in links(c,target,arm):
                counts['donor_links']+=1;counts['changed_donor_links']+=int(link['changed'])
                buckets[tuple(map(str,pitches(*target['family'][1:],link['roles'])))].append(link)
            for layout,items in sorted(buckets.items()):
                changed=list(layout)!=target['pitches'];counts['unique_layouts']+=1
                status=preflight(c,target,items[0]['roles']) if changed else dict(stage='UNCHANGED')
                counts[status['stage']]+=1
                row=dict(target_ref=target['id'],roles=items[0]['roles'],pitches=layout,donor_refs=[l['donor']['id'] for l in items],changed=changed,**status)
                rows.append(row)
                if changed:keys.add((target['id'],layout))
        allkeys[arm]=keys;arms[arm]=dict(counts=dict(counts),rows=rows)
    old=json.loads(path.with_name('choices.json').read_text())
    expected={(r['target']['id'],encoded(o['roles']),tuple(o['donor_refs'])) for r in old if isinstance(r['target'],dict) for o in r.get('options',[])+r.get('rejected',[])}
    actual={(r['target_ref'],encoded(r['roles']),tuple(r['donor_refs'])) for r in arms['A']['rows']}
    if expected!=actual:raise ValueError('A differs from frozen policy denominator')
    return dict(status='OFFLINE_PREFLIGHT_COMPLETE',policy_activated=False,source_frame_reversal='PASS_IN_PROCESS_ONLY',frames=frames,arms=arms,
        new_changed_layouts=dict(B_vs_A=len(allkeys['B']-allkeys['A']),C_vs_B=len(allkeys['C']-allkeys['B']),C_vs_A=len(allkeys['C']-allkeys['A'])),
        limits='Not isolated QA2 or admission; catalog source provenance previously checked. No inferred key, voice role or artist quality.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('protocol',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text());args.output.mkdir(exist_ok=False,parents=True)
    if any(sha(p)!=h for p,h in protocol['hashes'].items()):raise ValueError('Frozen input/code drift')
    summary={}
    for case in protocol['cases']:
        try:
            result=run_case(Path(case['catalog']));summary[case['name']]={a:r['counts'] for a,r in result['arms'].items()};summary[case['name']]['new_changed_layouts']=result['new_changed_layouts']
        except Exception as error:result=dict(status='FAIL_RETAINED',error=str(error));summary[case['name']]=result
        (args.output/(case['name']+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    if any(sha(p)!=h for p,h in protocol['hashes'].items()):raise ValueError('Input/code drift during experiment')
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
