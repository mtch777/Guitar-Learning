// Independent ordinary-reader gate: deliberately no bridge/importer workarounds.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';
const [modulePath,corpus]=process.argv.slice(2),at=await import(pathToFileURL(path.resolve(modulePath)));
const root=path.join(corpus,'gp-files');let passed=0;const fail=[];
for(const file of fs.readdirSync(root).filter(n=>n.endsWith('.gp'))){
 try{const score=at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(path.join(root,file))));if(!score.tracks.length||!score.masterBars.length)throw Error('Empty score');passed++;}
 catch(error){fail.push({file,error:String(error)});}
}
fs.writeFileSync(path.join(corpus,'vanilla-imports.json'),JSON.stringify({passed,fail},null,2));
console.log(JSON.stringify({passed,fail}));if(fail.length||!passed)process.exitCode=1;
