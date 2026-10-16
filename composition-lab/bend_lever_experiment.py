"""Private GP/audio comparison for reference-freedom bend controls; no models."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
import wave
import zipfile
from xml.etree import ElementTree as ET
from bend_analysis import analyze,extract_score,tie_chains
from reference_levers import apply_bends


def render(source,destination,track_index,start_bar,end_bar,sample_rate=22050):
    import numpy as np
    score=extract_score(source);track=analyze(score)['tracks'][track_index]
    measures=score['tracks'][track_index]['measures']
    start=F(measures[start_bar-1]['onset_q'])
    end=F(measures[end_bar-1]['onset_q'])+sum((F(e['duration_q']) for e in measures[end_bar-1]['voices'][0]),F(0))
    # Empty bars still have metrical duration even if no explicit beats exist.
    num,den=map(int,measures[end_bar-1]['time_signature'].split('/'))
    end=F(measures[end_bar-1]['onset_q'])+F(4*num,den)
    with zipfile.ZipFile(source) as z:root=ET.fromstring(z.read('Content/score.gpif'))
    tempos=[(F(0),120.)]
    for a in root.findall('./MasterTrack/Automations/Automation'):
        if a.findtext('Type')!='Tempo':continue
        if a.findtext('Linear')=='true':raise ValueError('Tempo ramps unsupported in diagnostic renderer')
        bar=int(a.findtext('Bar'));position=F(a.findtext('Position') or '0')
        bpm,unit=map(float,a.findtext('Value').split())
        if unit!=2:raise ValueError('Unsupported tempo beat unit')
        m=measures[bar];n,d=map(int,m['time_signature'].split('/'))
        tempos.append((F(m['onset_q'])+position*F(4*n,d),bpm))
    tempo_map=dict(tempos);tempos=sorted(tempo_map.items())
    def seconds(q):
        total=0.
        for i,(pos,bpm) in enumerate(tempos):
            stop=tempos[i+1][0] if i+1<len(tempos) else q
            if q>pos:total+=float(min(q,stop)-pos)*60/bpm
        return total
    duration=seconds(end)-seconds(start)
    samples=np.zeros(round((duration+.1)*sample_rate));count=0;bent=0;max_semitones=0.
    chains,unresolved,dangling=tie_chains(track['occurrences'])
    if unresolved or dangling:raise ValueError('Unresolved ties')
    for chain in chains:
        first=chain[0];q0=F(first['onset_q']);q1=F(chain[-1]['onset_q'])+F(chain[-1]['duration_q'])
        if q1<=start or q0>=end or first['midi'] is None:continue
        left=max(start,q0);right=min(end,q1)
        t0=seconds(left)-seconds(start);t1=seconds(right)-seconds(start)
        i0=round(t0*sample_rate);i1=round(t1*sample_rate)
        times=np.arange(i0,i1)/sample_rate+seconds(start)
        shifts=np.zeros(len(times))
        for r in chain:
            onset=F(r['onset_q']);d=F(r['duration_q']);b=r['bend']
            if b is None or not d:continue
            xs=[seconds(onset+F(p['offset_fraction'])*d) for p in b['points']]
            ys=[float(F(p['semitones'])) for p in b['points']]
            mask=(times>=seconds(onset)) & (times<seconds(onset+d))
            shifts[mask]=np.interp(times[mask],xs,ys)
        frequency=440*2**((first['midi']-69+shifts)/12)
        phase=np.cumsum(frequency)*2*np.pi/sample_rate
        # Fixed gain across cases; no per-file loudness normalization.
        local=times-seconds(q0);remaining=seconds(q1)-times
        envelope=np.minimum(1,local/.008)*np.minimum(1,remaining/.025)
        samples[i0:i1]+=.12*np.sin(phase)*np.maximum(0,envelope)
        count+=1;bent+=any(r['bend'] is not None for r in chain)
        max_semitones=max(max_semitones,float(np.max(shifts)) if len(shifts) else 0)
    peak=float(np.max(np.abs(samples)))
    if peak>=1:raise ValueError('Clipped preview')
    with wave.open(str(destination),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(sample_rate)
        out.writeframes((samples*32767).astype('<i2').tobytes())
    return dict(seconds=duration,sustains=count,bent_sustains=bent,peak=peak,max_semitones=max_semitones,
                renderer='Solo-only fixed-gain sine preview with piecewise-linear GP bend curves and source tempo map; other performance effects not synthesized',
                listening_judgment=None)


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--track',type=int,required=True);p.add_argument('--start-bar',type=int,default=95);p.add_argument('--end-bar',type=int,default=110)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    conditions=[('original',0,'contextual'),('removed',100,'removed'),('frequency',100,'frequency'),
                ('contextual-25',25,'contextual'),('contextual-50',50,'contextual'),
                ('contextual-75',75,'contextual'),('contextual-100',100,'contextual')]
    random.Random(20261016).shuffle(conditions);records=[]
    for i,(name,strength,method) in enumerate(conditions,1):
        ident=f'case-{i:02d}';gp=a.out/(ident+'.gp');wav=a.out/(ident+'.wav')
        audit=apply_bends(a.source,gp,a.track,strength,method)
        audio=render(gp,wav,a.track,a.start_bar,a.end_bar)
        records.append(dict(id=ident,condition=name,audit=audit,audio=audio))
    (a.out/'review-key.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    seen={};visible=[]
    for record in records:
        digest=hashlib.sha256((a.out/(record['id']+'.wav')).read_bytes()).hexdigest()
        if digest not in seen:visible.append(record)
        seen.setdefault(digest,[]).append(record['id'])
    blocks=''.join(f'<section><h2>{r["id"]}</h2><audio controls preload="none" src="{r["id"]}.wav"></audio> '
                   f'<a href="{r["id"]}.gp" download>Full GP</a><p>How well do the bends fit? '
                   f'<select id="{r["id"]}-rating"><option value="">Unjudged</option>'
                   +''.join(f'<option>{x}</option>' for x in ['Poor','Mixed','Good','Cannot judge'])
                   +f'</select></p><textarea id="{r["id"]}-notes" placeholder="Too frequent? Wrong destination? Awkward timing? What works?"></textarea></section>' for r in visible)
    html='''<!doctype html><meta charset="utf-8"><title>Bend lever comparison</title>
<style>body{background:#121722;color:#eee;font:17px system-ui;max-width:850px;margin:40px auto;padding:20px}section{background:#202938;padding:20px;margin:20px 0;border-radius:12px}textarea{width:95%;height:70px}a{color:#9dc9ff}button,select{font:inherit;padding:8px}audio{width:75%}</style>
<h1>Bend-only comparison</h1><p>Same source passage, solo track, notes and timing. Only bend annotations vary. Some cases may sound alike; that is allowed. Previews reproduce pitch curves with a simple sine tone, not guitar timbre. Full GP files retain all original tracks.</p>
<p>Compare bend placement, destination and timing. Do not open review-key.json before judging. Feedback stays in this browser until exported.</p>'''+blocks+'''
<button id="save">Export feedback</button><script>
const key='bend-levers-v1';const fields=[...document.querySelectorAll('select,textarea')];
const old=JSON.parse(localStorage.getItem(key)||'{}');for(const f of fields){f.value=old[f.id]||'';f.onchange=()=>localStorage.setItem(key,JSON.stringify(Object.fromEntries(fields.map(x=>[x.id,x.value]))));}
document.querySelector('#save').onclick=()=>{const data={format:key,exportedAt:new Date().toISOString(),reviews:Object.fromEntries(fields.map(x=>[x.id,x.value]))};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='bend-lever-feedback.json';a.click();};</script>'''
    (a.out/'index.html').write_text(html,encoding='utf-8')
    print(json.dumps({'cases':len(records),'out':str(a.out),'locks_verified':all(r['audit']['locked_xml_verified'] for r in records)}))


if __name__=='__main__':main()
