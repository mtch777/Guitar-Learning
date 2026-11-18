// Silent regression: render the real uploaded Phoebe score at phone-size widths.
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseMusicXML} from '../../public/piano/learning-songs/score-model.js';
import {ScoreRenderer} from '../../public/piano/learning-songs/score-renderer.js';

const dependencies = createRequire(resolve(process.argv[2] || 'package.json'));
const {JSDOM} = dependencies('jsdom');
const {createCanvas} = dependencies('@napi-rs/canvas');
const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const xml = readFileSync(resolve(root, 'public/piano/learning-songs/uploads/I_Know_the_End.musicxml'), 'utf8');
const results = [];
for (const [width, height, longTextBounds] of [[900,300],[545,260],[420,300],[390,300],[390,180],[340,100],[390,300,true]]) {
  const dom = new JSDOM('<!doctype html><div id="viewport"><div id="score"></div></div>',
    {pretendToBeVisual:true, runScripts:'outside-only', url:'http://localhost/'});
  const {window} = dom;
  const canvases = new WeakMap();
  window.HTMLCanvasElement.prototype.getContext = function(type) {
    if (!canvases.has(this)) canvases.set(this, createCanvas(this.width || 300, this.height || 150));
    return canvases.get(this).getContext(type);
  };
  Object.defineProperty(window.HTMLElement.prototype,'clientWidth',{get(){return width;}});
  Object.defineProperty(window.HTMLElement.prototype,'offsetWidth',{get(){return width;}});
  Object.defineProperty(window.HTMLElement.prototype,'clientHeight',{get(){return this.id === 'viewport' ? height : 0;}});
  // Actual Android SVG getBBox includes direction/lyric text protruding far
  // beyond the note measures. This used to cause eight gutter passes and throw.
  if (longTextBounds) window.SVGSVGElement.prototype.getBBox = () => ({x:-15,y:0,width:50000,height:100});
  window.eval(readFileSync(resolve(root,'public/piano/learning-songs/vendor/opensheetmusicdisplay-2.3.1.min.js'),'utf8'));
  const model = parseMusicXML(xml,{DOMParser:window.DOMParser,XMLSerializer:window.XMLSerializer});
  const renderer = new ScoreRenderer(window.document.getElementById('score'),window.document.getElementById('viewport'));
  try {
    const report = await renderer.load(model);
    results.push({width,height,longTextBounds:Boolean(longTextBounds),status:'pass',systems:report.systems,mappedNotes:report.mappedNotes,zoom:renderer.osmd.Zoom});
  } catch(error) { results.push({width,height,longTextBounds:Boolean(longTextBounds),status:'fail',error:error.message,stack:String(error.stack).slice(0,500)}); }
  renderer.dispose?.();
  window.close();
}
console.log(JSON.stringify(results,null,2));
if(results.some(x=>x.status==='fail'))process.exitCode=1;
