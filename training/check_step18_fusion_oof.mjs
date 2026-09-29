#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';
import {extractRingingFeatures,prepareRingingAudio} from '../src/classifier/ringing-features.js';
import {harmonicFusionFeatures} from '../src/classifier/harmonic-fusion-features.js';
import {earlyMfccFusionFeatures} from '../src/classifier/early-mfcc-fusion-features.js';
import {predictFusionModel,maskFusionProbabilities} from '../src/classifier/xgboost-fusion-model.js';
import {crossFitFusion} from '../src/classifier/isotonic-fusion.js';
const [, , pythonJson, modelsDir, audioDir, outJson] = process.argv;
if(!outJson)throw Error('usage: node check_step18_fusion_oof.mjs python_probs.json models_dir trimmed_f32_dir out.json');
const rawAudio=process.argv.includes('--raw');
const rows=JSON.parse(fs.readFileSync(pythonJson));
const modelCache=new Map(),out=[],stats=Object.fromEntries(['baseline','harmonic','mfcc'].map(x=>[x,{rawMatches:0,maskedMatches:0,maxAbs:0}]));
for(const row of rows){
  let models=modelCache.get(row.midi);
  if(!models){models=Object.fromEntries(['baseline','harmonic','mfcc'].map(name=>[name,JSON.parse(fs.readFileSync(path.join(modelsDir,`midi_${row.midi}`,`${name}.json`)))]));modelCache.set(row.midi,models);}
  const bytes=fs.readFileSync(path.join(audioDir,row.file+'.f32'));
  const samples=new Float32Array(bytes.buffer,bytes.byteOffset,bytes.byteLength/4);
  const y=rawAudio?prepareRingingAudio(samples,44100):samples;
  const base=extractRingingFeatures(y,22050,{preprocessed:true});
  const features={baseline:base,harmonic:[...base,...harmonicFusionFeatures(y,22050,row.midi)],mfcc:earlyMfccFusionFeatures(y)};
  const result={file:row.file,midi:row.midi,string:row.string};
  for(const name of ['baseline','harmonic','mfcc']){
    const p=predictFusionModel(models[name],features[name]),q=row[name+'_probabilities'],s=stats[name];
    s.rawMatches+=Number(p.indexOf(Math.max(...p))===q.indexOf(Math.max(...q)));
    const mp=maskFusionProbabilities(p,row.midi),mq=maskFusionProbabilities(q,row.midi);
    s.maskedMatches+=Number(mp.indexOf(Math.max(...mp))===mq.indexOf(Math.max(...mq)));
    for(let i=0;i<8;i++)s.maxAbs=Math.max(s.maxAbs,Math.abs(p[i]-q[i]));
    result[name+'_pred']=mp.indexOf(Math.max(...mp))+1;result[name+'_conf']=Math.max(...mp);
    result[name+'_python_pred']=mq.indexOf(Math.max(...mq))+1;result[name+'_python_conf']=Math.max(...mq);
  }
  out.push(result);
}
const report={recordings:rows.length,models:stats};
if(rows.length===384){
  for(const kind of ['','_python']){
    const inputs=out.map(r=>({file:r.file,midi:r.midi,string:r.string,
      ...Object.fromEntries(['baseline','harmonic','mfcc'].flatMap(name=>[[name+'_pred',r[name+kind+'_pred']],[name+'_conf',r[name+kind+'_conf']]]))}));
    const fusion=crossFitFusion(inputs);report[kind?'pythonFeatures':'browserFeatures']={correct:fusion.filter(x=>x.string===x.true_string).length,
      predictions:Object.fromEntries(fusion.map(x=>[x.file,x.string]))};
  }
  report.fusionDecisionAgreement=out.filter(r=>report.browserFeatures.predictions[r.file]===report.pythonFeatures.predictions[r.file]).length;
}
fs.mkdirSync(path.dirname(outJson),{recursive:true});fs.writeFileSync(outJson,JSON.stringify({report,rows:out}));
const concise={...report};delete concise.browserFeatures?.predictions;delete concise.pythonFeatures?.predictions;
console.log(JSON.stringify(concise,null,2));
if(Object.values(stats).some(s=>s.maskedMatches!==rows.length))process.exitCode=1;
