import { maskProbabilitiesByPitch } from "./candidate-strings.js";

const MODEL_URL = "/model/ringing_xgboost.bin";
const SCALER_URL = "/model/ringing_scaler.json";

let loaded = null;

function softmax(scores) {
  const m=Math.max(...scores);
  const e=scores.map(x=>Math.exp(x-m));
  const s=e.reduce((a,b)=>a+b,0);
  return e.map(x=>x/s);
}

function readModel(buffer) {
  const v=new DataView(buffer); let p=0;
  const treeCount=v.getUint16(p,true); p+=2;
  const trees=[];
  for(let t=0;t<treeCount;t++){
    const cls=v.getUint8(p++), n=v.getUint8(p++);
    const nodes=[];
    for(let i=0;i<n;i++){
      const feature=v.getUint8(p++), value=v.getFloat32(p,true); p+=4;
      if(feature===255) nodes.push({leaf:value});
      else nodes.push({feature,threshold:value,left:v.getUint8(p++),right:v.getUint8(p++)});
    }
    trees.push({cls,nodes});
  }
  return trees;
}

function treeValue(tree,x) {
  let i=0;
  for(;;){
    const n=tree.nodes[i];
    if(n.leaf!==undefined) return n.leaf;
    const value=x[n.feature];
    i=(Number.isNaN(value)||value<n.threshold)?n.left:n.right;
  }
}

export async function loadFullRingingClassifier() {
  if(loaded) return loaded;
  const [modelResponse,scalerResponse]=await Promise.all([fetch(MODEL_URL),fetch(SCALER_URL)]);
  if(!modelResponse.ok) throw new Error(`Full classifier model missing (${modelResponse.status})`);
  if(!scalerResponse.ok) throw new Error(`Full classifier scaler missing (${scalerResponse.status})`);
  const [buffer,scaler]=await Promise.all([modelResponse.arrayBuffer(),scalerResponse.json()]);
  const trees=readModel(buffer);
  if(scaler.mean.length!==107||scaler.scale.length!==107) throw new Error("Classifier scaler must contain 107 features.");
  loaded={trees,scaler};
  return loaded;
}

export async function classifyRingingPluck({midi,features}) {
  if(features?.length!==107) throw new Error(`Expected 107 features; got ${features?.length ?? 0}`);
  const {trees,scaler}=await loadFullRingingClassifier();
  const x=Array.from(features,(v,i)=>(v-scaler.mean[i])/scaler.scale[i]);
  const scores=Array(8).fill(0);
  for(const tree of trees) scores[tree.cls]+=treeValue(tree,x);
  const raw=softmax(scores);
  const probabilities=maskProbabilitiesByPitch(raw,midi);
  let best=0;
  for(let i=1;i<8;i++) if(probabilities[i]>probabilities[best]) best=i;
  return {string:best+1,confidence:probabilities[best],probabilities};
}
