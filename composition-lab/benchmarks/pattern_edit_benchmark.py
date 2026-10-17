"""Private actual-score voicing edits; public summaries contain aggregates only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pattern_edits import generate, plain, FAMILIES
from exact_score import extract_score


def main():
    p=argparse.ArgumentParser();p.add_argument('sources',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    records=[]
    for si,source in enumerate(a.sources):
        score=extract_score(source)
        tracks=[t for t in score['tracks'] if 24<=t['program']<=31 and len(t['tunings'])==1]
        def count(t):return sum(plain(e) for m in t['measures'] if sum(bool(v) for v in m['voices'])==1 for v in m['voices'] for e in v)
        track=max(tracks,key=count);base=a.out/f'source-{si+1}';base.mkdir()
        for family in FAMILIES:
            for method in ('compact','upper'):
                path=base/f'{family}-{method}.gp';audit=generate(source,path,track['index'],family,method=method,pitch_unlocked=True,voicing_unlocked=True)
                path.with_suffix('.edit.json').write_text(json.dumps(audit,indent=2))
                # Exact expected occurrence table for independent alphaTab import.
                restored=extract_score(path)
                expected=[]
                for t in restored['tracks']:
                    for mi,m in enumerate(t['measures']):
                        for vi,v in enumerate(m['voices']):
                            for ei,e in enumerate(v):
                                for ni,n in enumerate(e['notes']):expected.append(dict(location=f"{t['index']}:{mi}:{vi}:{ei}:{ni}",midi=n['midi'],string=n['string'],fret=n['fret']))
                path.with_suffix('.expected.json').write_text(json.dumps(expected))
                records.append(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),file=str(path),track=track['index'],family=family,method=method,changed_events=audit['changed_events'],rhythm_locked=audit['rhythm_locked'],unselected_locked=audit['unselected_occurrences_locked']))
                print(json.dumps(records[-1]),flush=True)
                (a.out/'manifest.json').write_text(json.dumps(records,indent=2))
    print(json.dumps(dict(cases=len(records),all_nonempty=all(r['changed_events']>0 for r in records))))


if __name__=='__main__':main()
