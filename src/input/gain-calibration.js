// Diagnostics only: never changes PCM, classifier features, or detection thresholds.
export const db=x=>20*Math.log10(Math.max(x,1e-12));
export function percentile(values,q){const v=[...values].sort((a,b)=>a-b);return v.length?v[Math.floor((v.length-1)*q)]:null;}
export function measure(samples){let energy=0,peak=0,nearFullScale=0;for(const x of samples){energy+=x*x;peak=Math.max(peak,Math.abs(x));if(Math.abs(x)>=.999)nearFullScale++;}return {peakDb:db(peak),rmsDb:db(Math.sqrt(energy/samples.length)),nearFullScale};}
export function summarize(blocks,noiseDb=null){return {peakDb:Math.max(...blocks.map(b=>b.peakDb)),loudestBlockRmsDb:Math.max(...blocks.map(b=>b.rmsDb)),noiseMarginDb:noiseDb===null?null:Math.max(...blocks.map(b=>b.rmsDb))-noiseDb,nearFullScale:blocks.reduce((n,b)=>n+b.nearFullScale,0),blocks:blocks.length};}
export function assess(reading,noiseDb){
 if(reading.nearFullScale)return 'Possible digital clipping · lower Focusrite gain and repeat the hard-pick check.';
 if(reading.peakDb>-3)return 'Little headroom · lower Focusrite gain before harder picking.';
 if(reading.loudestBlockRmsDb<-48)return 'Below the current onset RMS gate · check channel/gain, then repeat with a clean pick.';
 if(noiseDb!==null&&reading.loudestBlockRmsDb-noiseDb<20)return 'Small noise margin · check noise, gain, and clean picking; louder software gain cannot improve this margin.';
 return 'Usable level for this attack · confirm hardest picks and soft picks during calibration.';
}
export function calibrationVerdict(notes){
 if(notes.some(n=>n.nearFullScale||n.peakDb>-3))return 'Lower gain · at least one attack had less than 3 dB headroom or reached full scale. Recalibrate after adjusting.';
 if(notes.some(n=>n.loudestBlockRmsDb<-48||n.noiseMarginDb<20))return 'Soft-note reliability needs attention · check noise/clean picking; raise gain only if hard picks leave enough headroom. Recalibrate.';
 return 'Keep this gain setting · measured picks have headroom and clear noise margin. This does not yet establish model accuracy.';
}
export const calibrationSteps=[{kind:'silence'},...[1,2,3,4,5,6,7,8].flatMap(string=>['hard','normal','soft'].map(attack=>({kind:'note',string,fret:0,attack})))];
