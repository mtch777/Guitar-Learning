#!/usr/bin/env python3
"""Step 18 deep numerical parity: find first JS/librosa MFCC sub-stage divergence."""
import argparse,json
from pathlib import Path
import librosa,numpy as np
def st(a,b):
 a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel();n=min(len(a),len(b));a=a[:n];b=b[:n];d=a-b
 return {"n":n,"rmse":float(np.sqrt(np.mean(d*d))) if n else None,"mae":float(np.mean(abs(d))) if n else None,"max_abs":float(np.max(abs(d))) if n else None,"corr":float(np.corrcoef(a,b)[0,1]) if n>1 and np.std(a)>0 and np.std(b)>0 else None}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("browser_json",type=Path);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 rows=json.loads(a.browser_json.read_text()); reports=[]
 for r in rows:
  if "debug" not in r: continue
  y,sr=librosa.load(a.wav_dir/r["file"],sr=22050,mono=True);yt,idx=librosa.effects.trim(y,top_db=50); stages={"trimmed_samples":st(yt[:2646],r["debug"]["trimmed_samples"])}
  for fi,t0 in enumerate((0,.04,.08)):
   seg=yt[int(t0*sr):int((t0+.04)*sr)];nfft=512;hop=128
   S=np.abs(librosa.stft(seg,n_fft=nfft,hop_length=hop,center=True))**2
   M=librosa.feature.melspectrogram(S=S,sr=sr,n_mels=40); D=librosa.power_to_db(M)
   C=librosa.feature.mfcc(S=D,n_mfcc=13)
   tr=r["debug"]["frames"][fi]["trace"]; jp=np.asarray([x["power"] for x in tr]).T;jm=np.asarray([x["mel"] for x in tr]).T;jd=np.asarray([x["db"] for x in tr]).T;jc=np.asarray([x["mfcc"] for x in tr]).T
   stages[f"f{fi}_power"]=st(S,jp);stages[f"f{fi}_mel"]=st(M,jm);stages[f"f{fi}_db"]=st(D,jd);stages[f"f{fi}_mfcc"]=st(C,jc)
  reports.append({"file":r["file"],"librosa_trim_start":int(idx[0]),"librosa_trim_len":len(yt),"js_trim_len":r["debug"]["trimmed_len"],"stages":stages})
 names=list(reports[0]["stages"]);summary={}
 for n in names:
  vals=[x["stages"][n]["rmse"] for x in reports];summary[n]={"mean_rmse":float(np.mean(vals)),"max_rmse":float(np.max(vals))}
 (a.out/"parity.json").write_text(json.dumps({"summary":summary,"files":reports},indent=2));print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
