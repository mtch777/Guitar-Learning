// Explicit source tremolo rates for paired preview playback only. Native GP
// notation is unchanged; no global prototypes or source objects are mutated.
import {createHash} from 'node:crypto';
const SCHEMA='composition-lab.source-tremolo-timing.v1';
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const need=(x,m)=>{if(!x)throw Error(`Source tremolo timing: ${m}`);};
const key=a=>JSON.stringify(a);
const gcd=(a,b)=>b?gcd(b,a%b):a;
function rational(n,d){const g=gcd(n,d);return[n/g,d/g];}
function ticks(q){need(Array.isArray(q)&&q.length===2&&q.every(x=>Number.isSafeInteger(x)&&x>0),'invalid positive quarter fraction');const n=q[0]*960;need(Number.isSafeInteger(n)&&n%q[1]===0,'unsupported fractional MIDI clock');return n/q[1];}
function sourceDuration(b){need(Array.isArray(b.duration)&&b.duration.length===2&&b.duration.every(x=>Number.isSafeInteger(x)&&x>0),'missing source duration');return rational(b.duration[0]*4,b.duration[1]);}
function rate(raw){if(raw===undefined||raw===null||raw===false)return null;need(Array.isArray(raw)&&raw.length===2&&raw[0]===1&&[8,16,32].includes(raw[1]),'unsupported explicit rate');return rational(4,raw[1]);}
function inventory(score){
 const beats=new Map(),notes=new Map();
 for(const[ti,t]of score.tracks.entries())for(const[si,s]of t.staves.entries())for(const[mi,m]of s.bars.entries())for(const[vi,v]of m.voices.entries())for(const[bi,b]of v.beats.entries()){
  const address=[ti,si,mi,vi,bi];beats.set(key(address),{address,beat:b,staff:s});
  for(const[ni,n]of b.notes.entries())notes.set(n,[...address,ni]);
 }
 return{beats,notes};
}
function plain(n){return !n.isDead&&!n.isGhost&&!n.isLetRing&&!n.isPalmMute&&!n.isStaccato&&!n.isHammerPullOrigin&&!n.isLeftHandTapped&&!n.isSlurDestination&&!n.bendPoints?.length&&!n.isContinuedBend&&!n.harmonicType&&!n.slideInType&&!n.slideOutType&&!n.vibrato&&n.trillValue<0&&!n.ornament&&n.durationPercent===1;}
function identity(row,all){const b=row.beat;return digest({address:row.address,tuning:row.staff.tuning,capo:row.staff.capo,
 duration:b.duration,dots:b.dots,tuplet:[b.tupletNumerator,b.tupletDenominator],grace:b.graceType,
 onset:b.absoluteDisplayStart,playbackOnset:b.absolutePlaybackStart,length:b.displayDuration,playbackLength:b.playbackDuration,
 tremolo:b.tremoloPicking?{marks:b.tremoloPicking.marks,style:b.tremoloPicking.style}:null,
 notes:b.notes.map(n=>({string:n.string,fret:n.fret,pitch:n.realValueWithoutHarmonic,tie:n.isTieDestination,
  origin:n.tieOrigin?all.notes.get(n.tieOrigin):null,destination:n.tieDestination?all.notes.get(n.tieDestination):null,
  dead:n.isDead,ghost:n.isGhost,letRing:n.isLetRing,palmMute:n.isPalmMute,staccato:n.isStaccato,hammer:n.isHammerPullOrigin,
  slur:n.isSlurDestination,tap:n.isLeftHandTapped,harmonic:n.harmonicType,slide:[n.slideInType,n.slideOutType],
  vibrato:n.vibrato,bend:n.bendType,trill:n.trillValue,ornament:n.ornament,durationPercent:n.durationPercent}))});}
