"""Publish the reviewed structural pack, never the private score library.

Run after private selector/pack/realization tests. The deployed module is identical
to the reviewed engine; gzip changes storage only. Existing recipe assets remain
historical regression fixtures and are not called by the new builder.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'composition-lab/local-artifacts/fretboard-study-2026-11-04/riff-engine-001'
PUBLIC=ROOT/'public/riff-builder'

def package():
    raw=(RESEARCH/'PATTERN_PACK.json').read_bytes()
    pack=json.loads(raw)
    assert pack['schema']=='riff-pattern-pack/1'
    source=(RESEARCH/'pattern_engine.py').read_bytes()
    packed=gzip.compress(raw,mtime=0)
    availability={'rhythms':{},'palettes':{},'scope':'Labelled reference availability only, not a promise of a generated result.'}
    for artist in pack['artists']:
        availability['rhythms'][artist]={}
        availability['palettes'][artist]={}
        for style in pack['styles']:
            availability['rhythms'][artist][style]={focus:sum(any(s['artist']==artist and style in s['style_ids'] for s in pack['templates'][i]['support']) for i in pack['admissions']['rhythms'].get(style+':'+focus,[])) for focus in pack['focuses']}
            availability['palettes'][artist][style]={mode:sum(pack['palettes'][i]['artist']==artist for i in pack['admissions']['palettes'].get(style+':'+mode,[])) for mode in pack['modes']}
    receipt={'schema':'riff-browser-packaging/1','pattern_pack_sha256':hashlib.sha256(raw).hexdigest(),
        'engine_sha256':hashlib.sha256(source).hexdigest(),'gzip_sha256':hashlib.sha256(packed).hexdigest(),
        'source_library_sha256':pack['source_library_sha256'],'templates':len(pack['templates']),
        'palettes':len(pack['palettes']),'compressed_bytes':len(packed),
        'input_policy':pack['pack_scope']['private_input_policy']}
    PUBLIC.mkdir(exist_ok=True,parents=True)
    (PUBLIC/'pattern_engine.py').write_bytes(source)
    (PUBLIC/'pattern-pack.json.gz').write_bytes(packed)
    (PUBLIC/'availability.json').write_text(json.dumps(availability,separators=(',',':'))+'\n',encoding='utf8')
    (PUBLIC/'pattern-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return receipt

if __name__=='__main__': print(json.dumps(package(),indent=2))
