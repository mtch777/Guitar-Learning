"""Build three private, fully unlocked generated-only bend comparisons."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from contextual_bends import apply
from bend_lever_experiment import render
from bend_analysis import extract_score,bend_shape


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--track',type=int,required=True)
    p.add_argument('--round',type=int,choices=(2,3),default=2)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    variants=['destinations','trajectories','spaced'] if a.round==2 else ['pulse','delayed','response']
    apply_fn=apply
    if a.round==3:
        from bend_timing import apply as apply_fn
    random.Random(20261017).shuffle(variants);records=[]
    for i,variant in enumerate(variants,1):
        ident=f'bend-{i:02d}';gp=a.out/(ident+'.gp');wav=a.out/(ident+'.wav')
        audit=apply_fn(a.source,gp,a.track,variant);audio=render(gp,wav,a.track,95,110)
        track=extract_score(gp)['tracks'][a.track]
        expected=[[[[bend_shape(n['note_xml']) for n in e['notes']] for e in v] for v in m['voices']] for m in track['measures']]
        gp.with_suffix('.curves.json').write_text(json.dumps(expected),encoding='utf-8')
        if not audio['bent_sustains']:raise AssertionError('No-bend preview excluded')
        records.append(dict(id=ident,method=variant,audit=audit,audio=audio,
                            gp_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
                            wav_sha256=hashlib.sha256(wav.read_bytes()).hexdigest()))
    if len({r['wav_sha256'] for r in records})!=3:raise AssertionError('Duplicate comparison')
    version=hashlib.sha256(json.dumps([r['gp_sha256'] for r in records]).encode()).hexdigest()[:16]
    (a.out/'review-key.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    blocks=[]
    for r in records:
        ident=r['id'];parts=[f'<section><h2>{ident}</h2><audio controls preload="none" src="{ident}.wav"></audio> <a href="{ident}.gp">Full GP</a>']
        for metric,label in [('fit','Overall bend fit'),('targets','Bend destinations'),('timing','Timing / interaction'),('shape','Rise, hold and release')]:
            parts.append(f'<p><label>{label} <select id="{ident}-{metric}"><option value="">Unjudged</option>'+''.join(f'<option>{x}</option>' for x in ['Poor','Mixed','Good','Cannot judge'])+'</select></label></p>')
        parts.append(f'<textarea id="{ident}-notes" placeholder="What worked or failed? Ignore the excerpt ending."></textarea></section>');blocks.append(''.join(parts))
    html='''<!doctype html><meta charset="utf-8"><title>Generated bend comparison</title><style>body{font:17px system-ui;background:#121722;color:#eee;max-width:850px;margin:30px auto;padding:20px}section{background:#202938;padding:20px;margin:20px 0;border-radius:12px}textarea{width:95%;height:65px}audio{width:75%}a{color:#9dc9ff}select,button{padding:7px;font:inherit}</style><h1>Generated bends — round 2</h1><p>Three generated-only versions. Same passage, base notes, timing and arrangement. Only bends change. No original or no-bend control. Ignore final resolution.</p><p>Solo sine previews render bend curves; full GP files retain every track. Judge placement, destination and shape. Methods stay hidden until review. Responses save locally; export when finished.</p>'''+''.join(blocks)+'''<button id="export">Export feedback</button><script>
const version=VERSION, cases=CASES, key='bend-v2-'+version, fields=[...document.querySelectorAll('select,textarea')];
const old=JSON.parse(localStorage.getItem(key)||'{}');for(const f of fields){f.value=old[f.id]||'';f.oninput=()=>localStorage.setItem(key,JSON.stringify(Object.fromEntries(fields.map(x=>[x.id,x.value]))));}
document.querySelector('#export').onclick=()=>{const data={format:'bend-feedback-v2',version,cases,exportedAt:new Date().toISOString(),reviews:Object.fromEntries(fields.map(x=>[x.id,x.value]))};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='bend-v2-feedback.json';a.click();};</script>'''
    html=html.replace('VERSION',json.dumps(version)).replace('CASES',json.dumps([{k:r[k] for k in ('id','gp_sha256','wav_sha256')} for r in records]))
    if a.round==3:
        html=html.replace('round 2','round 3: timing').replace('bend-v2-','bend-v3-').replace('bend-feedback-v2','bend-feedback-v3').replace('bend-v2-feedback.json','bend-v3-feedback.json')
        html=html.replace('Only bends change.','The same notes receive bends to the same peak pitches. Only bend start, arrival, hold and release timing change.')
    (a.out/'index.html').write_text(html,encoding='utf-8');print(json.dumps(dict(cases=3,version=version)))


if __name__=='__main__':main()
