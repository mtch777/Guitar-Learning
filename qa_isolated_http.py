# Isolated QA only: ephemeral HTTP ports, in-memory copied source session,
# temporary editor/render files. Never contacts production ports8878/8879.
import os,sys,pathlib,json,copy,tempfile,threading,urllib.request,urllib.error,time
os.environ.update(RIFF_CSV='F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/data/all_riffs_phrase_composition.csv',RIFF_TIMING='F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/data/pitch_free_all_lengths_phrase_rhythms.json',RIFF_SESSION_COOKIE='isolated_qa_session',RIFF_KONTAKT_PRESET_DIR='F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/renderer',RIFF_RENDER_PYTHON='C:/Users/User/kontakt-render-test/venv312/Scripts/python.exe',RIFF_RENDER_WORKER='F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/renderer/kontakt_isolated_worker.py',RIFF_KONTAKT_PRESETS='modern-metal-1,ready-to-djent')
sys.path.insert(0,'F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/app')
sys.dont_write_bytecode=True
qa_temp=pathlib.Path('F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/temp').resolve()
assert qa_temp.drive.upper()=='F:'
qa_temp.mkdir(parents=True,exist_ok=True)
for key in ('TEMP','TMP','TMPDIR','RIFF_TEMP_DIR'):os.environ[key]=str(qa_temp)
tempfile.tempdir=str(qa_temp)
import engine,server,save_service
w=json.loads(pathlib.Path('F:/dot-workspaces/Guitar-Learning-rhythm/riff-generator-runtime/riff-editor-state/ba24e90ac60db518c58679dfa09c5af95213c91c3c7415556fc7ef777f357d8e.json').read_text())
app=server.App();app.engine=engine.Engine();app.loading=False
source=server.http.server.ThreadingHTTPServer(('127.0.0.1',0),server.handler_for(app));threading.Thread(target=source.serve_forever,daemon=True).start();origin='http://127.0.0.1:'+str(source.server_address[1])
with tempfile.TemporaryDirectory(prefix='riff-isolated-http-') as tmp:
 pub=save_service.Publisher(pathlib.Path(tmp)/'midi',source.server_address[1]);comp=server.http.server.ThreadingHTTPServer(('127.0.0.1',0),save_service.handler_for(pub,[origin]));threading.Thread(target=comp.serve_forever,daemon=True).start()
 def req(path,data):
  r=urllib.request.Request('http://127.0.0.1:'+str(comp.server_address[1])+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':origin,'Cookie':'isolated_qa_session='+session.id})
  try:return json.load(urllib.request.urlopen(r,timeout=240))
  except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode())
 for mode in ['rhythm','pitches','both']:
  session=server.Session();session.version=w['source_version'];session.stages=copy.deepcopy(w['state']['stages']);session.stages[-1]['output']=copy.deepcopy(w['output']);app.sessions[session.id]=session
  o=req('/editor/open',{'version':session.version});old=o['output']['audio']['notes'];r=req('/editor/regenerate',{'version':session.version,'revision':o['revision'],'selected':[2],'mode':mode})
  assert r['revision']==1;assert r['output']['audio']['notes']!=old;assert session.stages[-1]['output']==w['output'];print('ISOLATED HTTP PASS',mode,'actual note data changed; original copy unchanged',flush=True)
 r=req('/render/start',{'stage':6,'version':session.version,'editor_revision':r['revision'],'view':'current','selected':None,'preset':'modern-metal-1'})
 for i in range(180):
  r=req('/render/status',{'job_id':r['job_id']})
  if r['status'] in ('ready','failed'):break
  time.sleep(1)
 print('REAL RENDER',r['status'],r.get('error'),r.get('duration_seconds'),flush=True);assert r['status']=='ready' and any(a or b for a,b in r['waveform'])
 comp.shutdown();comp.server_close()
source.shutdown();source.server_close()
