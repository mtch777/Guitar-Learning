// Independent alphaTab curve comparison. Expected nested bars/voices/beats/notes
// are generated privately from the edited GPIF, not committed source material.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath,trackIndex,...files]=process.argv.slice(2);
if(!files.length)throw new Error('Usage: node verify_bend_curves.mjs ALPHATAB_MODULE TRACK FILE.gp ...');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const fraction=x=>{const [a,b='1']=String(x).split('/');return Number(a)/Number(b);};
function value(points,x){
  if(!points.length)return 0;
  if(x<=points[0][0])return points[0][1];
  for(let i=1;i<points.length;i++){
    const [a,v]=points[i-1],[b,w]=points[i];
    if(x<=b)return b===a?w:v+(w-v)*(x-a)/(b-a);
  }
  return points.at(-1)[1];
}
for(const file of files){
  const expected=JSON.parse(fs.readFileSync(file.replace(/\.gp$/i,'.curves.json'),'utf8'));
  const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
  const bars=score.tracks[Number(trackIndex)].staves[0].bars;
  let notes=0,bends=0,maxError=0;
  if(bars.length!==expected.length)throw new Error('Bar count mismatch');
  for(const [mi,voices] of expected.entries())for(const [vi,beats] of voices.entries())for(const [bi,ns] of beats.entries()){
    const actual=bars[mi].voices[vi]?.beats[bi]?.notes;
    if(!actual||actual.length!==ns.length)throw new Error(`Note alignment mismatch ${mi}/${vi}/${bi}`);
    for(const [ni,bend] of ns.entries()){
      const x=bend?bend.points.map(p=>[fraction(p.offset_fraction),fraction(p.semitones)]):[];
      const y=(actual[ni].bendPoints??[]).map(p=>[p.offset/60,p.value/2]);
      const positions=[...Array.from({length:101},(_,i)=>i/100),...x.map(p=>p[0]),...y.map(p=>p[0])];
      for(const q of positions)maxError=Math.max(maxError,Math.abs(value(x,q)-value(y,q)));
      notes++;if(bend)bends++;
    }
  }
  if(maxError>1e-6)throw new Error(`Independent curve mismatch ${file}: ${maxError} semitones`);
  console.log(JSON.stringify({file,notes,bendSegments:bends,maxSemitoneError:maxError,curveFidelityVerified:true}));
}
