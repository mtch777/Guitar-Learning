"""Offline projection through the retained Songsterr JSON -> GP bridge.

The caller supplies source or SAME-relation reconstructed documents. This module
does not select/generate notes, repair analysis or contact Songsterr.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def export(capture,backend,output):
    if output.exists() or 'local-artifacts' not in output.resolve().parts:raise ValueError('Fresh private export folder required')
    output.mkdir(parents=True)
    files=[capture/'metadata.json']+sorted(capture.glob('track-*.json'),key=lambda p:int(p.stem.split('-')[-1]))
    documents={p.name:json.loads(p.read_text(encoding='utf-8-sig')) for p in files}
    for name,value in documents.items():(output/name).write_text(json.dumps(value),encoding='utf-8')
    sys.path.insert(0,str(backend.resolve()));sys.path.insert(0,str(Path(__file__).parent/'songsterr_automation/songsterr_api'))
    import guitarpro as gp
    from songsterr_dl import build_song,ConversionStats,to_guitarpro
    from songsterr_dl.guitarpro_writer import _fold_song_text
    from download_csv import split_for_gp5
    metadata=documents['metadata.json'];parts=[documents[p.name] for p in files[1:]]
    stats=ConversionStats();model=build_song(metadata,parts,stats);original=to_guitarpro(model,stats)
    bridge,mapping=split_for_gp5(original);_fold_song_text(bridge,'cp1252',stats)
    gp.write(bridge,str(output/'bridge.gp5'),version=(5,1,0))
    (output/'bridge-map.json').write_text(json.dumps(mapping),encoding='utf-8')
    (output/'notation-map.json').write_text(json.dumps([[[[dict(value=b.duration.value,dots=b.duration.dots,enters=b.duration.enters,times=b.duration.times) for b in v.beats] for v in m.voices] for m in t.measures] for t in model.tracks]),encoding='utf-8')
    (output/'capture.json').write_text(json.dumps(dict(capture_complete=True,song_id=metadata['songId'],offline_owned_document_projection=True)),encoding='utf-8')
    report=dict(status='BRIDGE_WRITTEN_GP7_CHECK_PENDING',tracks=len(model.tracks),source_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                codec='Existing build_song/to_guitarpro/split_for_gp5; no new note selection',conversion_stats=repr(stats))
    (output/'offline-export.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('backend',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=export(a.capture,a.backend,a.output);print(json.dumps(dict(status=r['status'],tracks=r['tracks'])))
