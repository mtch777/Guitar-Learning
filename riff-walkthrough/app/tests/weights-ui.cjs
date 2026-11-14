const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const noop=()=>{};const listeners={};const node={addEventListener:(k,v)=>listeners[k]=v,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop};
const sandbox={console,document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem:noop},setTimeout,clearTimeout,setInterval,clearInterval,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8').replace('  init();\n})();',`globalThis.t={normalizedDraft,isDirty,parameterMarkup,editorMarkup,editorAction,set(c,s,d,e){config=c;state=s;drafts=d;editor=e;connected=true;},get(){return editor;}};\n})();`);vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.t;
const controls=[{key:'phrase_preferences.mostly_silent',label:'50% or more silence/rest x',type:'number',default:.1,group:'phrase_preferences'}];
const c={stages:[{id:'3',parameters:controls,defaults:{phrase_preferences:{mostly_silent:.1}}},{id:'6'}],phrase_preference_controls:{'3':[{key:'mostly_silent',label:'50% or more silence/rest x',default:.1}]}};
const s={session_id:'abc',version:1,stages:[{id:'3',applied:{}},{id:'6',status:'complete'}]};const e={key:'abc:1',selected:[],revision:0,preferences:{'3':{mostly_silent:.1}}};t.set(c,s,{'3':{phrase_preferences:{mostly_silent:.1}}},e);
const markup=t.parameterMarkup(c.stages[0]);assert.ok(markup.includes('phrase-preferences'));assert.ok(!markup.includes('<details'));assert.ok(markup.includes('value="0.1"'));
const review=t.editorMarkup({});assert.ok(review.includes('data-editor-preference="mostly_silent"'));assert.ok(review.includes('Applied to the next selected-phrase regeneration'));
listeners.input({target:{dataset:{editorPreference:'mostly_silent',prefStage:'3'},value:'0.25'}});assert.equal(t.get().preferences['3'].mostly_silent,.25);
console.log('PASS visible phrase weights, Review controls, input wiring');

// Removed legacy settings must not create a permanent Not applied badge.
const schema={phrase_preferences:{minor_second:2}};
const cc={stages:[{id:'4',defaults:schema}]};
t.set(cc,{stages:[{id:'4',applied:schema}]},{'4':{phrase_preferences:{minor_second:2,intervals:99}}},null);
assert.equal(t.isDirty('4'),false);
t.set(cc,{stages:[{id:'4',applied:schema}]},{'4':{phrase_preferences:{minor_second:3,intervals:99}}},null);
assert.equal(t.isDirty('4'),true);
assert.equal(t.normalizedDraft({phrase_preferences:{intervals:99}},schema).phrase_preferences.minor_second,2);
console.log('PASS draft schema migration: stale keys ignored, defaults filled, real changes retained');
