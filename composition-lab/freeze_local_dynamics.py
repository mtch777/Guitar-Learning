"""One preregistered unseen capture; retain failures without replacement."""
import argparse,json,secrets
from datetime import datetime,timezone
from pathlib import Path
from run_declared_chord_qa import sha,dump


def freeze(output,backend,module,font):
    root=Path(__file__).resolve().parent
    if output.exists()or'local-artifacts'not in output.resolve().parts:raise ValueError('Fresh private output required')
    excluded=set();origins=[]
    for name,key in (('metadata.json','songId'),('selection.json','selected_song_id')):
        for p in(root/'local-artifacts').rglob(name):
            try:
                j=json.loads(p.read_text(encoding='utf-8-sig'))
                if type(j)is dict and type(j.get(key))is int:excluded.add(j[key]);origins.append(str(p.resolve()))
            except(ValueError,UnicodeError):pass
    code=list(root.glob('*.py'))+list((root/'songsterr_automation/songsterr_api').glob('*.py'))
    native=list(root.glob('*.mjs'))+list((root/'songsterr_automation/songsterr_api').glob('*.mjs'))+list((backend/'songsterr_dl').rglob('*.py'))+list(module.parent.glob('*.mjs'))+[font]
    manifest=dict(schema='local-dynamics-freeze/1',started_utc=datetime.now(timezone.utc).isoformat(),seed=secrets.randbits(64),
        excluded_song_ids=sorted(excluded),exclusion_evidence=sorted(origins),backend=str(backend.resolve()),case_count=1,
        code_hashes={str(p.resolve()):sha(p)for p in sorted(code)},native_hashes={str(p.resolve()):sha(p)for p in sorted(native)},
        sampling='Existing seed-selected letter search, first100 returned IDs; uniform among previously uncaptured candidate IDs, not uniform catalog. Exactly one slot; failure/no choice retained.',
        review_selection='All declaration palettes checked. First changed fixed draw in onset/part/ref order, entire pitched influence <=7 source bars plus1 context bar each side. Preview scope only.',
        controls=dict(strengths=[0,50,100],seeds=list(range(32))),
        acceptance='Complete inverse/raw field parity; independent full palette/influence; actual stripped zero and selected changed worker; native GP/MIDI/audio. Source observation support is not intended expression or human musical-fit approval.')
    output.mkdir(parents=True);dump(output/'freeze.json',manifest);return manifest


def capture(output):
    from sample_reversible_qa_song import sample
    manifest=json.loads((output/'freeze.json').read_text());hashes={**manifest['code_hashes'],**manifest['native_hashes']}
    if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Frozen dependencies changed')
    try:r=sample(output/'fresh',Path(manifest['backend']),seed=manifest['seed'],extra_excluded_ids=manifest['excluded_song_ids'])
    except Exception as exc:
        r=json.loads((output/'fresh/selection.json').read_text());r['capture_error']=str(exc)
    dump(output/'capture-result.json',r)
    if any(sha(Path(p))!=h for p,h in hashes.items()):raise ValueError('Dependencies changed during capture')
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('freeze');a.add_argument('output',type=Path);a.add_argument('backend',type=Path);a.add_argument('module',type=Path);a.add_argument('font',type=Path)
    a=s.add_parser('capture');a.add_argument('output',type=Path);a=p.parse_args()
    r=freeze(a.output,a.backend,a.module,a.font)if a.action=='freeze'else capture(a.output)
    print(json.dumps({k:v for k,v in r.items()if k in ('seed','case_count','status','selected_song_id','title','artist','tracks','capture_error')}))
