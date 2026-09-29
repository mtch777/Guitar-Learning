#!/usr/bin/env node
// Step 18 browser-compatible audio front end.
// Runs the same JS YIN + MFCC extraction that can be used in the live site.
import fs from "node:fs";
import path from "node:path";



const OPEN={1:27,2:34,3:39,4:44,5:49,6:54,7:58,8:63};
const RX=/s(\d+)_f(\d+)_(soft|normal|hard)_ringing\.wav$/i;
const MIN_FREQ=35,MAX_FREQ=1600;
function decodeWav(buf){
  if(buf.toString("ascii",0,4)!=="RIFF"||buf.toString("ascii",8,12)!=="WAVE")throw new Error("Not RIFF/WAVE");
  let pos=12,fmt=null,dataOff=-1,dataLen=0;
  while(pos+8<=buf.length){
    const id=buf.toString("ascii",pos,pos+4),len=buf.readUInt32LE(pos+4),off=pos+8;
    if(id==="fmt ") fmt={format:buf.readUInt16LE(off),channels:buf.readUInt16LE(off+2),sampleRate:buf.readUInt32LE(off+4),bits:buf.readUInt16LE(off+14)};
    if(id==="data"){dataOff=off;dataLen=Math.min(len,buf.length-off);break}
    pos=off+len+(len&1);
  }
  if(!fmt||dataOff<0)throw new Error("Missing WAV fmt/data");
  const bytes=fmt.bits/8,frames=Math.floor(dataLen/(bytes*fmt.channels)),channels=Array.from({length:fmt.channels},()=>new Float32Array(frames));
  for(let i=0;i<frames;i++)for(let ch=0;ch<fmt.channels;ch++){
    const o=dataOff+(i*fmt.channels+ch)*bytes;let v;
    if(fmt.format===3&&fmt.bits===32)v=buf.readFloatLE(o);
    else if(fmt.format===1&&fmt.bits===16)v=buf.readInt16LE(o)/32768;
    else if(fmt.format===1&&fmt.bits===24){v=buf.readIntLE(o,3)/8388608}
    else if(fmt.format===1&&fmt.bits===32)v=buf.readInt32LE(o)/2147483648;
    else throw new Error("Unsupported WAV format "+fmt.format+"/"+fmt.bits);
    channels[ch][i]=v;
  }
  return {sampleRate:fmt.sampleRate,channelData:channels};
}


