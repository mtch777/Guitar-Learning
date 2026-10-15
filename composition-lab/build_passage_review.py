"""Matched-gain 8-second passage media, from independently verified generated GP."""
import hashlib,json,shutil,wave
from pathlib import Path
import numpy as np
from playback_review import render_midi


def main():
    root=Path(__file__).resolve().parents[1];out=root/'public/composition-passage-review';out.mkdir(exist_ok=False)
    passages=[]
    for family in ('cloud','sweet'):
        folder=root/f'composition-lab/local-artifacts/{family}-audible-phrases'
        for mode in ('full','solo'):
            data={};peaks={}
            for name in ('baseline','rhythm','developed'):
                stem=name+('-solo' if mode=='solo' else '')
                report=render_midi(folder/(stem+'.mid'),folder/(stem+'.wav'))
                with wave.open(str(folder/(stem+'.wav')),'rb') as src:
                    assert src.getframerate()==22050
                    data[name]=np.frombuffer(src.readframes(src.getnframes()),dtype='<i2').astype(float)
                peaks[name]=report['raw_peak']
                shutil.copy2(folder/(stem+'.gp'),out/(family+'-'+stem+'.gp'))
            gain=max(peaks.values()) or 1
            # Undo independent peak normalization and apply ONE gain per family/mode.
            for name,samples in data.items():
                samples=np.clip(samples*peaks[name]/gain,-32767,32767).astype('<i2')
                for bar,start in [(1,0),(13,24)]:
                    target=out/f'{family}-{bar}-{name}-{mode}.wav'
                    clip=samples[int(start*22050):int((start+8)*22050)]
                    assert len(clip)==8*22050
                    with wave.open(str(target),'wb') as dest:
                        dest.setnchannels(1);dest.setsampwidth(2);dest.setframerate(22050);dest.writeframes(clip.tobytes())
        for bar in (1,13):passages.append(dict(id=f'{family}-{bar}',title=family.title()+f' / bars {bar}-{bar+3}',family=family,bar=bar,seconds=8))
    media={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
    version=hashlib.sha256(json.dumps(media,sort_keys=True).encode()).hexdigest()[:16]
    (out/'cases.json').write_text(json.dumps(dict(version=version,passages=passages,media=media),indent=2),encoding='utf-8')
    print(version,'4 passages, 24 matched-gain WAVs, 12 GP files')


if __name__=='__main__':main()
