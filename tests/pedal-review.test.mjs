import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const code=fs.readFileSync(new URL('../composition-lab/pedal-review.js',import.meta.url),'utf8');
function setup(storage=new Map()){
 const node=(extra={})=>({value:'',dataset:{},listeners:{},attrs:{},classList:{values:new Set(),add(x){this.values.add(x)},toggle(x,on){on?this.values.add(x):this.values.delete(x)}},addEventListener(e,f){this.listeners[e]=f},setAttribute(k,v){this.attrs[k]=v},...extra});
 const notes=[node({dataset:{note:'n1',pitch:'40',bar:'1',start:'0',end:'1'}}),node({dataset:{note:'n2',pitch:'47',bar:'1',start:'1',end:'2'}})];
 const select=node(),text=node(),coverage=node(),identity=node(),extent=node(),reveal=node(),clear=node(),summary=node(),line=node(),audio=node({paused:true,currentTime:0,pause(){this.paused=true}});
 const elements={'select':select,'textarea':text,'.marking-coverage':coverage,'.anchor-identity':identity,'.anchor-extent':extent,'.reveal':reveal,'.clear-notes':clear,'.selection-summary':summary,'.playhead':line,'audio':audio,'svg':node({dataset:{timeMap:JSON.stringify([{x:0,seconds:0},{x:480,seconds:1},{x:960,seconds:3}])}})};
 const card=node({dataset:{id:'case-1',cohort:'new_source'},querySelector:s=>elements[s],querySelectorAll:s=>s==='.source-note'?notes:[audio]});
 const context=vm.createContext({document:{querySelector:s=>s.includes('meta')?{content:'study'}:s==='.reveal'?reveal:node(),querySelectorAll:s=>s==='article'?[card]:[audio]},location:{search:'?qa=1'},URLSearchParams,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},requestAnimationFrame(){},URL:{},Blob,Date,setTimeout});
 vm.runInContext(code,context);
 return {notes,select,text,coverage,identity,extent,reveal,storage,card,context,clear};
}
test('anchor selections and completeness survive reload with exact identities',()=>{
 const a=setup();a.notes[0].listeners.click();a.coverage.value='examples';a.coverage.onchange();
 const b=setup(a.storage);assert.equal(b.notes[0].attrs['aria-pressed'],'true');assert.equal(b.coverage.value,'examples');
 const saved=JSON.parse(a.storage.get('study-qa'))['case-1'];assert.deepEqual(saved.selected_notes,[{occurrence:'n1',pitch:40,bar:1}]);assert.equal(a.storage.has('study'),false);
});
test('first reveal preserves independent markings and judgment after edits',()=>{
 const a=setup();a.notes[0].listeners.click();a.select.value='Yes';a.reveal.onclick();
 a.notes[1].listeners.click();a.select.value='Unclear';a.select.onchange();a.reveal.onclick();
 const saved=JSON.parse(a.storage.get('study-qa'))['case-1'];
 assert.equal(saved.pre_reveal_judgment.answer,'Yes');assert.equal(saved.pre_reveal_selection.length,1);assert.equal(saved.selected_notes.length,2);assert.equal(saved.answer,'Unclear');
});
test('playhead interpolation follows changing tempo rather than audio duration',()=>{
 const a=setup();assert.equal(vm.runInContext('positionAt(2,[{x:0,seconds:0},{x:480,seconds:1},{x:960,seconds:3}])',a.context),720);
});
