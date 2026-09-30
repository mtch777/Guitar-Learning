import { LivePipelineEngine } from './live-pipeline-engine.js';
let bundle,engine,chunks=[],id,lastSequence=null;
self.onmessage=async ({data:d})=>{
  try{
    if(d.type==='load'){
      const r=await fetch(`${d.baseUrl}/manifest.json`);if(!r.ok)throw Error('Model manifest missing');
      const manifest=await r.json(),loaded={};
      for(const name of ['baseline','harmonic','mfcc','calibrators']){
        const response=await fetch(`${d.baseUrl}/${name}.json`);if(!response.ok)throw Error(`${name} model missing`);
        const bytes=await response.arrayBuffer();
        const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
        if(hash!==manifest.sha256[`${name}.json`])throw Error(`${name} model checksum mismatch`);
        loaded[name]=JSON.parse(new TextDecoder().decode(bytes));
      }
      const {calibrators,...models}=loaded;bundle={models,calibrators};
      self.postMessage({type:'ready',manifest});
    }else if(d.type==='start'){
      if(!bundle)throw Error('Models not ready');
      engine=new LivePipelineEngine(bundle,d.sampleRate);chunks=[];id=d.id;lastSequence=null;
    }else if(d.type==='frame'&&engine){
      if(d.id!==id)return;
      const gaps=lastSequence===null?0:d.sequence-lastSequence-1;lastSequence=d.sequence;
      const samples=new Float32Array(d.samples);chunks.push(samples);
      const result=engine.push(samples,{sequence:d.sequence,missingCallbacks:gaps,
        inputAudioTime:d.audioTime,receivedWallMs:d.receivedWallMs,workerStartWallMs:performance.timeOrigin+performance.now()});
      self.postMessage({type:'progress',id,...result});
    }else if(d.type==='finish'&&engine&&d.id===id){
      const report=engine.finish(),pcm=new Float32Array(chunks.length*4096);
      chunks.forEach((a,i)=>pcm.set(a,i*4096));
      engine=null;chunks=[];self.postMessage({type:'finished',id,report,pcm:pcm.buffer},[pcm.buffer]);
    }
  }catch(error){self.postMessage({type:'error',id,message:error.message});}
};
