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
    const files = await Promise.all(['composer.py', 'materials.json'].map(async name => {
      const response = await fetch(new URL(name, assets));
      if (!response.ok) throw new Error(`Could not load ${name} (${response.status}).`);
      return [name, await response.text()];
    }));
    py.FS.mkdirTree('/riff-builder');
    for (const [name, value] of files) py.FS.writeFile(`/riff-builder/${name}`, value);
    await py.runPythonAsync("import sys\nsys.path.insert(0, '/riff-builder')\nfrom composer import generate_json");
    return py;
  })().catch(error => {runtimePromise = null; throw error;});
  return runtimePromise;
}
self.onmessage = async ({data}) => {
  const {id, recipe, tempo, assetBase} = data;
  try {
    self.__assetBase = assetBase;
    const py = await runtime(id);
    self.postMessage({id, type: 'status', message: 'Composing original and developed return…'});
    py.globals.set('request_recipe', recipe);
    py.globals.set('request_tempo', tempo);
    const json = await py.runPythonAsync('generate_json(recipe=request_recipe, tempo=request_tempo)');
    self.postMessage({id, type: 'result', result: JSON.parse(json)});
  } catch (error) {
    self.postMessage({id, type: 'error', message: error?.message || String(error)});
  }
};
