"""Presentation packaging after QA; never changes analysis or native evidence."""
import argparse,json
from pathlib import Path
from write_accent_review import build,read,sha


def package(qa,native,fresh):
    result=build(qa,native,fresh);fresh_native=fresh/'native-preview-bundle'
    if not fresh_native.exists():fresh_native=fresh/'native-preview'
    status=dict(status='NOT_VERIFIED',differences=None,evidence_hashes={})
    audit=fresh_native/'independent-accent-artifacts.json';failure=fresh_native/'failure.json'
    if audit.exists():
        report=read(audit);status.update(status=report['status'],evidence_hashes={str(audit.resolve()):sha(audit)})
    if failure.exists():
        reports=[fresh_native/name/'gp7-validation.json'for name in('source','zero','changed')]
        available=[p for p in reports if p.exists()]
        # Report the original baseline denominator, never add duplicated source,
        # zero and changed mismatches or reinterpret them as musical equivalence.
        baseline=read(fresh_native/'source/gp7-validation.json')if(fresh_native/'source/gp7-validation.json').exists()else{}
        status.update(status='BLOCKED_NATIVE_BASELINE',differences=baseline.get('directSource',{}).get('differences'),
            evidence_hashes={str(p.resolve()):sha(p)for p in[ failure,*available]})
    (native/'fresh-native-status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    result['fresh_native_status']=status['status'];return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('qa',type=Path);p.add_argument('native',type=Path);p.add_argument('fresh',type=Path);a=p.parse_args();print(json.dumps(package(a.qa,a.native,a.fresh)))
