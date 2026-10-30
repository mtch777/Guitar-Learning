// Actual source/isolated-inverse outputs only. No note selection in this script.
import fs from 'node:fs';import path from 'node:path';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const [qaArg,captureArg,python,backend,modulePath,font]=process.argv.slice(2);
if(!font)throw Error('qa capture backendPython backendRoot alphaTabModule soundfont required');
const qa=path.resolve(qaArg),capture=path.resolve(captureArg),root=path.dirname(fileURLToPath(import.meta.url)),out=path.join(qa,'native-preview');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),result=read(path.join(qa,'result.json')),demo=read(path.join(qa,'demonstration.json'));
if(result.status!=='PASS_SOURCE_GROUP_RHYTHM_CHANGE')throw Error('Verified actual rhythm worker change required');
if(fs.existsSync(out))throw Error('Fresh native output required');fs.mkdirSync(out);
process.on('uncaughtException',e=>{fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({status:'FAIL_RETAINED',error:String(e),stack:e.stack},null,2));console.error(e);process.exitCode=1;});
const run=(exe,args,log)=>{const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',timeout:600000,windowsHide:true});fs.writeFileSync(path.join(out,log),(r.stdout||'')+'\n'+(r.stderr||''));if(r.status!==0)throw Error('Command failed: '+log);};
const bind="from pathlib import Path; import json,sys; from source_fact_tier1 import extract; q=Path(sys.argv[1]); c=Path(sys.argv[2]); z=json.loads((q/'zero-isolated/worker/output.json').read_bytes()); a=json.loads((q/'changed-isolated/worker/output.json').read_bytes()); assert extract(c)==z; assert extract(q/'zero-capture')==z; assert extract(q/'changed-capture')==a; print('PASS_ACTUAL_WORKER_BINDING')";
run(python,['-c',bind,qa,capture],'worker-binding-before.log');
for(const name of ['source','zero','changed'])run(python,[path.join(root,'export_owned_capture.py'),name==='source'?capture:path.join(qa,name+'-capture'),backend,path.join(out,name)],name+'-export.log');
run(process.execPath,[path.join(root,'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),modulePath,out,'--restore-pitched-graces'],'native-gp.log');
for(const name of ['source','zero','changed']){const v=read(path.join(out,name,'gp7-validation.json'));if(v.error||v.directSource?.differences!==0||!['PASS_INDEPENDENT_PITCHED_SOURCE_GRACES','NO_COVERED_PITCHED_GRACE_VOICES'].includes(v.directPitchedGraces?.status))throw Error('Native GP/source validation failed: '+name);}
run(process.execPath,[path.join(root,'audit_dynamic_gp.mjs'),modulePath,qa,out,'gp_with_exact_model_bends',capture],'native-snapshot.log');
run(process.execPath,[path.join(root,'audit_group_rhythm_origins.mjs'),modulePath,out],'midi-origins.log');
const jobs=[];
for(const name of ['source','zero','changed'])for(const mode of ['focused','ensemble'])jobs.push({case_id:name+'-'+mode,method:name,mode,file:path.join(out,name,'score.gp'),out:path.join(out,name,mode+'.wav'),track:demo.clip.part,start_bar:demo.clip.first,end_bar:demo.clip.last,target_bar:demo.target.bar,target_offset_q:demo.target.context_key[4]});
fs.writeFileSync(path.join(out,'audio-jobs.json'),JSON.stringify(jobs,null,2));
run(process.execPath,[path.join(root,'render_source_passages.mjs'),modulePath,font,path.join(out,'audio-jobs.json')],'audio-render.log');
run(python,[path.join(root,'check_group_rhythm_artifacts.py'),out,qa,capture],'native-audio-audit.log');
run(python,['-c',bind,qa,capture],'worker-binding-after.log');
console.log(JSON.stringify({status:'NATIVE_RHYTHM_OUTPUT_CHECKED',output:out,listening_judgment:null}));
