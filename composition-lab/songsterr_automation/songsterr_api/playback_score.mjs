// Routine playback discovers an adjacent, hash-bound bend companion.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadWithExactBends} from './bend_fidelity.mjs';
import {registerContinuousMutePlayback} from './continuous_mute_playback.mjs';
import {restoreHammerPullThroughTies} from './restore_hammer_pull_through_ties.mjs';

const POLICY_SCHEMA='composition-lab.execution-policy/1';
const POLICY_NAME='composition-lab.continuous-mute-terminal-release/1';
const hash=data=>createHash('sha256').update(data).digest('hex');
function verifyExecutionPolicy(receipt,data,sidecarData){
 const keys=['exact_model_bends_sha256','gp_sha256','policy','schema'];
 if(!receipt||typeof receipt!=='object'||Array.isArray(receipt)||
    JSON.stringify(Object.keys(receipt).sort())!==JSON.stringify(keys)||
    receipt.schema!==POLICY_SCHEMA||receipt.policy!==POLICY_NAME)
  throw Error('Unsupported or non-closed playback execution policy receipt');
 if(receipt.gp_sha256!==hash(data))throw Error('Playback execution policy GP hash mismatch');
 const bendHash=sidecarData?hash(sidecarData):null;
 if(receipt.exact_model_bends_sha256!==bendHash)throw Error('Playback execution policy bend companion hash mismatch');
}

export function loadPlaybackScore(at,file,job={}) {
 const data=fs.readFileSync(file);
 const adjacent=file.slice(0,file.length-path.extname(file).length)+'.exact-model-bends.json';
 const explicit=typeof job.exact_model_bends==='string';
 const sidecarPath=job.exact_model_bends===false?null:explicit?job.exact_model_bends:fs.existsSync(adjacent)?adjacent:null;
 const sidecarData=sidecarPath?fs.readFileSync(sidecarPath):null;
 const requested=job.execution_policy;
 if(requested!==undefined&&requested!==false&&typeof requested!=='string')
  throw Error('execution_policy must be an explicit path, false, or omitted');
 if(typeof requested==='string'&&!requested.length)throw Error('Explicit execution policy path is empty');
 const executionAdjacent=file.slice(0,file.length-path.extname(file).length)+'.execution-policy.json';
 const executionPath=requested===false?null:typeof requested==='string'?requested:fs.existsSync(executionAdjacent)?executionAdjacent:null;
 const executionData=executionPath?fs.readFileSync(executionPath):null;
 const executionReceipt=executionData?JSON.parse(executionData.toString('utf8')):null;
 if(executionReceipt)verifyExecutionPolicy(executionReceipt,data,sidecarData);
 else if(executionData)throw Error('Playback execution policy receipt must be an object');
 const restored=sidecarData?loadWithExactBends(at,data,JSON.parse(sidecarData.toString('utf8'))):null;
 const score=restored?restored.score:at.importer.ScoreLoader.loadScoreFromBytes(data);
 const hammerPullRegistration=executionReceipt?restoreHammerPullThroughTies(score):null;
 const executionRegistration=executionReceipt?registerContinuousMutePlayback(at,score):null;
 return {data,score,restored,sidecarData,sidecarPath,
         executionPolicyData:executionData,executionPolicyPath:executionPath,
         execution_policy_receipt:executionReceipt,execution_policy_registration:executionRegistration,
         hammer_pull_registration:hammerPullRegistration,
         execution_policy_selection:executionReceipt?(typeof requested==='string'?'explicit':'adjacent'):requested===false?'disabled':'absent',
         companion_selection:restored?(explicit?'explicit':'adjacent'):job.exact_model_bends===false?'disabled':'absent'};
}
