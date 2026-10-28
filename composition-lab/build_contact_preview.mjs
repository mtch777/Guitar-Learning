// Private source/zero/changed GP and audio preview. No musical decisions here.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {spawnSync} from 'node:child_process';import {fileURLToPath,pathToFileURL} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const [qaArg,captureArg,python,backend,modulePath,font,freshQaArg]=process.argv.slice(2);
if(!freshQaArg)throw Error('qa capture backendPython backendRoot alphaTabModule soundfont freshQa required');
const qa=path.resolve(qaArg),capture=path.resolve(captureArg),root=path.dirname(fileURLToPath(import.meta.url)),out=path.join(qa,'native-preview');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const result=read(path.join(qa,'result.json')),demo=read(path.join(qa,'demonstration.json')),plan=read(path.join(qa,'plan.json'));
if(result.status!=='PASS_PROVISIONAL_CONTACT_PREVIEW_QA'||demo.actual_worker_audit.status!=='PASS_PROVISIONAL_INNER_CONTACTS')throw Error('Verified provisional symbolic result required');
const freshQa=path.resolve(freshQaArg),freshResult=read(path.join(freshQa,'result.json')),freshPlan=read(path.join(freshQa,'plan.json'));
if(!['PASS_CONTACT_PREVIEW_QA_NO_CHANGE','PASS_PROVISIONAL_CONTACT_PREVIEW_QA'].includes(freshResult.status))throw Error('Fresh result failed or incomplete');
if(JSON.stringify(read(path.join(qa,'zero-and-pair/result.json')).modules)!==JSON.stringify(read(path.join(freshQa,'zero-and-pair/result.json')).modules))throw Error('Fresh and development inverse code differ');
for(const [p,h]of Object.entries(freshPlan.source_hashes))if(hash(p)!==h)throw Error('Fresh capture changed');
const freshCapture=path.dirname(Object.keys(freshPlan.source_hashes)[0]),selectionText=fs.readFileSync(path.join(path.dirname(freshCapture),'selection.json'),'utf8'),selection=JSON.parse(selectionText);
const seedText=selectionText.match(/"seed"\s*:\s*(\d+)\s*[,}]/)?.[1];if(!seedText)throw Error('Exact integer sampling seed missing');
if(selection.status!=='captured'||selection.selected_song_id!==freshResult.song_id)throw Error('Fresh selection provenance mismatch');
const sourceNames=Object.keys(plan.source_hashes).map(p=>path.basename(p)).sort();
if(JSON.stringify(fs.readdirSync(capture).filter(n=>n.toLowerCase().endsWith('.json')).sort())!==JSON.stringify(sourceNames))throw Error('Supplied source file inventory differs from frozen capture');
for(const [p,h] of Object.entries(plan.source_hashes))if(hash(p)!==h||hash(path.join(capture,path.basename(p)))!==h)throw Error('Source changed after symbolic audit');
if(fs.existsSync(out))throw Error('Fresh native preview folder required');fs.mkdirSync(out);
const run=(exe,args,log)=>{const r=spawnSync(exe,args,{cwd:root,encoding:'utf8',timeout:600000,windowsHide:true});fs.writeFileSync(path.join(out,log),(r.stdout||'')+'\n'+(r.stderr||''));if(r.status!==0)throw Error('Command failed; see '+log+': '+r.error);};
const bind="from pathlib import Path; import json,sys; from source_fact_tier1 import extract; q=Path(sys.argv[1]); c=Path(sys.argv[2]); z=json.loads((q/'zero-and-pair/zero-isolated/worker/output.json').read_text()); a=json.loads((q/'changed-isolated/worker/output.json').read_text()); assert extract(c)==z, 'Source does not equal actual zero worker'; assert extract(q/'zero-capture')==z, 'Zero export capture differs from actual worker'; assert extract(q/'changed-capture')==a, 'Changed export capture differs from actual worker'; print('PASS_ACTUAL_WORKER_CAPTURE_BINDING')";
run(python,['-c',bind,qa,capture],'worker-binding-before.log');
for(const name of ['source','zero','changed'])run(python,[path.join(root,'export_owned_capture.py'),name==='source'?capture:path.join(qa,name+'-capture'),backend,path.join(out,name)],name+'-export.log');
run(process.execPath,[path.join(root,'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),modulePath,out],'native-gp.log');
for(const name of ['source','zero','changed']){const r=read(path.join(out,name,'gp7-validation.json'));if(!r.roundtripPass||r.directSource?.differences!==0)throw Error('Native GP/source validation failed for '+name);}
const target=demo.target,bar=Number(target.id.split(':')[3]),part=target.part_id;
const docs={};for(const name of ['zero','changed'])docs[name]=read(path.join(qa,name+'-capture','track-'+part+'.json'));
const first=Math.max(1,bar-1),last=Math.min(docs.zero.measures.length,bar+1);
const at=await import(pathToFileURL(path.resolve(modulePath)));
const loaded=loadPlaybackScore(at,path.join(out,'zero/score.gp'),{}).score;
const timingGenerator=new at.midi.MidiFileGenerator(loaded,new at.Settings(),new at.midi.AlphaSynthMidiFileHandler(new at.midi.MidiFile(),false));timingGenerator.generate();
const timingBars=timingGenerator.tickLookup.masterBars,tempoPoints=timingBars.flatMap(b=>b.tempoChanges).sort((a,b)=>a.tick-b.tick);
function secondsBetween(a,b){let cursor=a,tempo=loaded.tempo,total=0;for(const point of tempoPoints){if(point.tick<=a){tempo=point.tempo;continue;}if(point.tick>=b)break;total+=(point.tick-cursor)/960*60/tempo;cursor=point.tick;tempo=point.tempo;}return total+(b-cursor)/960*60/tempo;}
const beatIndex=Number(target.id.split(':')[5]),voice=Number(target.id.split(':')[4]);
const targetBeat=loaded.tracks[part].staves[0].bars[bar-1].voices[voice].beats[beatIndex];
if(!targetBeat||!Number.isFinite(targetBeat.playbackStart))throw Error('Actual GP target beat not addressable');
const jobs=[];for(const name of ['source','zero','changed'])for(const mode of ['focused','ensemble'])jobs.push({case_id:name+'-'+mode,method:name,mode,file:path.join(out,name,'score.gp'),out:path.join(out,name,mode+'.wav'),track:part,start_bar:first,end_bar:last,target_bar:bar,target_offset_q:String(targetBeat.playbackStart/960)});
fs.writeFileSync(path.join(out,'audio-jobs.json'),JSON.stringify(jobs,null,2));
run(process.execPath,[path.join(root,'render_source_passages.mjs'),modulePath,font,path.join(out,'audio-jobs.json')],'audio-render.log');
run(python,['-c',"from pathlib import Path; from check_voicing_artifacts import check; import sys; r=check(Path(sys.argv[1]),Path(sys.argv[2]),allow_inner_degree_changes=True); print(r['status']); raise SystemExit(0 if r['status']=='PASS_NATIVE_GP_AND_AUDIO_CHANGE' else 1)",out,qa],'native-audio-audit.log');
run(python,['-c',bind,qa,capture],'worker-binding-after.log');
const renders=read(path.join(out,'audio-jobs.results.json')),audit=read(path.join(out,'independent-gp-audio-check.json'));
const clip=renders.find(r=>r.method==='zero'&&r.mode==='focused');
const targetTick=timingBars.find(b=>b.masterBar.index===bar-1).start+targetBeat.playbackStart;
const label=m=>['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][m%12]+'_'+(Math.floor(m/12)-1);
const notes=target.member_refs.map((ref,i)=>{const n=Number(ref.split(':')[6]);const a=docs.zero.measures[bar-1].voices[voice].beats[beatIndex].notes[n],b=docs.changed.measures[bar-1].voices[voice].beats[beatIndex].notes[n];const pitch=(doc,note)=>doc.tuning[note.string]+(doc.capo||0)+note.fret;return {ref,string:a.string+1,before:label(pitch(docs.zero,a)),after:label(pitch(docs.changed,b)),old_fret:a.fret,new_fret:b.fret,old_degree:target.roles[i].degree_token,new_degree:demo.chosen.roles[i].degree_token,changed:a.fret!==b.fret};});
const rawBeat=docs.zero.measures[bar-1].voices[voice].beats[beatIndex];
const covers=demo.chosen.relationship.contact_coverage;
const meta=read(path.join(capture,'metadata.json'));
const view={status:'PROVISIONAL_AUDIBLE_EXPERIMENT',human_playability:'UNVERIFIED',listening_judgment:null,title:result.title,artist:meta.artist,part:loaded.tracks[part].name,bar,first,last,notes,source_chord:rawBeat.chord?.text||null,donor_bars:[...new Set(demo.chosen.donor_refs.map(r=>Number(r.split(':')[3])))],covers,
 duration:clip.seconds,target_seconds:clip.target_seconds,target_duration_seconds:secondsBetween(targetTick,targetTick+targetBeat.playbackDuration),
 counts:result.counts,notes_exact:result.notes,facts_exact:result.facts,controls:demo.controls,
 fresh:{title:freshResult.title,notes:freshResult.notes,facts:freshResult.facts,eligible_targets:freshResult.counts.eligible_targets||0,changed:freshResult.changed_demonstration,seed:seedText,pool_rule:selection.pool_rule},
 audio:{source:'zero/focused.wav',changed:'changed/focused.wav',source_ensemble:'zero/ensemble.wav',changed_ensemble:'changed/ensemble.wav'},
 build_hashes:Object.fromEntries([fileURLToPath(import.meta.url),path.join(root,'render_source_passages.mjs'),path.join(root,'contact-preview.html'),...fs.readdirSync(path.join(root,'songsterr_automation/songsterr_api')).filter(n=>n.endsWith('.mjs')).map(n=>path.join(root,'songsterr_automation/songsterr_api',n))].map(p=>[p,hash(p)])),
 audit,source_hashes:plan.source_hashes,render_sources:renders.map(r=>({method:r.method,mode:r.mode,gp_sha256:r.gp_sha256,audio_sha256:r.audio_sha256,font_sha256:r.font_sha256})),
 qa1:'This is a development song; the separate fresh-song result is not a listening-quality claim.',qa2:'Full capture reconstructed after lower payloads were removed; independent raw-source check. Actual changed worker passed outside locks.',qa3:'Source-supported inner chord degrees; same root/formula and outer notes. No claim of artistic preference or comfortable fingering.'};
// The rendered difference must not start before the selected chord. Release
// tails may extend beyond its nominal duration and are measured, not clipped.
for(const a of Object.values(audit.audio))if(a.delta_start_seconds<clip.target_seconds-.03)throw Error('Audio changed before the selected chord');
fs.writeFileSync(path.join(out,'preview.json'),JSON.stringify(view,null,2));
fs.copyFileSync(path.join(root,'contact-preview.html'),path.join(out,'index.html'));
console.log(JSON.stringify({status:view.status,output:out,bar,changed_notes:notes.filter(n=>n.changed).length,audio:audit.status}));
