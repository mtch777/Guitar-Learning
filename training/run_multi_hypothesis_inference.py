#!/usr/bin/env python3
"""Step 10: hard-MIDI vs multi-hypothesis inference.

Consumes preserved Step-9 pitch outputs; Step 9 is never rerun.
For each held-out TRUE MIDI fold, trains the Step-8 three-frame 0-120 ms MFCC
Stage-B model once, retaining RAW 8-string probabilities. Candidate masks are
then applied separately for each detected MIDI hypothesis, which could not be
reconstructed from Step-8's preserved CSV because that artifact stores only
the final ground-truth-MIDI-masked prediction.

Compares:
  hard: custom YIN 160-ms top-1 MIDI -> candidate mask -> Stage-B
  topK: custom YIN candidate hypotheses -> joint pitch*Stage-B scoring
"""
from __future__ import annotations
import argparse,json,math,re,time
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
FRAMES=[("f0_40",0,.04),("f40_80",.04,.08),("f80_120",.08,.12)]
KS=(2,3,5)

def model(n,num_class=8):
    return XGBClassifier(n_estimators=n,max_depth=3,learning_rate=.04,subsample=.85,
      colsample_bytree=.85,reg_lambda=2,objective="multi:softprob",num_class=num_class,
      random_state=42,n_jobs=8)

def mfcc26(y,sr,t0,t1):
    a=int(t0*sr); b=min(len(y),max(a+1,int(t1*sr))); seg=y[a:b]
    if len(seg)<128: seg=np.pad(seg,(0,128-len(seg)))
    nfft=max(64,2**int(np.floor(np.log2(len(seg))))); nfft=min(2048,nfft,len(seg))
    hop=max(16,nfft//4); n_mels=min(40,max(16,nfft//8))
    m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=n_mels)
    return np.asarray([v for i in range(13) for v in (np.mean(m[i]),np.std(m[i]))],np.float32)

def possible(midi,s):
    return OPEN[s]<=midi<=OPEN[s]+24

def masked(p,midi):
    q=np.asarray(p,float).copy()
    for s in range(1,9):
        if not possible(midi,s): q[s-1]=0
    z=q.sum(); return q/z if z>0 else q

def parse_candidates(row):
    vals=[]
    try: vals=json.loads(row.candidates_json) if isinstance(row.candidates_json,str) else []
    except Exception: vals=[]
    # Guarantee detector top-1 is represented first if absent.
    if pd.notna(row.pred_midi):
        pm=int(row.pred_midi); pc=float(row.confidence)
        vals=[{"midi":pm,"confidence":pc}]+[x for x in vals if int(x.get("midi",-999))!=pm]
    out=[]
    for x in vals:
        try: m=int(x["midi"]); q=float(x.get("confidence",0))
        except Exception: continue
        if m<OPEN[1] or m>OPEN[8]+24: continue
        if any(z["midi"]==m for z in out): continue
        out.append({"midi":m,"confidence":max(q,1e-9)})
    return out

def load_audio(wav_dir,files):
    rec=[]
    for name in files:
        m=RX.fullmatch(name)
        if not m: raise ValueError(f"bad filename {name}")
        p=wav_dir/name; y,sr=librosa.load(p,sr=22050,mono=True); y,_=librosa.effects.trim(y,top_db=50)
        rec.append((name,int(m[1]),int(m[2]),m[3].lower(),OPEN[int(m[1])]+int(m[2]),y,sr))
    return rec

