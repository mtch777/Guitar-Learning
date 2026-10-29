"""Fixed-population opportunity check; does not admit or generate a score."""
import argparse,hashlib,json
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from inner_voicing import component_links
from probe_voicing_frames import links,preflight
from voicing_frames import pitches
from fretting_contacts import analyze as contacts


def inventory(c,evidence,*,framed):
    units={u['id']:u for u in c['units']};rows=[]
    for group in evidence['groups']:
        allrefs=[h['id'] for h in group['hypotheses']];out={}
        for hid in allrefs:
            target=units.get(hid)
            if target is None or target['reasons']:continue
            source_links=links(c,target,'C') if framed else component_links(c,target)
            for link in source_links:
                donor=link['donor'];key=tuple(map(str,pitches(*target['family'][1:],link['roles'])))
                support=out.setdefault(key,{}).setdefault(hid,dict(roles=link['roles'],donor_hypothesis_refs=set(),donor_group_refs=set()))
                if support['roles']!=link['roles']:raise ValueError('Different coordinates for one hypothesis/output')
                support['donor_hypothesis_refs'].add(donor['id']);support['donor_group_refs'].add(donor['group_ref'])
        layouts=[]
        for values,mapped in sorted(out.items()):
            support=[dict(target_hypothesis_ref=h,roles=s['roles'],donor_hypothesis_refs=sorted(s['donor_hypothesis_refs']),donor_group_refs=sorted(s['donor_group_refs'])) for h,s in sorted(mapped.items())]
            target=units[support[0]['target_hypothesis_ref']]
            layouts.append(dict(pitches=list(values),support=support,donor_refs=sorted({r for s in support for r in s['donor_group_refs']}),
                changed=values!=tuple(str(F(p)) for p in target['pitches']),all_assumptions=set(mapped)==set(allrefs)))
        rows.append(dict(target_ref=group['member_refs'][0],all_hypothesis_refs=allrefs,layouts=layouts))
    return rows


def baseline_rows(evidence,ledger):
    saved={g['group_ref']:g for g in ledger['groups']};rows=[]
    for group in evidence['groups']:
        row=saved.get(group['group_ref']);layouts=[]
        for item in row['layouts'] if row else []:
            layouts.append(dict(pitches=item['pitches'],support=item['support'],donor_refs=sorted({r for s in item['support'] for r in s['donor_group_refs']}),
                changed=item['changed'],all_assumptions=item['support_class']=='ALL_ENUMERATED_TARGET_ASSUMPTIONS'))
        rows.append(dict(target_ref=group['member_refs'][0],all_hypothesis_refs=[h['id']for h in group['hypotheses']],layouts=layouts))
    return rows


def cheap_guard(c,layout):
    if not layout['all_assumptions']:return 'NOT_SUPPORTED_UNDER_EVERY_ASSUMPTION'
    if not layout['changed']:return 'UNCHANGED'
    units={u['id']:u for u in c['units']};target=units[layout['support'][0]['target_hypothesis_ref']]
    gate=preflight(c,target,layout['support'][0]['roles'])
    if gate['stage'] not in ('NO_INDEPENDENT_WHOLE_GEOMETRY','WHOLE_GEOMETRY_PREFLIGHT_ONLY'):return gate['stage']
    source=next(g for g in c['geometries'] if set(g['member_refs'])==set(target['member_refs']))
    _,tuning,capo,_,_,_=json.loads(source['key'])
    required=[dict(string=s,fret=int(F(p)-F(tuning[s])-F(capo))) for s,p in zip(target['strings'],layout['pitches'])]
    contact=contacts(required)
    return 'PASSES_CHEAP_GUARDS_ONLY' if contact['status']=='COVERED' else 'CONTACT_'+contact['status']


def compare(c,evidence,baseline):
    old=inventory(c,evidence,framed=False)
    if old!=baseline_rows(evidence,baseline):raise ValueError('Old complete denominator differs from saved baseline')
    new=inventory(c,evidence,framed=True);old_by={r['target_ref']:r for r in old};counts=Counter();changes=[]
    for row in new:
        counts['all_source_groups']+=1;counts['groups_with_hypotheses']+=bool(row['all_hypothesis_refs'])
        prior={tuple(x['pitches']) for x in old_by[row['target_ref']]['layouts']}
        for layout in row['layouts']:
            stage=cheap_guard(c,layout);counts['concrete_outcomes']+=1;counts[stage]+=1
            added=tuple(layout['pitches']) not in prior
            counts['new_changed_concrete_outcomes']+=bool(added and layout['changed'])
            if added and layout['changed']:
                counts['new_'+stage]+=1
                changes.append(dict(target_ref=row['target_ref'],stage=stage,layout=layout))
    return dict(status='OPPORTUNITY_CHECK_ONLY_NOT_ADMISSION',policy_activated=False,counts=dict(counts),targets=new,added_changes=changes,
        still_required=['Actual inverse and exact outside facts','Source fret limits','Execution/tie/technique/pedal guards','Independent complete native comparison','Fresh portability','Musical/physical acceptance'])


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(protocol,output):
    protocol=json.loads(Path(protocol).read_text());output=Path(output);output.mkdir(parents=True,exist_ok=False)
    def unchanged():
        if any(sha(p)!=h for p,h in protocol['hashes'].items()):raise ValueError('Protocol input/code drift')
    unchanged();summary={}
    for case in protocol['cases']:
        try:
            result=compare(*[json.loads(Path(case[k]).read_text()) for k in ('catalog','evidence','baseline')])
            summary[case['name']]=dict(status=result['status'],counts=result['counts'])
        except Exception as exc:
            result=dict(status='FAIL_RETAINED',error=str(exc));summary[case['name']]=result
        (output/(case['name']+'.json')).write_text(json.dumps(result,indent=2))
    unchanged();(output/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('protocol');p.add_argument('output');a=p.parse_args()
    r=run(a.protocol,a.output);print(json.dumps(r,indent=2));raise SystemExit(1 if any(v['status']=='FAIL_RETAINED'for v in r.values())else 0)
