#!/usr/bin/env node
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { LivePipelineEngine } from '../src/input/live-pipeline-engine.js';
import { predictFusionModel,maskFusionProbabilities } from '../src/classifier/xgboost-fusion-model.js';
import { fitIsotonic,FUSION_MODELS } from '../src/classifier/isotonic-fusion.js';
import { trialZip } from '../src/input/trial-archive.js';
const [,,sourcePath,rawDir,foldDir,featuresPath,pythonPath,outPath]=process.argv;
const source=JSON.parse(fs.readFileSync(sourcePath));
const oof=JSON.parse(fs.readFileSync(`${foldDir}/python_oof_probabilities.json`));
const detected=JSON.parse(fs.readFileSync('training/results/reference/step18_reference_yin_midi_384.json'));
const cache=new Map();
function heldout(midi){if(!cache.has(midi)){
  const train=oof.filter(r=>r.midi!==midi);
  cache.set(midi,{models:Object.fromEntries(FUSION_MODELS.map(n=>[n,JSON.parse(fs.readFileSync(`${foldDir}/midi_${midi}/${n}.json`))])),
    calibrators:Object.fromEntries(FUSION_MODELS.map(n=>{const p=train.map(r=>maskFusionProbabilities(r[n+'_probabilities'],detected[r.file]));
      return [n,fitIsotonic(p.map(p=>Math.max(...p)),p.map((p,i)=>Number(p.indexOf(Math.max(...p))+1===train[i].string)))];}))});
}return cache.get(midi);}
const targets=source.rows.filter(r=>(r.true_midi>=54&&r.true_midi<=60&&r.file.includes('_normal_'))||[27,32,51,87].includes(r.true_midi));
let compared=0;
for(const r of targets){const bytes=fs.readFileSync(`${rawDir}/${r.file}.f32`),raw=new Float32Array(bytes.buffer,bytes.byteOffset,bytes.byteLength/4);
  const engine=new LivePipelineEngine(heldout(r.true_midi),44100);
  for(let i=0;i+4096<=raw.length;i+=4096){engine.push(raw.subarray(i,i+4096));if(engine.routes.hybrid.events.length)break;}
  const e=engine.routes.hybrid.events[0];assert.equal(!!e,!!r.fusion,r.file);
  if(e){assert.equal(e.midi,r.fusion.midi,r.file);assert.equal(e.string,r.fusion.string,r.file);assert.equal(e.captureEndMs,r.capture_ms,r.file);}compared++;
}
const features=JSON.parse(fs.readFileSync(featuresPath)),python=JSON.parse(fs.readFileSync(pythonPath));
const final={models:Object.fromEntries(FUSION_MODELS.map(n=>[n,JSON.parse(fs.readFileSync(`public/model/fusion3-live/${n}.json`))])),
  calibrators:JSON.parse(fs.readFileSync('public/model/fusion3-live/calibrators.json'))};
let maxDifference=0,decisions=0;
for(const n of FUSION_MODELS)for(let i=0;i<features.length;i++){
 const p=predictFusionModel(final.models[n],features[i][n+'_features']),ref=python[n][i];
 assert.equal(p.indexOf(Math.max(...p)),ref.indexOf(Math.max(...ref)));
 for(let k=0;k<8;k++)maxDifference=Math.max(maxDifference,Math.abs(p[k]-ref[k]));decisions++;
}assert.ok(maxDifference<1e-5);
for(const sr of [44100,48000]){
 const silent=new LivePipelineEngine(final,sr);for(let i=0;i<16;i++)silent.push(new Float32Array(4096));
 assert.equal(silent.routes.hybrid.events.length,0);assert.equal(silent.routes.correlation.events.length,0);
 const tone=new LivePipelineEngine(final,sr);for(let i=0;i<18;i++){
   const samples=Float32Array.from({length:4096},(_,j)=>i<2?0:.1*Math.sin(2*Math.PI*155.56349186104046*(i*4096+j)/sr));tone.push(samples);
 }assert.equal(tone.routes.hybrid.events[0]?.midi,51);
}
let Capture;const messages=[];
const sandbox={AudioWorkletProcessor:class{constructor(){this.port={postMessage:(d)=>messages.push(d)};}},
  registerProcessor:(_,c)=>{Capture=c;},sampleRate:44100,currentTime:0,Float32Array};
vm.runInNewContext(fs.readFileSync('public/live-pipeline-capture.js','utf8'),sandbox);
const capture=new Capture({processorOptions:{channel:1}});
for(let i=0;i<64;i++)capture.process([[new Float32Array(128),new Float32Array(128).fill(.25)]]);
assert.equal(messages.length,2);assert.deepEqual(messages.map(m=>m.sequence),[0,1]);
for(const m of messages)assert.ok([...new Float32Array(m.samples)].every(v=>v===.25));
capture.process([[new Float32Array(128)]]);assert.ok(messages.some(m=>m.type==='channel-error'));
const pcm=Float32Array.of(0,.25,-.5,1,-1),zip=trialZip({schema:'test'},[{id:'test',pcm,report:{sampleRate:44100}}]);
fs.writeFileSync('/tmp/live_pipeline_export_test.zip',Buffer.from(await zip.arrayBuffer()));
const report={heldout_callback_parity:compared,model_python_js_argmax_matches:decisions,
  model_max_probability_difference:maxDifference,sample_rates_checked:[44100,48000],
  silent_false_events:0,audio_worklet_channel2_blocks:2,export_zip:'/tmp/live_pipeline_export_test.zip'};
fs.writeFileSync(outPath,JSON.stringify(report,null,2));console.log(report);
