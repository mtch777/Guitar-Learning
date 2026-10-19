// Compare selected GPIF-written contours with native-reader contours, not audio.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath,file,expectedPath]=process.argv.slice(2);
if(!expectedPath)throw Error('Usage: verify_window_curves.mjs MODULE SCORE.gp EXPECTED.json');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
const expected=JSON.parse(fs.readFileSync(expectedPath,'utf8'));
const fraction=x=>{const [a,b=1]=String(x).split('/').map(Number);return a/b;};
function value(points,x){
 if(!points.length)return 0;
 if(x<=points[0][0])return points[0][1];
 for(let i=1;i<points.length;i++){
  const [a,v]=points[i-1],[b,w]=points[i];
  if(x<=b)return b===a?w:v+(w-v)*(x-a)/(b-a);
 }
 return points.at(-1)[1];
}
let checked=0,bends=0,maxError=0;
for(const [identity,shape] of Object.entries(expected)){
 const [ti,mi,vi,bi,ni]=identity.split(':').map(Number);
 const note=score.tracks[ti]?.staves[0]?.bars[mi-1]?.voices[vi]?.beats[bi]?.notes[ni];
 if(!note)throw Error('Missing native occurrence '+identity);
 const want=(shape?.points??[]).map(p=>[fraction(p.offset_fraction),fraction(p.semitones)]);
 const actual=(note.bendPoints??[]).map(p=>[p.offset/60,p.value/2]);
 if([...want,...actual].some(([x,y])=>!Number.isFinite(x)||!Number.isFinite(y)||x<0||x>1))throw Error('Invalid normalized curve '+identity);
 if(Boolean(want.length)!==Boolean(actual.length))throw Error('Curve presence mismatch '+identity);
 const grid=new Set([...want.map(p=>p[0]),...actual.map(p=>p[0]),...Array.from({length:61},(_,i)=>i/60)]);
 for(const x of grid){const error=Math.abs(value(want,x)-value(actual,x));maxError=Math.max(maxError,error);if(error>1e-8)throw Error('Written/native curve mismatch '+identity+' at '+x+': '+error);}
 checked++;if(want.length)bends++;
}
if(!checked)throw Error('Empty contour verification scope');
console.log(JSON.stringify({file,checked,bends,maxError,scope:'Selected written/native contours; not acoustic execution or listening'}));
