"""Frozen all-unit, actual inverse QA for source-observed motion relationships."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from source_fact_tier1 import extract,project_documents
from connected_tier2 import analyze,strip_lower,reconstruct,realize
from voicing_register import inventory,empirical_options,intervene,sample_choice,apply_family_choice
from voicing_context_relations import POLICY,JOINT_POLICY
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check as source_check
from check_technique_connections import check as relationship_check
from check_family_policy import check as inventory_check
from check_voicing_context import check as changed_check
from run_voicing_register_qa import save_capture


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')


def run(capture,output,freeze):
    if output.exists()or'local-artifacts'not in output.resolve().parts:raise ValueError('Fresh private folder required')
    frozen=json.loads(freeze.read_text(encoding='utf-8'))
    policy=frozen.get('policy',POLICY)
    if policy not in(POLICY,JOINT_POLICY):raise ValueError('Declared incident relation policy required')
    if any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Frozen implementation changed')
    source_hashes={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    output.mkdir(parents=True);dump(output/'source-hashes-before.json',source_hashes)
    result=dict(status='RUNNING',policy=policy)
    try:
        lower=extract(capture);docs=project_documents(lower);upper=analyze(lower,families=True)
        if upper['unsupported']:
            dump(output/'unsupported.json',upper['unsupported']);raise ValueError('Unsupported source owners retained')
        upper=strip_lower(upper);dump(output/'stripped-tier2.json',upper)
        code,modules=bundle(Path(__file__).parent)
        zero=execute(code,upper,dict(variation=0),lower,output/'zero-isolated',timeout=300)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text())
        exact=source_check(capture,actual)
        if exact['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError(exact)
        source_relations=relationship_check(docs,analyze(actual,families=True))
        if source_relations['status']!='PASS_SOURCE_BACKED_RELATIONSHIPS':raise ValueError(source_relations)
        # Actual family->core isolated boundary, not just composed recovery.
        from run_reversible_tier_qa import extract_documents as written
        import musical_tier2 as music
        expected=music.strip_lower(music.analyze(written(docs)))
        pair_code=code+"\ndef reconstruct(upper,controls):\n    if controls!={'variation':0}:raise ValueError('Explicit zero required')\n    return sys.modules['voicing_families'].validate(upper)\n"
        pair=execute(pair_code,upper['musical_relationships'],dict(variation=0),expected,output/'pair-isolated',timeout=300)
        if pair['status']!='PASS':raise ValueError(pair)
        cat=inventory(lower,policy);raw_inventory=inventory_check(docs,cat)
        if raw_inventory['status']!='PASS_INDEPENDENT_POLICY':raise ValueError(raw_inventory)
        counts=Counter();rows=[];selected=None;verified=[]
        for target in cat['units']:
            if target['refusal_reasons']:counts['refused_source_units']+=1;continue
            counts['eligible_units']+=1;evidence=empirical_options(cat,target['id'],policy)
            counts.update('rejected:'+r['reason']for r in evidence.get('rejected',[]))
            for choice in evidence['options']:
                counts['accepted_distinct_choices']+=1;counts['accepted_donor_links']+=len(choice['donor_refs'])
                pitch_change=choice['realization']['intervals']!=target['realization']['intervals']
                string_change=choice['realization']['strings']!=target['fixed_output_strings']
                if not pitch_change and not string_change:continue
                counts['pitch_changing_choices']+=pitch_change;counts['string_changing_choices']+=string_change
                # QA exercises EACH admitted pitch choice through the real inverse;
                # this is not a runtime policy or an assistant-selected demo.
                edited=apply_family_choice(upper,target,choice['realization'])
                changed=realize(edited);oracle=changed_check(lower,changed,target['member_refs'],choice['donor_refs'],**({'allow_string_changes':True}if policy==JOINT_POLICY else{}))
                if oracle['status']!='PASS_INDEPENDENT_VOICING_CONTEXT':raise ValueError(oracle)
                verified.append(dict(target_ref=target['id'],choice=choice,oracle=oracle))
                if selected is None and pitch_change:selected=target
            rows.append(dict(target_ref=target['id'],evidence=evidence))
        dump(output/'ALL-source-options.json',rows);dump(output/'ALL-independent-changed-checks.json',verified)
        draws=[];demo=None;changed_worker=None
        if selected is not None:
            for strength in(0,50,100):
                for seed in range(9427,9447):
                    controls=dict(context_policy=policy,voicing=strength,register=0,physical=strength if policy==JOINT_POLICY else 0,target_ref=selected['id'],seed=seed)
                    _,decision=sample_choice(cat,controls);draws.append(dict(controls=controls,decision=decision))
                    if strength==100 and decision['changed']and decision['chosen']['realization']['intervals']!=selected['realization']['intervals']and demo is None:demo=dict(controls=controls,decision=decision)
            if demo is not None:
                edited,decision=intervene(upper,demo['controls']);changed=realize(edited)
                changed_worker=execute(code,upper,demo['controls'],changed,output/'changed-isolated',timeout=300,purpose='voicing_register_intervention')
                if changed_worker['status']!='PASS':raise ValueError(changed_worker)
                real_changed=json.loads((output/'changed-isolated/worker/output.json').read_text())
                oracle=changed_check(lower,real_changed,selected['member_refs'],decision['chosen']['donor_refs'],**({'allow_string_changes':True}if policy==JOINT_POLICY else{}))
                if oracle['status']!='PASS_INDEPENDENT_VOICING_CONTEXT':raise ValueError(oracle)
                dump(output/'changed-independent-check.json',oracle)
                save_capture(actual,output/'zero-capture');save_capture(real_changed,output/'changed-capture')
        dump(output/'ALL-control-draws.json',draws)
        unchanged=set(source_hashes)=={str(p.resolve())for p in capture.glob('*.json')}and all(sha(Path(p))==h for p,h in source_hashes.items())and all(sha(Path(p))==h for p,h in frozen['code_hashes'].items())
        if not unchanged:raise ValueError('Frozen source or implementation changed')
        result=dict(status='PASS_BOUNDED_LANE_RELATION_QA',policy=policy,song_id=docs['metadata.json']['songId'],
            title=docs['metadata.json'].get('title'),source_occurrences=cat['source_occurrences'],source_facts=len(lower['facts']),
            all_units=len(cat['units']),counts=dict(counts),qa1=dict(source_relationships=source_relations,inventory=raw_inventory['status']),
            qa2=dict(zero=zero,pair=pair,independent_source=exact,changed=changed_worker),
            qa3=dict(independently_verified_changed_choices=len(verified),scope='Source-observed physical-lane written motion and vertical invariants; not musical preference'),
            demo=demo,unchanged=unchanged,audible_status='REQUIRES_GP_AUDIO_AND_HUMAN_REVIEW'if demo else'NO_SUPPORTED_PITCH_CHANGING_DRAW',modules=modules)
    except Exception as error:
        result.update(status='FAIL_RETAINED',error=str(error),traceback=traceback.format_exc())
    dump(output/'result.json',result)
    return {k:v for k,v in result.items()if k not in ('qa1','qa2','modules','demo','traceback')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps(result))
    raise SystemExit(0 if result['status']=='PASS_BOUNDED_LANE_RELATION_QA'else 1)
