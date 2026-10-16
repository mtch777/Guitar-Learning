// Independent directed HOPO linkage check against alphaTab's actual note graph.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath,source,reportPath]=process.argv.slice(2);
if(!reportPath)throw new Error('Usage: node verify_technique_links.mjs ALPHATAB SOURCE.gp REPORT.json');
const at=await import(pathToFileURL(path.resolve(modulePath)));
const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(source)));
const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
const locations=new Map();const notes=[];
for(const [ti,t] of score.tracks.entries())for(const [si,s] of t.staves.entries()){
  if(si!==0)throw new Error('Multi-staff linkage mapping not yet supported');
  for(const [mi,b] of s.bars.entries())for(const [vi,v] of b.voices.entries())for(const [bi,beat] of v.beats.entries())
    for(const [ni,n] of beat.notes.entries()){locations.set(n,`${ti}:${mi+1}:${vi}:${bi}:${ni}`);notes.push(n);}
}
const actual=new Set(notes.filter(n=>n.hammerPullDestination).map(n=>`${locations.get(n)}>${locations.get(n.hammerPullDestination)}`));
const expected=new Set(report.tracks.flatMap(t=>t.explicit_hopo).map(p=>`${p.origin_markers[0]}>${p.destination}`));
const missing=[...expected].filter(x=>!actual.has(x)),extra=[...actual].filter(x=>!expected.has(x));
if(missing.length||extra.length)throw new Error(JSON.stringify({missing,extra}));
console.log(JSON.stringify({source,explicitPairs:expected.size,independentPairs:actual.size,allDirectedLinksAgree:true}));
