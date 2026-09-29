#!/usr/bin/env python3
"""Step 18 deep numerical parity: locate first JS/librosa divergence."""
import argparse,json
from pathlib import Path
import librosa,numpy as np
def st(a,b):
 a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel();n=min(len(a),len(b));a=a[:n];b=b[:n];d=a-b
 return {"n":n,"rmse":float(np.sqrt(np.mean(d*d))) if n else None,"mae":float(np.mean(np.abs(d))) if n else None,"max_abs":float(np.max(np.abs(d))) if n else None,"corr":float(np.corrcoef(a,b)[0,1]) if n>1 and np.std(a)>0 and np.std(b)>0 else None}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("browser_json",type=Path);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 rows=json.loads(a.browser_json.read_text());reports=[]
 for r in rows:
  d=r.get("parity_debug")
  if not d:continue
  y,sr=librosa.load(a.wav_dir/r["file"],sr=22050,mono=True);yt,idx=librosa.effects.trim(y,top_db=50);seg=yt[:int(.04*sr)]
  centered=np.pad(seg,(256,256),mode="reflect")
  S=np.abs(librosa.stft(seg,n_fft=512,hop_length=128,center=True,window="hann"))**2\n  # Isolate STFT math from any upstream sample/resample/trim differences by feeding Python the exact JS-centered samples.\n  jcenter=np.asarray(d["centered"],dtype=float)\n  S_from_js_center=np.abs(librosa.stft(jcenter,n_fft=512,hop_length=128,center=False,window="hann"))**2
  M=librosa.feature.melspectrogram(S=S,sr=sr,n_mels=40)
  D=librosa.power_to_db(M)
  C=librosa.feature.mfcc(S=D,n_mfcc=13)
  tr=d["trace"]; jp=np.asarray([x["power"] for x in tr]).T;jm=np.asarray([x["mel"] for x in tr]).T;jd=np.asarray([x["db"] for x in tr]).T;jc=np.asarray([x["mfcc"] for x in tr]).T
  stages={"trimmed_head":st(yt[:1024],d["trimmed_head"]),"segment":st(seg,d["segment"]),"centered":st(centered,d["centered"]),"power":st(S,jp),"power_from_js_center":st(S_from_js_center,jp),"mel":st(M,jm),"db":st(D,jd),"mfcc":st(C,jc)}
  reports.append({"file":r["file"],"librosa_trim_start":int(idx[0]),"librosa_trim_end":int(idx[1]),"stages":stages})
 names=list(reports[0]["stages"]);summary={}
 for n in names:
  vals=[x["stages"][n]["rmse"] for x in reports];summary[n]={"mean_rmse":float(np.mean(vals)),"max_rmse":float(np.max(vals)),"mean_corr":float(np.nanmean([x["stages"][n]["corr"] for x in reports if x["stages"][n]["corr"] is not None]))}
 first=next((n for n in names if summary[n]["mean_rmse"]>1e-5),None)
 out={"recordings":len(reports),"first_divergent_stage":first,"summary":summary,"files":reports};(a.out/"parity.json").write_text(json.dumps(out,indent=2));print(json.dumps({"recordings":len(reports),"first_divergent_stage":first,"summary":summary},indent=2))
if __name__=="__main__":main()
