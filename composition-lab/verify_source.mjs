// Independent notation-time (not grace performance scheduling) GP comparison.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath, gp, canonicalPath, output] = process.argv.slice(2);
const at=await import(pathToFileURL(path.resolve(modulePath)));
const score=at.importer.ScoreLoader.loadScoreFromBytes(fs.readFileSync(gp));
const expected=JSON.parse(fs.readFileSync(canonicalPath,'utf8'));
const q=x=>{const [a,b='1']=String(x).split('/');return Number(a)/Number(b);};
let notes=0,beats=0,tieDestinations=0;const mismatches=[];const techniqueDifferences=[];
for(const [ti,t] of expected.tracks.entries()) for(const [mi,m] of t.measures.entries()) for(const [vi,v] of m.voices.entries()) {
  const actual=score.tracks[ti].staves[0].bars[mi].voices[vi]?.beats??[];
  for(const [ei,e] of v.entries()) {
    beats++;notes+=e.notes.length;const b=actual[ei];
    if(!b){mismatches.push({ti,mi,vi,ei,type:'missing_beat'});continue;}
    tieDestinations+=b.notes.filter(n=>n.isTieDestination).length;
    if(Math.abs(b.displayStart-q(e.local_onset_q)*960)>1e-6 || Math.abs(b.displayDuration-q(e.duration_q)*960)>1e-6)
      mismatches.push({ti,mi,vi,ei,type:'notation_timing',actual:[b.displayStart,b.displayDuration],expected:[q(e.local_onset_q)*960,q(e.duration_q)*960]});
    const left=b.notes.map(n=>n.isPercussion ? (score.tracks[ti].percussionArticulations[n.percussionArticulation]?.outputMidiNumber??n.realValue) : n.realValue).sort((a,b)=>a-b);
    const right=e.notes.map(n=>n.midi).sort((a,b)=>a-b);
    if(JSON.stringify(left)!==JSON.stringify(right)) {
      const detail={ti,mi,vi,ei,type:'pitch',actual:left,expected:right};
      if(e.notes.some(n=>(n.property_names??[]).includes('HarmonicType'))) techniqueDifferences.push({...detail,reason:'GP stored pitch versus sounding harmonic; not assumed equivalent'});
      else mismatches.push(detail);
    }
  }
}
const report={reader:'alphaTab 1.8.4',source:path.basename(gp),beats,notes,tieDestinations,soundingAttacks:notes-tieDestinations,mismatches,techniqueDifferences,
  scope:'notation display time; grace performance time is independently scheduled by alphaTab',listening_judgment:null};
fs.writeFileSync(output,JSON.stringify(report,null,2));
console.log(JSON.stringify({...report,mismatches:mismatches.length,techniqueDifferences:techniqueDifferences.length,examples:mismatches.slice(0,3)}));
if(mismatches.length)process.exitCode=1;
