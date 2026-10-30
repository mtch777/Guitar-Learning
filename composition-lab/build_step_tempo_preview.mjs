// Actual isolated inverse outputs only. No target/donor/tempo choices here.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const [qaArg,captureArg,python,backend,modulePath,font]=process.argv.slice(2);
if(!font)throw Error('QA folder, original capture, backend Python/root, alphaTab module and soundfont required');
const qa=path.resolve(qaArg),capture=path.resolve(captureArg),lab=path.dirname(fileURLToPath(import.meta.url)),out=path.join(qa,'native-preview');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const result=read(path.join(qa,'result.json')),demo=read(path.join(qa,'demonstration.json'));
if(!result.status.startsWith('PASS_')||!demo.chosen.changed)throw Error('Actual verified isolated tempo change required');
if(fs.existsSync(out))throw Error('Fresh native output folder required; preserve earlier failures');
fs.mkdirSync(out);
process.on('uncaughtException',error=>{
    fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({status:'FAIL_RETAINED',error:String(error),stack:error.stack},null,2));
    console.error(error);process.exitCode=1;
});
function run(exe,args,log){
    const r=spawnSync(exe,args,{cwd:lab,encoding:'utf8',timeout:600000,windowsHide:true});
    fs.writeFileSync(path.join(out,log),(r.stdout||'')+'\n'+(r.stderr||''));
    if(r.status!==0)throw Error('Command failed: '+log);
}
const binding=`from pathlib import Path
import json,sys
from source_fact_tier1 import extract
from check_step_tempo_artifacts import source_scope,capture_binding
q,c=map(Path,sys.argv[1:3])
source,z,a=capture_binding(q,json.loads((q/'plan.json').read_bytes()))
assert source.resolve()==c.resolve()
s=source_scope(z,a,json.loads((q/'demonstration.json').read_bytes()))
print(json.dumps({k:v for k,v in s.items()if k not in('docs','changed_docs')}))`;
run(python,['-c',binding,qa,capture],'tempo-source-scope.json');
const scope=read(path.join(out,'tempo-source-scope.json'));
if(scope.part!==demo.clip.part||scope.bar<demo.clip.first||scope.bar>demo.clip.last)throw Error('Source passage does not contain actual target');
for(const name of ['source','zero','changed'])
    run(python,[path.join(lab,'export_owned_capture.py'),name==='source'?capture:path.join(qa,name+'-capture'),backend,path.join(out,name)],name+'-export.log');
run(process.execPath,[path.join(lab,'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),modulePath,out,'--restore-pitched-graces'],'native-gp.log');
for(const name of ['source','zero','changed']){
    const v=read(path.join(out,name,'gp7-validation.json'));
    if(v.error||v.directSource?.differences!==0||!['PASS_INDEPENDENT_PITCHED_SOURCE_GRACES','NO_COVERED_PITCHED_GRACE_VOICES'].includes(v.directPitchedGraces?.status))
        throw Error('Native GP/source validation failed: '+name);
}
run(process.execPath,[path.join(lab,'audit_dynamic_gp.mjs'),modulePath,qa,out,'gp_with_exact_model_bends',capture],'native-snapshot.log');
run(process.execPath,[path.join(lab,'audit_step_tempo_gp.mjs'),modulePath,out],'native-tempo-reference.log');
const jobs=[];
for(const name of ['source','zero','changed'])for(const mode of ['focused','ensemble'])
    jobs.push({case_id:name+'-'+mode,method:name,mode,file:path.join(out,name,'score.gp'),out:path.join(out,name,mode+'.wav'),
        track:scope.part,start_bar:demo.clip.first,end_bar:demo.clip.last,target_bar:scope.bar,target_offset_q:'0'});
fs.writeFileSync(path.join(out,'audio-jobs.json'),JSON.stringify(jobs,null,2));
run(process.execPath,[path.join(lab,'render_source_passages.mjs'),modulePath,font,path.join(out,'audio-jobs.json')],'audio-render.log');
run(python,[path.join(lab,'check_step_tempo_artifacts.py'),out,qa],'native-artifact-audit.log');
run(python,['-c',binding,qa,capture],'worker-binding-after.json');
const audit=read(path.join(out,'step-tempo-artifact-audit.json'));
console.log(JSON.stringify({status:'NATIVE_STEP_TEMPO_OUTPUT_CHECKED',audit_status:audit.status,output:out,pcm_difference_measured:audit.pcm_difference_measured,listening_judgment:null}));
