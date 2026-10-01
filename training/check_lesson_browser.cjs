const {chromium}=require('playwright');const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
 const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
  window.__notes=[];window.__cellClicks=[];
  window.addEventListener('guitar-note-detected',e=>window.__notes.push({...e.detail,time:performance.now()}));
  document.addEventListener('click',e=>{if(e.detail?.guitarAudio)window.__cellClicks.push({string:e.target.dataset.stringIndex,fret:e.target.dataset.fret});},true);
  navigator.mediaDevices.enumerateDevices=async()=>[{kind:'audioinput',deviceId:'test',label:'Test stereo input'}];
  navigator.mediaDevices.getUserMedia=async()=>{
   const ac=new AudioContext({sampleRate:44100}),merge=ac.createChannelMerger(2),dest=ac.createMediaStreamDestination();merge.connect(dest);await ac.resume();
   window.__playWav=async b64=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const buffer=await ac.decodeAudioData(bytes.buffer);const source=ac.createBufferSource();source.buffer=buffer;source.connect(merge,0,1);window.__playTime=performance.now();source.start();};
   return dest.stream;
  };
 });
 await page.goto('http://127.0.0.1:5173/Guitar-Learning/');
 await page.click('#guitarInputButton');await page.waitForFunction(()=>document.querySelector('#guitarInputStatus').textContent.includes('Hybrid + fusion'),null,{timeout:40000});
 const wav=fs.readFileSync('training/data/live_2026-09-30/s1_f00_normal_live.wav').toString('base64');
 await page.evaluate(b=>window.__playWav(b),wav);
 await page.waitForTimeout(1800);if(await page.evaluate(()=>window.__notes.length))throw Error('Premature note action');
 await page.waitForFunction(()=>window.__notes.length===1,null,{timeout:10000});
 await page.waitForTimeout(3500);
 const result=await page.evaluate(()=>({notes:window.__notes,clicks:window.__cellClicks,playTime:window.__playTime}));
 if(result.notes.length!==1||result.notes[0].midi!==27||result.notes[0].string!==1||result.notes[0].fret!==0||result.notes[0].contextAdjusted)throw Error(JSON.stringify(result));
 if(result.clicks.length!==1||result.clicks[0].string!=='0'||result.clicks[0].fret!=='0')throw Error('Detection did not activate matching fretboard cell: '+JSON.stringify(result));
 await page.click('#guitarInputButton');if(!(await page.locator('#guitarInputStatus').textContent()).includes('Stopped'))throw Error('Stop failed');
 await page.screenshot({path:'/tmp/lesson_pipeline_screen.png',fullPage:true});
 if(errors.length)throw Error(errors.join('\n'));
 console.log('Real live WAV -> stereo AudioWorklet -> hybrid fusion Worker -> one completed detection -> actual lesson fret click; no early action.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
