// Restore temporary GP5 split tracks, export real GP7, and compare reimported data.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import crypto from 'node:crypto';
import {restoreDeadTies} from './restore_dead_ties.mjs';
const [modulePath,root,...options]=process.argv.slice(2),at=await import(pathToFileURL(path.resolve(modulePath)));
// Guard an upstream alphaTab GP5 importer bug when adjacent bars omit a voice.
let voicePaddingRepairs=0,emptyVoiceRestRepairs=0;
at.model.Voice.prototype._chain=function(beat,bag){
 if(!this.bar)return;
 const next=beat.index<this.beats.length-1?this.beats[beat.index+1]:this.bar.nextBar?.voices[this.index]?.beats[0];
 if(beat.index===this.beats.length-1&&this.bar.nextBar&&!next)voicePaddingRepairs++;
 beat.nextBeat=next??null;if(next)next.previousBeat=beat;beat.chain(bag);
};
const settings=new at.Settings();const load=p=>at.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(fs.readFileSync(p)),settings);
const results=[];
function curve(points){if(!points?.length)return null;return Array.from({length:61},(_,x)=>{if(x<=points[0].offset)return points[0].value;for(let i=1;i<points.length;i++)if(x<=points[i].offset){const a=points[i-1],b=points[i];return +(a.value+(b.value-a.value)*(x-a.offset)/(b.offset-a.offset)).toFixed(8);}return points.at(-1).value;});}
function simplify(points){if(!points?.length)return points;const p=[...points];while(p.length>2&&p[0].value===p[1].value)p.shift();while(p.length>2&&p.at(-1).value===p.at(-2).value)p.pop();for(let i=1;i<p.length-1;)if((p[i].value-p[i-1].value)*(p[i+1].offset-p[i].offset)===(p[i+1].value-p[i].value)*(p[i].offset-p[i-1].offset))p.splice(i,1);else i++;return p;}
function snapshot(score){return {bars:score.masterBars.map(b=>[b.timeSignatureNumerator,b.timeSignatureDenominator,b.isRepeatStart,b.repeatCount,b.alternateEndings]),tracks:score.tracks.map(t=>({name:t.name,program:t.playbackInfo.program,staves:t.staves.map(s=>({tuning:s.tuning,capo:s.capo,bars:s.bars.map(b=>b.voices.map(v=>v.beats.map(e=>({duration:e.duration,dots:e.dots,tuplet:[e.tupletNumerator,e.tupletDenominator],grace:e.graceType,vibrato:e.vibrato,whammy:curve(e.whammyBarPoints),notes:e.notes.map(n=>({string:n.string,fret:n.fret,pitch:n.realValueWithoutHarmonic,tie:n.isTieDestination,hp:n.isHammerPullOrigin,vibrato:n.vibrato,dead:n.isDead,palmMute:n.isPalmMute,ghost:n.isGhost,letRing:n.isLetRing,harmonic:[n.harmonicType,n.harmonicValue],slide:[n.slideInType,n.slideOutType],bend:curve(n.bendPoints)})).sort((a,b)=>a.string-b.string||a.fret-b.fret)}))))}))}))};}
function merge(score,map){
 const originalTracks=score.tracks,grouped=new Map();
 for(const [i,entry] of map.entries()){if(!grouped.has(entry.original_track))grouped.set(entry.original_track,[]);grouped.get(entry.original_track).push([originalTracks[i],entry]);}
 score.tracks=[];
 for(const parts of grouped.values()){
  const [base,info]=parts[0],staff=base.staves[0];if(base.staves.length!==1)throw Error('Unexpected multiple staves in bridge');
  const lanes=parts.map(([part,geometry])=>({geometry,bars:part.staves[0].bars.map(bar=>bar.voices.map(voice=>{const rows=[];let grace=[];for(const beat of voice.beats){if(beat.graceType!==0){grace.push(beat);continue;}rows.push({beat,grace});grace=[];}return rows;}))}));
  const restore=(target,items)=>{const notes=[];for(const [beat,geometry] of items)for(const n of beat.notes){if(!geometry.percussion){const gpString=geometry.source_strings.length-n.string+1,originalString=geometry.source_strings[gpString-1];if(!originalString)throw Error('Unmapped bridge string');n.string=geometry.original_string_count-originalString+1;}notes.push(n);}target.notes=[];target.noteStringLookup.clear();for(const n of notes)target.addNote(n);return target;};
  staff.stringTuning.tunings=info.percussion?staff.tuning:info.original_tuning;
  for(const [mi,bar] of staff.bars.entries())for(const [vi,voice] of bar.voices.entries()){
   const count=Math.max(...lanes.map(l=>l.bars[mi]?.[vi]?.length||0)),beats=[];
   for(let bi=0;bi<count;bi++){
    const rows=lanes.map(l=>({row:l.bars[mi]?.[vi]?.[bi],geometry:l.geometry})).filter(r=>r.row);
    const graceCount=Math.max(...rows.map(r=>r.row.grace.length));
    for(let gi=0;gi<graceCount;gi++){const items=rows.filter(r=>r.row.grace[gi]).map(r=>[r.row.grace[gi],r.geometry]);beats.push(restore(items[0][0],items));}
    beats.push(restore(rows[0].row.beat,rows.map(r=>[r.row.beat,r.geometry])));
   }
   voice.beats=[];for(const beat of beats)voice.addBeat(beat);
  }
  base.name=info.original_name;score.addTrack(base);
 }
 for(const track of score.tracks)for(const staff of track.staves){const count=Math.max(...staff.bars.map(b=>b.voices.length));if(count<2)continue;
  for(const bar of staff.bars){while(bar.voices.length<count)bar.addVoice(new at.model.Voice());for(const voice of bar.voices)if(!voice.beats.length||voice.beats.every(b=>b.isEmpty&&!b.notes.length)){
   const master=score.masterBars[bar.index],beat=new at.model.Beat();beat.duration=at.model.Duration.Quarter;beat.tupletNumerator=master.timeSignatureDenominator;beat.tupletDenominator=master.timeSignatureNumerator*4;beat.isEmpty=false;voice.beats=[];voice.addBeat(beat);emptyVoiceRestRepairs++;
  }}
 }
 score.finish(settings);return score;
}
function rawCheck(score,folder){
 const issues=[];let comparedNotes=0,comparedBeats=0;
 for(const [ti,t] of score.tracks.entries()){
  const raw=JSON.parse(fs.readFileSync(path.join(folder,`track-${ti}.json`),'utf8'));const staff=t.staves[0];
  if(raw.instrumentId!==1024&&JSON.stringify(raw.tuning)!==JSON.stringify(staff.tuning))issues.push({track:ti,field:'tuning'});
  for(const [mi,m] of raw.measures.entries())for(const [vi,v] of (m.voices||[]).entries()){
   const expected=(v.beats||[]).filter(b=>!b.graceNote),actual=(staff.bars[mi]?.voices[vi]?.beats||[]).filter(b=>b.graceType===0&&!b.isEmpty);
   if(!expected.length)continue;
   if(expected.length!==actual.length){issues.push({track:ti,bar:mi,voice:vi,field:'beat_count',source:expected.length,gp:actual.length});continue;}
   for(let bi=0;bi<expected.length;bi++){
    const a=expected[bi],b=actual[bi];comparedBeats++;
    if(a.duration){const duration=1/b.duration*(2-1/2**b.dots)*b.tupletDenominator/b.tupletNumerator;if(Math.abs(duration-a.duration[0]/a.duration[1])>1e-9)issues.push({track:ti,bar:mi,voice:vi,beat:bi,field:'duration',source:a.duration,gp:duration});}
    const en=(a.notes||[]).filter(n=>!n.rest).map(n=>[n.string,n.dead?'dead':n.fret]).sort((a,b)=>a[0]-b[0]);
    const an=b.notes.map(n=>[raw.instrumentId===1024?0:staff.tuning.length-n.string,n.isDead?'dead':n.fret]).sort((a,b)=>a[0]-b[0]);
    if(raw.instrumentId===1024)continue; // percussion needs instrument mapping, not fret comparison
    comparedNotes+=en.length;
    if(JSON.stringify(en)!==JSON.stringify(an))issues.push({track:ti,bar:mi,voice:vi,beat:bi,field:'fret_string',source:en,gp:an});
   }
  }
 }
 return {comparedNotes,comparedBeats,differences:issues.length,firstDifferences:issues.slice(0,30),limitations:['Percussion instrument mapping excluded','Grace notes excluded from direct source alignment','Direct source check covers regular fret/string/duration/tuning; effect fidelity additionally depends on source-to-model comparator and GP7 roundtrip']};
}
for(const entry of fs.readdirSync(root,{withFileTypes:true}).filter(e=>e.isDirectory())){
 if(options.some(o=>o.startsWith('--song='))&&!options.includes('--song='+entry.name))continue;
 const folder=path.join(root,entry.name),capture=path.join(folder,'capture.json');if(!fs.existsSync(capture))continue;
 const status=JSON.parse(fs.readFileSync(capture,'utf8'));if(!status.capture_complete)continue;
 const target=path.join(folder,'score.gp'),reportPath=path.join(folder,'gp7-validation.json');
 if(fs.existsSync(reportPath)&&!options.includes('--recheck')){const old=JSON.parse(fs.readFileSync(reportPath,'utf8'));if(old.roundtripPass){results.push(old);continue;}}
 let report={songId:status.song_id,file:target};
 try{
  const map=JSON.parse(fs.readFileSync(path.join(folder,'bridge-map.json'),'utf8'));
  voicePaddingRepairs=0;emptyVoiceRestRepairs=0;const score=merge(load(path.join(folder,'bridge.gp5')),map);
  const metadata=JSON.parse(fs.readFileSync(path.join(folder,'metadata.json'),'utf8'));score.title=metadata.title||score.title;score.artist=metadata.artist||score.artist;
  let rhythmRestorations=0;
  for(const [ti,track] of score.tracks.entries()){
   const raw=JSON.parse(fs.readFileSync(path.join(folder,`track-${ti}.json`),'utf8'));
   for(const [mi,m] of raw.measures.entries())for(const [vi,v] of (m.voices||[]).entries()){
    const expected=(v.beats||[]).filter(b=>!b.graceNote),actual=(track.staves[0].bars[mi]?.voices[vi]?.beats||[]).filter(b=>b.graceType===0&&!b.isEmpty);
    if(expected.length!==actual.length)continue;
    for(let bi=0;bi<expected.length;bi++)if(expected[bi].duration){const [n,d]=expected[bi].duration,b=actual[bi],duration=1/b.duration*(2-1/2**b.dots)*b.tupletDenominator/b.tupletNumerator;
     if(Math.abs(duration-n/d)>1e-9){b.duration=at.model.Duration.Quarter;b.dots=0;b.tupletNumerator=d;b.tupletDenominator=4*n;rhythmRestorations++;}
    }
   }
  }
  score.finish(settings);let percussionGraceRepairs=0;
  for(const track of score.tracks)for(const staff of track.staves)for(const bar of staff.bars)for(const voice of bar.voices)for(const beat of voice.beats){
   for(const note of beat.notes){if(staff.isPercussion&&beat.graceType!==0&&note.percussionArticulation<0&&note.fret>=0){note.percussionArticulation=note.fret;note.fret=-1;note.string=-1;percussionGraceRepairs++;}}
  }
  const deadTieRestoration={checked:0,restored:0,skippedGrace:0};
  for(const [ti,track] of score.tracks.entries()){
   const raw=JSON.parse(fs.readFileSync(path.join(folder,`track-${ti}.json`),'utf8'));
   const result=restoreDeadTies(track,raw);for(const key of Object.keys(deadTieRestoration))deadTieRestoration[key]+=result[key];
  }
  const before=snapshot(score);
  for(const track of score.tracks)for(const staff of track.staves)for(const bar of staff.bars)for(const voice of bar.voices)for(const beat of voice.beats)for(const note of beat.notes){if(note.bendPoints)note.bendPoints=simplify(note.bendPoints);}

  if(fs.existsSync(target)&&!options.includes('--recheck'))throw Error('Unverified existing GP preserved; use --recheck');
  fs.writeFileSync(target,new at.exporter.Gp7Exporter().export(score,settings));const afterScore=load(target),after=snapshot(afterScore);
  report={...report,rhythmRestorations,voicePaddingRepairs,emptyVoiceRestRepairs,percussionGraceRepairs,deadTieRestoration,curveComparisonGrid:61,roundtripPass:JSON.stringify(before)===JSON.stringify(after),tracks:after.tracks.length,bars:after.bars.length,
    notes:after.tracks.reduce((n,t)=>n+t.staves.reduce((n,s)=>n+s.bars.reduce((n,b)=>n+b.reduce((n,v)=>n+v.reduce((n,e)=>n+e.notes.length,0),0),0),0),0),
    directSource:rawCheck(afterScore,folder),sha256:crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex'),bytes:fs.statSync(target).size};
  if(!report.roundtripPass){fs.writeFileSync(path.join(folder,'roundtrip-before.json'),JSON.stringify(before));fs.writeFileSync(path.join(folder,'roundtrip-after.json'),JSON.stringify(after));}
 }catch(error){report.error=String(error);report.stack=error.stack;report.roundtripPass=false;}
 fs.writeFileSync(reportPath,JSON.stringify(report,null,2));results.push(report);console.log(JSON.stringify({songId:report.songId,roundtripPass:report.roundtripPass,notes:report.notes,sourceDifferences:report.directSource?.differences,error:report.error}));
 if(options.includes('--first'))break;
}
const manifest=fs.readdirSync(root,{withFileTypes:true}).filter(e=>e.isDirectory()&&fs.existsSync(path.join(root,e.name,'gp7-validation.json'))).map(e=>JSON.parse(fs.readFileSync(path.join(root,e.name,'gp7-validation.json'),'utf8')));
fs.writeFileSync(path.join(root,'gp7-manifest.json'),JSON.stringify(manifest,null,2));
console.log(JSON.stringify({files:results.length,roundtripPassed:results.filter(r=>r.roundtripPass).length}));
