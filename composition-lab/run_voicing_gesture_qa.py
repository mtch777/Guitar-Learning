"""Frozen source/inverse/context experiment for atomic voicing sequences."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import traceback
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower,realize
from voicing_register import apply_family_choices
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check as source_check
from check_technique_connections import check as relationship_check
from check_family_policy import check as inventory_check
from check_voicing_gesture import check as changed_check
from check_voicing_gesture_discovery import check as discovery_check
from run_voicing_register_qa import save_capture
import voicing_gestures as v


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,indent=2),encoding='utf-8')


def run(capture,output,freeze):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('New private output required')
    frozen=json.loads(freeze.read_text(encoding='utf-8'))
    if frozen['policy']!=v.POLICY or any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Frozen code/policy changed')
    source={str(p.resolve()):sha(p) for p in capture.glob('*.json')}
    output.mkdir(parents=True);dump(output/'source-hashes.json',source);result=dict(status='RUNNING')
    try:
        lower=extract(capture);docs=project_documents(lower);complete=analyze(lower,families=True)
        if complete['unsupported']:
            dump(output/'unsupported.json',complete['unsupported']);raise ValueError('Unsupported source owners retained')
        relations=relationship_check(docs,complete)
        if relations['status']!='PASS_SOURCE_BACKED_RELATIONSHIPS':raise ValueError(relations)
        upper=strip_lower(complete);dump(output/'stripped-tier2.json',upper);code,modules=bundle(Path(__file__).parent)
        zero=execute(code,upper,dict(variation=0),lower,output/'zero-isolated',timeout=300)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text());raw=source_check(capture,actual)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(raw)
        from run_reversible_tier_qa import extract_documents as written
        import musical_tier2 as music
        expected=music.strip_lower(music.analyze(written(docs)))
        pair_code=code+"\ndef reconstruct(upper,controls):\n    if controls!={'variation':0}:raise ValueError('Explicit zero required')\n    return sys.modules['voicing_families'].validate(upper)\n"
        pair=execute(pair_code,upper['musical_relationships'],dict(variation=0),expected,output/'pair-isolated',timeout=300)
        if pair['status']!='PASS':raise ValueError(pair)
        cat=v.catalog(lower);raw_inventory=inventory_check(docs,cat['base'])
        if raw_inventory['status']!='PASS_INDEPENDENT_POLICY':raise ValueError(raw_inventory)
        dump(output/'discovery.json',cat['discovery'])
        discovery=discovery_check(docs,cat['discovery'])
        dump(output/'discovery-independent-check.json',discovery)
        if discovery['status']!='PASS_INDEPENDENT_GESTURE_DISCOVERY':raise ValueError(discovery)
        if cat['discovery']['status']=='RESOURCE_BOUND_REFUSAL':raise ValueError('Exhaustive discovery resource bound; no truncated success')
        counts=Counter();rows=[];checks=[];selected=None
        for block in cat['units']:
            ev=v.options(cat,block['id']);rows.append(ev);counts['target_runs']+=1
            counts.update('refused:'+reason for r in ev['rejected'] for reason in r['reasons'])
            _,units,targets=v.assignments(cat,block['id'])
            for choice in ev['options']:
                counts['distinct_choices']+=1;counts['source_run_links']+=len(choice['donor_sequences'])
                pitch=any(a['intervals']!=b['intervals'] for a,b in zip(choice['realizations'],ev['original']))
                changed=choice['realizations']!=ev['original']
                if not changed:continue
                counts['changed_choices']+=1;counts['pitch_changed_choices']+=pitch
                edited=apply_family_choices(upper,list(zip(targets,choice['realizations'])));after=realize(edited)
                v.validate_actual(lower,after,targets,choice['realizations'],cat)
                for donor in choice['donor_sequences']:
                    checked=changed_check(lower,after,[t['member_refs'] for t in targets],[units[r]['member_refs'] for r in donor])
                    if checked['status']!='PASS_INDEPENDENT_VOICING_GESTURE':raise ValueError(checked)
                    checks.append(dict(target_ref=block['id'],donor_refs=donor,result=checked))
                if selected is None and pitch:selected=block['id']
        dump(output/'ALL-options.json',rows);dump(output/'ALL-changed-checks.json',checks)
        draws=[];demo=None;changed_worker=None
        if selected is not None:
            for strength in (0,50,100):
                for seed in range(9427,9447):
                    controls=dict(context_policy=v.POLICY,voicing=strength,register=0,physical=strength,target_ref=selected,seed=seed)
                    values,decision=v.sample_choice(cat,controls);draws.append(dict(controls=controls,decision=decision))
                    if strength==100 and decision['changed'] and demo is None:
                        _,_,targets=v.assignments(cat,selected)
                        if any(a['intervals']!=b['realization']['intervals'] for a,b in zip(values,targets)):demo=dict(controls=controls,decision=decision)
            if demo:
                edited,decision=v.intervene(upper,demo['controls']);after=realize(edited)
                changed_worker=execute(code,upper,demo['controls'],after,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
                if changed_worker['status']!='PASS':raise ValueError(changed_worker)
                worker_actual=json.loads((output/'changed-isolated/worker/output.json').read_text())
                _,units,targets=v.assignments(cat,selected)
                checked=changed_check(lower,worker_actual,[t['member_refs'] for t in targets],[units[r]['member_refs'] for r in decision['donor_refs']])
                if checked['status']!='PASS_INDEPENDENT_VOICING_GESTURE':raise ValueError(checked)
                dump(output/'changed-independent-check.json',checked)
                save_capture(actual,output/'zero-capture');save_capture(worker_actual,output/'changed-capture')
        dump(output/'ALL-draws.json',draws)
        if set(source)!={str(p.resolve()) for p in capture.glob('*.json')} or any(sha(Path(p))!=h for p,h in {**source,**frozen['code_hashes']}.items()):raise ValueError('Code/source changed during frozen run')
        result=dict(status='PASS_BOUNDED_GESTURE_QA',policy=v.POLICY,song_id=docs['metadata.json']['songId'],title=docs['metadata.json'].get('title'),
            source_occurrences=cat['base']['source_occurrences'],source_facts=len(lower['facts']),counts=dict(counts),
            qa1=dict(relationships=relations['status'],inventory=raw_inventory['status'],source_check=raw['status'],discovery=discovery['status']),
            qa2=dict(zero=zero,pair=pair,changed=changed_worker),
            qa3=dict(verified_changed_links=len(checks),meaning='Coordinated source-supported spacing choices with unchanged incident evidence requirements; not artist preference or phrase identification'),
            demo=demo,audible_status='GP_AUDIO_REVIEW_REQUIRED' if demo else 'NO_SUPPORTED_PITCH_CHANGE',modules=modules)
    except Exception as error:
        result.update(status='FAIL_RETAINED',error=str(error),traceback=traceback.format_exc())
    dump(output/'result.json',result)
    return {k:value for k,value in result.items() if k not in ('qa1','qa2','modules','demo','traceback')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps(result),flush=True)
    raise SystemExit(0 if result['status']=='PASS_BOUNDED_GESTURE_QA' else 1)
