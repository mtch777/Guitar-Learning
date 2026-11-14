const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
const handlers={},noop=()=>{},node={addEventListener:(name,fn)=>{handlers[name]=fn;},querySelectorAll:()=>[],querySelector:()=>node,setAttribute:noop,append:noop};
const sandbox={console,location:{origin:'http://127.0.0.1:8878'},CSS:{escape:String},document:{querySelector:()=>node,addEventListener:noop},window:{addEventListener:noop},sessionStorage:{getItem:()=>null,setItem(){throw Error('No writes');}},setTimeout:()=>1,clearTimeout:noop,setInterval:()=>1,clearInterval:noop,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,Map,Set,URL,Math,JSON,Number,String,Array,Object,Error,Promise};
let code=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
code=code.replace('  init();\n})();',`  globalThis.test={categoryData,categoricalMarkup,resultMarkup,set(){config={stages:[{id:'1'},{id:'2'},{id:'3'}]};state={version:1,stages:[]};connected=true;}};\n})();`);
vm.createContext(sandbox);vm.runInContext(code,sandbox);const t=sandbox.test;t.set();
const rows=[8,4,.5,13].map((length,i)=>({'Phrase #':i+1,'Length (beats)':length,'Phrase role':i?'phrase':'<script>','Dominant texture':'single_notes','Accent function':'unassigned','Intended same notes and timing as (phrase #s)':i?'none':'2','Intended same pitch sequence as (phrase #s)':'unknown','Intended same rhythm and holds as (phrase #s)':'none','Intended variation of (phrase #s)':'Not established','Variation target - what stays the same':'timing','Variation target - what changes':'pitches','Source variation evidence status':'not assessed'}));
const output={summary:{Beats:999,'Reference artist':'Currents'},details:{blueprint:{phrases:rows}},phrases:rows.map((r,i)=>({phrase:i+1,length_beats:999,start_beats:0})),audio:{tempo:120,length_beats:999,notes:[{start_beats:0,duration_beats:1,midi_pitch:28}]}};
const before=JSON.stringify(output),html=t.resultMarkup({id:'2'},{status:'complete',output});
assert.ok(html.includes('--category-columns:8fr 4fr 0.5fr 13fr'));assert.ok(html.includes('width:2244px')); // global scale 88, shortest44
for(const token of ['data-save-midi','data-timeline','data-kontakt','data-save-selection','beats','Beats','999','<script>'])assert.ok(!html.includes(token),token);
assert.ok(html.includes('&lt;script&gt;'));assert.ok(html.includes('unknown'));assert.ok(html.includes('Not established'));assert.ok(html.includes('Intended relationships'));
assert.equal(JSON.stringify(output),before);
const seed={details:{attributes:{'Phrase #':'1','Length (quarter-note beats)':'3','Phrase role':'phrase','Category - dominant texture':'single_notes','Accent function':'phrase function: unassigned; other data: 4','Same notes and timing as (phrase #s)':'8'}},phrases:[{phrase:1,length_beats:999}],summary:{Beats:3,Artist:'ERRA'}};
const seedHTML=t.resultMarkup({id:'1'},{status:'complete',output:seed});assert.ok(seedHTML.includes('--category-columns:3fr'));assert.ok(seedHTML.includes('unassigned'));assert.ok(!seedHTML.includes('other data'));assert.ok(!seedHTML.includes('Notes + timing'));assert.ok(!seedHTML.includes('Beats'));
const fallback=t.categoricalMarkup({phrases:[{phrase:1,length_beats:2,role:'phrase'}]},'1');assert.ok(fallback.includes('Not available'));assert.ok(!fallback.includes('Opening'));
assert.ok(t.categoricalMarkup({phrases:[{phrase:1,length_beats:0}]},'1').includes('cannot be sized'));
const later=t.resultMarkup({id:'3'},{status:'complete',output:{audio:output.audio}});assert.ok(later.includes('data-timeline'));assert.ok(later.includes('data-save-midi'));
console.log('PASS categorical timeline: source/blueprint lengths, fractional ratios, no MIDI controls/beat labels, exact source labels, escaping, unknowns, no mutation and later-stage retention.');

let disclosureScroll=null;const readout={hidden:true,textContent:'',scrollIntoView(options){disclosureScroll=options;}},cell={dataset:{categoryHeading:'Phrase 3 · Texture',categoryValue:'single notes'},closest:()=>({querySelector:()=>readout})};handlers.click({target:{closest:selector=>selector==='[data-category-value]'?cell:null}});assert.equal(readout.hidden,false);assert.equal(disclosureScroll.block,'nearest');assert.equal(readout.textContent,'Phrase 3 · Texture: single notes');console.log('PASS tap/keyboard click disclosure without network or state writes.');
if(fs.existsSync(require('path').join(__dirname,'actual-category-fixture.json'))){
const fixture=JSON.parse(fs.readFileSync(require('path').join(__dirname,'actual-category-fixture.json')));
const sourceSeed=fixture.state.stages[0].output,sourceScaffold=fixture.state.stages[1].output;
const actual=t.categoryData(sourceScaffold,'2');assert.deepEqual(Array.from(actual.phrases,p=>p.length),[3,3,13,7,1,8,6.75,1.25,5.5,3,.5,.5]);assert.equal(t.categoryData(sourceSeed,'1').phrases.length,1);assert.equal(t.categoryData(sourceSeed,'1').phrases[0].length,3);assert.ok(actual.phrases.every(p=>p.values[0]==='phrase'&&p.values[1]==='single notes'&&p.values[2]==='unassigned'));
console.log('PASS actual ERRA seed/Currents scaffold fixture: all12 phrase proportions and actual categorical values.');

}
