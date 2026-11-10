const textDecoder=new TextDecoder();
const hex=bytes=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
export async function sha256(bytes){return hex(await crypto.subtle.digest('SHA-256',bytes));}
export function localAsset(baseURL,path){
 if(typeof path!=='string'||!path||path.includes('\\')||path.split('/').some(x=>x==='..'||x==='.')||/^\w+:/.test(path)||path.startsWith('/'))throw Error('Invalid runtime asset path');
 const url=new URL(path,baseURL);
 if(url.origin!==baseURL.origin||!url.pathname.startsWith(baseURL.pathname))throw Error('Runtime asset must remain same-origin and inside its directory');
 return url;
}
export async function loadGenerationRuntime({baseURL=new URL('./',import.meta.url),readBytes=null,expectedManifestHash=null}={}){
 baseURL=new URL(baseURL);
 if(typeof location!=='undefined'&&location.protocol!=='file:'&&baseURL.origin!==location.origin)throw Error('Cross-origin runtime refused');
 const read=readBytes??(async url=>{
  if(url.origin!==baseURL.origin)throw Error('Cross-origin runtime request refused');
  const r=await fetch(url,{credentials:'omit',cache:'force-cache'});
  if(!r.ok)throw Error(`Runtime asset unavailable (${r.status}): ${url.pathname.split('/').at(-1)}`);
  return new Uint8Array(await r.arrayBuffer());
 });
 const manifestBytes=await read(localAsset(baseURL,'asset-manifest.json'));
 if(expectedManifestHash&&await sha256(manifestBytes)!==expectedManifestHash)throw Error('Runtime manifest integrity mismatch');
 const manifest=JSON.parse(textDecoder.decode(manifestBytes));
 if(manifest.schema!=='rhythm-pages-runtime-assets/1'||manifest.pyodide_version!=='314.0.7')throw Error('Unexpected runtime manifest');
 const verified=new Map();
 for(const asset of manifest.files){
  const bytes=await read(localAsset(baseURL,asset.path));
  if(bytes.byteLength!==asset.bytes||await sha256(bytes)!==asset.sha256)throw Error('Runtime integrity mismatch: '+asset.path);
  verified.set(asset.path,bytes);
 }
 // Execution uses the exact verified byte buffers, never a second URL import/read.
 const vendor='vendor/pyodide-314.0.7/';
 const moduleURLs=[];
 async function importVerified(bytes,name){
  if(globalThis.process?.versions?.node){
   const vm=await import('node:vm');
   if(!vm.SourceTextModule)throw Error('Node parity requires --experimental-vm-modules for verified in-memory module execution');
   const module=new vm.SourceTextModule(textDecoder.decode(bytes),{identifier:localAsset(baseURL,name).href,
    initializeImportMeta:meta=>{meta.url=localAsset(baseURL,name).href;},importModuleDynamically:specifier=>import(specifier)});
   await module.link(()=>{throw Error('Unexpected static runtime module import');});await module.evaluate();return module.namespace;
  }
  const url=URL.createObjectURL(new Blob([bytes],{type:'text/javascript'}));moduleURLs.push(url);return import(url);
 }
 const originalFetch=globalThis.fetch;
 const memoryFetch=async input=>{
  const url=new URL(typeof input==='string'?input:input.url??String(input),baseURL);
  for(const [name,bytes]of verified)if(url.href===localAsset(baseURL,name).href){
   return new Response(bytes,{status:200,headers:{'Content-Type':name.endsWith('.wasm')?'application/wasm':'application/octet-stream'}});
  }
  throw Error('Runtime request outside verified in-memory assets refused');
 };
 globalThis.fetch=memoryFetch;
 const {loadPyodide}=await importVerified(verified.get(vendor+'pyodide.mjs'),vendor+'pyodide.mjs');
 const {default:createModule}=await importVerified(verified.get(vendor+'pyodide.asm.mjs'),vendor+'pyodide.asm.mjs');
 let indexURL=localAsset(baseURL,vendor).href;
 if(baseURL.protocol==='file:')indexURL=decodeURIComponent(localAsset(baseURL,vendor).pathname).replace(/^\/([A-Za-z]:\/)/,'$1');
 let wasmReject;
 const wasmFailure=new Promise((_,reject)=>{wasmReject=reject;});
 const createVerifiedModule=settings=>{
  // Equivalent to upstream installStdlib, but no unverified reread is consumed.
  settings.preRun[0]=module=>{
   const version=module.HEAPU32[module._Py_Version>>>2];
   const tuple=[version>>>24&255,version>>>16&255,version>>>8&255];
   module.API.pyVersionTuple=tuple;
   const [major,minor]=tuple;
   module.API.sitePackages=`/lib/python${major}.${minor}/site-packages`;
   module.FS.mkdirTree(module.API.sitePackages);module.FS.mkdirTree(`/lib/python${major}.${minor}/lib-dynload`);
   module.FS.writeFile(`/lib/python${major}${minor}.zip`,verified.get(vendor+'python_stdlib.zip'));
  };
  // This is Pyodide's own supported Symbol-marker fallback, also used upstream on iOS.
  settings.instantiateWasm=(imports,receive)=>{
   const marker=Symbol('verified Pyodide error marker');
   imports.env.Jsv_GetError_import=()=>marker;
   imports.env.JsvError_Check=value=>value===marker;
   WebAssembly.instantiate(verified.get(vendor+'pyodide.asm.wasm'),imports)
    .then(({instance,module})=>receive(instance,module),wasmReject);
   return {};
  };
  return createModule(settings);
 };
 let pyodide;
 try{
  pyodide=await Promise.race([loadPyodide({indexURL,packageBaseUrl:indexURL,createPyodideModule:createVerifiedModule,
   lockFileContents:JSON.parse(textDecoder.decode(verified.get(vendor+'pyodide-lock.json'))),
   enableRunUntilComplete:false,checkAPIVersion:true}),wasmFailure]);
 }catch(error){globalThis.fetch=originalFetch;for(const url of moduleURLs)URL.revokeObjectURL(url);throw error;}
 pyodide.FS.mkdirTree('/app/generation');
 for(const asset of manifest.files.filter(x=>x.kind==='python')){
  const relative=asset.path.slice('python/'.length);
  if(relative.includes('..'))throw Error('Unsafe Python asset');
  pyodide.FS.writeFile('/app/'+relative,verified.get(asset.path));
 }
 pyodide.runPython("import sys; sys.dont_write_bytecode=True; sys.path.insert(0,'/app'); import runtime_bridge");
 const bridge=pyodide.globals.get('runtime_bridge');
 const call=bridge.execute;
 const parse=pyodide.runPython('import json; json.loads');
 const receipt={pyodide_version:manifest.pyodide_version,manifest_sha256:await sha256(manifestBytes),
  law:manifest.law,python_files:manifest.files.filter(x=>x.kind==='python').map(x=>({path:x.path,sha256:x.sha256})),
  network_policy:'same-origin acquisition, then verified memory-only runtime; no remote backend or package installation',
  execution_integrity:'verified loader/asm modules, verified WASM buffer, verified stdlib buffer and lockfile',
  wasm_error_marker:'upstream-compatible Symbol fallback'};
 return {receipt,pyodide,execute(command,payload){
  // Parse Python-side JSON from text, avoiding JS Number coercion of any large integers.
  const jsonText=JSON.stringify(payload);
  const pyPayload=parse(jsonText);
  try{return call(command,pyPayload);}finally{pyPayload.destroy();}
 },dispose(){parse.destroy();call.destroy();bridge.destroy();if(globalThis.fetch===memoryFetch)globalThis.fetch=originalFetch;for(const url of moduleURLs)URL.revokeObjectURL(url);}};
}
