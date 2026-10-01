import { detectPitch, frequencyToMidi } from '../audio/pitch.js';
import { referenceYin } from '../audio/reference-yin.js';
import { RingingPluckBuffer } from '../audio/ringing-pluck-buffer.js';
import { classifyFusion3 } from '../classifier/fusion3.js';
import { fretForMidiAndString } from '../guitar/tuning.js';

// Target labels intentionally never enter this acoustic engine.
export class LivePipelineEngine {
  constructor(bundle, sampleRate, {routeNames=['hybrid','correlation'],retainHistory=true,includePluck=false}={}) {
    this.routeNames=routeNames;this.retainHistory=retainHistory;this.includePluck=includePluck;this.frameCount=0;
    this.bundle=bundle; this.sampleRate=sampleRate; this.samples=0; this.frames=[];
    this.routes=Object.fromEntries(this.routeNames.map(name=>[name,
      {buffer:new RingingPluckBuffer(),events:[],trigger:null}]));
    this.recent=new Float32Array(0); this.signalOnsetMs=null;
  }
  push(samples, timing={}) {
    const start=performance.now();
    if (samples.length!==4096) throw Error('Expected 4096-sample callback');
    const prior=this.samples;this.samples+=samples.length;
    const joined=new Float32Array(this.recent.length+samples.length);
    joined.set(this.recent);joined.set(samples,this.recent.length);
    const windowSize=Math.ceil(this.sampleRate*.24);
    this.recent=joined.slice(Math.max(0,joined.length-windowSize));
    let peak=0,sum=0;for(const v of samples){peak=Math.max(peak,Math.abs(v));sum+=v*v;}
    const rms=Math.sqrt(sum/samples.length),dbfs=rms?20*Math.log10(rms):-120;
    const audioMs=this.samples/this.sampleRate*1000,frameStartMs=prior/this.sampleRate*1000;
    if(this.signalOnsetMs===null&&dbfs>=-48)this.signalOnsetMs=frameStartMs;
    const p0=performance.now(),old=detectPitch(samples,this.sampleRate),correlationMs=performance.now()-p0;
    const y0=performance.now(),yin=this.recent.length>=windowSize
      ?referenceYin(this.recent,this.sampleRate):{frequency:NaN,confidence:0};
    const yinMs=performance.now()-y0;
    const midi=p=>Number.isFinite(p.frequency)?frequencyToMidi(p.frequency):null;
    const emitted=[];
    // Alternate inference order to reduce systematic timing bias.
    const order=this.frameCount%2?[...this.routeNames].reverse():this.routeNames;
    for(const name of order){
      const route=this.routes[name],wasActive=route.buffer.active;
      const pitch=name==='hybrid'&&wasActive&&this.recent.length>=windowSize?yin:old;
      const pluck=route.buffer.push({samples,sampleRate:this.sampleRate,midi:midi(pitch),
        pitchConfidence:pitch.confidence,rms,peak,dbfs});
      // A first push can theoretically finish a tiny capture; our buffer is 0.82s.
      if(!wasActive&&route.buffer.active)route.trigger={audioMs:frameStartMs,wallMs:timing.receivedWallMs??null};
      if(pluck){
        const inferenceStart=performance.now();
        let prediction=null,error=null;
        if(pluck.midi!==null){try{prediction=classifyFusion3({samples:pluck.samples,
          sampleRate:this.sampleRate,midi:pluck.midi,...this.bundle});}catch(e){error=e.message;}}
        const inferenceMs=performance.now()-inferenceStart;
        const event={route:name,midi:pluck.midi,string:prediction?.string??null,
          fret:prediction?fretForMidiAndString(pluck.midi,prediction.string):null,
          confidence:prediction?.confidence??null,model:prediction?.model??null,
          predictions:prediction?.predictions??null,masked:prediction?.masked??null,
          pitchConfidence:pluck.pitchConfidence,capturedSamples:pluck.samples.length,
          captureStartMs:route.trigger?.audioMs??null,captureStartReceivedWallMs:route.trigger?.wallMs??null,captureEndMs:audioMs,
          inferenceMs,workerDecisionWallMs:performance.timeOrigin+performance.now(),
          onsetToAudioCompletionMs:route.trigger?audioMs-route.trigger.audioMs:null,error};
        if(this.includePluck)event.pluck=pluck;
        if(this.retainHistory)route.events.push(event);emitted.push(event);route.trigger=null;
      }
    }
    const frame={index:this.frameCount,audioMs,rms,dbfs,peak,correlationMidi:midi(old),
      correlationConfidence:old.confidence,yinMidi:midi(yin),yinConfidence:yin.confidence,
      correlationFrequency:old.frequency,yinFrequency:yin.frequency,
      correlationMs,yinMs,computeMs:performance.now()-start,...timing,
      hybrid:this.routes.hybrid?.buffer.getDiagnostics(),correlation:this.routes.correlation?.buffer.getDiagnostics()};
    this.frameCount++;if(this.retainHistory)this.frames.push(frame);return {frame,events:emitted};
  }
  finish(){return {sampleRate:this.sampleRate,frameSize:4096,durationMs:this.samples/this.sampleRate*1000,
    signalOnsetMs:this.signalOnsetMs,frames:this.frames,routes:Object.fromEntries(Object.entries(this.routes)
      .map(([name,r])=>[name,{events:r.events,incompleteCapture:r.buffer.active,diagnostics:r.buffer.getDiagnostics()}]))};}
}

