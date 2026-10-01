import { LivePipelineEngine } from './live-pipeline-engine.js';
let bundle,engine,sampleRate,lastSequence=null;
const makeEngine=()=>new LivePipelineEngine(bundle,sampleRate,{routeNames:['hybrid'],retainHistory:false,includePluck:true});
self.onmessage=async({data:d})=>{try{
 if(d.type==='load'){
  const response=await fetch(`${d.baseUrl}/manifest.json`);if(!response.ok)throw Error('Model manifest missing');
  const manifest=await response.json(),loaded={};
  for(const name of ['baseline','harmonic','mfcc','calibrators']){
   const r=await fetch(`${d.baseUrl}/${name}.json`);if(!r.ok)throw Error(`${name} model missing`);
   const bytes=await r.arrayBuffer();
   const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
   if(hash!==manifest.sha256[`${name}.json`])throw Error(`${name} checksum mismatch`);
   loaded[name]=JSON.parse(new TextDecoder().decode(bytes));
  }
  const {calibrators,...models}=loaded;bundle={models,calibrators};self.postMessage({type:'ready',manifest});
 }else if(d.type==='start'){
  if(!bundle)throw Error('Models not ready');sampleRate=d.sampleRate;engine=makeEngine();lastSequence=null;
 }else if(d.type==='frame'&&engine){
  if(lastSequence!==null&&d.sequence!==lastSequence+1){engine=makeEngine();self.postMessage({type:'warning',message:'Audio gap: discarded incomplete note. Please play again.'});}
  lastSequence=d.sequence;
  const result=engine.push(new Float32Array(d.samples),{receivedWallMs:d.receivedWallMs,sequence:d.sequence});
  self.postMessage({type:'progress',...result},result.events.filter(e=>e.pluck).map(e=>e.pluck.samples.buffer));
 }
}catch(e){self.postMessage({type:'error',message:e.message});}};
