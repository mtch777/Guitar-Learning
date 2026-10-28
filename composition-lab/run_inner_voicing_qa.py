"""Frozen complete-source gates for bounded inner-degree recombination."""
import argparse
from collections import Counter
from fractions import Fraction as F
import json
from pathlib import Path
import traceback
from run_declared_chord_qa import run as zero_and_pair,sha,dump
from run_connected_tier2_qa import bundle
from inner_voicing import catalog,component_links,options,apply,sample,POLICY
from check_inner_voicing import inventory,check
from connected_tier2 import realize
from qa_isolation_harness import execute


def run(capture,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());original={str(p.resolve()):sha(p) for p in capture.glob('*.json')}
    try:
        if any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Code changed after freeze')
        zero=zero_and_pair(capture,output/'zero-and-pair',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError('Source/zero gate failed; failure retained')
        upper=json.loads((output/'zero-and-pair/stripped-tier2.json').read_text());c=catalog(upper);native=inventory(c['before'])
        dump(output/'catalog.json',dict(units=c['units'],geometries=c['geometries']));dump(output/'independent-inventory.json',native)
        def unitset(rows,eligible=False):return {u['id'] for u in rows if not eligible or not u['reasons']}
        for eligible in (False,True):
            if unitset(c['units'],eligible)!=unitset(native['units'],eligible):raise ValueError('Independent unit denominator disagreement')
            if {frozenset(g['member_refs']) for g in c['geometries'] if not eligible or not g['reasons']}!={frozenset(g['member_refs']) for g in native['geometries'] if not eligible or not g['reasons']}:raise ValueError('Independent whole geometry denominator disagreement')
        links={(u['id'],r['donor']['id'],r['changed']) for u in c['units'] for r in component_links(c,u)}
        if links!={(r['target_ref'],r['donor_ref'],r['changed']) for r in native['component_links']}:raise ValueError('Independent component denominator disagreement')
        counts=Counter();ledger=[];audits=[];first=None;byid={u['id']:u for u in c['units']};nativegeom={frozenset(g['member_refs']):g for g in native['geometries']}
        for target in c['units']:
            if target['reasons']:
                counts['refused_targets']+=1;ledger.append(dict(target=target['id'],status='REFUSED_TARGET',reasons=target['reasons']));continue
            counts['eligible_targets']+=1;proposals=component_links(c,target);counts['component_links']+=len(proposals);counts['changed_component_links']+=sum(p['changed'] for p in proposals)
            evidence=options(upper,target['id'],c);ledger.append(evidence)
            for choice in evidence['options']:
                if not choice['changed']:continue
                counts['admitted_changed_layouts']+=1;after=realize(apply(upper,target,choice['roles']))
                witness=choice['relationship']['geometry_witness_refs'][0]
                # Every listed geometry must have passed the independent raw
                # denominator. Full after-state checks use one witness per donor.
                for refs in choice['relationship']['geometry_witness_refs']:
                    if frozenset(refs)not in nativegeom or nativegeom[frozenset(refs)]['reasons']:raise ValueError('Listed geometry is not independently eligible')
                for donor in choice['donor_refs']:
                    audit=check(c['before'],after,target['member_refs'],byid[donor]['member_refs'],witness)
                    audits.append(dict(target=target['id'],donor=donor,geometry_refs=witness,result=audit));counts['independently_checked_changed_pairs']+=1
                    if audit['status']!='PASS_LOCKED_INNER_VOICING':raise ValueError(dict(raw_checker_disagreement=audits[-1]))
                if first is None:first=(evidence,choice,after)
            counts['rejected_changed_layouts']+=len(evidence['rejected']);dump(output/'choices.json',ledger);dump(output/'independent.json',audits)
        dump(output/'choices.json',ledger);dump(output/'independent.json',audits)
        if first:
            evidence,choice,expected=first;control=dict(voicing=100,register=0,target_ref=evidence['target']['id'],seed=0,context_policy=POLICY)
            seed=next((i for i in range(100000) if sample(evidence,dict(control,seed=i))[0]==choice),None)
            if seed is None:raise ValueError('No reproducible demonstration seed')
            control['seed']=seed;code,_=bundle(Path(__file__).parent.resolve());isolated=execute(code,upper,control,expected,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
            if isolated['status']!='PASS':raise ValueError(isolated)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text());target=evidence['target'];donor=byid[choice['donor_refs'][0]];witness=choice['relationship']['geometry_witness_refs'][0]
            audit=check(c['before'],actual,target['member_refs'],donor['member_refs'],witness)
            if audit['status']!='PASS_LOCKED_INNER_VOICING':raise ValueError(audit)
            frequencies=[]
            for strength in (0,50,100):
                reports=[sample(evidence,dict(control,voicing=strength,seed=i))[1] for i in range(1000)]
                frequencies.append(dict(strength=strength,trials=1000,released=sum(r['released'] for r in reports),changed=sum(r['changed'] for r in reports)))
            dump(output/'demonstration.json',dict(controls=control,selection='First admitted source-order target, stable component order, first seed producing it. Not a probability estimate.',actual_worker_audit=audit,isolated=isolated,frequencies=frequencies))
        if any(sha(Path(p))!=h for p,h in original.items())or any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Source or code drift')
        result=dict(status='PASS_BOUNDED_INNER_VOICING_QA',policy=POLICY,song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],counts=dict(counts),independent_denominator=native['counts'],changed_demonstration=first is not None,
            capture_role='fresh_random' if capture.resolve()==(freeze.parent/'fresh/capture').resolve() else 'development_replay',
            qa1='Unchanged frozen code; capture role recorded separately; failures retained',qa2='Actual source-free whole/pair inverse; actual changed worker when admitted',qa3='Protected literal outer occurrences and observed coupled inner degrees; same pitch equations. Complete formula, explicit doubling release, observed whole geometry. No inferred melody, artist fit, acoustic endpoint or human playability claim.')
    except Exception as error:
        result=dict(status='FAIL_RETAINED',error=str(error));(output/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
    dump(output/'result.json',result);return result


def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args(argv)
    result=run(a.capture,a.output,a.freeze);print(json.dumps(result,indent=2));return 0 if result['status']=='PASS_BOUNDED_INNER_VOICING_QA' else 1


if __name__=='__main__':raise SystemExit(main())
