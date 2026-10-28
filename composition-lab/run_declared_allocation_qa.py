"""Enumerate complete declared-allocation choices under a pre-analysis code freeze."""
from collections import Counter
import argparse
import json
from pathlib import Path
import traceback
from run_declared_chord_qa import run as zero_and_pair,sha,dump
from run_connected_tier2_qa import bundle
from declared_degree_choices import catalog,options,apply,sample,encoded
from connected_tier2 import realize
from check_declared_allocation import check,proposal_inventory
from qa_isolation_harness import execute


def run(capture,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text())
    original={str(p.resolve()):sha(p) for p in capture.glob('*.json')}
    try:
        if any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Source code differs from preregistered freeze')
        zero=zero_and_pair(capture,output/'zero-and-pair',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError('Exact-zero/source gate failed; original failure retained')
        upper=json.loads((output/'zero-and-pair/stripped-tier2.json').read_text());c=catalog(upper)
        dump(output/'catalog.json',dict(units=c['units']))
        raw_inventory=proposal_inventory(c['before']);dump(output/'independent-proposal-inventory.json',raw_inventory)
        if {u['id'] for u in raw_inventory['units']}!={u['id'] for u in c['units']}:raise ValueError('Independent declared-unit inventory disagreement')
        if {u['id'] for u in raw_inventory['units'] if not u['reasons']}!={u['id'] for u in c['units'] if not u['reasons']}:raise ValueError('Independent eligible-unit inventory disagreement')
        own_links={(a['id'],b['id'],[dict(zip(b['strings'],b['roles']))[s] for s in a['strings']]!=a['roles']) for a in c['units'] for b in c['units'] if not a['reasons'] and not b['reasons'] and a['key']==b['key']}
        if own_links!={(r['target_ref'],r['donor_ref'],r['changed']) for r in raw_inventory['proposed_links']}:raise ValueError('Independent complete proposal-link denominator disagreement')
        results=[];independent=[];first=None;counts=Counter()
        byid={u['id']:u for u in c['units']}
        for target in c['units']:
            # All declared units are accounted for, including exact reasons for
            # excluded targets and candidates with no different observed layout.
            if target['reasons']:
                results.append(dict(target=target['id'],status='REFUSED_TARGET',reasons=target['reasons']));counts['refused_targets']+=1;continue
            peers=[u for u in c['units'] if u['key']==target['key'] and not u['reasons']]
            changed=[u for u in peers if [dict(zip(u['strings'],u['roles']))[s] for s in target['strings']]!=target['roles']]
            counts['eligible_targets']+=1;counts['changed_donor_pairs']+=len(changed)
            if not changed:
                results.append(dict(target=target['id'],status='NO_DIFFERENT_OBSERVED_LAYOUT',peer_refs=[p['id'] for p in peers]));continue
            evidence=options(upper,target['id'],c);results.append(evidence)
            for choice in evidence['options']:
                if not choice['changed']:continue
                after=realize(apply(upper,target,choice['roles']));counts['admitted_changed_layouts']+=1
                for ref in choice['donor_refs']:
                    audit=check(c['before'],after,target['member_refs'],byid[ref]['member_refs'])
                    independent.append(dict(target=target['id'],donor=ref,result=audit));counts['independently_checked_changed_pairs']+=1
                    if audit['status']!='PASS_LOCKED_DECLARED_ALLOCATION':raise ValueError(dict(independent_disagreement=independent[-1]))
                if first is None:first=(evidence,choice,after)
            counts['rejected_changed_layouts']+=len(evidence['rejected'])
            dump(output/'choices.json',results);dump(output/'independent.json',independent)
        dump(output/'choices.json',results);dump(output/'independent.json',independent)
        demonstration=None
        if first is not None:
            evidence,choice,expected=first
            control=dict(voicing=100,register=0,target_ref=evidence['target']['id'],seed=0,context_policy='declared_degree_allocation')
            seed=next((i for i in range(100000) if sample(evidence,dict(control,seed=i))[0]==choice),None)
            if seed is None:raise ValueError('No deterministic demonstration seed found')
            control['seed']=seed;code,_=bundle(Path(__file__).parent.resolve())
            isolated=execute(code,upper,control,expected,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
            if isolated['status']!='PASS':raise ValueError(isolated)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text())
            target=evidence['target'];donor=byid[choice['donor_refs'][0]]
            actual_audit=check(c['before'],actual,target['member_refs'],donor['member_refs'])
            if actual_audit['status']!='PASS_LOCKED_DECLARED_ALLOCATION':raise ValueError(actual_audit)
            frequencies=[]
            for strength in (0,50,100):
                reports=[sample(evidence,dict(control,voicing=strength,seed=i))[1] for i in range(1000)]
                frequencies.append(dict(strength=strength,trials=1000,released=sum(r['released'] for r in reports),changed=sum(r['changed'] for r in reports)))
            demonstration=dict(controls=control,selection='First admitted target/layout in stable source/parameter order; first seed producing that layout. Demonstration seed is not a probability estimate.',
                actual_worker_audit=actual_audit,isolated=isolated,frequencies=frequencies)
            dump(output/'demonstration.json',demonstration)
        if any(sha(Path(p))!=h for p,h in original.items()) or any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Source or code drift')
        result=dict(status='PASS_DECLARED_ALLOCATION_QA',song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],declared_groups=len(c['units']),counts=dict(counts),changed_demonstration=demonstration is not None,
            independent_denominator=raw_inventory['counts'],qa1='Untuned frozen full capture retained, including no-declaration cases',qa2='Actual source-free whole and degree-pair zero workers; changed worker if admitted',
            qa3='Conditional source-declared degrees; whole source-supported allocation and witnessed incident motion. Not identified melody, inferred acoustic harmony, style preference or human listening acceptance.')
    except Exception as error:
        result=dict(status='FAIL_RETAINED',error=str(error));(output/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
    dump(output/'result.json',result);return result


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args(argv)
    result=run(a.capture,a.output,a.freeze);print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS_DECLARED_ALLOCATION_QA' else 1


if __name__=='__main__':raise SystemExit(main())
