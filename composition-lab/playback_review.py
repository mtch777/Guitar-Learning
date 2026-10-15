"""Render alphaTab-exported SMF as a clearly labeled synthetic listening preview.

This does not reproduce Guitar Pro soundbanks or technique rendering. Human
judgments stay blank. Anonymous assignments are reproducible and kept local.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import wave


def render_midi(source, destination, sample_rate=22050):
    import mido
    import numpy as np
    midi=mido.MidiFile(source); now=0.; sounding={}; notes=[]
    for msg in midi:
        now+=msg.time
        if msg.type=='note_on' and msg.velocity:
            sounding.setdefault((msg.channel,msg.note),[]).append((now,msg.velocity))
        elif msg.type=='note_off' or (msg.type=='note_on' and not msg.velocity):
            queue=sounding.get((msg.channel,msg.note),[])
            if queue:
                start,velocity=queue.pop(0); notes.append((start,now,msg.note,velocity))
    if any(sounding.values()): raise ValueError('Unterminated MIDI note')
    samples=np.zeros(int((now+.5)*sample_rate),dtype=np.float64)
    for start,end,pitch,velocity in notes:
        size=max(1,int((end-start)*sample_rate)); t=np.arange(size)/sample_rate
        envelope=np.minimum(1,t/.008)*np.minimum(1,(end-start-t)/.04)
        tone=np.sin(2*np.pi*(440*2**((pitch-69)/12))*t)*np.maximum(0,envelope)*velocity/127
        offset=int(start*sample_rate); samples[offset:offset+size]+=tone[:len(samples[offset:offset+size])]
    peak=float(np.max(np.abs(samples)))
    if peak: samples*=.85/peak
    with wave.open(str(destination),'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(sample_rate)
        out.writeframes((samples*32767).astype('<i2').tobytes())
    return dict(midi_notes=len(notes),seconds=now,nonzero_samples=int(np.count_nonzero(samples)),
                renderer='sine MIDI approximation; no GP soundbank/techniques',listening_judgment=None)


def main():
    p=argparse.ArgumentParser(); p.add_argument('directory',type=Path); p.add_argument('--seed',type=int,default=17)
    args=p.parse_args(); files=sorted(args.directory.glob('*.mid'))
    if not files: p.error('Run verify_gp.mjs to export MIDI from GP first')
    queue=args.directory/'blind-review.csv'
    if queue.exists(): raise FileExistsError('Do not overwrite previous human review')
    random.Random(args.seed).shuffle(files); key={}; rows=[]
    for i,path in enumerate(files):
        ident=f'case-{i+1:02d}'; wav=args.directory/(ident+'.wav')
        report=render_midi(path,wav)
        key[ident]=dict(source=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**report)
        rows.append(dict(case_id=ident,audio=wav.name,coherence='',playability='',phrase_development='',preference='',notes=''))
    with queue.open('w',newline='',encoding='utf-8') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (args.directory/'review-key.json').write_text(json.dumps(key,indent=2),encoding='utf-8')
    print(json.dumps(dict(cases=len(rows),review=str(queue),judgments_collected=0)))


if __name__=='__main__': main()
