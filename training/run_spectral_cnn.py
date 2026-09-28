#!/usr/bin/env python3
"""Step 11: compact early-window log-mel CNN for physical-string classification.

One deliberately small learned spectral model. Evaluation is leave-one-entire-
MIDI-out. Candidate masking is reported separately from raw acoustic output.
The real run uses a fixed recipe; no held-out-fold hyperparameter search.
"""
from __future__ import annotations
import argparse,json,re,time,random
from pathlib import Path
import librosa,numpy as np,pandas as pd
from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
import torch
from torch import nn
from torch.utils.data import DataLoader,TensorDataset

OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63}
RX=re.compile(r"s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$",re.I)
SR=22050; DUR=.160; NFFT=256; HOP=64; NMELS=48; EPS=1e-8
SEED=42

def seed_all():
    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

def possible(midi,s): return OPEN[s]<=midi<=OPEN[s]+24

def mask_rows(p,midis):
    q=p.copy()
    for i,m in enumerate(midis):
        for s in range(1,9):
            if not possible(int(m),s): q[i,s-1]=0
        z=q[i].sum()
        if z>0:q[i]/=z
    return q

def logmel(y):
    n=int(SR*DUR); y=y[:n]
    if len(y)<n:y=np.pad(y,(0,n-len(y)))
    m=librosa.feature.melspectrogram(y=y,sr=SR,n_fft=NFFT,hop_length=HOP,
        win_length=NFFT,n_mels=NMELS,fmin=30,fmax=SR/2,power=2.0,center=False)
    return librosa.power_to_db(m,ref=1.0).astype(np.float32)

def load(wav_dir):
    rows=[]; specs=[]
    for p in sorted(wav_dir.glob("*.wav")):
        m=RX.fullmatch(p.name)
        if not m:continue
        s,f=int(m[1]),int(m[2]); y,_=librosa.load(p,sr=SR,mono=True); y,_=librosa.effects.trim(y,top_db=50)
        rows.append({"file":p.name,"string":s,"fret":f,"strength":m[3].lower(),"midi":OPEN[s]+f})
        specs.append(logmel(y))
    return pd.DataFrame(rows),np.stack(specs)

class TinyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(
          nn.Conv2d(1,16,3,padding=1),nn.BatchNorm2d(16),nn.ReLU(),nn.MaxPool2d(2),
          nn.Conv2d(16,32,3,padding=1),nn.BatchNorm2d(32),nn.ReLU(),nn.MaxPool2d(2),
          nn.Conv2d(32,64,3,padding=1),nn.BatchNorm2d(64),nn.ReLU(),
          nn.AdaptiveAvgPool2d((1,1)))
        self.fc=nn.Sequential(nn.Flatten(),nn.Linear(64,32),nn.ReLU(),nn.Linear(32,8))
    def forward(self,x):return self.fc(self.net(x))

def normalize(train,test):
    mu=float(train.mean()); sd=float(train.std()+EPS)
    return (train-mu)/sd,(test-mu)/sd,mu,sd

def train_fold(xtr,ytr,xte,epochs,batch,device):
    model=TinyCNN().to(device); opt=torch.optim.Adam(model.parameters(),lr=1e-3,weight_decay=1e-4)
    lossfn=nn.CrossEntropyLoss()
    ds=TensorDataset(torch.from_numpy(xtr[:,None]),torch.from_numpy(ytr.astype(np.int64)))
    dl=DataLoader(ds,batch_size=batch,shuffle=True,generator=torch.Generator().manual_seed(SEED))
    hist=[]
    for ep in range(epochs):
        model.train(); total=0.; count=0
        for xb,yb in dl:
            xb,yb=xb.to(device),yb.to(device); opt.zero_grad(); loss=lossfn(model(xb),yb); loss.backward(); opt.step()
            total+=float(loss)*len(xb); count+=len(xb)
        hist.append(total/count)
    model.eval()
    with torch.no_grad():
        t=torch.from_numpy(xte[:,None]).to(device)
        logits=model(t); probs=torch.softmax(logits,dim=1).cpu().numpy(); logits=logits.cpu().numpy()
    return probs,logits,hist,model

