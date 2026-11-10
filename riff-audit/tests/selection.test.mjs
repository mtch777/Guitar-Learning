import {test} from 'node:test';import assert from 'node:assert/strict';import {selectionEntries,matchesSelection,facetCounts,randomSelection} from '../selection.mjs';
const records=[{id:'a',artist:'IA',song:'A',status:'accepted',available:true,replay_export_status:'ready',range_q:['0','4']},{id:'b',artist:'ERRA',song:'B',status:'riff',available:true,replay_export_status:'ready',range_q:['4','8']},{id:'c',artist:'IA',status:'unknown',available:true,replay_export_status:'pending'}];
const entries=selectionEntries(records,{parts:[{record_id:'a',view:'v',unit:'u',kind:'pitched_line',range:['0','1']},{record_id:'c',view:'v',unit:'u'}]});
test('eligible whole riffs and bound candidates only',()=>assert.equal(entries.length,3));
test('counts reflect other active categories, not its own',()=>assert.deepEqual(facetCounts(entries,{scope:'whole',artist:'IA'},'artist'),[['ERRA',1],['IA',1]]));
test('empty intersections stay empty',()=>assert.equal(entries.filter(e=>matchesSelection(e,{scope:'part',artist:'ERRA'})).length,0));
test('random honors bounded pool, avoids immediate repeat, handles zero and one',()=>{assert.equal(randomSelection([],()=>0),null);assert.equal(randomSelection([entries[0]],()=>0,'a').id,'a');assert.equal(randomSelection(entries.slice(0,2),()=>0,'a').id,'b');});
