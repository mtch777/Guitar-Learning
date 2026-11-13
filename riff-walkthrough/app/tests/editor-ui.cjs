const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('Editor must not write storage');}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
// Phase 2 draft behavior is tested explicitly with its shipped-disabled gate enabled only in this harness.
code=code.replace('const selectiveRegenerationEnabled=false;', 'const selectiveRegenerationEnabled=true;');
code=code.replace('  init();\n})();',`  globalThis.test={togglePhrase,setEditorMode,editorAction,editorMarkup,getOutput,currentEditor,openEditor,selectedViews,set(s){config={stages:[]};state=s;connected=true;},get(){return state;}};\n})();`);
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
 sandbox.fetch=async()=>response({error:'No compatible candidate'},false);await t.editorAction('regenerate');assert.equal(t.currentEditor().revision,1);assert.equal(t.getOutput('6').audio.notes[0].midi_pitch,40);assert.equal(t.currentEditor().plan,null);
 // An old in-flight response cannot replace a new original session/version.
 sandbox.fetch=async()=>response({affected:[1],rhythm_affected:[],pitch_affected:[1]});await t.editorAction('plan');
 let finish;sandbox.fetch=()=>new Promise(resolve=>{finish=resolve;});const pending=t.editorAction('regenerate');await Promise.resolve();
 const newState={...state,version:8};t.set(newState);finish(response({revision:2,output:edited}));await pending;
 assert.equal(t.currentEditor(),null);assert.equal(t.getOutput('6'),original);assert.equal(JSON.stringify(state),snapshot);
 console.log('Editor UI PASS: lazy open, multi-select, explicit affected plan, mode invalidation, exact save scope, separate revision/playback, rollback and stale response isolation; no generation/session/storage mutation.');
})().catch(e=>{console.error(e);process.exitCode=1;});
