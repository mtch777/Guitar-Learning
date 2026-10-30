// Original and actual zero only: no fake demonstration, changed case or audio.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';import {pathToFileURL,fileURLToPath} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const [qaArg,python,backend,moduleArg,outName='native-zero-review']=process.argv.slice(2);
if(!moduleArg)throw Error('QA directory, backend Python/root, alphaTab module required');
if(!/^native-zero-review(?:-[a-z0-9-]+)?$/.test(outName))throw Error('Bounded native-zero-review output name required');
const lab=path.dirname(fileURLToPath(import.meta.url)),qa=path.resolve(qaArg),modulePath=path.resolve(moduleArg),out=path.join(qa,outName);
if(fs.existsSync(out))throw Error('Fresh zero review folder required');fs.mkdirSync(out);
process.on('uncaughtException',error=>{fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify({status:'FAIL_RETAINED',error:String(error),stack:error.stack},null,2));console.error(error);process.exitCode=1;});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=x=>crypto.createHash('sha256').update(x).digest('hex'),sha=p=>hash(fs.readFileSync(p));
const plan=read(path.join(qa,'plan.json')),capture=path.dirname(Object.keys(plan.source_hashes)[0]);
function run(exe,args,log){const r=spawnSync(exe,args,{cwd:lab,encoding:'utf8',timeout:600000,windowsHide:true});fs.writeFileSync(path.join(out,log),(r.stdout||'')+'\n'+(r.stderr||''));if(r.status!==0)throw Error('Command failed: '+log);}
run(python,['-c',`from pathlib import Path
import json,sys
from check_step_tempo_zero import source_binding
q=Path(sys.argv[1]);c,f=source_binding(q,json.loads((q/'plan.json').read_bytes()))
print(json.dumps(dict(status='PASS_ACTUAL_ZERO_BINDING',facts=len(f['facts']))))`,qa],'source-binding-before.json');
for(const name of ['source','zero'])run(python,[path.join(lab,'export_owned_capture.py'),name==='source'?capture:path.join(qa,'zero-capture'),backend,path.join(out,name)],name+'-export.log');
run(process.execPath,[path.join(lab,'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),modulePath,out,'--restore-pitched-graces'],'native-export.log');
const at=await import(pathToFileURL(modulePath));
const plain=x=>JSON.parse(JSON.stringify(x,(_k,v)=>v instanceof Map?Object.fromEntries(v):v));
const exporter=path.join(lab,'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),lines=fs.readFileSync(exporter,'utf8').split(/\r?\n/);
const curveText=lines.find(l=>l.startsWith('function curve(')),snapshotText=lines.find(l=>l.startsWith('function snapshot('));
const curve=Function(`return (${curveText})`)(),checked=Function('curve',`return (${snapshotText})`)(curve),cases={};
for(const name of ['source','zero']){
    const file=path.join(out,name,'score.gp'),{score,data,sidecarData,restored}=loadPlaybackScore(at,file,{}),settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;
    const profilePath=file.replace(/\.gp$/i,'.playback.json'),profile=fs.existsSync(profilePath)?read(profilePath):{};
    for(const [k,v]of Object.entries(profile)){if(!['noteSlightAmplitude','noteSlightLength'].includes(k)||!Number.isFinite(v)||v<=0)throw Error('Unknown playback setting');settings.player.vibrato[k]=v;}
    const model=plain(at.model.JsonConverter.scoreToJsObject(score)),checkedModel=checked(score),referencePath=path.join(out,name,'roundtrip-before.json'),reference=fs.existsSync(referencePath)?read(referencePath):null;
    const midi=new at.midi.MidiFile(),gen=new at.midi.MidiFileGenerator(score,settings,new at.midi.AlphaSynthMidiFileHandler(midi,false));gen.generate();
    const bars=gen.tickLookup.masterBars.map(b=>({bar:b.masterBar.index+1,start:b.start,end:b.end,tempo_changes:b.tempoChanges.map(p=>({tick:p.tick,tempo:p.tempo}))}));
    const points=midi.events.filter(e=>e.constructor.name==='TempoChangeEvent').map(e=>[e.tick,e.beatsPerMinute]);
    function seconds(tick){let q=0,bpm=points[0]?.[1],sum=0;if(points[0]?.[0]!==0)throw Error('No initial native tempo');for(const [t,b]of points){if(t>tick)break;sum+=(t-q)/960*60/bpm;q=t;bpm=b;}return sum+(tick-q)/960*60/bpm;}
    for(const b of bars){b.start_seconds=seconds(b.start);b.end_seconds=seconds(b.end);}
    cases[name]={gp_sha256:hash(data),sidecar_sha256:sidecarData?hash(sidecarData):null,model,checked_model:checkedModel,pre_export_model:reference,restored_curves:restored?.restored??0,
        playback_profile:profile,midi_tick_shift:midi.tickShift,events:midi.events.map(e=>({kind:e.constructor.name,data:plain(e)})),raw_midi_json:JSON.stringify(midi.events),midi_sha256:hash(JSON.stringify(midi.events)),performed_bars:bars};
}
fs.writeFileSync(path.join(out,'native-zero-snapshot.json'),JSON.stringify({schema:'native-step-tempo-zero/1',adapter_sha256:sha(fileURLToPath(import.meta.url)),
    module_path:modulePath,module_sha256:sha(modulePath),core_sha256:sha(path.join(path.dirname(modulePath),'alphaTab.core.mjs')),extractor_sha256:sha(exporter),cases}));
run(python,[path.join(lab,'check_step_tempo_zero.py'),out,qa],'native-zero-audit.log');
console.log(JSON.stringify({status:'ORIGINAL_ZERO_NATIVE_REVIEW_WRITTEN',output:out,review:read(path.join(out,'native-zero-audit.json')).status}));
