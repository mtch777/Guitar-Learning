const PYODIDE_ROOT = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let runtimePromise, queue = Promise.resolve();
const sha256 = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');

async function runtime(id, assetBase) {
  if (!runtimePromise) runtimePromise = (async () => {
    self.postMessage({id,type:'status',message:'Loading composer… first load takes a moment.'});
    const assets = new URL(assetBase);
    const manifestResponse = await fetch(new URL('procedural-manifest.json',assets),{cache:'no-store'});
    if (!manifestResponse.ok) throw new Error(`Could not load the composer manifest (${manifestResponse.status}).`);
    const manifest = await manifestResponse.json();
    if (manifest.schema !== 'procedural-riff-browser/1') throw new Error('Unsupported composer manifest.');
    const files = await Promise.all(['engine','pack'].map(async key => {
      const entry=manifest[key];
      if (!entry || !/^[a-zA-Z0-9._-]+$/.test(entry.file) || !/^[a-f0-9]{64}$/.test(entry.sha256)) throw new Error('Invalid composer asset declaration.');
      const response=await fetch(new URL(entry.file,assets));
      if (!response.ok) throw new Error(`Could not load the composer ${key} (${response.status}).`);
      const bytes=new Uint8Array(await response.arrayBuffer());
      const actual=await sha256(bytes);
      // Some static hosts serve .gz with Content-Encoding:gzip; fetch then
      // returns decoded JSON. Verify either representation explicitly.
      const decoded=key==='pack'&&/^[a-f0-9]{64}$/.test(entry.json_sha256)&&actual===entry.json_sha256;
      if (actual!==entry.sha256&&!decoded) throw new Error('Composer assets are from different versions. Reload and try again.');
      return {key,bytes,decoded};
    }));
    const {loadPyodide}=await import(/* @vite-ignore */ `${PYODIDE_ROOT}pyodide.mjs`);
    const py=await loadPyodide({indexURL:PYODIDE_ROOT});
    py.FS.mkdirTree('/riff-builder');
    for (const {key,bytes,decoded} of files) py.FS.writeFile(`/riff-builder/${key==='engine'?'procedural_engine.py':decoded?'program-pack.json':'program-pack.json.gz'}`,bytes);
    const pack=files.find(file=>file.key==='pack');
    await py.runPythonAsync("import sys,json,gzip\nsys.path.insert(0, '/riff-builder')\nfrom procedural_engine import generate\nprogram_pack=json.load("+(pack.decoded?"open('/riff-builder/program-pack.json','rt')":"gzip.open('/riff-builder/program-pack.json.gz','rt')")+")");
    return {py,manifest};
  })().catch(error=>{runtimePromise=null;throw error;});
  return runtimePromise;
}

async function handle({id,request,assetBase}) {
  try {
    const {py,manifest}=await runtime(id,assetBase);
    self.postMessage({id,type:'status',message:'Composing related phrases…'});
    py.globals.set('request_json',JSON.stringify(request));
    const result=JSON.parse(await py.runPythonAsync('json.dumps(generate(json.loads(request_json), program_pack),separators=(",",":"))'));
    result.runtime={engine_sha256:manifest.engine.sha256,pack_sha256:manifest.pack.sha256};
    self.postMessage({id,type:'result',result});
  } catch(error) {self.postMessage({id,type:'error',message:error?.message||String(error)});}
}

self.onmessage=({data})=>{queue=queue.then(()=>handle(data),()=>handle(data));};
