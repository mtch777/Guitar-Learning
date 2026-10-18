// Independent alphaTab flags against private occurrence-indexed expectations.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath,...files]=process.argv.slice(2);
if(!files.length)throw new Error('Usage: node verify_note_flags.mjs MODULE FILE.gp ...');
const at=await import(pathToFileURL(path.resolve(modulePath)));
for(const file of files){
 const expected=JSON.parse(fs.readFileSync(file.replace(/\.gp$/i,'.flags.json'),'utf8'));
 const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
 const seen=new Set();let muted=0;
 for(const[ti,t]of score.tracks.entries())for(const[si,s]of t.staves.entries()){
  if(si!==0)throw new Error('Unsupported multistaff flag mapping');
  for(const[mi,b]of s.bars.entries())for(const[vi,v]of b.voices.entries())for(const[bi,e]of v.beats.entries())for(const[ni,n]of e.notes.entries()){
   const id=`${ti}:${mi+1}:${vi}:${bi}:${ni}`;
   if(!(id in expected))throw new Error('Missing expected occurrence '+id);
   if(n.isPalmMute!==expected[id].palmMute)throw new Error('Palm mute mismatch '+id);
   seen.add(id);if(n.isPalmMute)muted++;
  }
 }
 if(seen.size!==Object.keys(expected).length)throw new Error('Occurrence coverage mismatch');
 console.log(JSON.stringify({file,notes:seen.size,palmMutedNotes:muted,allPalmMuteFlagsAgree:true}));
}
