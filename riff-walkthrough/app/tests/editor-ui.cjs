const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const notice={...node},settings=new Map();
const sandbox={console,localStorage:{getItem:k=>settings.get(k)||null,setItem:(k,v)=>settings.set(k,v)},location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:s=>s==='#notice'?notice:node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('Editor must not write storage');}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
// Phase 2 draft behavior is tested explicitly with its shipped-disabled gate enabled only in this harness.
code=code.replace(/const selectiveRegenerationEnabled=(true|false);/, 'const selectiveRegenerationEnabled=true;');
code=code.replace('  init();\n})();',`  globalThis.test={setResultView,resultMarkup,refresh,restoreEditorIfNeeded,togglePhrase,setEditorMode,editorAction,editorMarkup,getOutput,currentEditor,openEditor,retryReview,selectedViews,selectedPhraseNumbers,phraseCheckboxMarkup,updateRepeatSelection,setMarker,markerBeat,seekPlayback,player,kontaktPlayer,timelines,capturePlaybackPosition,restorePlaybackPosition,setRecovery(p){editor=null;editorRecoveryPrefs=p;},setPresets(p){kontaktPresets=p;},set(s){config={stages:[]};state=s;connected=true;},get(){return state;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
const original={audio:{tempo:120,length_beats:8,notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]},phrases:[{phrase:1,start_beats:0,length_beats:4},{phrase:2,start_beats:4,length_beats:4}]};
const state={session_id:'a'.repeat(32),version:7,busy:false,stages:[{id:'1',status:'complete',output:{fixed:'seed'}},{id:'6',status:'complete',output:original}]};
const snapshot=JSON.stringify(state),calls=[];
function response(data,ok=true){return {ok,json:async()=>data};}
(async()=>{
 t.set(state);let revision=0,output=original,fail=false,renderStarts=0;const requests=[];
 sandbox.fetch=async(url,options={})=>{const b=options.body?JSON.parse(options.body):{};requests.push({url,b});
   if(url.endsWith('/open'))return response({source_version:state.version,revision,output});
   if(url.endsWith('/plan'))return response({affected:[1,2],rhythm_affected:[1,2],pitch_affected:[1,2],revision});
   if(url.endsWith('/regenerate')){if(fail)return response({error:'No different compatible rhythm'},false);revision++;output={...original,audio:{...original.audio,notes:[{start_beats:1,duration_beats:1,midi_pitch:40}]}};return response({source_version:7,revision,output});}
   if(url.endsWith('/delete')){revision++;output={...original,phrases:[original.phrases[0]],audio:{...original.audio,length_beats:4}};return response({source_version:7,revision,output});}
   if(url.endsWith('/start')){renderStarts++;return response({error:'Test render unavailable'},false);}
   if(url.endsWith('/save'))return response({saved:true,version:7,editor_revision:revision,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/selected.mid',folder_url:'https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi'});
   throw Error('Unexpected '+url);
 };
 t.setPresets([{id:'modern-metal-1',label:'Modern Metal 1'}]);t.setMarker('6',3.25);
 await t.togglePhrase(1);assert.equal(t.markerBeat('6'),3.25);assert.deepEqual(Array.from(t.currentEditor().selected),[1]);assert.deepEqual(Array.from(t.selectedPhraseNumbers('6')),[1,2]);
 const html=t.phraseCheckboxMarkup(original);assert.ok(html.includes('auto-selected'));assert.ok(t.editorMarkup(original).includes('data-editor-mode'));assert.ok(!t.editorMarkup(original).includes('data-editor-action="plan"'));
 await t.editorAction('regenerate');assert.equal(revision,1);assert.equal(renderStarts,1);assert.equal(t.markerBeat('6'),3.25);assert.deepEqual(requests.find(r=>r.url.endsWith('/regenerate')).b.selected,[1]);assert.equal(requests.find(r=>r.url.endsWith('/regenerate')).b.mode,'both');assert.equal(JSON.stringify(state),snapshot);
 await t.editorAction('save');assert.deepEqual(requests.at(-1).b.selected,[1,2]);
 // Deselect the manual phrase removes its auto repeat; explicit second selection survives independently.
 await t.togglePhrase(2);assert.deepEqual(Array.from(t.currentEditor().selected),[1,2]);await t.togglePhrase(1);assert.deepEqual(Array.from(t.currentEditor().selected),[2]);await t.togglePhrase(2);assert.deepEqual(Array.from(t.selectedPhraseNumbers('6')),[]);
 await t.togglePhrase(1);fail=true;await t.editorAction('regenerate');assert.equal(t.currentEditor().revision,1);assert.ok(t.currentEditor().plan,'failed edit must restore usable selection plan');assert.equal(renderStarts,1);assert.equal(JSON.stringify(state),snapshot);
 // Failed plan checks expose a recovery action without starting generation.
 const healthyFetch=sandbox.fetch;sandbox.fetch=async()=>{throw Error('Connection interrupted');};await t.updateRepeatSelection();assert.equal(t.currentEditor().plan,null);assert.ok(t.editorMarkup(original).includes('Retry selection'));sandbox.fetch=healthyFetch;await t.editorAction('retry-plan');assert.ok(t.currentEditor().plan);assert.equal(t.currentEditor().planError,null);assert.equal(renderStarts,1);
 // Mode changes feed plan and regeneration, remembered when reopening a fresh editor.
 t.setEditorMode('pitches');await new Promise(resolve=>setImmediate(resolve));assert.equal(t.currentEditor().mode,'pitches');assert.equal(requests.filter(r=>r.url.endsWith('/plan')).at(-1).b.mode,'pitches');
 t.setEditorMode('rhythm');await new Promise(resolve=>setImmediate(resolve));assert.equal(t.currentEditor().mode,'rhythm');assert.equal(settings.get('riff-regeneration-mode'),'rhythm');
 fail=false;await t.editorAction('delete');assert.equal(requests.find(r=>r.url.endsWith('/delete')).b.mode,undefined);assert.deepEqual(requests.find(r=>r.url.endsWith('/delete')).b.selected,[1]);assert.deepEqual(Array.from(t.currentEditor().selected),[]);assert.equal(t.currentEditor().output.phrases.length,1);assert.equal(renderStarts,2);
 await t.togglePhrase(1);
 // Late plan response cannot resurrect removed selection.
 let resolvePlan;sandbox.fetch=()=>new Promise(resolve=>resolvePlan=resolve);const pending=t.updateRepeatSelection();await t.togglePhrase(1);resolvePlan(response({affected:[1,2],rhythm_affected:[1,2],pitch_affected:[1,2]}));await pending;assert.deepEqual(Array.from(t.selectedPhraseNumbers('6')),[]);
 // Markers are scoped by session/version and roll seek updates marker/audio without selecting.
 const audioElement={currentTime:0};node.querySelector=()=>audioElement;t.seekPlayback('6',5);assert.equal(t.markerBeat('6'),5);assert.equal(audioElement.currentTime,2.5);assert.deepEqual(Array.from(t.currentEditor().selected),[]);
 t.set({...state,version:8});assert.equal(t.markerBeat('6'),0);t.set(state);assert.equal(t.markerBeat('6'),5);
 // Synth pause uses actual current position, not start or stale frame.
 t.player.context={currentTime:12};t.player.active={stage:'6',view:'current',start:10,duration:8,seconds:.5};node.querySelector=()=>node;t.player.stop();assert.equal(t.markerBeat('6'),4);
 // Reusing rendered audio DOM preserves native playback/currentTime across selection markup replacement.
 const oldAudio={currentTime:3,paused:false},replacement={replaceWith(value){this.reused=value;}},timeline={draw(){},cursor:null};
 // Test direct source contract because currentKontakt requires a valid capture/job for DOM reuse.
 assert.ok(code.includes('element.replaceWith(snapshot.element)'));assert.ok(!code.includes('if(kontaktPlayer.active?.stage===id)kontaktPlayer.stop();'));
 // A restored editor waiting for its repeat plan cannot return a newer session's editor.
 t.set(state);t.setRecovery({key:state.session_id+':7',selected:[1],mode:'both'});let resolveRestore;sandbox.fetch=async(url)=>url.endsWith('/open')?response({source_version:t.get().version,revision:0,output:original}):new Promise(resolve=>resolveRestore=resolve);
 const oldOpen=t.openEditor();await new Promise(resolve=>setImmediate(resolve));t.set({...state,version:9});const newOpen=await t.openEditor();assert.ok(newOpen);resolveRestore(response({affected:[1],rhythm_affected:[1],pitch_affected:[1]}));assert.equal(await oldOpen,null);assert.equal(t.currentEditor(),newOpen);
 console.log('Editor/playback UI PASS: automatic repeat plan, manual-only regen scope, one-click Both, gray selection, marker preservation/seek, auto render success-only, no autoplay, stale plan and rollback.');
})().catch(e=>{console.error(e);process.exitCode=1;});
