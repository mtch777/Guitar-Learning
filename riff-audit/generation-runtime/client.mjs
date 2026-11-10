/* Runner outcomes are distinct from the law's retained musical/raw outcomes. */
export class GeneratorClient{
 constructor({workerURL=new URL('./worker.mjs',import.meta.url),workerFactory=url=>new Worker(url,{type:'module'}),timeoutMs=90000,onProgress=()=>{}}={}){
  this.workerURL=new URL(workerURL);this.workerFactory=workerFactory;this.timeoutMs=timeoutMs;this.onProgress=onProgress;this.worker=null;this.active=null;this.serial=0;
  if(typeof location!=='undefined'&&this.workerURL.origin!==location.origin)throw Error('Worker must be same-origin');
 }
 start(){
  if(this.worker)return;
  const worker=this.workerFactory(this.workerURL);this.worker=worker;
  worker.addEventListener('message',event=>{if(this.worker===worker)this.receive(event.data);});
  worker.addEventListener('error',event=>{if(this.worker===worker)this.fail('worker_error',String(event.message??'Worker failed'));});
  worker.addEventListener('messageerror',()=>{if(this.worker===worker)this.fail('worker_message_error','Worker message could not be decoded');});
 }
 run(command,payload){
  if(this.active)return Promise.resolve({status:'failed',error:{category:'runner_busy',message:'Another job is already running'}});
  if(!['generate','assess'].includes(command))return Promise.resolve({status:'failed',error:{category:'bridge_validation',message:'Unknown command'}});
  if(!Number.isFinite(this.timeoutMs)||this.timeoutMs<=0)return Promise.resolve({status:'failed',error:{category:'runner_configuration',message:'Positive timeout required'}});
  const id='rhythm-job-'+(++this.serial);
  return new Promise(resolve=>{
   this.active={id,command,resolve,started_at:new Date().toISOString()};
   this.timer=setTimeout(()=>this.fail('runner_timeout','Runtime time limit reached; unfinished Python state was not returned','timeout'),this.timeoutMs);
   try{this.start();this.worker.postMessage({id,command,payload});}catch(error){this.fail('worker_start_error',String(error.message??error));}
  });
 }
 generate(payload){return this.run('generate',payload);}
 assess(payload){return this.run('assess',payload);}
 receive(message){
  if(!this.active||message.id!==this.active.id)return; // Late results never replace newer state.
  if(message.status==='loading'||message.status==='running'){this.onProgress(message);return;}
  if(message.status==='result'){
   let result;try{result=JSON.parse(message.result_json);}catch{this.fail('invalid_worker_result','Worker returned invalid result JSON');return;}
   this.finish({status:'result',id:message.id,result,result_json:message.result_json,runtime_receipt:message.runtime_receipt});
  }else if(message.status==='failed'){this.finish({status:'failed',id:message.id,error:message.error});this.reset();}
 }
 finish(outcome){
  if(!this.active)return;clearTimeout(this.timer);const active=this.active;this.active=null;
  active.resolve({...outcome,command:active.command,started_at:active.started_at,finished_at:new Date().toISOString()});
 }
 fail(category,message,status='failed'){
  if(this.active)this.finish({status,id:this.active.id,error:{category,message},raw_available:false});
  this.reset();
 }
 cancel(){if(this.active)this.fail('user_cancelled','Cancelled; unfinished Python state was not returned','cancelled');}
 reset(){this.worker?.terminate();this.worker=null;}
 dispose(){this.cancel();this.reset();}
}
