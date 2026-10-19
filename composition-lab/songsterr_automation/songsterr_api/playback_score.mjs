// Routine playback discovers an adjacent, hash-bound bend companion.
import fs from 'node:fs';
import path from 'node:path';
import {loadWithExactBends} from './bend_fidelity.mjs';

export function loadPlaybackScore(at,file,job={}) {
 const data=fs.readFileSync(file);
 const adjacent=file.slice(0,file.length-path.extname(file).length)+'.exact-model-bends.json';
 const explicit=typeof job.exact_model_bends==='string';
 const sidecarPath=job.exact_model_bends===false?null:explicit?job.exact_model_bends:fs.existsSync(adjacent)?adjacent:null;
 const sidecarData=sidecarPath?fs.readFileSync(sidecarPath):null;
 const restored=sidecarData?loadWithExactBends(at,data,JSON.parse(sidecarData.toString('utf8'))):null;
 const score=restored?restored.score:at.importer.ScoreLoader.loadScoreFromBytes(data);
 return {data,score,restored,sidecarData,sidecarPath,
         companion_selection:restored?(explicit?'explicit':'adjacent'):job.exact_model_bends===false?'disabled':'absent'};
}
