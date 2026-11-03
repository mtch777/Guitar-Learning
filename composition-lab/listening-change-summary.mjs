// Optional measured totals for the existing listening page. No musical edits.
export function summaryRows(summary){
 if(!summary)return [];
 if(!Array.isArray(summary.tiers))throw Error('Measured tier rows are required.');
 return summary.tiers.map(row=>{
  if(!['tier','change','meaning'].every(k=>typeof row[k]==='string'&&row[k]))throw Error('A tier total needs its scope and denominator.');
  return [row.tier,row.change,row.meaning];
 });
}
export function showSummary(document,summary){
 const rows=summaryRows(summary);if(!rows.length)return;
 const nav=document.createElement('p');nav.className='downloads';
 const totals=document.createElement('a');totals.href='#change-summary';totals.textContent='See change percentages';nav.append(totals);
 for(const item of summary.links||[]){if(!/^\/[a-zA-Z0-9_/-]*$/.test(item.href))throw Error('Review links must stay on this listening server.');const a=document.createElement('a');a.href=item.href;a.textContent=item.label;nav.append(a);}
 document.querySelector('#scope').after(nav);
 document.querySelector('#change-summary-note').textContent=summary.note||'';
 for(const row of rows){const tr=document.createElement('tr');
  for(const value of row){const td=document.createElement('td');td.textContent=value;td.style.cssText='padding:10px 8px;border-top:1px solid #304954;vertical-align:top';tr.append(td);}
  document.querySelector('#change-summary-rows').append(tr);
 }
 for(const value of summary.controls||[]){const li=document.createElement('li');li.textContent=value;li.style.marginBottom='6px';document.querySelector('#control-results').append(li);}
 document.querySelector('#change-qa').textContent=summary.qa||'';
 document.querySelector('#change-summary').hidden=false;
}
if(typeof document!=='undefined')fetch('comparison.json').then(r=>{if(!r.ok)throw Error('Missing comparison data');return r.json();}).then(data=>showSummary(document,data.change_summary)).catch(error=>{const e=document.querySelector('#error');e.hidden=false;e.textContent='Change totals could not load: '+error.message;});
