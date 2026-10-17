import * as fs from 'node:fs';
import * as path from 'node:path';
import * as alphaTab from '@coderline/alphatab';
const root=process.argv[2]||'composition-lab/songsterr_automation/downloads';
const settings=new alphaTab.Settings();
const load=p=>alphaTab.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(p)),settings);
const results=[];
function walk(dir){if(!fs.existsSync(dir))return;for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(e.name.endsWith('.gp5')){const target=p.slice(0,-4)+'.gp';try{const src=load(p);const bytes=new alphaTab.exporter.Gp7Exporter().export(src,settings);fs.writeFileSync(target,Buffer.from(bytes));const dest=load(target);const count=s=>s.tracks.reduce((n,t)=>n+t.staves.reduce((q,st)=>q+st.bars.reduce((z,b)=>z+b.voices.reduce((w,v)=>w+v.beats.reduce((k,beat)=>k+beat.notes.length,0),0),0),0),0);const originalNotes=count(src),finalNotes=count(dest);const pass=originalNotes>0&&originalNotes===finalNotes&&src.masterBars.length===dest.masterBars.length&&src.tracks.length===dest.tracks.length;results.push({source:p,gp7:target,bytes:fs.statSync(target).size,originalNotes,finalNotes,bars:dest.masterBars.length,tracks:dest.tracks.length,pass});}catch(e){results.push({source:p,error:String(e),pass:false})}}}}
walk(root);
const report={files:results,success:results.length>0&&results.every(r=>r.pass)};
fs.mkdirSync('songsterr-run',{recursive:true});fs.writeFileSync('songsterr-run/exports.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(!report.success)process.exitCode=1;
