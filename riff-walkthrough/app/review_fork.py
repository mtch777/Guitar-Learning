"""Isolated Review copy. Never writes or calls the original generator session."""
import argparse,copy,hashlib,http.server,json,os,pathlib,threading
# Cookie names are host-wide, not port-wide. Isolate before importing runtime_options.
if __name__=='__main__':
 os.environ.setdefault('RIFF_SESSION_COOKIE','riff_review_fix_session')
 if os.environ['RIFF_SESSION_COOKIE'] in ('riff_session','riff_weights_session'):
  raise ValueError('Review copy requires a distinct session cookie name')
import server as S
from editor_service import EditorManager
from save_service import Publisher,handler_for as companion_handler

class ReviewApp(S.App):
 def __init__(self,workspace,publisher):
  super().__init__();self.workspace=copy.deepcopy(workspace);self.publisher=publisher
  if not workspace.get('output',{}).get('can_export'):raise ValueError('A complete saved Review is required')
  class Config:
   def config(inner):return {'stages':[{'id':'6','title':'Review copy','parameters':[],'defaults':{}}], 'defaults':{'6':{}},'phrase_preference_controls':__import__('engine').preference_controls(),'counts':{},'engine':'review-copy','dataset':workspace['state']['dataset']}
  self.engine=Config();self.loading=False
 def session(self,cookie):
  session,new=super().session(cookie)
  if new:
   session.version=self.workspace['source_version'];session.stages=copy.deepcopy(self.workspace['state']['stages'])
   session.stages[5]['output']=copy.deepcopy(self.workspace['output'])
   key=hashlib.sha256((session.id+':'+str(session.version)).encode()).hexdigest()
   EditorManager(self.publisher).write(key,copy.deepcopy(self.workspace))
  return session,new

def handler_for(app):
 base=S.handler_for(app)
 class Handler(base):
  def do_POST(self):self.reply(409,{'error':'This is a separate Review copy. Earlier generation steps are unavailable here.'})
  def do_GET(self):
   if self.path.split('?')[0] in ('/','/index.html'):
    body=(S.STATIC/'index.html').read_text(encoding='utf-8').replace('<h1>Riff generator</h1>','<h1>Review copy</h1>').replace('<main>','<main><p class="notice">Separate copy. Edits here do not change your original generator. Earlier generation steps are unavailable.</p>')
    session,new=app.session(self.headers.get('Cookie'))
    self.reply(200,body.encode(),'text/html',cookie=session.id if new else None);return
   super().do_GET()
 return Handler

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--repo',required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8888);p.add_argument('--origin',action='append',required=True);a=p.parse_args()
 workspace=json.loads(pathlib.Path(a.snapshot).read_text(encoding='utf-8'));publisher=Publisher(a.repo,a.port);app=ReviewApp(workspace,publisher)
 companion=http.server.ThreadingHTTPServer((a.host,a.port+1),companion_handler(publisher,a.origin));threading.Thread(target=companion.serve_forever,daemon=True).start()
 server=http.server.ThreadingHTTPServer((a.host,a.port),handler_for(app));print('Separate Review copy ready',flush=True);server.serve_forever()
