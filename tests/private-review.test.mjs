import test from 'node:test';
import assert from 'node:assert/strict';
import {validateBundle,synthesizeWav} from '../src/private-review-bundle.mjs';
import {recordReview,mergeFeedback,csvFeedback} from '../src/ablation-review-state.mjs';

function fixture(){return {format:'composition-private-review-v1',manifest:{version:'private-test',cases:[{id:'a',family:'cloud',audio:'a.wav',roll:'a.json',gp:'a.gp',seconds:1}]},media:{a:{gpBase64:'UEs=',notes:[{start:0,end:.5,pitch:60,velocity:90,part:0}]}}};}

test('private review rejects invalid paths and notes without altering input',()=>{
  const b=fixture();assert.equal(validateBundle(b),b);
  const bad=structuredClone(b);bad.manifest.cases[0].gp='../source.gp';assert.throws(()=>validateBundle(bad));
  const wrong=structuredClone(b);wrong.media.a.notes[0].end=20;assert.throws(()=>validateBundle(wrong));
  assert.equal(b.media.a.notes[0].end,.5);
});

test('local synthesis produces bounded audible PCM at exact declared duration',()=>{
  const bytes=synthesizeWav(fixture().media.a.notes,1,8000),view=new DataView(bytes);
  assert.equal(bytes.byteLength,44+16000);assert.equal(view.getUint32(24,true),8000);
  let nonzero=0,max=0;for(let i=44;i<bytes.byteLength;i+=2){const x=Math.abs(view.getInt16(i,true));max=Math.max(max,x);nonzero+=x>0;}
  assert.ok(nonzero>1000);assert.ok(max>0&&max<32767);
});

test('consolidated questions survive validation, JSON restore and CSV export',()=>{
  const bundle=fixture();bundle.manifest.ratingMetrics=[['coherence','Overall coherence'],['holds','Meaningful pauses/holds'],['resolution','Meaningful ending']];
  validateBundle(bundle);
  const review=recordReview({}, {coherence:'uncertain',holds:'4',resolution:'2'});
  const incoming={format:'composition-ablation-feedback-v1',version:bundle.manifest.version,reviews:{a:review}};
  const restored=mergeFeedback({},incoming,bundle.manifest);assert.equal(restored.a.holds,'4');
  const csv=csvFeedback(bundle.manifest,restored,{});assert.ok(csv.includes('"holds","resolution"'));assert.ok(csv.includes('"uncertain","4","2"'));
  assert.throws(()=>recordReview(review,{resolution:'invented'}));
  bundle.manifest.ratingMetrics.push(['holds','Duplicate']);assert.throws(()=>validateBundle(bundle));
});
