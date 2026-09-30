const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
 const ctx=await browser.newContext({acceptDownloads:true,viewport:{width:1100,height:1200}});
 await ctx.addInitScript(()=>{
  navigator.mediaDevices.getUserMedia=async()=>{
   const ac=new AudioContext({sampleRate:44100}),osc=ac.createOscillator(),gain=ac.createGain(),merge=ac.createChannelMerger(2),dest=ac.createMediaStreamDestination();
   osc.frequency.value=155.56349186104046;gain.gain.value=0;osc.connect(gain);gain.connect(merge,0,1);merge.connect(dest);osc.start();await ac.resume();window.__trialToneGain=gain;return dest.stream;
  };
  navigator.mediaDevices.enumerateDevices=async()=>[{kind:'audioinput',deviceId:'synthetic',label:'Synthetic stereo test'}];
 });
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/Guitar-Learning/live-pipeline-test.html');
 await page.waitForFunction(()=>!document.querySelector('#microphone').disabled,null,{timeout:30000});
 await page.click('#microphone');await page.waitForFunction(()=>!document.querySelector('#record').disabled);
 await page.click('#calibrate');await page.click('#calibrationMeasure');
 await page.waitForFunction(()=>document.querySelector('#calibrationPrompt').textContent.includes('Recording 2 of 25'),null,{timeout:10000});
 await page.click('#calibrationMeasure');await page.waitForFunction(()=>document.querySelector('#calibrationPrompt').textContent.includes('PLAY NOW'));
 await page.evaluate(()=>window.__trialToneGain.gain.value=.15);
 await page.waitForFunction(()=>document.querySelector('#calibrationPrompt').textContent.includes('Recording 3 of 25'),null,{timeout:10000});
 await page.evaluate(()=>window.__trialToneGain.gain.value=0);
 if(!(await page.locator('#gainFeedback').textContent()).includes('recorded example'))throw Error('Missing reference level feedback');
 const calDownload=page.waitForEvent('download');await page.click('#calibrationExport');await (await calDownload).saveAs('/tmp/gain_calibration.json');
 // Let the calibration tone drain out of the continuously assembled capture block.
 await page.waitForTimeout(1200);
 await page.click('#record');await page.waitForTimeout(1200);await page.evaluate(()=>window.__trialToneGain.gain.value=.15);
 await page.waitForTimeout(1500);await page.evaluate(()=>window.__trialToneGain.gain.value=0);
 await page.waitForFunction(()=>document.querySelector('#history').rows.length===1,null,{timeout:20000});
 await page.selectOption('#kind','silence');await page.click('#record');
 await page.waitForFunction(()=>document.querySelector('#history').rows.length===2,null,{timeout:20000});
 const download=page.waitForEvent('download');await page.click('#export');await (await download).saveAs('/tmp/live_browser_trial.zip');
 await page.screenshot({path:'/tmp/live_pipeline_screen.png',fullPage:true});
 console.log(JSON.stringify({errors,status:await page.locator('#status').textContent(),rows:await page.locator('#history tr').count()}));
 if(errors.length)throw Error(errors.join('\n'));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
