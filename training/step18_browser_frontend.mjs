#!/usr/bin/env node
// Step 18 browser-compatible audio front end.
// Runs the same JS YIN + MFCC extraction that can be used in the live site.
import fs from "node:fs";
import path from "node:path";
import Meyda from "meyda";


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
function midi(hz){return Number.isFinite(hz)&&hz>0?Math.round(69+12*Math.log2(hz/440)):null}
function trim(y,topDb=50){
  let peak=0;for(const x of y)peak=Math.max(peak,Math.abs(x));if(!peak)return y;
  const th=peak*Math.pow(10,-topDb/20);let a=0,b=y.length;while(a<b&&Math.abs(y[a])<th)a++;while(b>a&&Math.abs(y[b-1])<th)b--;
  return y.slice(a,b);
}
function reflectPad(seg,pad){
  const out=new Float32Array(seg.length+2*pad);out.set(seg,pad);
  for(let i=0;i<pad;i++){
    out[pad-1-i]=seg[Math.min(seg.length-1,i+1)];
    out[pad+seg.length+i]=seg[Math.max(0,seg.length-2-i)];
  }
  return out;
}
function mfcc26(seg,sr){
  // Match training/run_temporal_aggregation.py for a 40 ms (882-sample) frame:
  // n_fft=512, hop=128, n_mels=40, n_mfcc=13, librosa center=True.
  const bs=512,hop=128,frames=[];
  if(seg.length<128){const z=new Float32Array(128);z.set(seg);seg=z}
  const centered=reflectPad(seg,bs>>1);
  for(let start=0;start+bs<=centered.length;start+=hop){
    const frame=centered.slice(start,start+bs);
    const m=Meyda.extract("mfcc",frame,{sampleRate:sr,bufferSize:bs,melBands:40,numberOfMFCCCoefficients:13});
    if(m&&m.length===13&&m.every(Number.isFinite))frames.push(m);
  }
  if(!frames.length)frames.push(new Array(13).fill(0));
  const out=[];for(let j=0;j<13;j++){const v=frames.map(x=>x[j]),mean=v.reduce((a,b)=>a+b,0)/v.length;let q=0;for(const x of v)q+=(x-mean)**2;out.push(mean,Math.sqrt(q/v.length))}
  return out;
}
function resampleLinear(input,inRate,outRate=22050){
  if(inRate===outRate)return input;const n=Math.max(1,Math.round(input.length*outRate/inRate)),out=new Float32Array(n),ratio=inRate/outRate;
  for(let i=0;i<n;i++){const p=i*ratio,j=Math.floor(p),f=p-j,a=input[Math.min(j,input.length-1)],b=input[Math.min(j+1,input.length-1)];out[i]=a+(b-a)*f}return out;
}
const args=process.argv.slice(2),dir=args[0],out=args[1],smoke=args.includes("--smoke");
if(!dir||!out)throw new Error("usage: node step18_browser_frontend.mjs WAV_DIR OUT_JSON [--smoke]");
const files=fs.readdirSync(dir).filter(x=>RX.test(x)).sort(),rows=[];let done=0;
for(const name of files){
  const m=name.match(RX),s=+m[1],f=+m[2],strength=m[3].toLowerCase(),truth=OPEN[s]+f;
  if(smoke&&!(truth>=54&&truth<=60&&strength==="normal"))continue;
  const fileBuffer=fs.readFileSync(path.join(dir,name));
  const raw=decodeWav(fileBuffer),mono=raw.channelData[0];
  const y=trim(resampleLinear(mono,raw.sampleRate,22050)),sr=22050;
  const t0=performance.now(),p=yin(y.slice(0,Math.min(y.length,Math.round(.24*sr))),sr),pitchMs=performance.now()-t0;
  const feats=[];let featureMs=0;
  for(const [a,b] of [[0,.04],[.04,.08],[.08,.12]]){const q=performance.now();feats.push(mfcc26(y.slice(Math.round(a*sr),Math.round(b*sr)),sr));featureMs+=performance.now()-q}
  rows.push({file:name,string:s,fret:f,strength,true_midi:truth,pred_midi:midi(p.frequency),pitch_hz:p.frequency,pitch_confidence:p.confidence,pitch_runtime_ms:pitchMs,feature_runtime_ms:featureMs,features:feats});
  done++;if(done===1||done%25===0)console.log("BROWSER EXTRACT ["+done+"]");
}
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(rows));
console.log("WROTE",rows.length,out);
