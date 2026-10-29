// Address actual source occurrences, including coattacks split across voices.
export function address(ref){
  const fields=ref.split(':');
  if(fields.length!==7||fields[0]!=='event')throw Error('Invalid source note address');
  const [song,part,bar,voice,beat,note]=fields.slice(1).map(Number);
  if([song,part,bar,voice,beat,note].some(x=>!Number.isInteger(x)||x<0)||bar<1)throw Error('Invalid numeric source address');
  return {song,part,bar,voice,beat,note};
}
export function sourceNote(doc,a){
  if(doc.partId!==a.part||doc.songId!==a.song)throw Error('Source document identity mismatch');
  const note=doc.measures[a.bar-1]?.voices[a.voice]?.beats[a.beat]?.notes[a.note];
  if(!note)throw Error('Source note not addressable');
  return note;
}
export function sharedTargetBeat(score,addresses){
  if(!addresses.length)throw Error('Empty target');
  const first=addresses[0];
  if(addresses.some(a=>a.part!==first.part||a.bar!==first.bar))throw Error('Coattack changes part/bar scope');
  const beats=addresses.map(a=>score.tracks[a.part]?.staves[0]?.bars[a.bar-1]?.voices[a.voice]?.beats[a.beat]);
  if(beats.some(b=>!b||!Number.isFinite(b.playbackStart)||!Number.isFinite(b.playbackDuration)||b.playbackDuration<=0)||
     new Set(beats.map(b=>b.playbackStart)).size!==1||new Set(beats.map(b=>b.playbackDuration)).size!==1)
    throw Error('Actual GP target members lack a shared onset/duration');
  return beats[0];
}
