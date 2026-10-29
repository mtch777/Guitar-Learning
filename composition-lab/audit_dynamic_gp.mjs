// Read-only actual alphaTab note/MIDI snapshot for the dynamics auditor.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL,fileURLToPath} from 'node:url';
import {loadPlaybackScore} from './songsterr_automation/songsterr_api/playback_score.mjs';
const [moduleArg,qaArg,nativeArg,arg4,arg5]=process.argv.slice(2);
const fidelityScope=['standalone_gp','gp_with_exact_model_bends'].includes(arg4)?arg4:'standalone_gp',captureArg=['standalone_gp','gp_with_exact_model_bends'].includes(arg4)?arg5:arg4;
if(!nativeArg)throw Error('modulePath QA native-preview [original-capture] required');
const modulePath=path.resolve(moduleArg),root=path.resolve(nativeArg),qa=path.resolve(qaArg);
const plan=JSON.parse(fs.readFileSync(path.join(qa,'plan.json'),'utf8'));
const capture=path.resolve(captureArg??path.dirname(Object.keys(plan.source_hashes)[0])),at=await import(pathToFileURL(modulePath));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),filehash=p=>hash(fs.readFileSync(p));
const enumName=x=>at.model.DynamicValue[x]??null,plain=x=>JSON.parse(JSON.stringify(x));
const exporterPath=path.join(path.dirname(fileURLToPath(import.meta.url)),'songsterr_automation/songsterr_api/export_csv_gp7.mjs'),exporterText=fs.readFileSync(exporterPath,'utf8');
const curveText=exporterText.split(/\r?\n/).find(s=>s.startsWith('function curve(')),snapshotText=exporterText.split(/\r?\n/).find(s=>s.startsWith('function snapshot('));
if(!curveText||!snapshotText)throw Error('Original checked-field extractor unavailable');
// Execute only these hash-bound existing local extractor definitions; do not run exporter CLI.
const originalCurve=Function(`return (${curveText})`)(),checkedSnapshot=Function('curve',`return (${snapshotText})`)(originalCurve);
const extractor={path:exporterPath,sha256:filehash(exporterPath),curve_sha256:hash(curveText),snapshot_sha256:hash(snapshotText),scope:'Exact existing exported model fields; not all raw source or every native score property'};
const cases={};
for(const method of ['source','zero','changed']){
 const folder=method==='source'?capture:path.join(qa,method+'-capture'),file=path.join(root,method,'score.gp');
 const {data,score,sidecarData,restored}=loadPlaybackScore(at,file,{}),settings=new at.Settings();settings.notation.notationMode=at.NotationMode.GuitarPro;
 const profilePath=file.replace(/\.gp$/i,'.playback.json'),profile=fs.existsSync(profilePath)?JSON.parse(fs.readFileSync(profilePath,'utf8')):{};
 for(const [key,value]of Object.entries(profile)){
  if(!['noteSlightAmplitude','noteSlightLength'].includes(key)||!Number.isFinite(value)||value<=0)throw Error('Unsupported playback profile');settings.player.vibrato[key]=value;
 }
 const referencePath=path.join(root,method,'roundtrip-before.json'),checkedModel=fidelityScope==='gp_with_exact_model_bends'?checkedSnapshot(score):null,reference=fs.existsSync(referencePath)?{file:'roundtrip-before.json',sha256:filehash(referencePath)}:null;
 const comparison=checkedModel&&reference?(JSON.stringify(checkedModel)===JSON.stringify(JSON.parse(fs.readFileSync(referencePath,'utf8')))?'MATCH':'MISMATCH'):'NO_PREEXPORT_REFERENCE';
 const notes=[],beats=[],qualifications=[],lookup=new WeakMap(),docs={};
 for(const name of fs.readdirSync(folder).filter(n=>/^track-\d+\.json$/.test(n)))docs[name]=JSON.parse(fs.readFileSync(path.join(folder,name),'utf8'));
 for(const [part,t]of score.tracks.entries()){
  const raw=docs[`track-${part}.json`];if(!raw)throw Error('Missing source track mapping');
  if(t.staves.length!==1)throw Error('Single native staff mapping required');
  for(const [mi,b]of t.staves[0].bars.entries())for(const [vi,v]of b.voices.entries()){
   const sourceBeats=raw.measures[mi]?.voices?.[vi]?.beats??[],regularSource=sourceBeats.map((beat,index)=>({beat,index})).filter(x=>!x.beat.graceNote),regularNative=v.beats.filter(b=>b.graceType===0&&!b.isEmpty);
   const aligned=regularSource.length===regularNative.length;
   for(const [bi,s]of sourceBeats.entries())if(s.graceNote)qualifications.push({source_refs:(s.notes??[]).map((n,ni)=>!n.rest?`event:${raw.songId}:${part}:${mi+1}:${vi}:${bi}:${ni}`:null).filter(Boolean),reason:'SOURCE_GRACE_ALIGNMENT_UNVERIFIED'});
   for(const beat of v.beats){
    const loc=regularNative.indexOf(beat),source=aligned&&loc>=0?regularSource[loc]:null,sourceRef=source?`track-${part}.json#/measures/${mi}/voices/${vi}/beats/${source.index}`:null;
    const nativeBeatRef=`native:${part}:${mi+1}:${vi}:${beat.index}`,sourceNotes=source?(source.beat.notes??[]).map((n,index)=>({n,index})).filter(x=>!x.n.rest):[];
    beats.push({native_ref:nativeBeatRef,source_beat_ref:sourceRef,part,bar:mi+1,voice:vi,beat:beat.index,dynamic:enumName(beat.dynamics),grace:beat.graceType,empty:beat.isEmpty,source_refs:sourceNotes.map(x=>`event:${raw.songId}:${part}:${mi+1}:${vi}:${source.index}:${x.index}`)});
    for(const note of beat.notes){
     const matching=source&&!t.staves[0].isPercussion?sourceNotes.filter(x=>Number.isInteger(x.n.string)&&raw.tuning.length-x.n.string===note.string&&(x.n.dead&&note.isDead||x.n.fret===note.fret)):[];
     const mapped=matching.length===1?matching[0]:null,ref=mapped?`event:${raw.songId}:${part}:${mi+1}:${vi}:${source.index}:${mapped.index}`:null;
     const row={native_ref:`${nativeBeatRef}:${note.index}`,native_beat_ref:nativeBeatRef,source_ref:ref,source_group_refs:sourceNotes.map(x=>`event:${raw.songId}:${part}:${mi+1}:${vi}:${source.index}:${x.index}`),part,bar:mi+1,voice:vi,beat:beat.index,note:note.index,dynamic:enumName(note.dynamics),beat_dynamic:enumName(beat.dynamics),pitch:note.realValue,string:note.string,fret:note.fret,is_percussion:t.staves[0].isPercussion,dead:note.isDead,ghost:note.isGhost,accentuated:note.accentuated,hammer_pull_origin:!!note.hammerPullOrigin,tie_destination:note.isTieDestination,slide_origin_legato:!!note.slideOrigin&&note.slideOrigin.slideOutType===at.model.SlideOutType.Legato};
     notes.push(row);lookup.set(note,row);
     if(!ref)qualifications.push({native_ref:row.native_ref,source_refs:row.source_group_refs,reason:t.staves[0].isPercussion?'PERCUSSION_COLLECTIVE_MAPPING_ONLY':'NATIVE_NOTE_SOURCE_MAPPING_UNAVAILABLE'});
    }
   }
  }
 }
 const midi=new at.midi.MidiFile(),handler=new at.midi.AlphaSynthMidiFileHandler(midi,false),callbacks=[],bindings=new WeakMap();let current=null,call=null;
 const originalAdd=midi.addEvent.bind(midi);midi.addEvent=e=>{if(call!==null)bindings.set(e,call);return originalAdd(e);};
 const originalNote=handler.addNote.bind(handler);handler.addNote=(track,start,length,key,velocity,channel)=>{
  const row=current?lookup.get(current):null,index=callbacks.length;
  callbacks.push({native_ref:row?.native_ref??null,source_ref:row?.source_ref??null,track,start:start+handler.tickShift,length,key,velocity,channel});
  const previous=call;call=index;try{return originalNote(track,start,length,key,velocity,channel);}finally{call=previous;}
 };
 const generator=new at.midi.MidiFileGenerator(score,settings,handler),originalGenerate=generator._generateNote;
 if(typeof originalGenerate!=='function')throw Error('Pinned generator binding API unavailable');
 generator._generateNote=function(note,...args){const previous=current;current=note;try{return originalGenerate.call(this,note,...args);}finally{current=previous;}};
 generator.generate();
 const rawEvents=midi.events,events=rawEvents.map(e=>({kind:e.constructor.name,data:plain(e),binding:bindings.get(e)??null}));
 cases[method]={checked_model:checkedModel,pre_export_reference:reference,checked_field_comparison:comparison,restored_curves:restored?.restored??null,gp_sha256:hash(data),sidecar_sha256:sidecarData?hash(sidecarData):null,playback_profile:profile,capture_hashes:Object.fromEntries(fs.readdirSync(folder).filter(n=>n.endsWith('.json')).sort().map(n=>[n,filehash(path.join(folder,n))])),notes,beats,mapping_qualifications:qualifications,callbacks,events,raw_midi_json:JSON.stringify(rawEvents),midi_event_sha256:hash(JSON.stringify(rawEvents)),midi_tick_shift:midi.tickShift};
}
const snapshot={schema:'native-dynamic-snapshot/1',fidelity_scope:fidelityScope,checked_model_extractor:extractor,module_path:modulePath,module_sha256:filehash(modulePath),core_sha256:filehash(path.join(path.dirname(modulePath),'alphaTab.core.mjs')),snapshot_script_sha256:filehash(fileURLToPath(import.meta.url)),cases};
const out=path.join(root,'dynamic-native-snapshot.json');if(fs.existsSync(out))throw Error('Refusing to overwrite native snapshot');fs.writeFileSync(out,JSON.stringify(snapshot,null,2));console.log(JSON.stringify({status:'SNAPSHOT_WRITTEN_NOT_ACCEPTANCE',out,notes:Object.fromEntries(Object.entries(cases).map(([k,v])=>[k,v.notes.length]))}));
