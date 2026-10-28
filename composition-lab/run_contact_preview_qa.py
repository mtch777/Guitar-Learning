"""Complete-source gates for a provisional, source-derived inner-voicing preview.

No caller supplies pitches or a preferred target. The existing source component
population and SAME owned degree inverse choose and realize every proposal.
"""
import argparse,json,traceback
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from run_declared_chord_qa import run as exact_qa,sha,dump
from run_connected_tier2_qa import bundle
from run_voicing_register_qa import save_capture
from inner_voicing import catalog,options,apply,sample,component_links,PREVIEW_POLICY
from check_inner_voicing import inventory,check
from connected_tier2 import realize
from qa_isolation_harness import execute

SEEDS=list(range(32))


def run(capture,output,freeze):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text())
    sources={str(p.resolve()):sha(p) for p in capture.glob('*.json')}
    dump(output/'plan.json',dict(policy=PREVIEW_POLICY,seeds=SEEDS,source_hashes=sources,
        selection='All eligible targets in rational onset/part/identity order; first target with a changed draw among fixed seeds0..31 at100%; keep every draw and refusal',
        physical_scope='At most four contacts; no reach, comfort, clean tone or movement claim'))
    try:
        if any(sha(Path(p))!=h for p,h in frozen.get('native_hashes',{}).items()):raise ValueError('Frozen native dependency drift')
        zero=exact_qa(capture,output/'zero-and-pair',freeze)
        if zero['status']!='PASS_DECLARED_WRITTEN_CHORD_QA':raise ValueError('Whole-source/pair inverse failed; retained')
        upper=json.loads((output/'zero-and-pair/stripped-tier2.json').read_text())
        actual_zero=json.loads((output/'zero-and-pair/zero-isolated/worker/output.json').read_text())
        save_capture(actual_zero,output/'zero-capture')
        c=catalog(upper);native=inventory(actual_zero);dump(output/'independent-inventory.json',native)
        def unitset(rows,eligible=False):return {r['id'] for r in rows if not eligible or not r['reasons']}
        for eligible in (False,True):
            if unitset(c['units'],eligible)!=unitset(native['units'],eligible):raise ValueError('Independent target denominator disagreement')
        links={(t['id'],r['donor']['id'],r['changed']) for t in c['units'] for r in component_links(c,t)}
        if links!={(r['target_ref'],r['donor_ref'],r['changed']) for r in native['component_links']}:raise ValueError('Independent source component population disagreement')
        zero_ref=next(iter(c['lane_graph']['nodes']), 'event:unused-exact-zero-target')
        code,_=bundle(Path(__file__).parent.resolve())
        preview_zero=execute(code,upper,dict(voicing=0,register=0,target_ref=zero_ref,seed=0,context_policy=PREVIEW_POLICY),actual_zero,
            output/'preview-zero-isolated',timeout=600,purpose='voicing_register_intervention')
        if preview_zero['status']!='PASS':raise ValueError(preview_zero)
        ordered=sorted(c['units'],key=lambda t:(F(c['lane_graph']['nodes'][t['id']]['onset_q']),t['part_id'],t['id']))
        byid={t['id']:t for t in ordered};counts=Counter();ledger=[];audits=[];demonstration=None
        for target in ordered:
            legacy=options(upper,target['id'],c)
            evidence=options(upper,target['id'],c,physical_policy=PREVIEW_POLICY)
            if legacy['target']!=evidence['target']:raise ValueError('Provisional route changed musical target ownership')
            counts['targets']+=1;counts['eligible_targets']+=not bool(target['reasons'])
            counts['legacy_changed_layouts']+=sum(o['changed'] for o in legacy['options'])
            counts['provisional_changed_layouts']+=sum(o['changed'] for o in evidence['options'])
            counts['rejected_layouts']+=len(evidence['rejected'])
            for choice in evidence['options']:
                if not choice['changed']:continue
                after=realize(apply(upper,target,choice['roles']))
                for donor_ref in choice['donor_refs']:
                    audit=check(actual_zero,after,target['member_refs'],byid[donor_ref]['member_refs'],[],contact_coverage=choice['relationship']['contact_coverage'])
                    audits.append(dict(target=target['id'],donor=donor_ref,result=audit))
                    if audit['status']!='PASS_PROVISIONAL_INNER_CONTACTS':raise ValueError(dict(independent_rejection=audits[-1]))
                    counts['independent_changed_pairs']+=1
            control=dict(voicing=100,register=0,target_ref=target['id'],context_policy=PREVIEW_POLICY)
            draws=[]
            for seed in SEEDS:
                chosen,report=sample(evidence,dict(control,seed=seed));draws.append(dict(seed=seed,decision=report))
                if demonstration is None and chosen is not None and chosen['changed']:
                    demonstration=(target,evidence,chosen,dict(control,seed=seed))
            ledger.append(dict(target=target['id'],legacy=legacy,provisional=evidence,draws=draws))
            dump(output/'choices.json',ledger);dump(output/'independent-pairs.json',audits)
        demo=None
        if demonstration is not None:
            target,evidence,chosen,control=demonstration
            expected=realize(apply(upper,target,chosen['roles']))
            code,_=bundle(Path(__file__).parent.resolve())
            worker=execute(code,upper,control,expected,output/'changed-isolated',timeout=600,purpose='voicing_register_intervention')
            if worker['status']!='PASS':raise ValueError(worker)
            actual=json.loads((output/'changed-isolated/worker/output.json').read_text())
            actual_audit=check(actual_zero,actual,target['member_refs'],byid[chosen['donor_refs'][0]]['member_refs'],[],contact_coverage=chosen['relationship']['contact_coverage'])
            if actual_audit['status']!='PASS_PROVISIONAL_INNER_CONTACTS':raise ValueError(actual_audit)
            save_capture(actual,output/'changed-capture')
            frequencies=[]
            for strength in (0,50,100):
                reports=[sample(evidence,dict(control,voicing=strength,seed=i))[1] for i in range(1000)]
                frequencies.append(dict(strength=strength,trials=1000,released=sum(r['released'] for r in reports),changed=sum(r['changed'] for r in reports)))
            demo=dict(controls=control,target=target,chosen=chosen,actual_worker_audit=actual_audit,isolated=worker,frequencies=frequencies,
                      status='PROVISIONAL_AUDIBLE_ARTIFACT_NOT_YET_BUILT',human_playability='UNVERIFIED',listening_judgment=None)
            dump(output/'demonstration.json',demo)
        if set(sources)!={str(p.resolve()) for p in capture.glob('*.json')}:raise ValueError('Source file inventory drift')
        if any(sha(Path(p))!=h for p,h in {**sources,**frozen['code_hashes'],**frozen.get('native_hashes',{})}.items()):raise ValueError('Frozen source, code or native dependency drift')
        result=dict(status='PASS_PROVISIONAL_CONTACT_PREVIEW_QA' if demo else 'PASS_CONTACT_PREVIEW_QA_NO_CHANGE',
            song_id=zero['song_id'],title=zero['title'],notes=zero['note_occurrences'],facts=zero['source_facts'],counts=dict(counts),changed_demonstration=demo is not None,
            human_playability='UNVERIFIED',listening_judgment=None,creative_gateway='NOT_PASSED',
            qa1='Frozen unchanged code; fresh status is established only by the preregistered selection manifest',
            qa2='Actual source-free whole and degree-pair inverse plus explicit preview0%; actual changed worker if admitted; independently checked against captured facts',
            qa3='Source coupled inner degrees and complete chord PC set; literal outer and all other source facts locked. Contact coverage is provisional, not anatomy or artist intent')
    except Exception as e:
        result=dict(status='FAIL_RETAINED',error=str(e));(output/'traceback.txt').write_text(traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze);print(json.dumps(r),flush=True)
    raise SystemExit(0 if r['status'].startswith('PASS_') else 1)
