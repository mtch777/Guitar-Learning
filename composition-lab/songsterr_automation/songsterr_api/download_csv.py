"""Private, resumable CSV corpus capture using the existing songsterr-dl backend.

GP5's seven-string limitation is bridged with temporary split tracks; the GP7
exporter restores original tracks/strings. Raw notation is always retained.
"""
import argparse
from copy import deepcopy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor


def selections(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    songs={}
    for i,row in enumerate(rows,1):
        match=re.search(r'-s(\d+)(?:t\d+)?(?:[/?#]|$)',row['URL'])
        if not match:raise ValueError(f'Invalid Songsterr URL at CSV row {i}')
        sid=int(match.group(1));songs.setdefault(sid,[]).append(dict(csv_row=i,**row))
    return songs


def split_for_gp5(song):
    """Return GP5-compatible temporary tracks and a reversible geometry map."""
    import guitarpro as gp
    result=deepcopy(song);result.tracks=[];mapping=[]
    for ti,track in enumerate(song.tracks):
        count=len(track.strings)
        chunks=[list(range(1,count+1))] if count<=7 else [list(range(i,min(i+7,count+1))) for i in range(1,count+1,7)]
        for chunk in chunks:
            copy=deepcopy(track,{id(song):result});copy.song=result;copy.number=len(result.tracks)+1
            original_strings={s.number:s for s in track.strings}
            copy.strings=[gp.GuitarString(i,original_strings[s].value) for i,s in enumerate(chunk,1)]
            for m in copy.measures:
                m.track=copy
                for v in m.voices:
                    v.measure=m
                    for b in v.beats:
                        b.voice=v;b.notes=[n for n in b.notes if n.string in chunk]
                        for n in b.notes:n.beat=b;n.string=chunk.index(n.string)+1
                        if not b.notes and b.status==gp.BeatStatus.normal:b.status=gp.BeatStatus.rest
            mapping.append(dict(original_track=ti,original_string_count=count,source_strings=chunk,original_name=track.name,original_tuning=[s.value for s in track.strings],percussion=track.isPercussionTrack))
            result.tracks.append(copy)
    return result,mapping


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')


def restore_bridge(song,mapping):
    import guitarpro as gp
    result=deepcopy(song);parts=result.tracks;result.tracks=[]
    for ti in sorted({m['original_track'] for m in mapping}):
        group=[(parts[i],m) for i,m in enumerate(mapping) if m['original_track']==ti]
        base,info=group[0];base.song=result;base.number=ti+1;base.name=info['original_name']
        base.strings=[gp.GuitarString(i+1,p) for i,p in enumerate(info['original_tuning'])]
        collected={}
        for part,m in group:
            for mi,measure in enumerate(part.measures):
                for vi,voice in enumerate(measure.voices):
                    for bi,beat in enumerate(voice.beats):
                        for n in beat.notes:
                            if not m['percussion']:n.string=m['source_strings'][n.string-1]
                            collected.setdefault((mi,vi,bi),[]).append(n)
        for mi,measure in enumerate(base.measures):
            measure.track=base
            for vi,voice in enumerate(measure.voices):
                for bi,beat in enumerate(voice.beats):
                    beat.notes=collected.get((mi,vi,bi),[])
                    for n in beat.notes:n.beat=beat
                    if beat.notes:beat.status=gp.BeatStatus.normal
        result.tracks.append(base)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('csv',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--limit',type=int);a=p.parse_args()
    import guitarpro as gp
    from songsterr_dl import SongsterrClient,build_song,ConversionStats,to_guitarpro
    selection=selections(a.csv);root=a.out.resolve();repo=Path(__file__).resolve().parents[2]
    if repo/'local-artifacts' not in root.parents:raise ValueError('Corpus output must be inside ignored composition-lab/local-artifacts')
    root.mkdir(parents=True,exist_ok=True)
    upstream_sha=subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD'],text=True).strip()
    # This comparator is independent of the converter mappings but has a limited scope.
    spec=importlib.util.spec_from_file_location('source_comparison',a.upstream/'tests/comparison.py');comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)
    records=[]
    with SongsterrClient(timeout=30) as client:
        for index,(sid,rows) in enumerate(selection.items()):
            if a.limit and index>=a.limit:break
            folder=root/str(sid);folder.mkdir(exist_ok=True);status=folder/'capture.json'
            if status.exists():
                old=json.loads(status.read_text(encoding='utf-8'))
                if old.get('capture_complete') and old.get('serialized_source_comparison'):
                    records.append(old);continue
            record=dict(song_id=sid,csv_rows=rows,converter_commit=upstream_sha,capture_complete=False)
            try:
                meta_path=folder/'metadata.json'
                meta=json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else client.meta(sid)
                dump(meta_path,meta);revision=meta['revisionId'];raw=[]
                def fetch_part(ti):
                    path=folder/f'track-{ti}.json'
                    part=json.loads(path.read_text(encoding='utf-8')) if path.exists() else client.track(sid,revision,meta['image'],ti)
                    dump(path,part);return part
                with ThreadPoolExecutor(max_workers=3) as pool:raw=list(pool.map(fetch_part,range(len(meta['tracks']))))
                stats=ConversionStats();model=build_song(meta,raw,stats);original=to_guitarpro(model,stats)
                differences=[]
                for ti,part in enumerate(raw):
                    try:
                        issues=comparison.compare_track(part,original.tracks[ti],part.get('instrumentId')==1024)
                        differences.append(dict(track=ti,differences=len(issues),first_differences=issues[:30]))
                    except Exception as exc:differences.append(dict(track=ti,differences=None,error=f'{type(exc).__name__}: {exc}'))
                # Preserve exact normalized notation before GP5 can truncate double dots.
                dump(folder/'notation-map.json',[[[[dict(value=b.duration.value,dots=b.duration.dots,enters=b.duration.enters,times=b.duration.times) for b in v.beats] for v in m.voices] for m in t.measures] for t in model.tracks])
                bridge,mapping=split_for_gp5(original)
                from songsterr_dl.guitarpro_writer import _fold_song_text
                _fold_song_text(bridge,'cp1252',stats)
                gp5=folder/'bridge.gp5';gp.write(bridge,str(gp5),version=(5,1,0))
                # Reopen the intermediate format; no count-only acceptance for split strings.
                reread=gp.parse(str(gp5))
                if len(reread.tracks)!=len(mapping):raise AssertionError('Bridge track count changed')
                restored=restore_bridge(reread,mapping);serialized=[]
                for ti,part in enumerate(raw):
                    try:
                        issues=comparison.compare_track(part,restored.tracks[ti],part.get('instrumentId')==1024)
                        serialized.append(dict(track=ti,differences=len(issues),first_differences=issues[:30]))
                    except Exception as exc:serialized.append(dict(track=ti,differences=None,error=f'{type(exc).__name__}: {exc}'))
                dump(folder/'bridge-map.json',mapping)
                record.update(capture_complete=True,title=meta.get('title'),artist=meta.get('artist'),revision_id=revision,tracks=len(raw),
                              source_notes=sum(len(b.get('notes',[])) for part in raw for m in part.get('measures',[]) for v in m.get('voices',[]) for b in v.get('beats',[])),
                              source_comparison=differences,serialized_source_comparison=serialized,converter_warnings=dict(stats.warnings),bridge_tracks=len(mapping),
                              metadata_sha256=hashlib.sha256(meta_path.read_bytes()).hexdigest())
            except Exception as exc:record['error']=f'{type(exc).__name__}: {exc}'
            dump(status,record);records.append(record);dump(root/'capture-manifest.json',records)
            print(json.dumps(dict(index=index+1,total=len(selection),song_id=sid,captured=record['capture_complete'],tracks=record.get('tracks'),error=record.get('error'))),flush=True)
            time.sleep(.25)
    dump(root/'capture-manifest.json',records)
    return int(any(not r['capture_complete'] for r in records))


if __name__=='__main__':raise SystemExit(main())

