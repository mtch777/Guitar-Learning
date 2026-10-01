import fs from 'node:fs';
import assert from 'node:assert/strict';
import {LivePipelineEngine} from '../src/input/live-pipeline-engine.js';
const root='training/data/live_2026-09-30',manifest=JSON.parse(fs.readFileSync(root+'/manifest.json'));
const models=Object.fromEntries(['baseline','harmonic','mfcc'].map(n=>[n,JSON.parse(fs.readFileSync(`public/model/fusion3-live/${n}.json`))]));
const calibrators=JSON.parse(fs.readFileSync('public/model/fusion3-live/calibrators.json'));
assert.equal(manifest.records.length,23);assert(!manifest.records.some(r=>r.string===7&&r.fret===12));
for(const r of manifest.records){
 const b=fs.readFileSync(root+'/'+r.file);let offset=12,raw;
 while(offset<b.length){const size=b.readUInt32LE(offset+4);if(b.toString('ascii',offset,offset+4)==='data'){raw=b.subarray(offset+8,offset+8+size);break;}offset+=8+size+(size%2);}
 const pcm=new Float32Array(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.length));
 const engine=new LivePipelineEngine({models,calibrators},r.sampleRate,{routeNames:['hybrid'],retainHistory:false,includePluck:true});const events=[];
 for(let i=0;i+4096<=pcm.length;i+=4096)events.push(...engine.push(pcm.slice(i,i+4096)).events);
 assert.equal(events.length,r.hybridEvents.length,r.file);
 events.forEach((e,i)=>{const saved=r.hybridEvents[i];for(const key of ['midi','string','fret','model','captureStartMs','captureEndMs'])assert.equal(e[key],saved[key],r.file+':'+key);assert(Math.abs(e.confidence-saved.confidence)<1e-6);});
 assert.equal(events[0].string,r.string);assert.equal(events[0].fret,r.fret);assert.equal(engine.frames.length,0);assert.equal(engine.routes.hybrid.events.length,0);
}
console.log('23/23 live WAVs: lesson hybrid matches archived pilot decisions and capture timing; no retained session history; accidental-pluck file excluded.');
