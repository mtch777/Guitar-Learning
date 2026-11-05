const PYODIDE_ROOT = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
let runtimePromise;
async function runtime(id) {
  if (!runtimePromise) runtimePromise = (async () => {
    self.postMessage({id, type: 'status', message: 'Loading composer… first load takes a moment.'});
    const {loadPyodide} = await import(/* @vite-ignore */ `${PYODIDE_ROOT}pyodide.mjs`);
    const py = await loadPyodide({indexURL: PYODIDE_ROOT});
    const base = new URL('../riff-builder/', self.location.href);
    // The caller supplies the deployed base URL: Vite workers live under assets/.
    const assets = new URL(self.__assetBase || base.href);
    const files = await Promise.all(['pattern_engine.py', 'pattern-pack.json.gz'].map(async name => {
      const response = await fetch(new URL(name, assets));
      if (!response.ok) throw new Error(`Could not load ${name} (${response.status}).`);
      return [name, name.endsWith('.gz') ? new Uint8Array(await response.arrayBuffer()) : await response.text()];
    }));
    py.FS.mkdirTree('/riff-builder');
    for (const [name, value] of files) py.FS.writeFile(`/riff-builder/${name}`, value);
    await py.runPythonAsync("import sys,json,gzip\nsys.path.insert(0, '/riff-builder')\nfrom pattern_engine import generate\npattern_pack=json.load(gzip.open('/riff-builder/pattern-pack.json.gz','rt'))");
    return py;
  })().catch(error => {runtimePromise = null; throw error;});
  return runtimePromise;
}
self.onmessage = async ({data}) => {
  const {id, request, assetBase} = data;
  try {
    self.__assetBase = assetBase;
    const py = await runtime(id);
    self.postMessage({id, type: 'status', message: 'Composing riff…'});
    py.globals.set('request_json', JSON.stringify(request));
    const json = await py.runPythonAsync('json.dumps(generate(json.loads(request_json), pattern_pack))');
    self.postMessage({id, type: 'result', result: JSON.parse(json)});
  } catch (error) {
    self.postMessage({id, type: 'error', message: error?.message || String(error)});
  }
};