function chains(row,all){
 const result=new Map();
 for(const first of row.beat.notes){
  let origin=first;const backward=new Set();
  while(origin.tieOrigin){need(!backward.has(origin),'cyclic tie');backward.add(origin);origin=origin.tieOrigin;}
  need(!origin.isTieDestination,'unresolved tie origin');
  let n=origin;const seen=new Set();
  while(n){
   need(!seen.has(n),'cyclic tie');seen.add(n);
   const a=all.notes.get(n);need(a,'tie outside score');const r=all.beats.get(key(a.slice(0,5)));
   need(plain(n)&&!r.staff.isPercussion&&!n.beat.graceType,'unsupported execution in tie');
   need(a[0]===row.address[0]&&a[1]===row.address[1]&&a[3]===row.address[3],'tie changed voice');
   result.set(key(r.address),{address:r.address,identity_sha256:identity(r,all)});
   const next=n.tieDestination;
   if(next)need(next.tieOrigin===n&&next.isTieDestination&&next.string===n.string&&next.fret===n.fret&&
    next.beat.absoluteDisplayStart===n.beat.absoluteDisplayStart+n.beat.displayDuration,'broken/noncontiguous tie');
   n=next;
  }
  need(seen.has(first),'unresolved tie membership');
 }
 return[...result.values()].sort((a,b)=>key(a.address).localeCompare(key(b.address)));
}
function compatible(row){const b=row.beat;need(!row.staff.isPercussion&&!b.graceType&&!b.isEmpty&&b.notes.length&&
 b.notes.every(plain)&&b.playbackDuration===b.displayDuration&&b.absolutePlaybackStart===b.absoluteDisplayStart&&
 !b.voice.bar.masterBar.tripletFeel&&!b.fade&&!b.brushType&&!b.isLegatoOrigin&&!b.whammyBarPoints?.length,'unsupported beat execution');}

export function collectSourceTremoloTiming(score,parts){
 need(Array.isArray(parts)&&parts.length===score.tracks.length,'source track correspondence');
 const all=inventory(score),source=new Map(),records=[];
 for(const[ti,part]of parts.entries()){
  const active=part.measures?.some(m=>(m.voices||[]).some(v=>(v.beats||[]).some(b=>b.tremolo||(b.notes||[]).some(n=>n.tremolo))));
  if(!active)continue;
  const track=score.tracks[ti];need(track.staves.length===1,'multiple staves');const staff=track.staves[0];
  need(!staff.isPercussion&&part.instrumentId!==1024&&equal(staff.tuning,part.tuning),'source tuning/instrument');
  need(part.measures.length===staff.bars.length,'source bar count');
  let absolute=0,signature=null;
  for(const[mi,m]of part.measures.entries()){
   if(m.signature)signature=m.signature;
   need(Array.isArray(signature)&&signature.length===2&&signature.every(x=>Number.isSafeInteger(x)&&x>0),'source meter');
   const master=score.masterBars[mi];need(master.timeSignatureNumerator===signature[0]&&master.timeSignatureDenominator===signature[1],'source meter mismatch');
   for(const[vi,v]of(m.voices||[]).entries()){
    const native=staff.bars[mi].voices[vi];need(native&&native.beats.length===v.beats.length,'source beat correspondence');let offset=0;
    for(const[bi,b]of v.beats.entries()){
     const address=[ti,0,mi,vi,bi],row=all.beats.get(key(address)),nb=row.beat,dq=sourceDuration(b),duration=ticks(dq);
     need(!b.graceNote&&nb.graceType===0&&nb.displayDuration===duration&&nb.absoluteDisplayStart===absolute+offset,'source clock mismatch');
     const raw=(b.notes||[]).filter(n=>!n.rest);need(raw.length===nb.notes.length,'source multiplicity');const mapped=new Set();
     for(const n of raw){const matches=nb.notes.filter(x=>x.string===part.tuning.length-n.string&&x.fret===n.fret&&x.isDead===(n.dead===true)&&x.isTieDestination===(n.tie===true));
      need(matches.length===1&&!mapped.has(matches[0]),'source member identity/ambiguity');mapped.add(matches[0]);
      const q=rate(n.tremolo??b.tremolo);source.set(matches[0],{raw:n,rate:q,row,duration_q:dq});
     }
     const rates=raw.map(n=>rate(n.tremolo??b.tremolo));
     if(rates.some(Boolean)){
      need(raw.length&&rates.every(q=>q&&equal(q,rates[0])),'conflicting/missing coattack rates');compatible(row);
      // The native generator already repeats an origin through its tied hold.
      // A separately marked destination currently generates duplicate attacks.
      need(nb.notes.every(n=>!n.isTieDestination),'explicit tremolo tie destination unsupported');
      need(nb.tremoloPicking&&nb.tremoloPicking.style===0,'missing native tremolo');
      const interval=ticks(rates[0]),expected=3840/2**(nb.tremoloPicking.marks+2);need(interval===expected,'source/native tremolo rate mismatch');
      records.push({address,source_interval_q:rates[0],source_duration_q:dq,source_onset_ticks:absolute+offset,identity_sha256:identity(row,all)});
     }
     offset+=duration;
    }
   }
   absolute+=ticks(rational(signature[0]*4,signature[1]));
  }
 }
 for(const record of records){
  const row=all.beats.get(key(record.address));record.dependencies=chains(row,all);
  for(const first of row.beat.notes){let origin=first;while(origin.tieOrigin)origin=origin.tieOrigin;
   const initial=source.get(origin);need(initial?.rate&&equal(initial.rate,record.source_interval_q),'tie origin rate absent/conflicting');
   let n=origin;while(n){const s=source.get(n);need(s&&(!s.rate||equal(s.rate,initial.rate)),'tie rate conflict');n=n.tieDestination;}
  }
 }
 const extension={schema:SCHEMA,rates:records,scope:'PREVIEW_ONLY explicit source tremolo intervals; standalone GP playback unproved'};
 prepareSourceTremoloTiming(score,extension);return extension;
}

