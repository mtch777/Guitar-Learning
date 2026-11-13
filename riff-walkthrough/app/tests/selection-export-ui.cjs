const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('Editor must not write storage');}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
code=code.replace('  init();\n})();',`  globalThis.test={togglePhrase,setEditorMode,editorAction,editorMarkup,getOutput,currentEditor,openEditor,selectedViews,set(s){config={stages:[]};state=s;connected=true;},get(){return state;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
const original={audio:{tempo:120,length_beats:8,notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]},phrases:[{phrase:1,start_beats:0,length_beats:4},{phrase:2,start_beats:4,length_beats:4}]};
const state={session_id:'a'.repeat(32),version:7,busy:false,stages:[{id:'1',status:'complete',output:{fixed:'seed'}},{id:'6',status:'complete',output:original}]};
const snapshot=JSON.stringify(state),calls=[];
function response(data,ok=true){return {ok,json:async()=>data};}
(async()=>{
 t.set(state);sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({source_version:7,revision:0,output:original});};
 await t.togglePhrase(2);await t.togglePhrase(1);assert.deepEqual(Array.from(t.currentEditor().selected),[1,2]);
 const markup=t.editorMarkup(original);assert.ok(markup.includes('Save selected MIDI'));assert.ok(!markup.includes('data-editor-mode'));assert.ok(!markup.includes('data-editor-action="plan"'));assert.ok(!markup.includes('data-editor-action="regenerate"'));
 const n=calls.length;await t.editorAction('plan');await t.editorAction('regenerate');t.setEditorMode('pitches');assert.equal(calls.length,n);assert.equal(t.currentEditor().mode,'both');
 const folder='https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi';
 sandbox.fetch=async(url,options)=>{calls.push({url,...options});return response({saved:true,version:7,editor_revision:0,file_url:'https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/selected.mid',folder_url:folder});};
 await t.editorAction('save');assert.deepEqual(JSON.parse(calls.at(-1).body),{version:7,revision:0,selected:[1,2]});assert.ok(calls.at(-1).url.endsWith('/editor/save'));assert.equal(JSON.stringify(state),snapshot);
 assert.ok(calls.every(c=>!c.url.includes('/regenerate')&&!c.url.includes('/plan')&&!c.url.includes('/api/generate')));
 console.log('Phase 1 selection/export UI PASS: multi-select, exact scope, no original mutation, regeneration controls absent and handlers disabled.');
})().catch(e=>{console.error(e);process.exitCode=1;});
