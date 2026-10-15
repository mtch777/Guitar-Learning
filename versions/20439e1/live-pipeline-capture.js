// AudioWorklet keeps 4096-sample blocks continuous while inference runs in a Worker.
class TrialCapture extends AudioWorkletProcessor{
  constructor(options){super();this.channel=options.processorOptions.channel;
    this.block=new Float32Array(4096);this.used=0;this.sequence=0;this.badChannel=false;
    this.port.onmessage=e=>{if(e.data.type==='channel'){this.channel=e.data.channel;this.used=0;}};
  }
  process(inputs){
    const channels=inputs[0];if(!channels?.length)return true;
    const selected=channels[this.channel];
    if(!selected){if(!this.badChannel)this.port.postMessage({type:'channel-error',channels:channels.length});this.badChannel=true;return true;}
    this.badChannel=false;
    const levels=channels.map(a=>{let s=0,p=0;for(const x of a){s+=x*x;p=Math.max(p,Math.abs(x));}return {rms:Math.sqrt(s/a.length),peak:p};});
    for(let i=0;i<selected.length;i++){
      this.block[this.used++]=selected[i];
      if(this.used===4096){const samples=this.block;this.block=new Float32Array(4096);this.used=0;
        this.port.postMessage({type:'frame',samples:samples.buffer,sequence:this.sequence++,
          audioTime:currentTime+(i+1)/sampleRate,channels:channels.length,levels},[samples.buffer]);}
    }
    return true;
  }
}
registerProcessor('live-pipeline-capture',TrialCapture);
