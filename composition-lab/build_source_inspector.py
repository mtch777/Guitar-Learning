"""Create an isolated private source-GP/stored-JSON inspection bundle."""
import argparse,csv,hashlib,json,shutil
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(corpus,alpha,output):
    corpus,alpha,output=map(Path,(corpus,alpha,output))
    if 'local-artifacts' not in output.resolve().parts or output.exists():raise ValueError('Fresh private output required')
    report=corpus/('relationships-unblock-v1.json' if (corpus/'relationships-unblock-v1.json').is_file() else 'relationships-v2.json');report_hash=digest(report);data=json.loads(report.read_text(encoding='utf-8'));songs={s['song_id']:s for s in data['songs']}
    output.mkdir();(output/'songs').mkdir();(output/'lib').mkdir()
    source=Path(__file__).parent
    for name in ('source_inspector.html','source_inspector.js','source_inspector_logic.mjs'):
        shutil.copy2(source/name,output/('index.html' if name.endswith('html') else name))
    for name in ('alphaTab.min.js','alphaTab.worker.min.mjs','alphaTab.worklet.min.mjs'):
        shutil.copy2(alpha/name,output/'lib'/name)
    for name in ('font','soundfont'):shutil.copytree(alpha/name,output/'lib'/name)
    reports=[]
    report_names=('analysis-evidence-v2.json','api-field-coverage.json','pattern-robustness.json','source-techniques.json','technique-validation-unblock-v1.json')
    (output/'reports').mkdir()
    for name in report_names:
        path=corpus/name
        if path.is_file():
            shutil.copy2(path,output/'reports'/name)
            reports.append(dict(name=name,url='reports/'+name,bytes=path.stat().st_size,sha256=digest(path)))
    (output/'reports.json').write_text(json.dumps(reports),encoding='utf-8')
    entries=[]
    with (corpus/'catalog.csv').open(encoding='utf-8-sig',newline='') as stream:
        for catalog in csv.DictReader(stream):
            sid=int(catalog['song_id']);gp=Path(catalog['gp_file']);song=songs.get(sid)
            entry=dict(song_id=sid,title=catalog['song'],artist=catalog['artist'],revision=catalog['revision'],available=gp.is_file() and song is not None)
            if entry['available']:
                folder=output/'songs'/str(sid);folder.mkdir();shutil.copy2(gp,folder/'source.gp')
                (folder/'stored.json').write_text(json.dumps(song,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
                raw=Path(catalog['raw_source_folder']);track_files=[]
                for p in sorted(raw.glob('track-*.json')):
                    shutil.copy2(p,folder/p.name);track_files.append(p.name)
                entry.update(gp=f'songs/{sid}/source.gp',json=f'songs/{sid}/stored.json',gp_sha256=digest(gp),json_sha256=digest(folder/'stored.json'),track_files=track_files,
                    source_report=report.name,source_report_sha256=report_hash,provenance='Stored analysis from captured Songsterr track JSON; GP converted from the same capture',catalog=catalog,track_ids=[t['part_id'] for t in song['tracks']],native_bends_only=True)
            entries.append(entry)
    (output/'catalog.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    files=sorted(p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file())
    (output/'served-files.json').write_text(json.dumps(files),encoding='utf-8')
    return dict(songs=len(entries),available=sum(e['available'] for e in entries),files=len(files),output=str(output))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('corpus','alpha','output'):p.add_argument(name,type=Path)
    a=p.parse_args();print(json.dumps(build(a.corpus,a.alpha,a.output)))
