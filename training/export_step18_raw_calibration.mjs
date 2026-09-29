#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';
import {maskFusionProbabilities} from '../src/classifier/xgboost-fusion-model.js';
import {FUSION_MODELS,fitIsotonic} from '../src/classifier/isotonic-fusion.js';
const [, , oofPath,out]=process.argv;
if(!out)throw Error('usage: node export_step18_raw_calibration.mjs python_oof_probabilities.json out.json');
const rows=JSON.parse(fs.readFileSync(oofPath));if(rows.length!==384)throw Error('Expected 384 OOF rows');
const calibrators=Object.fromEntries(FUSION_MODELS.map(name=>{
 const masked=rows.map(r=>maskFusionProbabilities(r[name+'_probabilities'],r.midi));
 const conf=masked.map(p=>Math.max(...p));const correct=masked.map((p,i)=>Number(p.indexOf(Math.max(...p))+1===rows[i].string));
 return [name,fitIsotonic(conf,correct)];
}));
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(calibrators));
console.log('Fitted final curves from 384 raw-JS-domain held-out predictions');
