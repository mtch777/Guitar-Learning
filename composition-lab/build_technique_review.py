"""Private reproducible controlled probes, explicitly not artist-style compositions."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
from gp_author import write_gp
from exact_score import extract_score
from technique_edits import generate_hopo,generate_vibrato
from pattern_edits import generate,FAMILIES
from technique_analysis import analyze


def fixture():
    frets=[0,2,4,7,9,7,2,0,12,14,16,19,21,17,4,0,0,4,6,9,9,7,2,0,12,14,16,19,21,17,4,0]
    measures=[];q=F(0)
    for bar in range(8):
        events=[];local=F(0)
        for i,fret in enumerate(frets[bar*4:bar*4+4]):
            duration=F(1,2) if i%2==0 else F(3,2)
            events.append(dict(onset_q=str(q+local),local_onset_q=str(local),duration_q=str(duration),notes=[dict(midi=64+fret,string=5,fret=fret,tie=None,technique_tags=[])]));local+=duration
        measures.append(dict(number=bar+1,onset_q=str(q),time_signature='4/4',section='Controlled probe' if bar==0 else None,voices=[events]));q+=4
    return dict(tracks=[dict(index=0,name='Controlled guitar probe',program=25,tunings=[[40,45,50,55,59,64]],measures=measures)])


def roll(score):
    return [dict(start=float(F(n['onset_q'])),duration=float(F(n['duration_q'])),pitch=n['midi'],fret=n['fret'],string=n['string'],hopo='HopoDestination' in n['property_names'],vibrato='Vibrato' in n['note_xml']) for m in score['tracks'][0]['measures'] for v in m['voices'] for e in v for n in e['notes']]


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.out/'diagnostic-reference.gp';write_gp(fixture(),source,title='Authored technique control fixture')
    families=['hammer_on_fretted','pull_off_fretted','hammer_on_from_open','pull_off_to_open','finger_vibrato',*FAMILIES];cases=[];keys=[]
    for fi,family in enumerate(families):
        methods=('Slight','Wide') if family=='finger_vibrato' else ('compact','upper') if family in FAMILIES else ('short_intervals','long_arrivals')
        methods=list(methods);random.Random(20261016+fi).shuffle(methods)
        group=dict(id=family,title=family.replace('_',' '),scope='arrangement: pitches/voicings unlocked, timing locked' if family in FAMILIES else 'performance: pitches/frets/strings/timing locked',variants={})
        for strength in (25,50,75,100):
            pair=[]
            for label,method in zip(('A','B'),methods):
                ident=f'{fi+1:02}-{strength}-{label}';dest=a.out/(ident+'.gp')
                if family in FAMILIES:audit=generate(source,dest,0,family,strength,method,True,True)
                elif family=='finger_vibrato':audit=generate_vibrato(source,dest,0,strength,method)
                else:audit=generate_hopo(source,dest,0,family,strength,method)
                restored=extract_score(dest)
                dest.with_suffix('.edit.json').write_text(json.dumps(audit,indent=2))
                analysis=analyze(restored)
                dest.with_suffix('.analysis.json').write_text(json.dumps(analysis))
                expected=[dict(location=f'0:{mi}:0:{ei}:{ni}',midi=n['midi'],string=n['string'],fret=n['fret']) for mi,m in enumerate(restored['tracks'][0]['measures']) for ei,e in enumerate(m['voices'][0]) for ni,n in enumerate(e['notes'])]
                dest.with_suffix('.expected.json').write_text(json.dumps(expected))
                active=bool(analysis['tracks'][0]['explicit_hopo']) if family not in FAMILIES and family!='finger_vibrato' else any(n['vibrato'] for n in roll(restored)) if family=='finger_vibrato' else True
                pair.append(dict(id=ident,label=label,gp=dest.name,audio=dest.stem+'.instrument.wav',notes=roll(restored),active=active))
                keys.append(dict(id=ident,family=family,strength=strength,method=method))
            # Preserve zero-effect artifacts privately, never offer them for listening.
            if all(v['active'] for v in pair):group['variants'][str(strength)]=pair
        if not group['variants']:raise AssertionError('No nonempty paired method comparison: '+family)
        cases.append(group)
    version=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()[:16]
    (a.out/'cases.json').write_text(json.dumps(dict(version=version,cases=cases)))
    (a.out/'review-key.json').write_text(json.dumps(keys,indent=2))
    template=Path(__file__).with_name('technique_review.html').read_text(encoding='utf-8')
    (a.out/'index.html').write_text(template,encoding='utf-8')
    print(json.dumps(dict(groups=len(cases),gp_variants=len(keys),version=version,authored_probes=True,human_judgments=0)))


if __name__=='__main__':main()

