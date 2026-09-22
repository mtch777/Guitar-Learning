// Exact browser counterpart of training/train_full_ringing.py.
//
// Produces the same 107 values, in the same order:
//   2 regions × (13 MFCC mean/std + 5 spectral descriptors × 5 stats)
//   + 5 amplitude/energy features.
//
// Training audio is resampled to 22050 Hz before feature extraction. Live audio
// must therefore be resampled identically before calling extractRingingFeatures.

const TARGET_SR = 22050;
const N_FFT = 2048;
const HOP = 512;
const N_MELS = 128;
const N_MFCC = 13;
const EPS = 1e-12;

const hzToMel = hz => 2595 * Math.log10(1 + hz / 700);
const melToHz = mel => 700 * (10 ** (mel / 2595) - 1);

function percentile(values, q) {
  const a = Array.from(values).sort((x, y) => x - y);
  if (!a.length) return 0;
  const p = (a.length - 1) * q;
  const lo = Math.floor(p), hi = Math.ceil(p);
  return lo === hi ? a[lo] : a[lo] * (hi - p) + a[hi] * (p - lo);
}
function summary(a) {
  const v = Array.from(a);
  const mean = v.reduce((s,x)=>s+x,0) / Math.max(1,v.length);
  const variance = v.reduce((s,x)=>s+(x-mean)**2,0) / Math.max(1,v.length);
  return [mean, Math.sqrt(variance), percentile(v,.25), percentile(v,.5), percentile(v,.75)];
}
function rms(a) {
  if (!a.length) return 0;
  let s=0; for (const x of a) s += x*x;
  return Math.sqrt(s/a.length);
}
const db = x => 20 * Math.log10(Math.max(x, EPS));

export function resampleLinear(input, sourceRate, targetRate=TARGET_SR) {
  if (sourceRate === targetRate) return new Float32Array(input);
  const n = Math.max(1, Math.round(input.length * targetRate / sourceRate));
  const out = new Float32Array(n);
  const scale = sourceRate / targetRate;
  for (let i=0;i<n;i++) {
    const p=i*scale, a=Math.floor(p), b=Math.min(input.length-1,a+1), t=p-a;
    out[i]=(input[a]||0)*(1-t)+(input[b]||0)*t;
  }
  return out;
}

function trimTopDb(y, topDb=50) {
  // librosa.effects.trim uses frame RMS. This mirrors its default frame/hop
  // geometry closely enough for runtime parity while keeping the browser
  // dependency-free.
  if (!y.length) return y;
  const frame=2048, hop=512;
  let peak=0; const levels=[];
  for (let start=0; start<y.length; start+=hop) {
    let s=0;
    for(let i=0;i<frame;i++){const x=y[start+i]||0;s+=x*x;}
    const r=Math.sqrt(s/frame); levels.push(r); peak=Math.max(peak,r);
  }
  const threshold=peak * 10**(-topDb/20);
  let first=0,last=levels.length-1;
  while(first<levels.length && levels[first]<threshold) first++;
  while(last>=first && levels[last]<threshold) last--;
  const start=Math.max(0,first*hop);
  const end=Math.min(y.length,last*hop+frame);
  return y.slice(start,end);
}

function hann(n) {
  const w=new Float64Array(n);
  for(let i=0;i<n;i++) w[i]=0.5-0.5*Math.cos(2*Math.PI*i/n);
  return w;
}
const WINDOW=hann(N_FFT);

