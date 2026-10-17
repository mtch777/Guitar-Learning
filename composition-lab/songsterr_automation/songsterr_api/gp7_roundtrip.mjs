import * as fs from 'node:fs';
import * as path from 'node:path';
import * as alphaTab from '@coderline/alphatab';

const root = process.argv[2] || 'songsterr-e2e';
const input = fs.readdirSync(root).find(n => n.endsWith('.gp5'));
if (!input) throw new Error('Missing source GP5');
const settings = new alphaTab.Settings();
const load = file => alphaTab.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(file)), settings);
const source = load(path.join(root,input));
const exporter = new alphaTab.exporter.Gp7Exporter();
const gp = path.join(root, input.replace(/\.gp5$/,'.gp'));
fs.writeFileSync(gp,Buffer.from(exporter.export(source,settings)));
const roundtrip = load(gp);
function extract(score) {
 const events=[];
 const effects={bend:0,slide:0,hammerPull:0,vibrato:0,palmMute:0,dead:0,ghost:0,harmonic:0,letRing:0};
 for(const [ti,track] of score.tracks.entries()) for(const [si,staff] of track.staves.entries()) for(const [bi,bar] of staff.bars.entries()) for(const [vi,voice] of bar.voices.entries()) for(const [beatIndex,beat] of voice.beats.entries()) for(const note of beat.notes) {
  const ev={track:ti,staff:si,bar:bi,voice:vi,beat:beatIndex,string:note.string,fret:note.fret,beatDuration:beat.duration,beatDots:beat.dots,beatTupletNumerator:beat.tupletNumerator,beatTupletDenominator:beat.tupletDenominator};
  events.push(ev);
  for(const [name,value] of Object.entries({bend:note.hasBend,slide:note.slideOutType!==0||note.slideInType!==0,hammerPull:note.isHammerPullOrigin||note.isHammerPullDestination,vibrato:note.vibrato!==0,palmMute:note.isPalmMute,dead:note.isDead,ghost:note.isGhost,harmonic:note.harmonicType!==0,letRing:note.isLetRing}))if(value)effects[name]++;
 }
 return {tracks:score.tracks.length,bars:score.masterBars.length,notes:events.length,effects,events};
}
const a=extract(source), b=extract(roundtrip);
const mismatches=[];
for(let i=0;i<Math.max(a.events.length,b.events.length);i++)if(JSON.stringify(a.events[i])!==JSON.stringify(b.events[i])){if(mismatches.length<20)mismatches.push({index:i,source:a.events[i],gp7:b.events[i]});}
const summary={source_gp5:input,export_gp7:path.basename(gp),gp7_bytes:fs.statSync(gp).size,source:{tracks:a.tracks,bars:a.bars,notes:a.notes,effects:a.effects},roundtrip:{tracks:b.tracks,bars:b.bars,notes:b.notes,effects:b.effects},event_mismatch_count:a.events.length===b.events.length? a.events.filter((e,i)=>JSON.stringify(e)!==JSON.stringify(b.events[i])).length:Math.max(a.events.length,b.events.length),first_mismatches:mismatches};
summary.success=summary.event_mismatch_count===0 && a.tracks===b.tracks && a.bars===b.bars && Object.keys(a.effects).every(k=>a.effects[k]===b.effects[k]) && fs.statSync(gp).size>0;
fs.mkdirSync('composition-lab/songsterr_automation/results',{recursive:true});
fs.writeFileSync('composition-lab/songsterr_automation/results/gp7_roundtrip_report.json',JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary,null,2));
if(!summary.success)process.exitCode=1;