def select_smoke(pitch):
    # Whole-cycle smoke: multiple ambiguous notes + at least one top-1 error when available.
    base=pitch[(pitch.detector=="yin_custom")&(pitch.frame_ms==160)].copy()
    err=base[base.pred_midi!=base.true_midi]
    names=[]
    if len(err): names.append(err.iloc[0].file)
    amb=base[base.true_midi.apply(lambda m:sum(possible(int(m),s) for s in range(1,9))>=2)]
    names+=list(amb.file.head(15))
    names+=list(base.file.head(8))
    return list(dict.fromkeys(names))[:24]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("wav_dir",type=Path); ap.add_argument("step9_csv",type=Path)
    ap.add_argument("--out",type=Path,required=True); ap.add_argument("--trees",type=int,default=100)
    ap.add_argument("--smoke",action="store_true")
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    pitch=pd.read_csv(a.step9_csv)
    pitch=pitch[(pitch.detector=="yin_custom")&(pitch.frame_ms==160)].copy()
    files=select_smoke(pitch) if a.smoke else sorted(pitch.file.unique())
    pitch=pitch[pitch.file.isin(files)].set_index("file")
    rec=load_audio(a.wav_dir,files)
    meta=pd.DataFrame([{"file":r[0],"string":r[1],"fret":r[2],"strength":r[3],"true_midi":r[4]} for r in rec])
    print(f"Loaded {len(meta)} recordings from preserved Step-9 outputs; extracting Stage-B frames",flush=True)
    X=[]
    for k,(name,t0,t1) in enumerate(FRAMES,1):
        X.append(np.vstack([mfcc26(r[5],r[6],t0,t1) for r in rec]))
        print(f"EXTRACT [{k}/{len(FRAMES)}] {name}",flush=True)
    truth=meta.string.to_numpy(int); mids=meta.true_midi.to_numpy(int); unique=sorted(set(mids))
    P=np.zeros((len(meta),3,8),float); total=len(unique)*3; done=0; st=time.time()
    for midi in unique:
        te=np.where(mids==midi)[0]; tr=np.where(mids!=midi)[0]
        for fi,(name,_,_) in enumerate(FRAMES):
            classes=np.sort(np.unique(truth[tr]))
            if len(classes)<2:
                # Smoke can be sparse: expand training with all non-test smoke rows is still impossible
                # only for pathological tiny selection; fail loudly rather than fake probabilities.
                raise RuntimeError(f"fold MIDI {midi} has <2 training string classes")
            enc={s:i for i,s in enumerate(classes)}; ytr=np.asarray([enc[s] for s in truth[tr]])
            sc=StandardScaler().fit(X[fi][tr]); clf=model(20 if a.smoke else a.trees,len(classes))
            clf.fit(sc.transform(X[fi][tr]),ytr); raw=clf.predict_proba(sc.transform(X[fi][te]))
            for ci,s in enumerate(classes): P[te,fi,s-1]=raw[:,ci]
            done+=1; elapsed=time.time()-st; eta=elapsed/done*(total-done)
            print(f"MODEL [{done}/{total}] MIDI {midi} {name} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    stage=P.mean(axis=1)
    rows=[]; methods=["hard"]+[f"top{k}" for k in KS]
    for i,r in meta.iterrows():
        pr=pitch.loc[r.file]; cands=parse_candidates(pr)
        if not cands: cands=[{"midi":int(pr.pred_midi),"confidence":max(float(pr.confidence),1e-9)}]
        def choose(use):
            hyps=[]
            for rank,x in enumerate(use,1):
                m=int(x["midi"]); pc=float(x["confidence"]); sp=masked(stage[i],m)
                for s in range(1,9):
                    if sp[s-1]>0:
                        hyps.append({"midi":m,"string":s,"fret":m-OPEN[s],"pitch_conf":pc,
                          "string_prob":float(sp[s-1]),"joint":pc*float(sp[s-1]),"pitch_rank":rank})
            if not hyps: return None,[]
            z=sum(h["joint"] for h in hyps)
            if z>0:
                for h in hyps:h["joint_norm"]=h["joint"]/z
            hyps.sort(key=lambda h:h["joint"],reverse=True)
            return hyps[0],hyps
        sets={"hard":cands[:1]}
        for k in KS: sets[f"top{k}"]=cands[:k]
        for meth,use in sets.items():
            best,hyps=choose(use)
            if best is None: continue
            rows.append({"method":meth,"file":r.file,"true_midi":int(r.true_midi),"true_string":int(r.string),"true_fret":int(r.fret),
              "pitch_top1":int(cands[0]["midi"]),"pitch_top1_correct":int(cands[0]["midi"])==int(r.true_midi),
              "candidate_count":len(use),"pred_midi":best["midi"],"pred_string":best["string"],"pred_fret":best["fret"],
              "midi_correct":best["midi"]==int(r.true_midi),"string_correct":best["string"]==int(r.string),
              "joint_correct":best["midi"]==int(r.true_midi) and best["string"]==int(r.string) and best["fret"]==int(r.fret),
              "joint_confidence":best.get("joint_norm",0),"hypotheses_json":json.dumps(hyps,separators=(",",":"))})
    df=pd.DataFrame(rows); df.to_csv(a.out/"joint_predictions.csv",index=False)
    summary={"step":10,"smoke":a.smoke,"recordings":len(meta),"stage_a":"Step-9 custom YIN 160 ms preserved outputs","stage_b":"Step-8-style 3x40ms MFCC raw probability mean; trained here because preserved Step-8 CSV did not retain raw 8-class probabilities","trees":20 if a.smoke else a.trees,"methods":{}}
    hard=df[df.method=="hard"].set_index("file")
    for meth in methods:
        g=df[df.method==meth].set_index("file"); n=len(g)
        joint=int(g.joint_correct.sum()); midiok=int(g.midi_correct.sum()); strok=int(g.string_correct.sum())
        top_oracle=0
        for _,row in g.iterrows():
            hs=json.loads(row.hypotheses_json)
            if any(h["midi"]==row.true_midi and h["string"]==row.true_string and h["fret"]==row.true_fret for h in hs): top_oracle+=1
        resc=reg=0
        if meth!="hard":
            common=g.join(hard[["joint_correct"]],rsuffix="_hard")
            resc=int((common.joint_correct & ~common.joint_correct_hard).sum())
            reg=int((~common.joint_correct & common.joint_correct_hard).sum())
        summary["methods"][meth]={"joint_correct":joint,"joint_accuracy":joint/n if n else 0,"midi_correct":midiok,
          "midi_accuracy":midiok/n if n else 0,"string_correct":strok,"string_accuracy":strok/n if n else 0,
          "hypothesis_oracle_correct":top_oracle,"unique_rescues_vs_hard":resc,"regressions_vs_hard":reg}
    # Detector-only candidate oracle: can the true MIDI be found before Stage B?
    for k in KS:
        found=sum(any(x["midi"]==int(meta.iloc[i].true_midi) for x in parse_candidates(pitch.loc[meta.iloc[i].file])[:k]) for i in range(len(meta)))
        summary[f"pitch_top{k}_oracle"]={"correct":int(found),"accuracy":found/len(meta)}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2))
    # Compact rescue/error table.
    wide=df.pivot(index="file",columns="method",values="joint_correct")
    wide.to_csv(a.out/"method_correctness.csv")
    print(json.dumps(summary,indent=2),flush=True)
if __name__=="__main__": main()
