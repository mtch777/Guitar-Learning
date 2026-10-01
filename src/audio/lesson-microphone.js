// Same capture, pitch voting and model bundle as the live pilot. Worker history is bounded.
export class LessonMicrophone {
 constructor({channel=1,deviceId='',onFrame=()=>{},onError=()=>{}}={}){Object.assign(this,{channel,deviceId,onFrame,onError});this.running=false;}
 async start(){
  const base=new URL(import.meta.env.BASE_URL,location.origin);
  const tuning=window.getGuitarTrainerTuning?.();
  if(tuning&&tuning.join(',')!=='27,34,39,44,49,54,58,63')throw Error('This model requires the tested 8-string drop D# tuning.');
  try{
   this.worker=new Worker(new URL('../input/lesson-worker.js',import.meta.url),{type:'module'});
   await new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>reject(Error('Model loading timed out')),30000);
    this.worker.onerror=e=>{clearTimeout(timeout);reject(Error(e.message));};
    this.worker.onmessage=({data:d})=>{if(d.type==='ready'){clearTimeout(timeout);this.manifest=d.manifest;resolve();}else if(d.type==='error'){clearTimeout(timeout);reject(Error(d.message));}};
    this.worker.postMessage({type:'load',baseUrl:new URL('model/fusion3-live',base).href});
   });
   this.stream=await navigator.mediaDevices.getUserMedia({audio:{deviceId:this.deviceId?{exact:this.deviceId}:undefined,channelCount:{ideal:2},echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
   this.context=new AudioContext({sampleRate:44100});await this.context.resume();
   await this.context.audioWorklet.addModule(new URL('live-pipeline-capture.js',base).href);
   this.processor=new AudioWorkletNode(this.context,'live-pipeline-capture',{processorOptions:{channel:this.channel}});
   this.silentGain=this.context.createGain();this.silentGain.gain.value=0;this.source=this.context.createMediaStreamSource(this.stream);
   this.worker.onmessage=({data:d})=>{
    if(!this.running)return;
    if(d.type==='error'||d.type==='warning'){this.onError(Error(d.message));return;}
    if(d.type!=='progress')return;
    const f=d.frame,e=d.events[0],valid=e&&Number.isInteger(e.fret)&&e.fret>=0&&e.fret<=24&&!e.error;
    const useYin=Number.isFinite(f.yinFrequency)&&f.yinConfidence>=.55;
    const frame={sampleRate:this.context.sampleRate,rms:f.rms,peak:f.peak,dbfs:f.dbfs,
     frequency:useYin?f.yinFrequency:f.correlationFrequency,midi:useYin?f.yinMidi:f.correlationMidi,
     pitchConfidence:useYin?f.yinConfidence:f.correlationConfidence,pitchCandidates:[],hybridDiagnostics:f.hybrid,
     completedPluck:valid?e.pluck:null,fusionResult:valid?{string:e.string,confidence:e.confidence,probabilities:e.masked[e.model],model:e.model}:null};
    Promise.resolve(this.onFrame(frame)).catch(error=>this.onError(error));
   };
   this.worker.onerror=e=>this.onError(Error(e.message));
   this.running=true;this.worker.postMessage({type:'start',sampleRate:this.context.sampleRate});
   this.processor.port.onmessage=({data:d})=>{
    if(!this.running)return;
    if(d.type==='channel-error'){this.onError(Error(`Channel ${this.channel+1} unavailable. Disable input and select the guitar channel.`));return;}
    this.worker.postMessage({type:'frame',samples:d.samples,sequence:d.sequence,receivedWallMs:performance.timeOrigin+performance.now()},[d.samples]);
   };
   this.source.connect(this.processor);this.processor.connect(this.silentGain);this.silentGain.connect(this.context.destination);
   return {sampleRate:this.context.sampleRate};
  }catch(e){this.stop();throw e;}
 }
 stop(){this.running=false;this.worker?.terminate();this.worker=null;
  this.stream?.getTracks().forEach(t=>t.stop());this.source?.disconnect();this.processor?.disconnect();this.silentGain?.disconnect();
  this.context?.close().catch(()=>{});this.context=null;this.stream=null;
 }
}
