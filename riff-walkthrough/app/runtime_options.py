"""Deployment-local session isolation; defaults preserve existing install."""
import os,re
SESSION_COOKIE=os.environ.get('RIFF_SESSION_COOKIE','riff_session')
if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',SESSION_COOKIE):raise ValueError('Invalid configured session cookie name')
