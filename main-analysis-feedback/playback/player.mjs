import {compileSchedule,scheduleAudio,qnum,Q} from './timing.mjs?v=piano-roll-1';
export class ReferencePlayer{
  constructor(update,contextFactory=()=>new AudioContext()){
    this.update=update;this.contextFactory=contextFactory;this.ctx=null;this.nodes=[];this.cycles=[];this.state='stopped';this.position=0;this.positionQ='0';this.token=0;
    this.options={mode:'pitch',speed:1,normalized:false,bpm:120,loop:false,allowPartial:false};
  }
  load(ref,range){this.stop();this.ref=ref;this.range=range.map(String);this.positionQ=this.range[0];this.position=qnum(this.positionQ);this.plan=null;this.emit();}
  setOptions(options){const was=this.state==='playing';if(was)this.pause();Object.assign(this.options,options);this.emit();if(was)return this.play();return Promise.resolve();}
  emit(){this.update?.({state:this.state,position:this.position,positionQ:this.positionQ,plan:this.plan,contextState:this.ctx?.state??'not-created'});}
  current(){if(this.state!=='playing')return this.position;const time=this.ctx.currentTime;const cycle=this.cycles.find(c=>time<c.when+c.plan.duration)??this.cycles.at(-1);if(!cycle)return this.position;return cycle.plan.clock.atSeconds(cycle.plan.range[0],Math.max(0,time-cycle.when),cycle.plan.range[1]);}
  cancel(){this.token++;clearInterval(this.timer);cancelAnimationFrame(this.frame);for(const n of this.nodes){try{n.osc.stop();}catch{}n.osc.disconnect();n.gain.disconnect();}this.nodes=[];this.cycles=[];}
  async play(){
    if(!this.ref||this.state==='playing'||this.state==='starting')return;
    if(new Q(this.positionQ).cmp(this.range[1])>=0)this.positionQ=this.range[0];
    // Use the exact source selection origin, including 2/3 etc. Never round it before attack membership.
    this.plan=compileSchedule(this.ref,[this.positionQ,this.range[1]],this.options);
    if(this.options.loop&&this.plan.duration<.005)throw Error('Loop is shorter than the 5 ms scheduling limit; audition without looping.');
    const fullPlan=this.options.loop?compileSchedule(this.ref,this.range,this.options):null;
    const epoch=++this.token;this.state='starting';this.emit();
    try{this.ctx??=this.contextFactory();await this.ctx.resume();}catch(e){if(epoch===this.token){this.state='paused';this.emit();}throw e;}
    if(epoch!==this.token)return;
    const addCycle=(plan,when)=>{this.cycles.push({plan,when});this.nodes.push(...scheduleAudio(this.ctx,plan,when,this.options.mode));};
    const firstWhen=this.ctx.currentTime+.04;addCycle(this.plan,firstWhen);let nextWhen=firstWhen+this.plan.duration;
    // Audio nodes are scheduled at contiguous AudioContext times. Timers never define loop boundaries.
    const pump=()=>{if(epoch!==this.token)return;const now=this.ctx.currentTime;
      if(this.options.loop){let count=0;while(nextWhen<now+.3&&count++<128){addCycle(fullPlan,nextWhen);nextWhen+=fullPlan.duration;}}
      else if(now>=nextWhen){this.stop();return;}
      this.cycles=this.cycles.filter(c=>c.when+c.plan.duration>=now-.1);
      const expired=this.nodes.filter(n=>n.end<now-.1);for(const n of expired){n.osc.disconnect();n.gain.disconnect();}this.nodes=this.nodes.filter(n=>n.end>=now-.1);
    };
    this.state='playing';pump();this.timer=setInterval(pump,20);
    const tick=()=>{if(this.state!=='playing'||epoch!==this.token)return;this.position=this.current();this.emit();this.frame=requestAnimationFrame(tick);};tick();
  }
  pause(){if(this.state==='playing'){this.position=this.current();const first=this.cycles[0];this.positionQ=first&&this.ctx.currentTime<=first.when?first.plan.range[0]:this.position.toFixed(12);}this.cancel();this.state='paused';this.emit();}
  stop(){this.cancel();this.state='stopped';if(this.range){this.positionQ=this.range[0];this.position=qnum(this.positionQ);}this.emit();}
  seek(value){const was=this.state==='playing';this.pause();let q=new Q(typeof value==='number'?value.toFixed(12):value);if(q.cmp(this.range[0])<0)q=new Q(this.range[0]);if(q.cmp(this.range[1])>0)q=new Q(this.range[1]);this.positionQ=String(q);this.position=qnum(q);this.emit();if(was)return this.play();return Promise.resolve();}
}
