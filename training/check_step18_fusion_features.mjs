#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { extractRingingFeatures } from '../src/classifier/ringing-features.js';
import { harmonicFusionFeatures } from '../src/classifier/harmonic-fusion-features.js';
import { earlyMfccFusionFeatures } from '../src/classifier/early-mfcc-fusion-features.js';
import { predictFusionModel, maskFusionProbabilities } from '../src/classifier/xgboost-fusion-model.js';
const [, , vectorsPath, audioDir, modelDir] = process.argv;
if (!vectorsPath || !audioDir || !modelDir) throw new Error('usage: node check_step18_fusion_features.mjs vectors.json trimmed_f32_dir model_dir');
const rows = JSON.parse(fs.readFileSync(vectorsPath, 'utf8'));
const models = Object.fromEntries(['baseline','harmonic','mfcc'].map(name => [name, JSON.parse(fs.readFileSync(path.join(modelDir, `${name}.json`)))]));
const stats = Object.fromEntries(['baseline','harmonic','mfcc'].map(name => [name, { maxFeatureAbs: 0, featureSquares: 0, featureCount: 0, rawArgmaxMatch: 0, maskedArgmaxMatch: 0, maxProbabilityAbs: 0 }]));
const start=performance.now();
for (const row of rows) {
  const bytes=fs.readFileSync(path.join(audioDir, `${row.file}.f32`));
  const y=new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength/4);
  const base=extractRingingFeatures(y,22050,{preprocessed:true});
  const featureBy={ baseline: base, harmonic: [...base, ...harmonicFusionFeatures(y,22050,row.midi)], mfcc: earlyMfccFusionFeatures(y) };
  for (const [name, feature] of Object.entries(featureBy)) {
    const s=stats[name], expectedFeature=row[`${name}_features`];
    if(feature.length!==expectedFeature.length)throw Error(`${name} feature count mismatch`);
    for(let i=0;i<feature.length;i++){const d=feature[i]-expectedFeature[i];s.maxFeatureAbs=Math.max(s.maxFeatureAbs,Math.abs(d));s.featureSquares+=d*d;s.featureCount++;}
    const p=predictFusionModel(models[name],feature),q=row[`${name}_probabilities`];
    s.rawArgmaxMatch+=Number(p.indexOf(Math.max(...p))===q.indexOf(Math.max(...q)));
    const mp=maskFusionProbabilities(p,row.midi),mq=maskFusionProbabilities(q,row.midi);
    s.maskedArgmaxMatch+=Number(mp.indexOf(Math.max(...mp))===mq.indexOf(Math.max(...mq)));
    for(let i=0;i<8;i++)s.maxProbabilityAbs=Math.max(s.maxProbabilityAbs,Math.abs(p[i]-q[i]));
  }
}
for (const s of Object.values(stats)) {s.featureRmse=Math.sqrt(s.featureSquares/s.featureCount);delete s.featureSquares;}
const report={recordings:rows.length,runtimeMs:performance.now()-start,models:stats};
console.log(JSON.stringify(report,null,2));
if(Object.values(stats).some(s=>s.maskedArgmaxMatch!==rows.length||s.maxFeatureAbs>0.002))process.exitCode=1;
