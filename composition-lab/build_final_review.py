"""Package sampled generated outputs privately; public review UI loads locally."""
import argparse,base64,hashlib,json,random
from pathlib import Path
from playback_review import read_midi_notes
from exact_score import extract_score


def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);args=p.parse_args();root=args.workspace
    choices=[]
    for family in ('cloud','sweet'):
        choices += [(family,p,'Exploratory learned pool + form-state + joint-role engine') for p in sorted((root/'compositions').glob('*'+family+'.gp'))[:10]]
        prior=root.parent/f'{family}-native-ablations/roles-phrases.gp'
        choices.append((family,prior,'Historical 16-bar roles/motif baseline; shorter reference, not matched full-song comparison'))
    random.Random(16102026).shuffle(choices);cases=[];media={}
    for i,(family,path,method) in enumerate(choices,1):
        midi=path.with_suffix('.mid');seconds,notes=read_midi_notes(midi);data=path.read_bytes();score=extract_score(path);ident=f'final-{i:02d}'
        roll=[dict(start=round(a,6),end=round(b,6),pitch=p,velocity=v,part=c) for a,b,p,v,c in notes]
        media[ident]=dict(gpBase64=base64.b64encode(data).decode(),notes=roll)
        cases.append(dict(id=ident,family=family,familyTitle=family.title()+' output collection',label=f'Piece {i:02d}',audio=ident+'.wav',roll=ident+'.json',gp=ident+'.gp',
            gpSha256=hashlib.sha256(data).hexdigest(),audioSha256=None,notesSha256=hashlib.sha256(json.dumps(roll).encode()).hexdigest(),seconds=seconds,
            method=method,tracks=[dict(name=t['name'],strings=len(t['tunings'][0]),program=t['program']) for t in score['tracks']]))
    version=hashlib.sha256(json.dumps(cases,sort_keys=True).encode()).hexdigest()[:16]+'-v2'
    manifest=dict(format='composition-ablation-review-v1',version=version,cases=cases,title='Consolidated full-composition review',
        intro='Twenty 64-bar exploratory compositions and two shorter historical references. Musical quality and failed research gates remain for review.',
        asideIntro='Private generated material; full-length outputs plus shorter historical references. Nothing is uploaded. Audio is synthesized locally with one fixed gain.',
        guidance='Judge overall coherence, development, meaningful pauses and endings. Historical references are shorter, so comparisons are exploratory rather than controlled preference estimates.',judgments=[],
        ratingMetrics=[['coherence','Overall coherence'],['melody','Melody continuity'],['harmony','Harmony fit'],['phrasing','Idea development'],['holds','Meaningful pauses/holds'],['resolution','Meaningful ending'],['playability','Playability (if assessable)']])
    target=root/'consolidated-review-v2.json'
    if target.exists():raise FileExistsError('Preserve prior bundle')
    target.write_text(json.dumps(dict(format='composition-private-review-v1',manifest=manifest,media=media),separators=(',',':')),encoding='utf-8')
    print(json.dumps(dict(bundle=str(target),bytes=target.stat().st_size,cases=len(cases),version=version)))


if __name__=='__main__':main()
