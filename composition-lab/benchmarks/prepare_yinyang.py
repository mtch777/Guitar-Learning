"""Prepare only official inference dictionaries; never load training pickles.

Download the artifact ZIP via the official README link into ignored .local.
This script verifies the inspected archive hash and extracts an exact allowlist.
No code/data/weight redistribution license is inferred from public availability.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

OFFICIAL_SHA256='1a4d3c7c482d27a6a53ee8ea8615f87749fede29d9033ba94bba956194152627'


def prepare(archive,destination):
    repo=Path(__file__).resolve().parents[2]
    destination=destination.resolve()
    if not destination.is_relative_to(repo/'.local'):raise ValueError('Checkpoints must stay under ignored .local')
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest!=OFFICIAL_SHA256:raise ValueError('Archive changed; verify new official artifact before use')
    names={'artifacts/tokenizer.json'}
    for model in ('phrase_generation','phrase_refinement','phrase_selection'):
        names|={f'artifacts/{model}/{file}' for file in ('config.json','pytorch_model.bin')}
    destination.mkdir(parents=True,exist_ok=False);manifest={}
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP entries')
        for name in sorted(names):
            info=z.getinfo(name)
            if info.file_size>200_000_000:raise ValueError('Unexpected model size')
            path=destination/Path(*Path(name).parts[1:])
            if not path.resolve().is_relative_to(destination):raise ValueError('Unsafe path')
            data=z.read(info);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            manifest[str(path.relative_to(destination))]=hashlib.sha256(data).hexdigest()
    (destination/'artifact-manifest.json').write_text(json.dumps(dict(archive_sha256=digest,files=manifest,license='unverified; no redistribution'),indent=2),encoding='utf-8')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('destination',type=Path);args=p.parse_args()
    print(json.dumps(prepare(args.archive,args.destination),indent=2))
