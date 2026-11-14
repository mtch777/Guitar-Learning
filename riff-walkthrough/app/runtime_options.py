"""Deployment-local session isolation; defaults preserve existing install."""
import os,re
SESSION_COOKIE=os.environ.get('RIFF_SESSION_COOKIE','riff_session')
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',SESSION_COOKIE):raise ValueError('Invalid configured session cookie name')


def output_path(value):
 """Reject Windows project writes outside F, including resolved junction targets."""
 import pathlib
 path=pathlib.Path(value).resolve()
 if os.name=='nt' and path.drive.upper()!='F:':
  raise ValueError('Project output must be on F: '+str(path))
 return path

def temporary_directory(prefix):
 """Explicit project temp root, never the OS default temp directory."""
 import pathlib,tempfile
 base=pathlib.Path(__file__).resolve().parent.parent
 directory=output_path(os.environ.get('RIFF_TEMP_DIR',str(base/'temp')))
 directory.mkdir(parents=True,exist_ok=True)
 return tempfile.TemporaryDirectory(prefix=prefix,dir=directory)
