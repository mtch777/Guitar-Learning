"""Loopback, exact-manifest-only private inspector hosting with audio ranges."""
import argparse,json
from functools import partial
from pathlib import Path
from urllib.parse import unquote,urlsplit
from http.server import ThreadingHTTPServer
from serve_private_review import Handler

def make_handler(root):
    root=Path(root).resolve();allowed=set(json.loads((root/'served-files.json').read_text(encoding='utf-8')))
    class InspectorHandler(Handler):
        def send_head(self):
            name=unquote(urlsplit(self.path).path).lstrip('/') or 'index.html';target=root/name
            if name not in allowed or target.resolve()!=target or not target.resolve().is_relative_to(root):
                self.send_error(404);return None
            return super().send_head()
    return partial(InspectorHandler,directory=str(root))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--port',type=int,default=5201);a=p.parse_args()
    if 'local-artifacts' not in a.root.resolve().parts:p.error('Private bundle required')
    ThreadingHTTPServer(('127.0.0.1',a.port),make_handler(a.root)).serve_forever()
