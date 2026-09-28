#!/usr/bin/env python3
"""Step 18 numerical JS↔librosa parity harness. Compares preprocessing and MFCC checkpoints."""
import argparse,json
from pathlib import Path
import librosa,numpy as np
def stats(a,b):
 a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel();n=min(len(a),len(b));a=a[:n];b=b[:n];d=a-b
 return {"n":n,"max_abs":float(np.max(np.abs(d))) if n else None,"mae":float(np.mean(np.abs(d))) if n else None,"rmse":float(np.sqrt(np.mean(d*d))) if n else None,"corr":float(np.corrcoef(a,b)[0,1]) if n>1 and np.std(a)>0 and np.std(b)>0 else None}
def mfcc26(y,sr,t0,t1):
 a=int(t0*sr);b=min(len(y),max(a+1,int(t1*sr)));seg=y[a:b]
 if len(seg)<128:seg=np.pad(seg,(0,128-len(seg)))
 nfft=max(64,2**int(np.floor(np.log2(len(seg)))));nfft=min(2048,nfft,len(seg));hop=max(16,nfft//4);n_mels=min(40,max(16,nfft//8))
 m=librosa.feature.mfcc(y=seg,sr=sr,n_mfcc=13,n_fft=nfft,hop_length=hop,n_mels=n_mels)
 return np.asarray([v for i in range(13) for v in (np.mean(m[i]),np.std(m[i]))],float)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("wav_dir",type=Path);ap.add_argument("browser_json",type=Path);ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 rows=json.loads(a.browser_json.read_text()); report={"files":[]}
 for r in rows:
  p=a.wav_dir/r["file"]; y0,sr0=librosa.load(p,sr=None,mono=True); y,sr=librosa.load(p,sr=22050,mono=True);yt,idx=librosa.effects.trim(y,top_db=50)
  frames=[mfcc26(yt,sr,x,x+.04) for x in (0,.04,.08)]
  item={"file":r["file"],"source_sr":sr0,"librosa_trim_start":int(idx[0]),"librosa_trim_end":int(idx[1]),"librosa_trim_len":len(yt),"mfcc":[stats(frames[i],r["features"][i]) for i in range(3)]}
  report["files"].append(item)
 allrm=[x["rmse"] for z in report["files"] for x in z["mfcc"]]; allma=[x["max_abs"] for z in report["files"] for x in z["mfcc"]]
 report["summary"]={"recordings":len(rows),"mfcc_frame_rmse_mean":float(np.mean(allrm)),"mfcc_frame_rmse_max":float(np.max(allrm)),"mfcc_max_abs_max":float(np.max(allma))}
 (a.out/"parity.json").write_text(json.dumps(report,indent=2));print(json.dumps(report["summary"],indent=2))
if __name__=="__main__":main()
