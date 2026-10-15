"""Publish generated phrase experiments, with byte-identical prior baselines."""
import hashlib
import json
from pathlib import Path
import random
import shutil
from playback_review import render_midi,read_midi_notes
from exact_score import extract_score


def main():
    root=Path(__file__).resolve().parents[1]
    old=root/'public/composition-ablation-review'
    original=json.loads((old/'cases.json').read_text())
    out=root/'public/composition-phrase-review';out.mkdir(exist_ok=False)
    methods={'baseline':'Previous roles/motif baseline','linked':'Linked contour development',
             'endings':'Phrase-end accompaniment targeting','combined':'Linked contour + end targeting','v2':'V2 reference baseline'}
    cases=[]
    for family in ('cloud','sweet'):
        folder=root/f'composition-lab/local-artifacts/{family}-phrase-experiments'
        names=list(methods);random.Random(20261015+(family=='sweet')).shuffle(names)
        for i,name in enumerate(names,1):
            ident=f'{family}-phrase-{i:02d}';gp=out/(ident+'.gp');wav=out/(ident+'.wav');roll=out/(ident+'.json')
            if name in ('baseline','v2'):
                prior=next(c for c in original['cases'] if c['family']==family and c['method']==('V2 reference baseline' if name=='v2' else 'Instrument roles + motif structure'))
                for source,dest in [(prior['gp'],gp),(prior['audio'],wav),(prior['roll'],roll)]:shutil.copy2(old/source,dest)
                assert hashlib.sha256(gp.read_bytes()).hexdigest()==prior['gpSha256']
            else:
                shutil.copy2(folder/(name+'.gp'),gp);render_midi(folder/(name+'.mid'),wav)
                seconds,notes=read_midi_notes(folder/(name+'.mid'))
                roll.write_text(json.dumps(dict(duration=seconds,notes=[dict(start=round(a,6),end=round(b,6),pitch=p,velocity=v,part=c) for a,b,p,v,c in notes])),encoding='utf-8')
            score=extract_score(gp)
            cases.append(dict(id=ident,family=family,familyTitle=family.title()+' phrase study',label=f'Sketch {i:02d}',
                audio=wav.name,gp=gp.name,roll=roll.name,gpSha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
                audioSha256=hashlib.sha256(wav.read_bytes()).hexdigest(),seconds=json.loads(roll.read_text())['duration'],
                method=methods[name],seed=17,tracks=[dict(name=t['name'],strings=len(t['tunings'][0]),program=t['program']) for t in score['tracks']]))
    version=hashlib.sha256(''.join(c['gpSha256']+c['audioSha256'] for c in cases).encode()).hexdigest()[:16]
    manifest=dict(format='composition-ablation-review-v1',version=version,cases=cases,judgments=[],
        title='Phrase development review',intro='Does a musical idea continue, develop and arrive somewhere? Compare five sketches per study.',
        guidance='Listen for a connecting thread between statements, varied expression and convincing endings. Also flag loss of pitch range or excessive smoothness.',
        audio='Same sine MIDI preview as the previous review; timing and accompaniment fixed within the four controlled cases.')
    (out/'cases.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(dict(version=version,cases=len(cases))))


if __name__=='__main__':main()
