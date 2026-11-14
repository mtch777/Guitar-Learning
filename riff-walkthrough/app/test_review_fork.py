import copy,hashlib,pathlib,tempfile,unittest,os,subprocess,sys
from review_fork import ReviewApp
from save_service import Publisher
from runtime_options import SESSION_COOKIE
class ReviewCopyTests(unittest.TestCase):
 def test_standalone_default_cookie_is_isolated_before_imports(self):
  env=os.environ.copy();env.pop('RIFF_SESSION_COOKIE',None)
  code="import runpy,sys,os;sys.argv=['review_fork.py','--help'];\ntry:runpy.run_path('review_fork.py',run_name='__main__')\nexcept SystemExit:pass\nprint('COOKIE='+os.environ['RIFF_SESSION_COOKIE'])"
  r=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('COOKIE=riff_review_fix_session',r.stdout)
 def test_standalone_rejects_original_cookie_names(self):
  for name in ('riff_session','riff_weights_session'):
   r=subprocess.run([sys.executable,'-B','review_fork.py','--help'],env={**os.environ,'RIFF_SESSION_COOKIE':name},capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('distinct session cookie',r.stderr)
 def test_isolated_sessions_preserve_import_revision(self):
  with tempfile.TemporaryDirectory() as tmp:
   output={'can_export':True,'audio':{'notes':[],'length_beats':4,'tempo':120},'phrases':[]}
   workspace={'source_version':3,'revision':7,'output':output,'state':{'dataset':{'csv':'test'},'stages':[{'id':str(i),'status':'complete','output':copy.deepcopy(output)} for i in range(1,7)]}}
   original=copy.deepcopy(workspace);pub=Publisher(pathlib.Path(tmp)/'repo',9999);app=ReviewApp(workspace,pub)
   a,new=app.session('');self.assertTrue(new);b,new=app.session('');self.assertNotEqual(a.id,b.id)
   self.assertEqual(a.stages[5]['output'],output);self.assertEqual(app.engine.config()['stages'][0]['id'],'6');self.assertEqual(len(app.engine.config()['stages']),1)
   key=hashlib.sha256((a.id+':3').encode()).hexdigest()
   from editor_service import EditorManager
   import json
   saved=json.loads(EditorManager(pub).path(key).read_text());self.assertEqual(saved['revision'],7)
   same,new=app.session(SESSION_COOKIE+'='+a.id);self.assertFalse(new);self.assertIs(same,a)
   a.stages[5]['output']['can_export']=False;self.assertTrue(b.stages[5]['output']['can_export']);self.assertEqual(workspace,original)
if __name__=='__main__':unittest.main()