def eval_probs(df,prob):
    truth=df.string.to_numpy(int); pred=prob.argmax(1)+1
    return {"correct":int((pred==truth).sum()),"errors":int((pred!=truth).sum()),
      "accuracy":float(accuracy_score(truth,pred)),"macro_f1":float(f1_score(truth,pred,average="macro")),
      "confusion":confusion_matrix(truth,pred,labels=list(range(1,9))).tolist()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("wav_dir",type=Path); ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--smoke",action="store_true"); ap.add_argument("--epochs",type=int,default=18)
    ap.add_argument("--batch",type=int,default=32); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); seed_all()
    device="cuda" if torch.cuda.is_available() else "cpu"
    t0=time.time(); df,X=load(a.wav_dir); print(f"EXTRACT [384/384] log-mel {X.shape} | {time.time()-t0:.1f}s",flush=True)
    # Smoke evaluates a few real held-out MIDI folds but trains each against the full remaining dataset.
    all_midi=sorted(df.midi.unique()); eval_midi=all_midi if not a.smoke else [54,58,61]
    raw=np.full((len(df),8),np.nan); masked=np.full((len(df),8),np.nan); logits_all=np.full((len(df),8),np.nan)
    curves=[]; norms=[]; runtimes=[]; modelsizes=[]; st=time.time()
    for k,midi in enumerate(eval_midi,1):
        te=np.where(df.midi.to_numpy()==midi)[0]; tr=np.where(df.midi.to_numpy()!=midi)[0]
        xtr,xte,mu,sd=normalize(X[tr],X[te]); ep=2 if a.smoke else a.epochs
        ts=time.perf_counter(); p,l,h,model=train_fold(xtr,df.string.to_numpy()[tr]-1,xte,ep,a.batch,device); runtime=(time.perf_counter()-ts)*1000
        raw[te]=p; logits_all[te]=l; masked[te]=mask_rows(p,df.midi.to_numpy()[te])
        curves += [{"midi":int(midi),"epoch":i+1,"loss":float(v)} for i,v in enumerate(h)]
        norms.append({"midi":int(midi),"mean":mu,"std":sd})
        params=sum(x.numel() for x in model.parameters()); modelsizes.append(params)
        runtimes.append({"midi":int(midi),"train_plus_test_ms":runtime,"test_recordings":len(te)})
        elapsed=time.time()-st; eta=elapsed/k*(len(eval_midi)-k)
        print(f"MODEL [{k}/{len(eval_midi)}] MIDI {midi} epochs {ep} loss {h[0]:.4f}->{h[-1]:.4f} | elapsed {elapsed/60:.1f}m ETA {eta/60:.1f}m",flush=True)
    keep=np.isfinite(raw).all(1); edf=df.loc[keep].reset_index(drop=True); rp=raw[keep]; mp=masked[keep]; lp=logits_all[keep]
    rr=eval_probs(edf,rp); mr=eval_probs(edf,mp)
    rows=[]
    for i,r in edf.iterrows():
        rows.append({**r.to_dict(),"raw_pred":int(rp[i].argmax()+1),"raw_conf":float(rp[i].max()),
          "masked_pred":int(mp[i].argmax()+1),"masked_conf":float(mp[i].max()),"raw_probs_json":json.dumps(rp[i].tolist()),
          "masked_probs_json":json.dumps(mp[i].tolist()),"logits_json":json.dumps(lp[i].tolist())})
    pd.DataFrame(rows).to_csv(a.out/"spectral_cnn_predictions.csv",index=False)
    pd.DataFrame(curves).to_csv(a.out/"training_curves.csv",index=False)
    pd.DataFrame(norms).to_csv(a.out/"fold_normalization.csv",index=False)
    # Error overlap against preserved reference predictions is intentionally deferred to Step 12;
    # Step 11 saves full OOF probabilities/logits needed for that comparison without retraining.
    summary={"step":11,"smoke":a.smoke,"evaluated_recordings":len(edf),"folds":len(eval_midi),"device":device,
      "input":{"sr":SR,"duration_ms":160,"n_fft":NFFT,"hop":HOP,"n_mels":NMELS,"shape":list(X.shape[1:])},
      "network":"Conv16-BN-ReLU-pool -> Conv32-BN-ReLU-pool -> Conv64-BN-ReLU -> GAP -> Dense32 -> 8",
      "epochs":2 if a.smoke else a.epochs,"parameters":int(max(modelsizes)),"raw":rr,"candidate_masked":mr,
      "mean_train_plus_test_ms_per_fold":float(np.mean([x["train_plus_test_ms"] for x in runtimes])),
      "leakage_rule":"held-out MIDI excluded from training and normalization; fixed recipe; no test-fold tuning"}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2)); (a.out/"config.json").write_text(json.dumps(summary["input"]|{"epochs":summary["epochs"],"batch":a.batch,"seed":SEED},indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__":main()
