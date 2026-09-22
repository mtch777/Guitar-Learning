import { extractRingingFeatures } from "../src/classifier/ringing-features.js";

export const FEATURE_STATS=["mean","std","p25","median","p75"];
export const FEATURE_NAMES=(()=>{
  const names=[];
  for(const part of ["attack","sustain"]){
    for(let i=1;i<=13;i++) names.push(`${part}_mfcc${i}_mean`,`${part}_mfcc${i}_std`);
    for(const descriptor of ["centroid","bandwidth","rolloff","flatness","zcr"]){
      for(const stat of FEATURE_STATS) names.push(`${part}_${descriptor}_${stat}`);
    }
  }
  names.push("attack_peak_dbfs","attack_rms_50_dbfs","attack_rms_100_dbfs","attack_energy_100","total_rms_dbfs");
  if(names.length!==107) throw new Error(`Expected 107 feature names, got ${names.length}`);
  return names;
})();

export function compareFeatureParity(samples,sampleRate,reference){
  const actual=extractRingingFeatures(samples,sampleRate);
  const rows=FEATURE_NAMES.map((name,i)=>{
    const expected=Number(reference.features[name]);
    const got=Number(actual[i]);
    const absError=Math.abs(got-expected);
    const relError=absError/Math.max(Math.abs(expected),1e-12);
    return {index:i,name,expected,actual:got,absError,relError};
  });
  rows.sort((a,b)=>b.relError-a.relError);
  return {
    count:rows.length,
    maxAbsError:Math.max(...rows.map(r=>r.absError)),
    maxRelError:Math.max(...rows.map(r=>r.relError)),
    worst:rows.slice(0,25),
    rows
  };
}
