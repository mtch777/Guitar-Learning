// GP5 NoteType cannot express both dead and tied. Restore the source dead flag
// only on identity-checked regular tied destinations before native GP7 export.
export function restoreDeadTies(track, raw) {
 let restored=0,checked=0,skippedGrace=0;
 for(const [mi,measure] of (raw.measures||[]).entries())for(const [vi,voice] of (measure.voices||[]).entries()){
  const beats=voice.beats||[];
  skippedGrace+=beats.filter(b=>b.graceNote).reduce((n,b)=>n+(b.notes||[]).filter(x=>x.dead&&x.tie&&!x.rest).length,0);
  const expected=beats.filter(b=>!b.graceNote);
  if(!expected.some(b=>(b.notes||[]).some(n=>n.dead&&n.tie&&!n.rest)))continue;
  if(raw.instrumentId===1024)throw Error('Dead-tie restoration excludes percussion');
  if(track.staves.length!==1)throw Error('Dead-tie restoration requires one restored staff');
  const staff=track.staves[0],actual=(staff.bars[mi]?.voices[vi]?.beats||[]).filter(b=>b.graceType===0&&!b.isEmpty);
  if(expected.length!==actual.length)throw Error(`Dead-tie beat alignment mismatch at ${mi}:${vi}`);
  for(let bi=0;bi<expected.length;bi++)for(const source of expected[bi].notes||[]){
   if(!source.dead||!source.tie||source.rest)continue;
   const target=actual[bi].notes.filter(n=>staff.tuning.length-n.string===source.string);
   if(target.length!==1||!target[0].isTieDestination||target[0].fret!==source.fret)throw Error(`Dead-tie note identity mismatch at ${mi}:${vi}:${bi}`);
   checked++;if(!target[0].isDead){target[0].isDead=true;restored++;}
  }
 }
 return {checked,restored,skippedGrace};
}
