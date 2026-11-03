// Bind the selected native traversal to actual generated MIDI time.
// alphaTab's grace preroll shifts note ticks, not tickLookup bar coordinates.
export function sourcePassageClock({masterBars, sourceBarCount, midiTickShift, tempoChanges, initialTempo, job}) {
 if(typeof midiTickShift!=='number'||!Number.isFinite(midiTickShift)||midiTickShift<0)throw Error('Known native MIDI tick shift required');
 if(typeof initialTempo!=='number'||!Number.isFinite(initialTempo)||initialTempo<=0)throw Error('Known native initial tempo required');
 if(job.complete_score!==undefined&&typeof job.complete_score!=='boolean')throw Error('Explicit boolean complete-score request required');
 if(!Array.isArray(masterBars)||!masterBars.length)throw Error('Known native traversal required');
 const complete=job.complete_score===true;
 let start,end;
 if(complete){
  if(!Number.isSafeInteger(sourceBarCount)||sourceBarCount<1||job.start_bar!==1||job.end_bar!==sourceBarCount
    ||masterBars[0].masterBar.index!==0||masterBars.at(-1).masterBar.index!==sourceBarCount-1)
   throw Error('Complete score requires the full native traversal and declared source endpoints');
  if(masterBars.some((b,i)=>!Number.isSafeInteger(b.masterBar.index)||b.masterBar.index<0||b.masterBar.index>=sourceBarCount
    ||(i===0?b.start!==0:b.start!==masterBars[i-1].end)))
   throw Error('Complete score requires a continuous native traversal');
  start=0;end=masterBars.length-1;
 }else{
  start=masterBars.findIndex(b=>b.masterBar.index===job.start_bar-1);
  end=masterBars.findIndex((b,i)=>i>=start&&b.masterBar.index===job.end_bar-1);
  if(start<0||end<start||end-start>16)throw Error('Unresolved passage playback range');
 }
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
