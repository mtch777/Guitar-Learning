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
  // Match librosa.effects.trim defaults:
  // frame_length=2048, hop_length=512, ref=np.max, center=True RMS with
  // constant-zero padding. Non-silent frame indices are converted back to
  // sample boundaries exactly as librosa does.
  if (!y.length) return y;
  const frame=2048, hop=512, pad=frame>>1;
  const frameCount=1+Math.floor((y.length+2*pad-frame)/hop);
  const rmsLevels=new Float64Array(Math.max(1,frameCount));
  let peakRms=0;

  for(let fi=0;fi<rmsLevels.length;fi++){
    const start=fi*hop-pad;
    let sum=0;
    for(let i=0;i<frame;i++){
      const idx=start+i;
      const x=(idx>=0 && idx<y.length) ? y[idx] : 0;
      sum+=x*x;
    }
    const level=Math.sqrt(sum/frame);
    rmsLevels[fi]=level;
    if(level>peakRms) peakRms=level;
  }

  if(peakRms<=0) return y.slice(0,0);
  const thresholdDb=-topDb;
  let first=-1,last=-1;
  for(let i=0;i<rmsLevels.length;i++){
    const relDb=20*Math.log10(Math.max(rmsLevels[i],1e-10)/peakRms);
    if(relDb>thresholdDb){
      if(first<0) first=i;
      last=i;
    }
  }
  if(first<0) return y.slice(0,0);

  const startSample=Math.min(y.length,Math.max(0,first*hop));
  const endSample=Math.min(y.length,(last+1)*hop);
  return y.slice(startSample,endSample);
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
  // librosa STFT defaults: center=true, pad_mode="constant".
  const out=[];
  if(!y.length) return [new Float32Array(N_FFT)];
  const pad=N_FFT>>1;
  const paddedLength=y.length+2*pad;
  for(let start=0; start+N_FFT<=paddedLength; start+=HOP){
    const f=new Float32Array(N_FFT);
    for(let i=0;i<N_FFT;i++){
      const source=start+i-pad;
      f[i]=(source>=0 && source<y.length) ? y[source] : 0;
    }
    out.push(f);
  }
  return out.length ? out : [new Float32Array(N_FFT)];
}
function hzToMelSlaney(hz) {
  const fSp=200/3;
  const minLogHz=1000;
  const minLogMel=minLogHz/fSp;
  const logstep=Math.log(6.4)/27;
  return hz < minLogHz
    ? hz/fSp
    : minLogMel + Math.log(hz/minLogHz)/logstep;
}
function melToHzSlaney(mel) {
  const fSp=200/3;
  const minLogHz=1000;
  const minLogMel=minLogHz/fSp;
  const logstep=Math.log(6.4)/27;
  return mel < minLogMel
    ? fSp*mel
    : minLogHz*Math.exp(logstep*(mel-minLogMel));
}
function melBank(sr) {
  // librosa.filters.mel defaults: htk=False, norm="slaney".
  const lo=hzToMelSlaney(0), hi=hzToMelSlaney(sr/2);
  const edges=Array.from(
    {length:N_MELS+2},
    (_,i)=>melToHzSlaney(lo+(hi-lo)*i/(N_MELS+1))
  );
  const fftFreq=Array.from({length:N_FFT/2+1},(_,k)=>k*sr/N_FFT);
  return Array.from({length:N_MELS},(_,m)=>{
    const w=new Float64Array(N_FFT/2+1);
    const lower=edges[m], center=edges[m+1], upper=edges[m+2];
    const enorm=2/Math.max(EPS,upper-lower);
    for(let k=0;k<w.length;k++){
      const f=fftFreq[k];
      const lowerSlope=(f-lower)/Math.max(EPS,center-lower);
      const upperSlope=(upper-f)/Math.max(EPS,upper-center);
      w[k]=Math.max(0,Math.min(lowerSlope,upperSlope))*enorm;
    }
    return w;
  });
}
function regionFeatures(y,sr) {
  const bank=melBank(sr), timeFrames=frames(y), specs=timeFrames.map(fftMag);
  const centroid=[], bandwidth=[], rolloff=[], flatness=[], zcr=[];
  const mfcc=Array.from({length:N_MFCC},()=>[]);
  for(let fi=0;fi<specs.length;fi++){
    const mag=specs[fi], power=Array.from(mag,x=>x*x);
    let sum=0, weighted=0;
    for(let k=0;k<mag.length;k++){sum+=mag[k];weighted+=mag[k]*(k*sr/N_FFT);}
    const c=sum?weighted/sum:0; centroid.push(c);
    let bw=0; for(let k=0;k<mag.length;k++) bw+=mag[k]*(k*sr/N_FFT-c)**2;
    bandwidth.push(sum?Math.sqrt(bw/sum):0);
    // librosa.feature.spectral_rolloff(y=...) operates on magnitude S.
    const total=mag.reduce((a,b)=>a+b,0), target=.85*total;
    let cum=0,ro=0; for(let k=0;k<mag.length;k++){cum+=mag[k];if(cum>=target){ro=k*sr/N_FFT;break;}}
    rolloff.push(ro);
    // librosa.feature.spectral_flatness defaults to power=2 and amin=1e-10.
    let logsum=0,amsum=0;
    for(const x of power){
      const floored=Math.max(x,1e-10);
      logsum+=Math.log(floored);
      amsum+=floored;
    }
    flatness.push(Math.exp(logsum/power.length)/(amsum/power.length));
    // librosa.feature.zero_crossing_rate centers with edge-value padding,
    // unlike STFT-based descriptors which use constant-zero padding.
    const zStart=fi*HOP-(N_FFT>>1);
    let crossings=0;
    let prev=null;
    for(let i=0;i<N_FFT;i++){
      const source=Math.max(0,Math.min(y.length-1,zStart+i));
      const value=y[source] || 0;
      if(prev!==null && ((prev>=0)!==(value>=0))) crossings++;
      prev=value;
    }
    zcr.push(crossings/N_FFT);
    // Store mel power now; librosa's dB conversion is applied after the full
    // mel spectrogram is known (ref=max, amin=1e-10, top_db=80).
    const melPower=bank.map(w=>{
      let s=0;
      for(let k=0;k<w.length;k++) s+=power[k]*w[k];
      return s;
    });
    mfcc._melPower ??= [];
    mfcc._melPower.push(melPower);
  }
  const allMel=mfcc._melPower || [];
  let maxDb=-Infinity;
  const rawDb=allMel.map(frameMel=>frameMel.map(x=>{
    const value=10*Math.log10(Math.max(x,1e-10)); // ref=1.0
    if(value>maxDb) maxDb=value;
    return value;
  }));
  const minDb=maxDb-80;
  for(const melDbRaw of rawDb){
    const melDb=melDbRaw.map(x=>Math.max(minDb,x));
    for(let q=0;q<N_MFCC;q++){
      let s=0;
      for(let m=0;m<N_MELS;m++) s+=melDb[m]*Math.cos(Math.PI*q*(m+.5)/N_MELS);
      const norm=q===0 ? Math.sqrt(1/N_MELS) : Math.sqrt(2/N_MELS);
      mfcc[q].push(s*norm);
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
