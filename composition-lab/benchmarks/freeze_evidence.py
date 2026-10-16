"""Private immutable evidence inventory; publish only count/root hash summaries."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    root=Path(__file__).resolve().parents[2]
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    if not args.out.resolve().is_relative_to(root/'composition-lab/local-artifacts'):raise ValueError('Private manifest location required')
    files={}
    for folder in ['composition-lab/private-sources','composition-lab/local-artifacts','.local/yinyang-models','.local/models']:
        for path in sorted((root/folder).rglob('*')):
            if path.is_file() and path.resolve()!=args.out.resolve():files[str(path.relative_to(root))]=dict(bytes=path.stat().st_size,sha256=sha(path))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    if args.out.exists():raise FileExistsError('Do not overwrite evidence manifest')
    args.out.write_text(json.dumps(dict(files=files),indent=2),encoding='utf-8')
    print(json.dumps(dict(files=len(files),bytes=sum(f['bytes'] for f in files.values()),manifest_sha256=sha(args.out))))


if __name__=='__main__':main()