function rms(y){let s=0;for(const x of y)s+=x*x;return Math.sqrt(s/y.length)}
function parabolic(a,i){if(i<=0||i>=a.length-1)return i;const A=a[i-1],b=a[i],c=a[i+1],d=A-2*b+c;return Math.abs(d)<1e-12?i:i+.5*(A-c)/d}
function yin(y,sr,threshold=.18){
  const r=rms(y);if(r<1e-4)return {frequency:NaN,confidence:0};
  const lo=Math.max(2,Math.floor(sr/MAX_FREQ)),hi=Math.min(Math.floor(sr/MIN_FREQ),Math.floor(y.length/2));
  if(hi<=lo+2)return {frequency:NaN,confidence:0};
  const d=new Float64Array(hi+1),cm=new Float64Array(hi+1);cm.fill(1);
  for(let t=1;t<=hi;t++){let s=0;for(let i=0;i<y.length-t;i++){const z=y[i]-y[i+t];s+=z*z}d[t]=s}
  let run=0;for(let t=1;t<=hi;t++){run+=d[t];cm[t]=run>0?d[t]*t/run:1}
  let tau=-1;for(let t=lo;t<hi;t++)if(cm[t]<threshold&&cm[t]<=cm[t+1]){tau=t;break}
  if(tau<0){tau=lo;for(let t=lo+1;t<=hi;t++)if(cm[t]<cm[tau])tau=t}
  const pt=parabolic(cm,tau);return {frequency:pt>0?sr/pt:NaN,confidence:Math.max(0,Math.min(1,1-cm[tau]))}
}
// Opt-in reproduction of the Step-9 librosa YIN240 decision: 4096-sample
// centered zero-padded frames, 1024 hop, 0.1 trough threshold, median F0.
function yinReference(y,sr){
  if(!y.length)return {frequency:NaN,confidence:0};
  const n=4096,hop=n>>2,minP=Math.floor(sr/MAX_FREQ),maxP=Math.min(Math.ceil(sr/MIN_FREQ),n-1);
  const frequencies=[],confidences=[];
  for(let start=0;start<=y.length;start+=hop){
    const frame=new Float64Array(n);
    for(let t=0;t<n;t++){const i=start+t-(n>>1);if(i>=0&&i<y.length)frame[t]=y[i]}
    let energy=0;for(const v of frame)energy+=v*v;
    const cm=new Float64Array(maxP+1);let head=0,run=0;
    for(let lag=1;lag<=maxP;lag++){
      head+=frame[lag-1]*frame[lag-1];
      let acf=0;for(let t=0;t<n-lag;t++)acf+=frame[t]*frame[t+lag];
      const d=2*(energy-acf)-head;run+=d;cm[lag]=d*lag/(run+Number.MIN_VALUE);
    }
    let best=minP;
    for(let lag=minP+1;lag<=maxP;lag++)if(cm[lag]<cm[best])best=lag;
    let selected=best;
    for(let lag=minP;lag<=maxP;lag++){
      const trough=lag===minP?cm[lag]<cm[lag+1]:lag===maxP?cm[lag]<cm[lag-1]:cm[lag]<cm[lag-1]&&cm[lag]<=cm[lag+1];
      if(trough&&cm[lag]<.1){selected=lag;break}
    }
    let shift=0;
    if(selected>minP&&selected<maxP){
      const a=cm[selected+1]+cm[selected-1]-2*cm[selected],b=(cm[selected+1]-cm[selected-1])/2;
      if(Math.abs(b)<Math.abs(a))shift=-b/a;
    }
    frequencies.push(sr/(selected+shift));
    confidences.push(Math.max(0,Math.min(1,1-cm[selected])));
  }
  frequencies.sort((a,b)=>a-b);confidences.sort((a,b)=>a-b);
  const middle=Math.floor(frequencies.length/2),median=a=>a.length%2?a[middle]:(a[middle-1]+a[middle])/2;
  return {frequency:median(frequencies),confidence:median(confidences)};
}
function midi(hz){return Number.isFinite(hz)&&hz>0?Math.round(69+12*Math.log2(hz/440)):null}
function trim(y,topDb=50,frameLength=2048,hopLength=512){
  // Match librosa.effects.trim(top_db=50): frame RMS, centered with constant padding,
  // threshold relative to max frame RMS, then convert first/last non-silent frames to samples.
  const pad=Math.floor(frameLength/2), nFrames=1+Math.floor((y.length+2*pad-frameLength)/hopLength);
  const rmsFrames=new Float64Array(Math.max(0,nFrames)); let maxRms=0;
  for(let fi=0;fi<nFrames;fi++){
    const start=fi*hopLength-pad; let ss=0;
    for(let j=0;j<frameLength;j++){const ix=start+j,x=(ix>=0&&ix<y.length)?y[ix]:0;ss+=x*x}
    const r=Math.sqrt(ss/frameLength);rmsFrames[fi]=r;if(r>maxRms)maxRms=r;
  }
  if(!rmsFrames.length||maxRms<=0)return y.slice();
  const threshold=maxRms*Math.pow(10,-topDb/20);let first=0,last=rmsFrames.length-1;
  while(first<rmsFrames.length&&rmsFrames[first]<threshold)first++;
  if(first===rmsFrames.length)return y.slice(0,0);
  while(last>=first&&rmsFrames[last]<threshold)last--;
  const a=Math.min(y.length,first*hopLength),b=Math.min(y.length,(last+1)*hopLength);
  return y.slice(a,b);
}
function reflectPad(seg,pad){
  const out=new Float64Array(seg.length+2*pad);out.set(seg,pad);
  for(let i=0;i<pad;i++){out[pad-1-i]=seg[Math.min(seg.length-1,i+1)];out[pad+seg.length+i]=seg[Math.max(0,seg.length-2-i)]}
  return out;
}
const hzToMelSlaney=f=>{const fsp=200/3,minLogHz=1000,minLogMel=minLogHz/fsp,logstep=Math.log(6.4)/27;return f<minLogHz?f/fsp:minLogMel+Math.log(f/minLogHz)/logstep};
const melToHzSlaney=m=>{const fsp=200/3,minLogHz=1000,minLogMel=minLogHz/fsp,logstep=Math.log(6.4)/27;return m<minLogMel?fsp*m:minLogHz*Math.exp(logstep*(m-minLogMel))};
function melBasis(sr,nfft,nmels){
  const fftfreq=Array.from({length:nfft/2+1},(_,i)=>i*sr/nfft),m0=hzToMelSlaney(0),m1=hzToMelSlaney(sr/2);
  const hz=Array.from({length:nmels+2},(_,i)=>melToHzSlaney(m0+(m1-m0)*i/(nmels+1))),out=[];
  for(let m=0;m<nmels;m++){const row=new Float64Array(fftfreq.length),enorm=2/(hz[m+2]-hz[m]);
    for(let k=0;k<fftfreq.length;k++)row[k]=Math.max(0,Math.min((fftfreq[k]-hz[m])/(hz[m+1]-hz[m]),(hz[m+2]-fftfreq[k])/(hz[m+2]-hz[m+1])))*enorm;
    out.push(row);
  } return out;
}
function powerSpectrumDft(frame){
  const n=frame.length,out=new Float64Array(n/2+1);
  for(let k=0;k<=n/2;k++){let re=0,im=0;for(let t=0;t<n;t++){const w=.5-.5*Math.cos(2*Math.PI*t/n),x=frame[t]*w,a=-2*Math.PI*k*t/n;re+=x*Math.cos(a);im+=x*Math.sin(a)}out[k]=re*re+im*im}
  return out;
}
const HANN512=Float64Array.from({length:512},(_,i)=>.5-.5*Math.cos(2*Math.PI*i/512));
function powerSpectrumFft(frame){
  const n=frame.length,re=new Float64Array(n),im=new Float64Array(n);
  for(let i=0;i<n;i++)re[i]=frame[i]*HANN512[i];
  let j=0;
  for(let i=1;i<n;i++){
    let bit=n>>1;
    for(;j&bit;bit>>=1)j^=bit;
    j^=bit;
    if(i<j){[re[i],re[j]]=[re[j],re[i]];[im[i],im[j]]=[im[j],im[i]]}
  }
  for(let len=2;len<=n;len<<=1){
    const ang=-2*Math.PI/len,wr0=Math.cos(ang),wi0=Math.sin(ang);
    for(let i=0;i<n;i+=len){
      let wr=1,wi=0;
      for(let k=0;k<len/2;k++){
        const u=i+k,v=u+len/2,tr=wr*re[v]-wi*im[v],ti=wr*im[v]+wi*re[v];
        re[v]=re[u]-tr;im[v]=im[u]-ti;re[u]+=tr;im[u]+=ti;
        const next=wr*wr0-wi*wi0;wi=wr*wi0+wi*wr0;wr=next;
      }
    }
  }
  const out=new Float64Array(n/2+1);
  for(let k=0;k<out.length;k++)out[k]=re[k]*re[k]+im[k]*im[k];
  return out;
}
const MEL512=melBasis(22050,512,40);
function mfcc26(seg,sr,debug=false,globalDbFloor=false,constantPad=false,fft=false){
  const nfft=512,hop=128,nmels=40,nmfcc=13,centered=constantPad?new Float64Array(seg.length+nfft):reflectPad(seg,nfft>>1),frames=[],trace=[],spectra=[],melFrames=[];
  if(constantPad)centered.set(seg,nfft>>1);
  for(let start=0;start+nfft<=centered.length;start+=hop){
    const p=(fft?powerSpectrumFft:powerSpectrumDft)(centered.slice(start,start+nfft)),mel=new Float64Array(nmels);
    for(let m=0;m<nmels;m++){let s=0;for(let k=0;k<p.length;k++)s+=MEL512[m][k]*p[k];mel[m]=Math.max(1e-10,s)}
    spectra.push(p);melFrames.push(mel);
  }
  let globalMax=0;if(globalDbFloor)for(const mel of melFrames)for(const v of mel)globalMax=Math.max(globalMax,v);
  for(let fi=0;fi<melFrames.length;fi++){
    const mel=melFrames[fi],p=spectra[fi];let mx=globalDbFloor?globalMax:0;
    if(!globalDbFloor)for(const v of mel)mx=Math.max(mx,v);
    const floor=Math.max(1e-10,mx*1e-8),db=Array.from(mel,v=>10*Math.log10(Math.max(floor,v)));
    const mf=new Float64Array(nmfcc);for(let j=0;j<nmfcc;j++){let s=0;for(let m=0;m<nmels;m++)s+=db[m]*Math.cos(Math.PI*j*(2*m+1)/(2*nmels));mf[j]=s*(j===0?Math.sqrt(1/nmels):Math.sqrt(2/nmels))}
    frames.push(mf); if(debug)trace.push({power:Array.from(p),mel:Array.from(mel),db:Array.from(db),mfcc:Array.from(mf)});
  }
  const out=[];for(let j=0;j<nmfcc;j++){const v=frames.map(x=>x[j]),mean=v.reduce((x,y)=>x+y,0)/v.length;let q=0;for(const x of v)q+=(x-mean)**2;out.push(mean,Math.sqrt(q/v.length))}return debug?{features:out,centered:Array.from(centered),trace}:out;
}
function resampleLinear(input,inRate,outRate=22050){
  if(inRate===outRate)return input;const n=Math.max(1,Math.round(input.length*outRate/inRate)),out=new Float32Array(n),ratio=inRate/outRate;
  for(let i=0;i<n;i++){const p=i*ratio,j=Math.floor(p),f=p-j,a=input[Math.min(j,input.length-1)],b=input[Math.min(j+1,input.length-1)];out[i]=a+(b-a)*f}return out;
}
const args=process.argv.slice(2),dir=args[0],out=args[1],smoke=args.includes("--smoke"),debug=args.includes("--debug"),globalDbFloor=args.includes("--global-db-floor"),constantPad=args.includes("--constant-pad"),referenceYin=args.includes("--reference-yin"),compareYin=args.includes("--compare-yin"),compareFft=args.includes("--compare-fft"),fft=!args.includes("--dft");
if(!dir||!out)throw new Error("usage: node step18_browser_frontend.mjs WAV_DIR OUT_JSON [--smoke]");
const files=fs.readdirSync(dir).filter(x=>RX.test(x)).sort(),rows=[];let done=0;
for(const name of files){
  const m=name.match(RX),s=+m[1],f=+m[2],strength=m[3].toLowerCase(),truth=OPEN[s]+f;
  if(smoke&&!(truth>=54&&truth<=60&&strength==="normal"))continue;
  const fileBuffer=fs.readFileSync(path.join(dir,name));
  const raw=decodeWav(fileBuffer),mono=raw.channelData[0];
  const resampled=resampleLinear(mono,raw.sampleRate,22050),y=trim(resampled),sr=22050;
  const pitchInput=y.slice(0,Math.min(y.length,Math.round(.24*sr)));
  let p,pitchMs,baseline=null;
  if(compareYin){
    const timed=fn=>{const t=performance.now(),value=fn(pitchInput,sr);return {value,ms:performance.now()-t}};
    let reference;
    if(done%2===0){baseline=timed(yin);reference=timed(yinReference)}
    else{reference=timed(yinReference);baseline=timed(yin)}
    p=reference.value;pitchMs=reference.ms;
  }else{const t=performance.now();p=(referenceYin?yinReference:yin)(pitchInput,sr);pitchMs=performance.now()-t}
  const feats=[];let featureMs=0,parityDebug=null,baselineFeatures=[],baselineFeatureMs=0,maxPowerAbsDiff=0;
  for(const [fi,[a,b]] of [[0,.04],[.04,.08],[.08,.12]].entries()){
    const seg=y.slice(Math.round(a*sr),Math.round(b*sr));
    let z,q;
    if(compareFft){
      const run=(useFft,withDebug)=>{const start=performance.now(),value=mfcc26(seg,sr,withDebug,globalDbFloor,constantPad,useFft);return {value,ms:performance.now()-start}};
      let baseline,fast;
      if((done+fi)%2===0){baseline=run(false,debug&&fi===0);fast=run(true,debug&&fi===0)}
      else{fast=run(true,debug&&fi===0);baseline=run(false,debug&&fi===0)}
      baselineFeatures.push(debug&&fi===0?baseline.value.features:baseline.value);
      baselineFeatureMs+=baseline.ms;z=fast.value;q=fast.ms;
      if(debug&&fi===0){
        for(let frame=0;frame<z.trace.length;frame++)for(let bin=0;bin<z.trace[frame].power.length;bin++)
          maxPowerAbsDiff=Math.max(maxPowerAbsDiff,Math.abs(z.trace[frame].power[bin]-baseline.value.trace[frame].power[bin]));
      }
    }else{const start=performance.now();z=mfcc26(seg,sr,debug&&fi===0,globalDbFloor,constantPad,fft);q=performance.now()-start}
    if(debug&&fi===0){parityDebug={source_sample_rate:raw.sampleRate,resampled_head:Array.from(resampled.slice(0,2048)),trimmed_head:Array.from(y.slice(0,1024)),segment:Array.from(seg),centered:z.centered,trace:z.trace};feats.push(z.features)}else feats.push(z);
    featureMs+=q;
  }
  rows.push({file:name,string:s,fret:f,strength,true_midi:truth,pred_midi:midi(p.frequency),pitch_hz:p.frequency,pitch_confidence:p.confidence,pitch_runtime_ms:pitchMs,feature_runtime_ms:featureMs,features:feats,...(compareFft?{baseline_features:baselineFeatures,baseline_feature_runtime_ms:baselineFeatureMs,max_power_abs_diff:maxPowerAbsDiff}:{}),...(baseline?{baseline_pred_midi:midi(baseline.value.frequency),baseline_pitch_hz:baseline.value.frequency,baseline_pitch_confidence:baseline.value.confidence,baseline_pitch_runtime_ms:baseline.ms}:{}),...(parityDebug?{parity_debug:parityDebug}:{})});
  done++;if(done===1||done%25===0)console.log("BROWSER EXTRACT ["+done+"]");
}
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(rows));
console.log("WROTE",rows.length,out);
