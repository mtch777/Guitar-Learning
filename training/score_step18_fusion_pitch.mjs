#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';
import {maskFusionProbabilities} from '../src/classifier/xgboost-fusion-model.js';
import {crossFitFusion,FUSION_MODELS} from '../src/classifier/isotonic-fusion.js';
const [, , probsPath,pitchPath,out,...flags]=process.argv;
if(!out)throw Error('usage: node score_step18_fusion_pitch.mjs oof_probs.json pitch_midi.json out.json [--smoke]');
const rows=JSON.parse(fs.readFileSync(probsPath)),pitch=JSON.parse(fs.readFileSync(pitchPath));
if(rows.length!==384&&!(flags.includes('--smoke')&&rows.length===36))throw Error('Expected 384 OOF probabilities or 36 smoke rows');
const inputs=rows.map(r=>{
 const detected=pitch[r.file],entry={file:r.file,midi:r.midi,string:r.string,detected_midi:detected};
 for(const name of FUSION_MODELS){const p=maskFusionProbabilities(r[name+'_probabilities'],detected);
  entry[name+'_pred']=p.indexOf(Math.max(...p))+1;entry[name+'_conf']=Math.max(...p);}
 return entry;
});
const subset=flags.includes('--smoke')?new Set(inputs.filter(r=>r.midi>=54&&r.midi<=60&&r.file.includes('_normal_')).map(r=>r.file)):null;
const predictions=crossFitFusion(inputs,subset),source=new Map(inputs.map(r=>[r.file,r]));
const outputs=predictions.map(p=>({...p,detected_midi:source.get(p.file).detected_midi,
 pitch_correct:source.get(p.file).detected_midi===p.midi,
 tuple_correct:source.get(p.file).detected_midi===p.midi&&p.string===p.true_string}));
const report={phase:subset?'smoke':'real',recordings:outputs.length,pitch_correct:outputs.filter(x=>x.pitch_correct).length,
 string_correct_all:outputs.filter(x=>x.string===x.true_string).length,tuple_correct:outputs.filter(x=>x.tuple_correct).length};
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify({report,predictions:outputs}));console.log(report);
