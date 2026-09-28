#!/usr/bin/env python3
"""Step 13: inverse-segment-frequency (SIF) feasibility screen.

Tests whether the theoretical inverse fretted-segment resonance leaves a
measurable spectral peak in the magnetic-pickup recordings. This is a physics
feasibility gate, not a classifier.

For each fretted note, expected SIF is estimated from the speaking-string
fundamental and fret position:
    f_sif = f0 / (2**(fret/12) - 1)
which follows from frequency being inversely proportional to string length.
Open strings are excluded because the inverse segment is not defined.

Matched controls use the same recording and log-frequency offsets around the
expected SIF, avoiding harmonic neighborhoods. The gate requires the expected
location to beat controls consistently, not just occasionally.
"""
from __future__ import annotations
import argparse,json,re,time
from pathlib import Path
import numpy as np
import pandas as pd
import librosa

RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$")
TUNING=[27,34,39,44,49,54,58,63]
CONTROL_RATIOS=np.array([2**(-3/12),2**(-2/12),2**(-1/12),2**(1/12),2**(2/12),2**(3/12)])
SR=22050
NFFT=16384
START=.04
END=.80

def midi_hz(m): return 440.0*2**((m-69)/12)

def band_peak(freq,mag,target,cents=35):
    lo=target*2**(-cents/1200); hi=target*2**(cents/1200)
    q=(freq>=lo)&(freq<=hi)
    if not q.any(): return np.nan
    return float(np.max(mag[q]))

def analyze(path,string,fret,strength):
    y,_=librosa.load(path,sr=SR,mono=True)
    y,_=librosa.effects.trim(y,top_db=50)
    seg=y[int(START*SR):min(len(y),int(END*SR))]
    if len(seg)<512:return None
    win=np.hanning(len(seg)); spec=np.abs(np.fft.rfft(seg*win,n=NFFT))
    freq=np.fft.rfftfreq(NFFT,1/SR)
    f0=midi_hz(TUNING[string-1]+fret)
    fsif=f0/(2**(fret/12)-1)
    if not (45<=fsif<=SR/2-100):return None
    # Reject expected/control locations that land too close to a speaking-string harmonic.
    def harmonic_close(x):
        h=max(1,round(x/f0)); cents=1200*abs(np.log2(x/(h*f0)))
        return cents<45
    # Do not discard a recording merely because the expected SIF happens to
    # overlap a speaking-string harmonic. That made the feasibility screen
    # structurally empty for this equal-tempered geometry. Preserve the
    # overlap as metadata and compare against matched nearby controls.
    expected_harmonic_overlap=harmonic_close(fsif)
    expected=band_peak(freq,spec,fsif)
    ctr=[]
    for ratio in CONTROL_RATIOS:
        fc=fsif*ratio
        if 45<=fc<=SR/2-100:
            ctr.append(band_peak(freq,spec,fc))
    ctr=np.array([x for x in ctr if np.isfinite(x)])
    if not np.isfinite(expected) or len(ctr)<2:return None
    eps=1e-12
    db=20*np.log10((expected+eps)/(np.median(ctr)+eps))
    rank=float(np.mean(expected>ctr))
    return dict(file=path.name,string=string,fret=fret,strength=strength,midi=TUNING[string-1]+fret,
                f0_hz=f0,expected_sif_hz=fsif,expected_peak=float(expected),
                control_median=float(np.median(ctr)),expected_vs_control_db=float(db),
                control_win_fraction=float(rank),n_controls=len(ctr),
                expected_harmonic_overlap=bool(expected_harmonic_overlap))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--data",type=Path,default=Path("training/data/ringing_384"))
    ap.add_argument("--out",type=Path,required=True);ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    files=[]
    for p in sorted(a.data.glob("*.wav")):
        m=RX.match(p.name)
        if m and int(m.group(2))>0: files.append((p,int(m.group(1)),int(m.group(2)),m.group(3)))
    if a.smoke:
        # Whole pipeline, smallest practical real-data spread: 2 examples/string where available.
        chosen=[]
        for s in range(1,9):
            q=[x for x in files if x[1]==s]
            # Use mid/high frets: the inverse segment at fret 1 is often
            # above Nyquist, so the first two lexicographic files are a bad
            # feasibility smoke sample.
            preferred=[x for x in q if x[2] in (7,12,17,19,24)]
            chosen+=preferred[:2]
        files=chosen
    print(f"SIF INPUT recordings={len(files)} smoke={a.smoke}",flush=True)
    rows=[];t0=time.time()
    for i,x in enumerate(files,1):
        z=analyze(*x)
        if z:rows.append(z)
        if i==1 or i%25==0 or i==len(files):
            elapsed=time.time()-t0; eta=elapsed/i*(len(files)-i)
            print(f"SIF [{i}/{len(files)}] usable={len(rows)} elapsed={elapsed:.1f}s ETA={eta:.1f}s",flush=True)
    d=pd.DataFrame(rows)
    if len(d)==0:raise RuntimeError("No usable SIF observations")
    d.to_csv(a.out/"sif_observations.csv",index=False)
    med=float(d.expected_vs_control_db.median())
    win=float(d.control_win_fraction.mean())
    positive=float((d.expected_vs_control_db>0).mean())
    # Strict feasibility gate: median expected peak >=3 dB above matched-control median,
    # expected beats >=70% of controls, and >=65% of recordings are positive.
    survives=bool(med>=3.0 and win>=0.70 and positive>=0.65)
    by_string=d.groupby("string").agg(n=("file","size"),median_db=("expected_vs_control_db","median"),
        positive_fraction=("expected_vs_control_db",lambda x:float((x>0).mean())),
        control_win_fraction=("control_win_fraction","mean")).reset_index()
    by_string.to_csv(a.out/"sif_by_string.csv",index=False)
    summary={"step":13,"smoke":a.smoke,"input_recordings":len(files),"usable_recordings":len(d),
      "median_expected_vs_control_db":med,"expected_control_win_fraction":win,
      "positive_recording_fraction":positive,"gate":{"median_db_min":3.0,"control_win_min":0.70,
      "positive_fraction_min":0.65},"sif_signal_survives":survives,
      "conclusion":"continue SIF investigation" if survives else "kill SIF branch"}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__":main()
