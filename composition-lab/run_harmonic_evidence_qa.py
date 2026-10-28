"""Whole-source zero and source-denied common-harmony recomputation gates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from connected_tier2 import analyze,strip_lower
from source_fact_tier1 import extract
from check_complete_source_facts import check as check_source
from harmonic_evidence import source_patterns
from harmonic_pattern_ledger import build as ledger_build
from check_harmonic_evidence import check as check_evidence
from check_harmonic_pattern_ledger import check as check_ledger
from qa_isolation_harness import execute
from run_connected_tier2_qa import bundle as existing_bundle


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')


def bundle(root):
    code,hashes=existing_bundle(root)
    for name in ('voicing_frames','probe_voicing_frames','harmonic_evidence','harmonic_pattern_ledger'):
        source=(root/(name+'.py')).read_text(encoding='utf-8-sig')
        code+=f"_m=types.ModuleType({name!r});sys.modules[{name!r}]=_m\nexec(compile({source!r},{name!r},'exec'),_m.__dict__)\n"
        hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    code+='''
def reconstruct(upper,controls):
 if controls != {'variation':0}:raise ValueError('No creative activation in this gate')
 c=sys.modules['harmonic_evidence'].source_patterns(upper)
 return dict(evidence=c['harmonic_evidence'],catalog=dict(units=c['units'],geometries=c['geometries'],component_scope_refusals=c['component_scope_refusals']),ledger=sys.modules['harmonic_pattern_ledger'].build(c,c['harmonic_evidence']))
'''
    return code,hashes


def run(capture,output,freeze,upper_path=None):
    output.mkdir(parents=True,exist_ok=False);frozen=json.loads(freeze.read_text());root=Path(__file__).parent
    inputs={str(p.resolve()):sha(p)for p in capture.glob('*.json')}
    if upper_path:inputs[str(upper_path.resolve())]=sha(upper_path)
    dump(output/'input-hashes.json',inputs)
    try:
        hashes={**frozen['code_hashes'],**frozen.get('native_hashes',{})}
        if any(sha(p)!=h for p,h in hashes.items()):raise ValueError('Frozen code/native dependency drift')
        lower=extract(capture)
        upper=json.loads(upper_path.read_text())if upper_path else strip_lower(analyze(lower,declared_chords=True))
        c=source_patterns(upper);view=c['harmonic_evidence'];catalog=dict(units=c['units'],geometries=c['geometries'],component_scope_refusals=c['component_scope_refusals'])
        if check_source(capture,c['before'])['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Provided upper differs from complete raw capture')
        native=check_evidence(lower,view,catalog,profile=c['profile']);dump(output/'native.json',native)
        if native['status']!='PASS_NATIVE_HARMONIC_EVIDENCE':raise ValueError(native)
        ledger=ledger_build(c,view);independent=check_ledger(catalog,view,ledger);dump(output/'independent-ledger.json',independent)
        if independent['status']!='PASS_INDEPENDENT_PATTERN_LEDGER':raise ValueError(independent)
        expected=dict(evidence=view,catalog=catalog,ledger=ledger)
        for name,data in [('stripped-tier2',upper),('evidence',view),('catalog',catalog),('ledger',ledger)]:dump(output/(name+'.json'),data)
        zero_code,_=existing_bundle(root);zero=execute(zero_code,upper,dict(variation=0),lower,output/'zero-isolated',timeout=300)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text());raw_check=check_source(capture,actual);dump(output/'raw-source-check.json',raw_check)
        if raw_check['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS':raise ValueError('Actual inverse differs from raw capture')
        relation_code,modules=bundle(root);pair=execute(relation_code,upper,dict(variation=0),expected,output/'relations-isolated',timeout=300)
        if pair['status']!='PASS':raise ValueError(pair)
        restored=json.loads((output/'relations-isolated/worker/output.json').read_text())
        if restored!=expected:raise ValueError('Actual relation worker differs')
        if any(sha(p)!=h for p,h in {**inputs,**hashes}.items()):raise ValueError('Source/code drift during gate')
        result=dict(status='PASS_BOUNDED_COMMON_HARMONY_QA',qa1='Development replay unless paired with a preregistered fresh selection',
            qa2=dict(whole_source=zero['status'],common_relationships=pair['status'],independent_raw_source=raw_check['status']),
            qa3=dict(native_evidence=native['status'],independent_pattern_ledger=independent['status'],scope='Exact finite-vocabulary chord alternatives and source degree-pattern relationships, not established key/function, artist preference or creative permission'),
            source_facts=len(lower['facts']),groups=len(view['groups']),groups_with_source_labels=sum(bool(g['declarations'])for g in view['groups']),
            exact_fit_groups=sum(bool(g['hypotheses'])for g in view['groups']),unlabeled_fit_groups=sum(bool(g['hypotheses'])and not g['declarations']for g in view['groups']),
            group_statuses=dict(Counter(g['status']for g in view['groups'])),counts=ledger['counts'],modules=modules,
            removed=['Tier0 source files','Tier1 payload','Derived harmonic evidence/catalog/ledger caches','Expected answers','Source/cache filesystem access'],
            retained='Existing stripped Tier2 source owners and relationships; no new pitch backup. Harmonic labels alone are not claimed sufficient for inversion.')
    except Exception as e:result=dict(status='FAIL_RETAINED',error=repr(e))
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);p.add_argument('--upper',type=Path);a=p.parse_args()
    r=run(a.capture,a.output,a.freeze,a.upper);print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS_BOUNDED_COMMON_HARMONY_QA'else 1)