function fftMag(frame) {
  const re=new Float64Array(N_FFT), im=new Float64Array(N_FFT);
  for(let i=0;i<N_FFT;i++) re[i]=(frame[i]||0)*WINDOW[i];
  let j=0;
  for(let i=1;i<N_FFT;i++){
    let bit=N_FFT>>1;
    for(;j&bit;bit>>=1) j^=bit;
    j^=bit;
    if(i<j){[re[i],re[j]]=[re[j],re[i]];[im[i],im[j]]=[im[j],im[i]];}
  }
  for(let len=2;len<=N_FFT;len<<=1){
    const ang=-2*Math.PI/len, wr0=Math.cos(ang), wi0=Math.sin(ang);
    for(let i=0;i<N_FFT;i+=len){
      let wr=1,wi=0;
      for(let k=0;k<len/2;k++){
        const u=i+k,v=u+len/2;
        const tr=wr*re[v]-wi*im[v], ti=wr*im[v]+wi*re[v];
        re[v]=re[u]-tr;im[v]=im[u]-ti;re[u]+=tr;im[u]+=ti;
        const nwr=wr*wr0-wi*wi0;wi=wr*wi0+wi*wr0;wr=nwr;
      }
    }
  }
  const m=new Float64Array(N_FFT/2+1);
  for(let i=0;i<m.length;i++) m[i]=Math.hypot(re[i],im[i]);
  return m;
}
function frames(y) {
  const out=[];
  if(!y.length) return [new Float32Array(N_FFT)];
  for(let start=0; start<Math.max(1,y.length); start+=HOP){
    const f=new Float32Array(N_FFT);
    f.set(y.slice(start,Math.min(y.length,start+N_FFT)));
    out.push(f);
    if(start+N_FFT>=y.length) break;
  }
  return out;
}
function melBank(sr) {
  const lo=hzToMel(0), hi=hzToMel(sr/2);
  const hz=Array.from({length:N_MELS+2},(_,i)=>melToHz(lo+(hi-lo)*i/(N_MELS+1)));
  const bins=hz.map(x=>Math.floor((N_FFT+1)*x/sr));
  return Array.from({length:N_MELS},(_,m)=>{
    const w=new Float64Array(N_FFT/2+1);
    const a=bins[m],b=bins[m+1],c=bins[m+2];
    for(let k=a;k<b;k++) if(k<w.length) w[k]=(k-a)/Math.max(1,b-a);
    for(let k=b;k<c;k++) if(k<w.length) w[k]=(c-k)/Math.max(1,c-b);
    return w;
  });
}
function regionFeatures(y,sr) {
  const bank=melBank(sr), specs=frames(y).map(fftMag);
  const centroid=[], bandwidth=[], rolloff=[], flatness=[], zcr=[];
  const mfcc=Array.from({length:N_MFCC},()=>[]);
  for(let fi=0;fi<specs.length;fi++){
    const mag=specs[fi], power=Array.from(mag,x=>x*x);
    let sum=0, weighted=0;
    for(let k=0;k<mag.length;k++){sum+=mag[k];weighted+=mag[k]*(k*sr/N_FFT);}
    const c=sum?weighted/sum:0; centroid.push(c);
    let bw=0; for(let k=0;k<mag.length;k++) bw+=mag[k]*(k*sr/N_FFT-c)**2;
    bandwidth.push(sum?Math.sqrt(bw/sum):0);
    const total=power.reduce((a,b)=>a+b,0), target=.85*total;
    let cum=0,ro=0; for(let k=0;k<power.length;k++){cum+=power[k];if(cum>=target){ro=k*sr/N_FFT;break;}}
    rolloff.push(ro);
    let logsum=0,amsum=0; for(const x of power){logsum+=Math.log(Math.max(x,EPS));amsum+=x;}
    flatness.push(Math.exp(logsum/power.length)/Math.max(amsum/power.length,EPS));
    const fr=frames(y)[fi]; let crossings=0;
    for(let i=1;i<fr.length;i++) if((fr[i-1]>=0)!==(fr[i]>=0)) crossings++;
    zcr.push(crossings/fr.length);
    const mel=bank.map(w=>{let s=0;for(let k=0;k<w.length;k++)s+=power[k]*w[k];return 10*Math.log10(Math.max(s,EPS));});
    for(let q=0;q<N_MFCC;q++){
      let s=0; for(let m=0;m<N_MELS;m++) s+=mel[m]*Math.cos(Math.PI*q*(m+.5)/N_MELS);
      mfcc[q].push(s*Math.sqrt(2/N_MELS));
    }
  }
  const out=[];
  for(let q=0;q<N_MFCC;q++){
    const a=mfcc[q],mean=a.reduce((s,x)=>s+x,0)/a.length;
    const std=Math.sqrt(a.reduce((s,x)=>s+(x-mean)**2,0)/a.length);
    out.push(mean,std);
  }
  for(const d of [centroid,bandwidth,rolloff,flatness,zcr]) out.push(...summary(d));
  return out;
}

export function extractRingingFeatures(samples, sourceRate) {
  let y=trimTopDb(resampleLinear(samples,sourceRate),50);
  const attack=y.slice(0,Math.floor(.12*TARGET_SR));
  let sustain=y.slice(Math.floor(.15*TARGET_SR),Math.min(y.length,Math.floor(.8*TARGET_SR)));
  if(sustain.length<512) sustain=y.slice(Math.min(Math.floor(y.length/2),Math.floor(.12*TARGET_SR)));
  const values=[...regionFeatures(attack,TARGET_SR),...regionFeatures(sustain,TARGET_SR)];
  const n50=Math.min(y.length,Math.floor(.05*TARGET_SR));
  const n100=Math.min(y.length,Math.floor(.10*TARGET_SR));
  let peak=0; for(const x of attack) peak=Math.max(peak,Math.abs(x));
  let energy100=0; for(const x of y.slice(0,n100)) energy100+=x*x;
  values.push(db(peak),db(rms(y.slice(0,n50))),db(rms(y.slice(0,n100))),energy100,db(rms(y)));
  if(values.length!==107) throw new Error(`Expected 107 features, got ${values.length}`);
  return Float32Array.from(values);
}

export const RINGING_FEATURE_COUNT=107;
