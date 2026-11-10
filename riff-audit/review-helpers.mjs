// Reused verbatim pure helpers from composition-lab/arrangement-review.mjs. UI boot is excluded. 
// Read-only playback comparison. The payload contains measured native MIDI attacks.
export function noteKey(n){
 const written=n.score_start_tick!==undefined||n.score_end_tick!==undefined;
 if(written&&(!Number.isSafeInteger(n.score_start_tick)||!Number.isSafeInteger(n.score_end_tick)||n.score_start_tick>=n.score_end_tick))throw Error('Complete written score coordinates are required.');
 return JSON.stringify([n.comparison_identity??null,n.part,n.voice,...(written?['score',n.score_start_tick,n.score_end_tick]:[Math.round(n.start*44100),Math.round(n.end*44100)]),n.pitch,n.velocity,n.fret,n.string,n.dead,n.ghost]);
}
export function versionClock(data,version){return {bars:data.bars,seconds:version?.seconds??data.seconds,bar_times:version?.bar_times??data.bar_times};}
export function clockProjector(from,to){
 const anchors=clock=>clock.bar_times.filter(b=>b.bar>=clock.bars[0]&&b.bar<=clock.bars[1]+1).flatMap(b=>[b.time,...(b.beat_times||[])]);
 const a=anchors(from),b=anchors(to),shape=clock=>clock.bar_times.map(b=>[b.bar,(b.beat_times||[]).length]);
 if(JSON.stringify(shape(from))!==JSON.stringify(shape(to))||a.length<2||a.length!==b.length)throw Error('Version clocks need corresponding bar and beat boundaries.');
 const identical=from.seconds===to.seconds&&a.every((time,i)=>time===b[i]);
 return time=>{
  if(!Number.isFinite(time))throw Error('Finite playback position required.');
  if(identical)return Math.min(to.seconds,Math.max(0,time));
  if(time<=a[0])return b[0];if(time>=a.at(-1)||time>=from.seconds)return to.seconds;
  let low=0,high=a.length-1;while(high-low>1){const mid=(low+high)>>1;if(a[mid]<=time)low=mid;else high=mid;}
  return b[low]+(time-a[low])/(a[high]-a[low])*(b[high]-b[low]);
 };
}
export function mapClockTime(time,from,to){return clockProjector(from,to)(time);}
export function difference(current,baseline){
 if([...current,...baseline].some(n=>n.score_start_tick!==undefined||n.score_end_tick!==undefined)){
  for(const n of [...current,...baseline])if(!Number.isSafeInteger(n.score_start_tick)||!Number.isSafeInteger(n.score_end_tick)||n.score_start_tick>=n.score_end_tick||typeof n.comparison_identity!=='string'||!n.comparison_identity)throw Error('Complete written score coordinates and identities are required.');
 }
 // Only use occurrence correspondence explicitly supplied by a verified exporter.
 // Native list positions/ref strings alone are not stable across every edit.
 if([...current,...baseline].some(n=>n.comparison_identity!==undefined)){
  for(const notes of [current,baseline]){const ids=notes.map(n=>n.comparison_identity);
   if(ids.some(id=>typeof id!=='string'||!id)||new Set(ids).size!==ids.length)throw Error('Comparison identities must be complete and unique within each version.');}
 }
 const available=new Map();for(const n of baseline){const k=noteKey(n);if(!available.has(k))available.set(k,[]);available.get(k).push(n);}
 const shown=current.map(n=>{const matches=available.get(noteKey(n));return {...n,change:matches?.length?(matches.pop(),'same'):'new'};});
 const removed=[...available.values()].flat().map(n=>({...n,change:'old'}));return {shown,removed};
}
export function pitchName(n){return ['C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B'][((n%12)+12)%12]+'_'+(Math.floor(n/12)-1);}
export function partRange(versions,part){const pitches=versions.flatMap(v=>v.notes.filter(n=>n.part===part).map(n=>n.pitch));return {low:Math.min(...pitches)-1,high:Math.max(...pitches)+1};}
export function pitchedLaneGeometry(range){
 const rowCount=range.high-range.low+1,rowSize=Math.min(9,(280-34)/rowCount);
 return {rowCount,rowSize,height:Math.max(90,34+rowCount*rowSize),noteHeight:7*rowSize/9,outlineWidth:1.7*rowSize/9,
  mapY:p=>34+(range.high-p)*rowSize+rowSize/2};
}
export function barAt(data,time){return Math.min(data.bars[1],[...data.bar_times].reverse().find(b=>b.time<=time+1/44100)?.bar??data.bars[0]);}
export function formatTime(seconds){return `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;}
export function comparisonView(current,baseline,onlyChanged=false,data=null){
 const base=baseline&&baseline.id!==current.id?baseline:null;
 const result=base?difference(current.notes,base.notes):{shown:current.notes.map(n=>({...n,change:'same'})),removed:[]};
 if(base&&data){const project=clockProjector(versionClock(data,base),versionClock(data,current));result.removed=result.removed.map(n=>({...n,start:project(n.start),end:project(n.end)}));}
 const changes=[...result.shown.filter(n=>n.change==='new'),...result.removed];
 const canFilter=Boolean(base&&changes.length);
 return {...result,base,changes,canFilter,filterActive:onlyChanged&&canFilter,changedParts:new Set(changes.map(n=>n.part))};
}
export function changeScrollLeft(changes,left,visibleWidth,pxPerSecond){
 if(!changes.length||changes.some(n=>n.end*pxPerSecond>left&&n.start*pxPerSecond<left+visibleWidth))return left;
 return Math.max(0,Math.min(...changes.map(n=>n.start))*pxPerSecond-20);
}
export function playbackSwitchState(){
 let serial=0,pending=null;
 return {
  begin(position,playing,project=x=>x){const previous=pending||{position,playing};pending={...previous,position:project(previous.position),token:++serial};return serial;},
  seek(position){if(!pending)return false;pending.position=position;return true;},
  position(actual){return pending?.position??actual;},
  isCurrent(token){return token===serial;},
  complete(token,duration){
   if(!pending||token!==serial||!Number.isFinite(duration)||duration<0)return null;
   const target={position:Math.min(pending.position,duration),playing:pending.playing};pending=null;return target;
  }
 };
}


