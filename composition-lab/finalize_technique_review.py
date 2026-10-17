"""Fail closed on missing/silent audio; omit exact duplicate listening pairs."""
import argparse
import hashlib
import json
from pathlib import Path


def finalize(root):
    path=root/'cases.json';data=json.loads(path.read_text());omitted=[];pairs=0
    for group in data['cases']:
        for strength,pair in list(group['variants'].items()):
            hashes=[]
            for case in pair:
                if not case['active']:raise AssertionError('No-technique review case')
                meta=json.loads((root/(case['audio']+'.json')).read_text())
                audio=(root/case['audio']).read_bytes()
                if not meta['finite'] or meta['clipped'] or not meta['nonzeroSamples']:raise AssertionError('Invalid review audio')
                digest=hashlib.sha256(audio).hexdigest()
                if digest!=meta['audioSha256']:raise AssertionError('Audio changed since verification')
                hashes.append(digest)
            if hashes[0]==hashes[1]:
                del group['variants'][strength];omitted.append(dict(family=group['id'],strength=strength,reason='identical rendered audio'))
            else:pairs+=1
        if '100' not in group['variants']:raise AssertionError('No distinct fully unlocked pair: '+group['id'])
    data['version']=hashlib.sha256(json.dumps(data['cases'],sort_keys=True).encode()).hexdigest()[:16]
    data['audio_gate']=dict(distinct_pairs=pairs,omitted=omitted,authentic_legato_certified=False,human_judgments=0)
    path.write_text(json.dumps(data));(root/'review-gate.json').write_text(json.dumps(data['audio_gate'],indent=2));return data['audio_gate']


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();print(json.dumps(finalize(a.root)))
