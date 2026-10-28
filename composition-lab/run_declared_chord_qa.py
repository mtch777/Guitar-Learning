"""Frozen full-capture and isolated pair QA of declared chord-degree ownership."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import traceback
from source_fact_tier1 import extract
from connected_tier2 import analyze,strip_lower,validate
from run_connected_tier2_qa import bundle
from qa_isolation_harness import execute
from check_complete_source_facts import check as source_check
from check_technique_connections import check as technique_check
from check_declared_chord_ownership import check as degree_check
from declared_chord_ownership import LABEL,CAPO


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2),encoding='utf-8')


def run(capture,output,freeze):
    frozen=json.loads(freeze.read_text());output.mkdir(parents=True,exist_ok=False)
    sources={str(p.resolve()):sha(p) for p in capture.glob('*.json')};dump(output/'source-hashes.json',sources)
    try:
        if any(sha(Path(p))!=h for p,h in frozen['code_hashes'].items()):raise ValueError('Source code differs from preregistered freeze')
        lower=extract(capture);upper=analyze(lower,declared_chords=True);dump(output/'coverage.json',upper['derived_views']['declared_chord_ownership'])
        if upper['unsupported']:raise ValueError(dict(unsupported=upper['unsupported']))
        validate(upper);stripped=strip_lower(upper);dump(output/'stripped-tier2.json',stripped)
        docs={p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in capture.glob('*.json')}
        techniques=technique_check(docs,upper);dump(output/'technique-check.json',techniques)
        if techniques['status']!='PASS_SOURCE_BACKED_RELATIONSHIPS':raise ValueError(techniques)
        code,hashes=bundle(Path(__file__).parent.resolve())
        zero=execute(code,stripped,{'variation':0},lower,output/'zero-isolated',timeout=180)
        if zero['status']!='PASS':raise ValueError(zero)
        actual=json.loads((output/'zero-isolated/worker/output.json').read_text())
        raw=source_check(capture,actual);independent=degree_check(docs,upper,actual)
        dump(output/'raw-source-check.json',raw);dump(output/'independent-degree-check.json',independent)
        if raw['status']!='PASS_COMPLETE_CAPTURED_JSON_FACTS' or independent['issues']:raise ValueError(dict(raw=raw,independent=independent))
        # Pair input holds only this musical owner and its existing referenced
        # label/capo choices. No original pitches/bass/intervals or derived views.
        choices=[c for c in stripped['owned_parameters']['source_choices'] if LABEL.fullmatch(c['fact_ref']) or CAPO.fullmatch(c['fact_ref'])]
        refs={c['fact_ref'] for c in choices}
        pair_input=dict(musical_relationships=deepcopy(stripped['musical_relationships']),source_choices=deepcopy(choices),
            facts=[deepcopy(r) for r in stripped['source_structure']['facts'] if r['id'] in refs])
        import musical_tier2 as music
        from run_reversible_tier_qa import extract_documents
        previous=music.strip_lower(music.analyze(extract_documents(docs)))
        pair_code=code+'''\nfrom declared_chord_ownership import validate as _degree_validate,label_values as _label_values,capo_values as _capo_values
def reconstruct(value,controls):
    if controls!={'variation':0}:raise ValueError('This pair accepts exact zero only')
    return _degree_validate(value['musical_relationships'],_label_values(value['source_choices'],value['facts']),_capo_values(value['source_choices'],value['facts']))
'''
        pair=execute(pair_code,pair_input,{'variation':0},previous,output/'pair-isolated',timeout=180)
        if pair['status']!='PASS':raise ValueError(pair)
        coverage=upper['derived_views']['declared_chord_ownership']
        statuses=Counter(r['status'] for r in coverage['groups'])
        result=dict(status='PASS_DECLARED_WRITTEN_CHORD_QA',song_id=docs['metadata.json']['songId'],title=docs['metadata.json']['title'],
            note_occurrences=techniques['counts']['occurrences'],source_facts=len(lower['facts']),
            declarations=coverage['declaration_count'],unattached_declarations=len(coverage['unattached_declarations']),
            group_statuses=dict(statuses),independent_counts=independent['counts'],qa1=independent['status'],
            qa2=dict(zero=zero,pair=pair),qa3='Conditional source-declared chord degrees now own supported written notes; no acoustic harmony/key truth, preference or creative-control acceptance',modules=hashes)
        if set(sources)!={str(p.resolve()) for p in capture.glob('*.json')} or any(sha(Path(p))!=h for p,h in {**sources,**frozen['code_hashes']}.items()):raise ValueError('Frozen code or capture changed during run')
    except Exception as error:result=dict(status='FAIL_RETAINED',error=str(error),traceback=traceback.format_exc())
    dump(output/'result.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('freeze',type=Path);a=p.parse_args()
    result=run(a.capture,a.output,a.freeze);print(json.dumps({k:v for k,v in result.items() if k not in ('modules','qa2')}),flush=True)
    raise SystemExit(0 if result['status']=='PASS_DECLARED_WRITTEN_CHORD_QA' else 1)
