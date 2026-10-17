// Independent alphaTab occurrence pitch/string/fret verification; no listening claim.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const [modulePath,...files]=process.argv.slice(2);const at=await import(pathToFileURL(path.resolve(modulePath)));
for(const file of files){
 const allExpected=JSON.parse(fs.readFileSync(file.replace(/\.gp$/i,'.expected.json'),'utf8'));const expected=allExpected.filter(n=>n.string!==null);
 const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)));
 const actual=[];
 for(const [ti,t] of score.tracks.entries())for(const [si,s] of t.staves.entries()){
  if(si!==0)throw new Error('Multiple staves unsupported');
  for(const [mi,b] of s.bars.entries())for(const [vi,v] of b.voices.entries())for(const [ei,e] of v.beats.entries())for(const [ni,n] of e.notes.entries())if(n.isStringed)actual.push({location:`${ti}:${mi}:${vi}:${ei}:${ni}`,midi:n.realValueWithoutHarmonic,string:n.string-1,fret:n.fret});
 }
 if(JSON.stringify(actual)!==JSON.stringify(expected)){
  const i=actual.findIndex((n,i)=>JSON.stringify(n)!==JSON.stringify(expected[i]));throw new Error(JSON.stringify({file,index:i,actual:actual[i],expected:expected[i],counts:[actual.length,expected.length]}));
 }
 console.log(JSON.stringify({file,stringedNotes:actual.length,allStringedOccurrencesAgree:true,scope:'Written fretted pitch; harmonic sounding pitch and percussion excluded'}));
}


