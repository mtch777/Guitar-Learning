#!/usr/bin/env node
import fs from 'node:fs';import path from 'node:path';
import {FUSION_MODELS,fitIsotonic} from '../src/classifier/isotonic-fusion.js';
const [, , fixture,out]=process.argv;
if(!fixture||!out)throw Error('usage: node export_step18_fusion_calibrators.mjs oof_fixture.json out.json');
const {rows}=JSON.parse(fs.readFileSync(fixture));
if(rows.length!==384)throw Error('Expected 384 OOF rows');
const result=Object.fromEntries(FUSION_MODELS.map(name=>[name,fitIsotonic(
  rows.map(r=>r[name+'_conf']),rows.map(r=>Number(r[name+'_pred']===r.string))
)]));
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(result));
console.log('Fitted final isotonic curves from 384 preserved OOF predictions');
