// 26-feature 0–120 ms MFCC counterpart of run_time_phase_experiment.extract_window.
// Input: mono audio already resampled and trimmed at 22,050 Hz.
const SR = 22050, N = 2048, HOP = 512, MELS = 40, MFCC = 13;
const window = Float64Array.from({ length: N }, (_, i) => .5 - .5 * Math.cos(2 * Math.PI * i / N));
const mel = hz => { const fsp=200/3, min=1000, boundary=min/fsp, step=Math.log(6.4)/27;
  return hz < min ? hz/fsp : boundary + Math.log(hz/min)/step; };
const hz = v => { const fsp=200/3, min=1000, boundary=min/fsp, step=Math.log(6.4)/27;
  return v < boundary ? v*fsp : min*Math.exp(step*(v-boundary)); };
const low=mel(0), high=mel(SR/2), edges=Array.from({length:MELS+2},(_,i)=>hz(low+(high-low)*i/(MELS+1)));
const bank=Array.from({length:MELS},(_,m)=>Float64Array.from({length:N/2+1},(_,k)=>{
  const f=k*SR/N,lower=(f-edges[m])/(edges[m+1]-edges[m]),upper=(edges[m+2]-f)/(edges[m+2]-edges[m+1]);
  return Math.max(0,Math.min(lower,upper))*2/(edges[m+2]-edges[m]);
}));
const dct=Array.from({length:MFCC},(_,j)=>Float64Array.from({length:MELS},(_,m)=>
  Math.cos(Math.PI*j*(2*m+1)/(2*MELS))*(j===0?Math.sqrt(1/MELS):Math.sqrt(2/MELS))));
function power(frame) {
  const re=new Float64Array(N),im=new Float64Array(N);
  for(let i=0;i<N;i++) re[i]=frame[i]*window[i];
  let j=0;for(let i=1;i<N;i++){let bit=N>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j){[re[i],re[j]]=[re[j],re[i]];}}
  for(let len=2;len<=N;len<<=1){const ang=-2*Math.PI/len,wr0=Math.cos(ang),wi0=Math.sin(ang);
    for(let start=0;start<N;start+=len){let wr=1,wi=0;
      for(let k=0;k<len/2;k++){const a=start+k,b=a+len/2,tr=wr*re[b]-wi*im[b],ti=wr*im[b]+wi*re[b];
        re[b]=re[a]-tr;im[b]=im[a]-ti;re[a]+=tr;im[a]+=ti;const next=wr*wr0-wi*wi0;wi=wr*wi0+wi*wr0;wr=next;}}}
  return Float64Array.from({length:N/2+1},(_,k)=>re[k]*re[k]+im[k]*im[k]);
}
export function earlyMfccFusionFeatures(y, sampleRate=SR) {
  if(sampleRate!==SR) throw new Error('Early MFCC requires resampled 22,050 Hz audio');
  let seg=y.slice(0,Math.min(y.length,Math.floor(.12*SR)));
  if(seg.length<128){const padded=new Float32Array(128);padded.set(seg);seg=padded;}
  const melFrames=[];
  for(let center=0;center<=seg.length;center+=HOP){
    const frame=new Float64Array(N);
    for(let i=0;i<N;i++){const pos=center+i-N/2;if(pos>=0&&pos<seg.length)frame[i]=seg[pos];}
    const spec=power(frame),row=new Float64Array(MELS);
    for(let m=0;m<MELS;m++){let sum=0;for(let k=0;k<spec.length;k++)sum+=bank[m][k]*spec[k];row[m]=Math.max(1e-10,sum);}
    melFrames.push(row);
  }
  let maxDb=-Infinity;
  for(const frame of melFrames)for(const v of frame) maxDb=Math.max(maxDb,10*Math.log10(v));
  const coeffs=Array.from({length:MFCC},()=>[]);
  for(const frame of melFrames){const db=Float64Array.from(frame,v=>Math.max(maxDb-80,10*Math.log10(v)));
    for(let j=0;j<MFCC;j++){let sum=0;for(let m=0;m<MELS;m++)sum+=db[m]*dct[j][m];coeffs[j].push(sum);}}
  const result=[];
  for(const values of coeffs){const mean=values.reduce((a,b)=>a+b,0)/values.length;
    const variance=values.reduce((a,b)=>a+(b-mean)**2,0)/values.length;result.push(mean,Math.sqrt(variance));}
  return Float32Array.from(result);
}
