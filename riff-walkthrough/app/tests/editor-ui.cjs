const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const notice={...node};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:s=>s==='#notice'?notice:node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('Editor must not write storage');}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
// Phase 2 draft behavior is tested explicitly with its shipped-disabled gate enabled only in this harness.
code=code.replace(/const selectiveRegenerationEnabled=(true|false);/, 'const selectiveRegenerationEnabled=true;');
code=code.replace('  init();\n})();',`  globalThis.test={setResultView,resultMarkup,refresh,restoreEditorIfNeeded,togglePhrase,setEditorMode,editorAction,editorMarkup,getOutput,currentEditor,openEditor,retryReview,selectedViews,set(s){config={stages:[]};state=s;connected=true;},get(){return state;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
const original={audio:{tempo:120,length_beats:8,notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]},phrases:[{phrase:1,start_beats:0,length_beats:4},{phrase:2,start_beats:4,length_beats:4}]};
const state={session_id:'a'.repeat(32),version:7,busy:false,stages:[{id:'1',status:'complete',output:{fixed:'seed'}},{id:'6',status:'complete',output:original}]};
const snapshot=JSON.stringify(state),calls=[];
function response(data,ok=true){return {ok,json:async()=>data};}
(async()=>{
 t.set(state);
 sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({source_version:7,revision:0,output:original});};
 await t.togglePhrase(2);await t.togglePhrase(1);
 assert.deepEqual(Array.from(t.currentEditor().selected),[1,2]);assert.equal(calls.length,1);assert.ok(calls[0].url.endsWith('/editor/open'));
 assert.equal(calls[0].credentials,'include');assert.deepEqual(JSON.parse(calls[0].body),{version:7});
 const n=calls.length;await t.editorAction('regenerate');assert.equal(calls.length,n); // Must show plan first.
 sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({affected:[1,2,3],rhythm_affected:[1,3],pitch_affected:[1,2,3]});};
 await t.editorAction('plan');assert.ok(t.editorMarkup(original).includes('phrases 1, 2, 3'));assert.ok(t.editorMarkup(original).includes('Regenerate affected phrases'));
 t.setEditorMode('pitches');assert.equal(t.currentEditor().plan,null);await t.editorAction('plan');
 assert.equal(JSON.parse(calls.at(-1).body).mode,'pitches');
 await t.togglePhrase(2);assert.equal(t.currentEditor().plan,null);assert.deepEqual(Array.from(t.currentEditor().selected),[1]);await t.editorAction('plan');
 const edited={...original,audio:{...original.audio,notes:[{start_beats:0,duration_beats:1,midi_pitch:40}]}};
 sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({source_version:7,revision:1,output:edited});};
 await t.editorAction('regenerate');assert.equal(t.currentEditor().revision,1);assert.equal(t.getOutput('6').audio.notes[0].midi_pitch,40);assert.equal(t.currentEditor().plan,null);assert.equal(JSON.stringify(state),snapshot);
 assert.ok(t.editorMarkup(edited).includes('Edited · revision 1'));
 const folder='https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi';
 sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({saved:true,version:7,editor_revision:1,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/selected.mid',folder_url:folder});};
 await t.editorAction('save');assert.deepEqual(JSON.parse(calls.at(-1).body),{version:7,revision:1,selected:[1]});
 await t.editorAction('save',true);assert.deepEqual(JSON.parse(calls.at(-1).body),{version:7,revision:1,selected:null});
 assert.ok(calls.every(c=>!c.url.includes('/api/generate')&&!c.url.includes(state.session_id)));
 // Failed transaction retains complete last revision and removes approval plan.
 sandbox.fetch=async()=>response({affected:[1],rhythm_affected:[],pitch_affected:[1]});await t.editorAction('plan');
 sandbox.fetch=async(url)=>url.endsWith('/open')?response({source_version:7,revision:1,output:edited}):response({error:'No compatible candidate'},false);await t.editorAction('regenerate');assert.equal(t.currentEditor().revision,1);assert.equal(t.getOutput('6').audio.notes[0].midi_pitch,40);assert.equal(t.currentEditor().plan,null);
 // An old in-flight response cannot replace a new original session/version.
 sandbox.fetch=async()=>response({affected:[1],rhythm_affected:[],pitch_affected:[1]});await t.editorAction('plan');
 let finish;sandbox.fetch=()=>new Promise(resolve=>{finish=resolve;});const pending=t.editorAction('regenerate');await Promise.resolve();
 const newState={...state,version:8};t.set(newState);finish(response({revision:2,output:edited}));await pending;
 assert.equal(t.currentEditor(),null);assert.equal(t.getOutput('6'),undefined);assert.equal(JSON.stringify(state),snapshot);
 // Phase2 reconnect/refresh retrieves persisted working copy before offering original playback/save.
 const restoredState={...state,session_id:'f'.repeat(32),version:9};const restoredCalls=[];
 sandbox.fetch=async(url,options)=>{restoredCalls.push({url,options});return response(url==='/api/state'?restoredState:{source_version:9,revision:3,output:edited});};
 t.set(restoredState);await t.refresh();
 assert.equal(t.currentEditor().revision,3);assert.equal(t.getOutput('6').audio.notes[0].midi_pitch,40);assert.equal(t.get().stages[1].output.audio.notes[0].midi_pitch,28);
 assert.ok(restoredCalls.some(c=>c.url.endsWith('/editor/open')));assert.ok(restoredCalls.every(c=>!c.url.includes('/generate')));
 sandbox.fetch=async(url,options)=>{restoredCalls.push({url,options});return response({saved:true,version:9,editor_revision:3,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/restored.mid',folder_url:folder});};
 await t.editorAction('save',true);assert.ok(restoredCalls.at(-1).url.endsWith('/editor/save'));assert.deepEqual(JSON.parse(restoredCalls.at(-1).options.body),{version:9,revision:3,selected:null});
 // Restoration failure must never fall back to unlabelled original audio/save.
 const failedState={...state,session_id:'g'.repeat(32),version:10};t.set(failedState);
 assert.equal(t.getOutput('6'),undefined);assert.ok(!t.resultMarkup({id:'6'},failedState.stages[1]).includes('play-button'));
 sandbox.fetch=async(url)=>url==='/api/state'?response(failedState):response({error:'Offline workspace'},false);await t.refresh();
 const failure=t.resultMarkup({id:'6'},failedState.stages[1]);assert.ok(failure.includes('Retry Review'));assert.ok(!failure.includes('data-save-midi'));assert.equal(t.getOutput('6'),undefined);
 sandbox.fetch=async()=>response({source_version:10,revision:4,output:edited});await t.restoreEditorIfNeeded(true);
 assert.equal(t.currentEditor().revision,4);assert.equal(t.getOutput('6').audio.notes[0].midi_pitch,40);assert.equal(notice.textContent,'');
 // Previous view defers restore; returning Current triggers read-only reopen.
 const previousState={...state,session_id:'h'.repeat(32),version:11};t.set(previousState);t.selectedViews['6']='previous';const previousCalls=[];
 sandbox.fetch=async(url)=>{previousCalls.push(url);return response(url==='/api/state'?previousState:{source_version:11,revision:2,output:edited});};
 await t.refresh();assert.equal(previousCalls.length,1);await t.setResultView('6','current');assert.equal(t.currentEditor().revision,2);assert.ok(previousCalls.at(-1).endsWith('/editor/open'));
 // A committed edit with a lost response re-reads saved state; it never retries Generate.
 await t.togglePhrase(1);t.setEditorMode('pitches');
 sandbox.fetch=async()=>response({affected:[1],rhythm_affected:[],pitch_affected:[1]});await t.editorAction('plan');
 const recoveryCalls=[];let completeRecovery;
 sandbox.fetch=async(url)=>{recoveryCalls.push(url);if(url.endsWith('/regenerate'))throw Error('Response lost');if(url.endsWith('/open'))return await new Promise(resolve=>{completeRecovery=resolve;});throw Error('Unexpected request');};
 const recovering=t.editorAction('regenerate');for(let i=0;i<8&&!completeRecovery;i++)await Promise.resolve();assert.ok(completeRecovery);
 assert.equal(t.getOutput('6'),null);assert.ok(!t.resultMarkup({id:'6'},previousState.stages[1]).includes('play-button'));
 completeRecovery(response({source_version:11,revision:3,output:edited}));await recovering;
 assert.equal(t.currentEditor().revision,3);assert.equal(t.currentEditor().mode,'pitches');assert.deepEqual(Array.from(t.currentEditor().selected),[1]);assert.equal(recoveryCalls.filter(u=>u.endsWith('/regenerate')).length,1);assert.equal(recoveryCalls.filter(u=>u.endsWith('/open')).length,1);
 sandbox.fetch=async()=>response({affected:[1],rhythm_affected:[],pitch_affected:[1]});await t.editorAction('plan');
 sandbox.fetch=async()=>{throw Error('Connection lost');};await t.editorAction('regenerate');assert.equal(t.currentEditor(),null);assert.equal(t.getOutput('6'),undefined);assert.ok(t.resultMarkup({id:'6'},previousState.stages[1]).includes('Retry Review'));
 // Retry must fetch current source version before reopening; it must never generate.
 const renewed={...state,session_id:'z'.repeat(32),version:19};const retryCalls=[];
 sandbox.fetch=async(url)=>{retryCalls.push(url);return response(url==='/api/state'?renewed:{source_version:19,revision:0,output:original});};
 await t.retryReview();assert.equal(notice.textContent,'');assert.equal(retryCalls[0],'/api/state');assert.equal(t.get().version,19);assert.equal(t.currentEditor().revision,0);assert.ok(!retryCalls.some(u=>u.endsWith('/generate')||u.endsWith('/regenerate')));
 console.log('Editor UI PASS: lazy open, multi-select, explicit affected plan, mode invalidation, exact save scope, separate revision/playback, rollback and stale response isolation; no generation/session/storage mutation.');
})().catch(e=>{console.error(e);process.exitCode=1;});
