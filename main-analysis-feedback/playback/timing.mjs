/* Rational quarter-note values stay exact through clipping, ordering and identity.
   Only final time integration / drawing converts to IEEE-754. Scheduling tolerance 1e-9 s. */
export const TOLERANCE_SECONDS = 1e-9;
const gcd=(a,b)=>b?gcd(b,a%b):a<0n?-a:a;
export class Q {
  constructor(value, den) {
    if (value instanceof Q) {this.n=value.n;this.d=value.d;return;}
    if(den!==undefined){this.n=BigInt(value);this.d=BigInt(den);}
    else {const s=String(value);if(s.length>312)throw Error('Rational input exceeds resource bound.');if(!/^-?\d+(?:\/\d+|\.\d+)?$/.test(s))throw Error(`Invalid rational quarter: ${s}`);
      if(s.includes('/'))[this.n,this.d]=s.split('/').map(BigInt);
      else if(s.includes('.')){const [a,b]=s.split('.');this.d=10n**BigInt(b.length);this.n=BigInt(a+b);}
      else {this.n=BigInt(s);this.d=1n;}}
    if(this.d===0n)throw Error('Zero rational denominator.');
    const g=gcd(this.n,this.d);this.n/=g;this.d/=g;
    if(this.d<0n){this.n=-this.n;this.d=-this.d;}
  }
  add(v){v=new Q(v);return new Q(this.n*v.d+v.n*this.d,this.d*v.d);}
  sub(v){v=new Q(v);return new Q(this.n*v.d-v.n*this.d,this.d*v.d);}
  cmp(v){v=new Q(v);const d=this.n*v.d-v.n*this.d;return d<0n?-1:d>0n?1:0;}
  number(){const v=Number(this.n)/Number(this.d);if(!Number.isFinite(v))throw Error('Quarter position is out of numeric range.');return v;}
  toString(){return this.d===1n?String(this.n):`${this.n}/${this.d}`;}
}
export const qnum=v=>new Q(v).number();
export const qmin=(a,b)=>new Q(a).cmp(b)<0?new Q(a):new Q(b);
export const qmax=(a,b)=>new Q(a).cmp(b)>0?new Q(a):new Q(b);
export function makeClock(map,{speed=1,normalized=false,bpm=120}={}){
  if(!(speed>=0.25&&speed<=2))throw Error('Speed must be between 0.25 and 2.');
  if(!(bpm>=20&&bpm<=400))throw Error('Normalized tempo must be 20–400 quarter BPM.');
  const sorted=normalized?[]:map.map(t=>({...t,q:new Q(t.onset_q),tempo:qnum(t.quarter_bpm??t.bpm)})).sort((a,b)=>a.q.cmp(b.q));
  function seconds(a,b){a=new Q(a);b=new Q(b);if(a.cmp(b)>0)return -seconds(b,a);
    if(normalized)return b.sub(a).number()*60/bpm/speed;
    if(!sorted.length)throw Error('Source tempo unavailable. Choose explicit normalized tempo.');
    let governing=sorted[0]; for(const t of sorted)if(t.q.cmp(a)<=0)governing=t;
    const relevant=[governing,...sorted.filter(t=>t.q.cmp(a)>0&&t.q.cmp(b)<0)];
    if(relevant.some(t=>!Number.isFinite(t.tempo)||t.tempo<=0))throw Error('Invalid tempo in selected range.');
    if(relevant.some(t=>t.linear===true))throw Error('Gradual tempo transition in selected range is unsupported. Choose normalized tempo explicitly.');
    let tempo=sorted[0].tempo,now=a,sum=0;
    if(a.cmp(sorted[0].q)<0)throw Error('Tempo is unknown before the first source marking.');
    for(const t of sorted){if(t.q.cmp(a)<=0){tempo=t.tempo;continue;}if(t.q.cmp(b)>=0)break;
      sum+=t.q.sub(now).number()*60/tempo/speed;now=t.q;tempo=t.tempo;}
    return sum+b.sub(now).number()*60/tempo/speed;
  }
  function atSeconds(a, elapsed, end){let lo=qnum(a),hi=qnum(end);for(let i=0;i<52;i++){const mid=(lo+hi)/2;const qs=mid.toFixed(12);if(seconds(a,qs)<elapsed)lo=mid;else hi=mid;}return (lo+hi)/2;}
  return {seconds,atSeconds,policy:normalized?`Uniform ${bpm} quarter BPM × ${speed}`:`Source tempo map × ${speed}`};
}
export function memberEnd(m){return m.tied_end_q??m.written_end_q;}
export function playbackGaps(ref,mode='pitch',options={}){
  const gaps=[];const c=ref.coverage??{};
  if(c.neutral_rhythm_eligible===false&&!(options.normalized&&c.exact_clocks_known===true))gaps.push('Selected source has unresolved timing, grace or tempo evidence.');
  if(mode==='pitch'&&(c.playable_notation_eligible??c.pitched_notation_eligible)===false)gaps.push('Some selected source pitches cannot be reconstructed.');
  if((ref.unplaced_or_unknown??[]).length)gaps.push(`${ref.unplaced_or_unknown.length} unresolved or unplaced records remain visible in source details.`);
  if((ref.grace_members??[]).length)gaps.push(`${ref.grace_members.length} grace members are retained but not assigned invented timing.`);
  return gaps;
}
export function compileSchedule(ref,range,options={}){
  const [start,end]=range.map(x=>new Q(x));
  if(start.cmp(end)>=0)throw Error('Choose an increasing range.');
  const mode=options.mode??'pitch';
  if(ref.schema==='main-analysis-backing-excerpt/1'&&ref.coverage?.tempo_known===false&&!options.normalized)throw Error('Backing channel tempos are unknown or disagree. Choose normalized 120 BPM explicitly.');
  const clock=makeClock(ref.tempo_map??[],options);
  const duration=clock.seconds(start,end), notes=[], clicks=[], gaps=playbackGaps(ref,mode,options).map(reason=>({reason}));
  if(gaps.length&&!options.allowPartial)throw Error('Incomplete reconstruction. Review playback gaps and explicitly enable partial audition.');
  const seen=new Set();
  function member(m,event,carry=false){
    if((m.onset_q??event?.onset_q)==null||memberEnd(m)==null){gaps.push({id:m.occurrence??m.id,reason:'Unknown note clock; member cannot be scheduled.'});if(!options.allowPartial)throw Error('Unknown note clock requires explicit partial audition.');return;}
    const on=new Q(m.onset_q??event?.onset_q),off=new Q(memberEnd(m));
    if(off.cmp(start)<=0||on.cmp(end)>=0)return;
    const id=m.occurrence??m.id??JSON.stringify(m.source_ids??[String(on),m.voice,m.pitch]);
    if(seen.has(id))return;seen.add(id);
    const isCarry=carry||on.cmp(start)<0;
    const begin=qmax(start,on),finish=qmin(end,off);
    const pitch=m.pitch;
    const percussion=m.percussion===true&&Number.isInteger(m.percussion_id)&&m.percussion_id>=0&&m.percussion_id<=127;
    const item={id,pitch,percussion,percussion_id:percussion?m.percussion_id:null,onset_q:String(on),start_q:String(begin),end_q:String(finish),written_end_q:m.written_end_q,tied_end_q:String(off),voice:m.voice,carry_in:isCarry,carry_out:off.cmp(end)>0,start:clock.seconds(start,begin),end:clock.seconds(start,finish),marks:m.marks??{},source:m};
    if(mode==='pitch'&&!percussion&&(pitch==null||!Number.isFinite(Number(pitch))))gaps.push({id,reason:'Pitch unavailable; omitted from pitched preview. Rhythm timing remains available.'});
    notes.push(item);
  }
  for(const event of ref.events??[]){
    if(event.onset_q==null){gaps.push({id:event.attack_id,reason:'Unknown attack clock; attack cannot be scheduled.'});if(!options.allowPartial)throw Error('Unknown attack clock requires explicit partial audition.');continue;}
    const on=new Q(event.onset_q);
    if(on.cmp(start)>=0&&on.cmp(end)<0)clicks.push({id:event.attack_id,onset_q:String(on),start:clock.seconds(start,on),end:Math.min(duration,clock.seconds(start,on)+.025)});
    for(const m of event.members??[])member(m,event);
  }
  for(const m of ref.carry_in??[])member(m,null,true);
  // One neutral click per exact onset, not per note/chord member or tie continuation.
  const uniqueClicks=Array.from(new Map(clicks.map(c=>[c.onset_q,c])).values());
  if(gaps.length&&!options.allowPartial)throw Error('Playback gaps require explicit partial audition.');
  return {range:range.map(String),duration,notes,clicks:uniqueClicks,gaps,clock,mode,events:mode==='click'?uniqueClicks:notes,policy:'Score order, once; no repeat/ending expansion. Loop truncates at the selection boundary; incoming notation holds are synthesized, never counted as attacks.'};
}
export function frequency(midi){return 440*2**((Number(midi)-69)/12);}
/* This function works with AudioContext, OfflineAudioContext or a strict test double. */
export function scheduleAudio(ctx,plan,when,mode=plan.mode,destination=ctx.destination,options={}){
  const nodes=[];let active=0,peak=1;const points=plan.notes.flatMap(n=>[[n.start,1],[n.end,-1]]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);for(const [,delta]of points){active+=delta;peak=Math.max(peak,active);}const level=0.13/Math.sqrt(peak);
  for(const e of (mode==='click'?plan.clicks:plan.notes)){
    if(mode==='pitch'&&!e.percussion&&(e.pitch==null||!Number.isFinite(Number(e.pitch))))continue;
    // A short drum cue represents an attack, never a fabricated attack on a carried tail.
    if(mode==='pitch'&&e.percussion&&e.carry_in)continue;
    const start=when+e.start,end=e.percussion?Math.min(when+e.end,start+.035):when+e.end;if(end<=start)continue;
    const osc=ctx.createOscillator(),gain=ctx.createGain();
    osc.type=mode==='click'||e.percussion?'sine':mode==='neutral'?'sine':options.timbre==='bright'?'sawtooth':'triangle';
    osc.frequency.setValueAtTime(mode==='click'?1200:mode==='neutral'?220:e.percussion?700:frequency(e.pitch),start);
    const volume=mode==='click'?.14:e.percussion?Math.min(.08,level):level;
    gain.gain.setValueAtTime(0,start);
    gain.gain.linearRampToValueAtTime(volume,start+Math.min(e.carry_in?.005:.002,(end-start)/3));
    gain.gain.setValueAtTime(volume,Math.max(start+(end-start)/3,end-Math.min(.006,(end-start)/3)));
    gain.gain.linearRampToValueAtTime(0,end);
    osc.connect(gain);gain.connect(destination);osc.start(start);osc.stop(end);
    nodes.push({osc,gain,start,end,source:e});
  }
  return nodes;
}
