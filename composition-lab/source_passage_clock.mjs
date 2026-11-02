// Bind the selected native traversal to actual generated MIDI time.
// alphaTab's grace preroll shifts note ticks, not tickLookup bar coordinates.
export function sourcePassageClock({masterBars, midiTickShift, tempoChanges, initialTempo, job}) {
 if(typeof midiTickShift!=='number'||!Number.isFinite(midiTickShift)||midiTickShift<0)throw Error('Known native MIDI tick shift required');
 if(typeof initialTempo!=='number'||!Number.isFinite(initialTempo)||initialTempo<=0)throw Error('Known native initial tempo required');
 const start=masterBars.findIndex(b=>b.masterBar.index===job.start_bar-1);
 const end=masterBars.findIndex((b,i)=>i>=start&&b.masterBar.index===job.end_bar-1);
 if(start<0||end<start||end-start>16)throw Error('Unresolved passage playback range');
 const traversal=masterBars.slice(start,end+1).map((b,i)=>{
  if(!Number.isFinite(b.start)||!Number.isFinite(b.end)||b.end<=b.start)throw Error('Known native bar clock required');
  return {traversal_index:start+i,source_bar:b.masterBar.index+1,startTick:b.start+midiTickShift,endTick:b.end+midiTickShift};
 });
 const fraction=x=>{
  if(x===undefined)return 0;
  if(typeof x!=='number'&&typeof x!=='string')throw Error('Numeric target offset required');
  const parts=String(x).split('/').map(Number);
  const value=parts.length===1?parts[0]:parts.length===2&&parts[1]!==0?parts[0]/parts[1]:NaN;
  if(!Number.isFinite(value))throw Error('Finite target offset required');
  return value;
 };
 const target=traversal.find(b=>b.source_bar===job.target_bar);
 const playbackRange={startTick:traversal[0].startTick,endTick:traversal.at(-1).endTick};
 const targetTick=target?target.startTick+fraction(job.target_offset_q)*960:playbackRange.startTick;
 if(targetTick<playbackRange.startTick||targetTick>playbackRange.endTick)throw Error('Target outside selected native traversal');
 // Read the MIDI event clock directly. Tempo events need not carry the same
 // grace offset as note events; applying another shift here would be wrong.
 const byTick=new Map();
 for(const p of tempoChanges){
  if(typeof p.tick!=='number'||!Number.isFinite(p.tick)||p.tick<0||typeof p.tempo!=='number'||!Number.isFinite(p.tempo)||p.tempo<=0)throw Error('Known native MIDI tempo event required');
  byTick.set(p.tick,p.tempo);
 }
 const points=[...byTick].sort((a,b)=>a[0]-b[0]);
 function secondsBetween(a,b){
  let q=a,tempo=initialTempo,total=0;
  for(const[tick,value]of points){
   if(tick<=a){tempo=value;continue;}
   if(tick>=b)break;
   total+=(tick-q)/960*60/tempo;q=tick;tempo=value;
  }
  return total+(b-q)/960*60/tempo;
 }
 return {playbackRange,targetTick,targetSeconds:secondsBetween(playbackRange.startTick,targetTick),
  requestedSeconds:secondsBetween(playbackRange.startTick,playbackRange.endTick),midiTickShift,traversal};
}
