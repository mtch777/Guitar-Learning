import {loadGenerationRuntime} from './runtime-loader.mjs';
import {MANIFEST_SHA256} from './runtime-pin.mjs';
const runtimeBase=new URL('./',import.meta.url);
const nativeFetch=self.fetch.bind(self);
self.fetch=(input,options)=>{const url=new URL(typeof input==='string'?input:input.url??String(input),runtimeBase);if(url.origin!==runtimeBase.origin||!url.pathname.startsWith(runtimeBase.pathname))return Promise.reject(Error('Runtime network request outside same-origin asset directory refused'));return nativeFetch(input,options);};
let ready=null,busy=false;
const boundedError=error=>String(error?.message??error).slice(0,1200);
self.addEventListener('message',async event=>{
 const message=event.data;
 if(!message||typeof message.id!=='string'||!['generate','assess'].includes(message.command)||typeof message.payload!=='object'){
  self.postMessage({id:message?.id??null,status:'failed',error:{category:'bridge_validation',message:'Invalid fixed-command envelope'}});return;
 }
 if(busy){self.postMessage({id:message.id,status:'failed',error:{category:'runner_busy',message:'One active generation job is supported'}});return;}
 busy=true;
 try{
  self.postMessage({id:message.id,status:'loading'});
  ready??=loadGenerationRuntime({baseURL:new URL('./',import.meta.url),expectedManifestHash:MANIFEST_SHA256});
  const runtime=await ready;
  self.postMessage({id:message.id,status:'running',runtime_receipt:runtime.receipt});
  const result_json=runtime.execute(message.command,message.payload);
  self.postMessage({id:message.id,status:'result',result_json,runtime_receipt:runtime.receipt});
 }catch(error){
  self.postMessage({id:message.id,status:'failed',error:{category:'runtime_or_bridge_error',message:boundedError(error)}});
 }finally{busy=false;}
});
