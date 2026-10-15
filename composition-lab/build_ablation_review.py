"""Package only generated, independently imported GP/MIDI/audio for public review.

Never copies source songs, private reviewer files, canonical source timelines or
model weights. The allowlist is the two generated listening sets plus V2.
"""
import hashlib
import json
from pathlib import Path
import shutil
from exact_score import extract_score
from playback_review import read_midi_notes

ROOT=Path(__file__).resolve().parents[1]
METHODS={'harmony':'Harmony only','harmony-rhythm':'Harmony + rhythm',
         'harmony-rhythm-melody':'Harmony + rhythm + melody',
         'roles-phrases':'Instrument roles + motif structure','V2-baseline':'V2 reference baseline'}
SOURCE_HASHES={'63cfae7762a5ac56b2f0521d8c01cbf6025fac74ea525c7a6b7d260703492f66',
               '17c5ecc0606a6334bf2818ba3f2d1f4a8574f0777cf6750565f644a0ee0b9e7f'}


def main():
    destination=ROOT/'public/composition-ablation-review';destination.mkdir(parents=True,exist_ok=True)
    cases=[]
    for family,title in [('cloud','Cloud study'),('sweet','Sweet study')]:
        folder=ROOT/f'composition-lab/local-artifacts/{family}-native-listening'
        key=json.loads((folder/'review-key.json').read_text())
        for case_id,info in sorted(key.items()):
            midi=folder/info['source'];method=midi.stem
            if method not in METHODS:raise ValueError('Unapproved generated artifact')
            gp=midi.with_suffix('.gp');data=gp.read_bytes();digest=hashlib.sha256(data).hexdigest()
            if digest in SOURCE_HASHES:raise ValueError('Refusing to publish a commercial source score')
            score=extract_score(gp)
            if score['measure_count']!=16:raise ValueError('Expected generated 16-bar review artifact')
            ident=family+'-'+case_id;audio=folder/(case_id+'.wav')
            for path,suffix in [(gp,'.gp'),(audio,'.wav')]:shutil.copyfile(path,destination/(ident+suffix))
            seconds,notes=read_midi_notes(midi)
            roll=dict(duration=seconds,notes=[dict(start=round(a,6),end=round(b,6),pitch=p,velocity=v,part=c)
                                             for a,b,p,v,c in notes])
            (destination/(ident+'.json')).write_text(json.dumps(roll,separators=(',',':')),encoding='utf-8')
            cases.append(dict(id=ident,family=family,familyTitle=title,label='Sketch '+case_id[-2:],
                audio=ident+'.wav',gp=ident+'.gp',roll=ident+'.json',gpSha256=digest,
                audioSha256=hashlib.sha256(audio.read_bytes()).hexdigest(),seconds=seconds,
                method=METHODS[method],seed=17,
                tracks=[dict(name=t['name'],strings=len(t['tunings'][0]),program=t['program']) for t in score['tracks']]))
    version=hashlib.sha256(''.join(c['gpSha256']+c['audioSha256'] for c in cases).encode()).hexdigest()[:16]
    manifest=dict(format='composition-ablation-review-v1',version=version,cases=cases,
        audio='Standardized sine MIDI preview; download GP for instrument playback',judgments=[])
    (destination/'cases.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(dict(cases=len(cases),version=version,published_bytes=sum(p.stat().st_size for p in destination.iterdir() if p.is_file()))))


if __name__=='__main__':main()