// Validate every record and dependency before returning an atomic application.
export function prepareSourceTremoloTiming(score,extension){
 need(extension?.schema===SCHEMA&&Array.isArray(extension.rates),'invalid extension');
 const all=inventory(score),seen=new Set(),plans=[];
 for(const record of extension.rates){
  need(Array.isArray(record.address)&&record.address.length===5&&record.address.every(n=>Number.isSafeInteger(n)&&n>=0),'invalid address');
  const k=key(record.address);need(!seen.has(k),'duplicate address');seen.add(k);const row=all.beats.get(k);need(row,'missing beat');compatible(row);
  const b=row.beat,effect=b.tremoloPicking;need(effect&&effect.style===0&&[1,2,3].includes(effect.marks),'missing/unsupported native tremolo');
  need(b.notes.every(n=>!n.isTieDestination),'explicit tremolo tie destination unsupported');
  need(record.identity_sha256===identity(row,all),'paired beat identity mismatch');
  need(equal(record.dependencies,chains(row,all)),'missing/changed tie dependency');
  const interval=ticks(record.source_interval_q);need(interval===3840/2**(effect.marks+2),'source/native rate mismatch');
  need(ticks(record.source_duration_q)===b.displayDuration&&record.source_onset_ticks===b.absoluteDisplayStart,'source clock identity mismatch');
  const duration=b.duration,playback=b.playbackDuration,factor=playback/(3840/duration);need(Number.isFinite(factor)&&factor>0,'invalid host factor');
  plans.push({effect,b,duration,playback,value:interval/factor});
 }
 const marked=[...all.beats.entries()].filter(([,r])=>r.beat.tremoloPicking).map(([k])=>k);
 need(marked.length===seen.size&&marked.every(k=>seen.has(k)),'missing native tremolo rate coverage');
 return{count:plans.length,apply(){for(const{effect,b,duration,playback,value}of plans){
   effect.getDurationAsTicks=function(given){need(given===duration&&b.duration===duration&&b.playbackDuration===playback&&b.tremoloPicking===effect,'stale playback identity');return value;};
  }return plans.length;}};
}
