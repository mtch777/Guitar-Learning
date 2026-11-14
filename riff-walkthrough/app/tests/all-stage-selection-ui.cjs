const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const noop=()=>{},node={addEventListener:noop,querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop,textContent:'',hidden:false};
const sandbox={console,location:{origin:'http://127.0.0.1:8768'},CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('No storage writes');}},setTimeout,clearTimeout,setInterval,clearInterval,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
code=code.replace('  init();\n})();',`  globalThis.test={restoreSelectionsIfNeeded,openSelection,currentSelection,toggleStagePhrase,saveStageSelection,phraseCheckboxMarkup,resultMarkup,selectedViews,set(s){config={stages:[]};state=s;connected=true;},get(){return state;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;
const audio={tempo:120,length_beats:8,label:'Reference rhythm · E1',notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]};
const state={session_id:'a'.repeat(32),version:7,busy:false,stages:Array.from({length:5},(_,i)=>({id:String(i+1),status:i===4?'blocked':'complete',output:{...(i===4?{blocker:'Stopped'}:{}),audio:{...audio,label:i===4?'Partial pitched riff':audio.label},phrases:[{phrase:1,start_beats:0,length_beats:4},{phrase:2,start_beats:4,length_beats:4}]}}))};
state.stages[0].output.audio={...audio,notes:[]};
const snapshot=JSON.stringify(state),calls=[],folder='https://github.com/mtch777/Guitar-Learning/tree/generated-midi/generated-midi';
function response(data,ok=true){return {ok,json:async()=>data};}
(async()=>{
 t.set(state);
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,...options,body});return response({stage:body.stage,version:body.version,audio_label:audio.label,phrases:body.stage===1?[{phrase:1,start_beats:0,length_beats:8}]:[{phrase:1,start_beats:0,length_beats:3},{phrase:2,start_beats:3,length_beats:5}]});};
 await t.restoreSelectionsIfNeeded();assert.equal(calls.length,3);assert.ok(calls.every(c=>c.url.endsWith('/selection/open')&&c.credentials==='include'));assert.deepEqual(calls.map(c=>c.body.stage).sort(),[3,4,5]);
 await t.restoreSelectionsIfNeeded();assert.equal(calls.length,3); // No duplicate loads.
 for(let i=3;i<=5;i++){
  const id=String(i);await t.toggleStagePhrase(id,1);assert.deepEqual(Array.from(t.currentSelection(id).selected),[1]);
  assert.ok(t.resultMarkup({id},state.stages[i-1]).includes(`data-save-selection="${id}"`));
 }
 const seedHTML=t.resultMarkup({id:'1'},state.stages[0]);assert.ok(seedHTML.includes('category-timeline'));assert.ok(!seedHTML.includes('data-phrase-select'));assert.ok(!seedHTML.includes('play-button'));
 const donorHTML=t.resultMarkup({id:'2'},state.stages[1]);assert.ok(donorHTML.includes('category-timeline'));assert.ok(!donorHTML.includes('data-phrase-start'));
 await t.toggleStagePhrase('3',2);assert.deepEqual(Array.from(t.currentSelection('3').selected),[1,2]);assert.deepEqual(Array.from(t.currentSelection('4').selected),[1]);
 sandbox.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,...options,body});return response({saved:true,version:7,file_url:`https://github.com/mtch777/Guitar-Learning/blob/generated-midi/generated-midi/${body.stage}_selected.mid`,folder_url:folder});};
 for(let i=3;i<=5;i++){await t.saveStageSelection(String(i));assert.equal(calls.at(-1).body.stage,i);assert.equal(calls.at(-1).body.version,7);assert.deepEqual(calls.at(-1).body.selected,i===3?[1,2]:[1]);}
 assert.equal(JSON.stringify(state),snapshot);assert.ok(calls.every(c=>!c.url.includes('generate')&&!c.url.includes(state.session_id)));
 t.selectedViews['3']='previous';const n=calls.length;await t.saveStageSelection('3');assert.equal(calls.length,n);delete t.selectedViews['3'];
 const next={...state,session_id:'b'.repeat(32),version:8};t.set(next);assert.equal(t.currentSelection('3'),null);
 let finish;sandbox.fetch=()=>new Promise(resolve=>{finish=resolve;});const pending=t.openSelection('3');t.set({...next,version:9});finish(response({stage:3,version:8,phrases:[{phrase:1,start_beats:0,length_beats:8}]}));await pending;assert.equal(t.currentSelection('3'),null);
 sandbox.fetch=async()=>response({error:'Unavailable'},false);await t.openSelection('3');assert.ok(t.resultMarkup({id:'3'},state.stages[2]).includes('Retry phrase controls'));assert.ok(!t.resultMarkup({id:'3'},state.stages[2]).includes('data-save-selection'));
 console.log('Stage3-5 selection UI PASS: exact independent stage/version scope, categorical stage1/2 without MIDI selection controls, partial stage5, every save payload, no generation/original mutation, stale response isolation and failure retry.');
})().catch(e=>{console.error(e);process.exitCode=1;});
