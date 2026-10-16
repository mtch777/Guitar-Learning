// Private generated music stays in the browser; nothing is uploaded to a server.
export function validateBundle(bundle){
  if(bundle?.format!=='composition-private-review-v1'||!bundle.manifest?.version||!Array.isArray(bundle.manifest.cases))throw new Error('Not a private composition review bundle');
  const cases=bundle.manifest.cases;
  if(bundle.manifest.ratingMetrics){
    const allowed=new Set(['coherence','melody','harmony','phrasing','holds','resolution','playability']);
    const keys=bundle.manifest.ratingMetrics.map(m=>m[0]);
    if(new Set(keys).size!==keys.length||!keys.includes('coherence')||bundle.manifest.ratingMetrics.some(([k,label])=>!allowed.has(k)||typeof label!=='string'||label.length>80))throw new Error('Invalid review questions');
  }
  if(!cases.length||cases.length>100)throw new Error('Unsupported review size');
  const ids=new Set();
  for(const c of cases){
    if(ids.has(c.id)||!['cloud','sweet'].includes(c.family))throw new Error('Duplicate sketch or unknown study');ids.add(c.id);
    for(const name of [c.audio,c.roll,c.gp])if(!/^[a-zA-Z0-9_.-]+$/.test(name))throw new Error('Unsafe asset name');
    const media=bundle.media?.[c.id];
    if(!media||typeof media.gpBase64!=='string'||media.gpBase64.length>5000000||!Array.isArray(media.notes))throw new Error('Missing generated media');
    if(!(c.seconds>0&&c.seconds<=600)||media.notes.length>20000)throw new Error('Unsupported media duration');
    for(const n of media.notes)if(!Number.isFinite(n.start)||!Number.isFinite(n.end)||n.start<0||n.end<n.start||n.end>c.seconds+.01||!Number.isInteger(n.pitch)||n.pitch<0||n.pitch>127||!Number.isFinite(n.velocity)||n.velocity<0||n.velocity>127||!Number.isInteger(n.part)||n.part<0||n.part>15)throw new Error('Invalid generated note');
  }
  return bundle;
}

export function synthesizeWav(notes,seconds,rate=22050){
  const samples=new Float32Array(Math.ceil(seconds*rate));
  for(const n of notes){
    const start=Math.floor(n.start*rate),end=Math.min(samples.length,Math.ceil(n.end*rate)),duration=n.end-n.start;
    const frequency=440*2**((n.pitch-69)/12),gain=.035*n.velocity/127;
    for(let i=start;i<end;i++){
      const t=(i-start)/rate,envelope=Math.max(0,Math.min(1,t/.008)*Math.min(1,(duration-t)/.04));
      samples[i]+=Math.sin(2*Math.PI*frequency*t)*envelope*gain;
    }
  }
  const buffer=new ArrayBuffer(44+samples.length*2),view=new DataView(buffer);
  const text=(at,s)=>{for(let i=0;i<s.length;i++)view.setUint8(at+i,s.charCodeAt(i));};
  text(0,'RIFF');view.setUint32(4,buffer.byteLength-8,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,samples.length*2,true);
  for(let i=0;i<samples.length;i++)view.setInt16(44+i*2,Math.round(Math.max(-1,Math.min(1,samples[i]))*32767),true);
  return buffer;
}

export async function preparePrivateMedia(input){
  const bundle=validateBundle(input),urls=new Map(),audio=new Map(),byAudio=new Map();
  for(const c of bundle.manifest.cases){
    const media=bundle.media[c.id],bytes=Uint8Array.from(atob(media.gpBase64),s=>s.charCodeAt(0));
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(hash!==c.gpSha256)throw new Error('Generated GP checksum mismatch');
    urls.set(c.gp,URL.createObjectURL(new Blob([bytes],{type:'application/octet-stream'})));
    urls.set(c.roll,URL.createObjectURL(new Blob([JSON.stringify({duration:c.seconds,notes:media.notes})],{type:'application/json'})));
    byAudio.set(c.audio,{notes:media.notes,seconds:c.seconds});
  }
  return {manifest:bundle.manifest,asset:name=>urls.get(name),
    audio:async name=>{
      if(!audio.has(name)){
        const item=byAudio.get(name);if(!item)throw new Error('Missing local preview');
        await new Promise(resolve=>setTimeout(resolve,0));
        audio.set(name,URL.createObjectURL(new Blob([synthesizeWav(item.notes,item.seconds)],{type:'audio/wav'})));
      }
      return audio.get(name);
    },dispose:()=>{for(const url of [...urls.values(),...audio.values()])URL.revokeObjectURL(url);}};
}
