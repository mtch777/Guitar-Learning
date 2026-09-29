#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';
import {prepareRingingAudio,extractRingingFeatures} from '../src/classifier/ringing-features.js';
import {harmonicFusionFeatures} from '../src/classifier/harmonic-fusion-features.js';
import {earlyMfccFusionFeatures} from '../src/classifier/early-mfcc-fusion-features.js';
const [, , sourceRows,rawDir,out,pitchPath]=process.argv;
if(!out)throw Error('usage: node export_step18_raw_js_features.mjs rows.json raw_f32_dir output.json [detected_midi.json]');
const detected=pitchPath?JSON.parse(fs.readFileSync(pitchPath)):null;
const source=JSON.parse(fs.readFileSync(sourceRows));
const rows=Array.isArray(source)?source:source.rows;
const output=[];let totalMs=0;
for(const [i,row] of rows.entries()){
 const bytes=fs.readFileSync(path.join(rawDir,row.file+'.f32'));
 const samples=new Float32Array(bytes.buffer,bytes.byteOffset,bytes.byteLength/4);
 const start=performance.now(),y=prepareRingingAudio(samples,44100);
 const featureMidi=detected?detected[row.file]:row.midi;
 if(!Number.isInteger(featureMidi))throw Error(`Missing detected MIDI for ${row.file}`);
 const baseline=extractRingingFeatures(y,22050,{preprocessed:true}),harmonic=[...baseline,...harmonicFusionFeatures(y,22050,featureMidi)],mfcc=earlyMfccFusionFeatures(y);
 const ms=performance.now()-start;totalMs+=ms;
 output.push({file:row.file,midi:row.midi,string:row.string,feature_midi:featureMidi,
  baseline_features:Array.from(baseline),harmonic_features:harmonic,mfcc_features:Array.from(mfcc),feature_runtime_ms:ms});
 if(i===0||(i+1)%50===0)console.log(`RAW JS FEATURE [${i+1}/${rows.length}]`);
}
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(output));
console.log(JSON.stringify({recordings:output.length,mean_feature_ms:totalMs/output.length}));
