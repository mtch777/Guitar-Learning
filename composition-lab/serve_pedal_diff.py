"""Loopback-only source comparison with validated, cached on-demand previews."""
import argparse,json,subprocess,threading
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from serve_private_review import Handler


class DiffHandler(Handler):
    render_lock=threading.Lock()

    def do_POST(self):
        if self.path!='/render':return self.send_error(404)
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.send_error(403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=256:raise ValueError('Invalid render request')
            ident=json.loads(self.rfile.read(size))['id'];jobs=self.server.jobs.get(ident)
            if not jobs:raise ValueError('No renderable preview for this part')
            with self.render_lock:
                pending=[j for j in jobs if not Path(j['out']).exists()]
                if pending:
                    path=self.server.root/'audio'/f'{ident}.jobs.json'
                    path.write_text(json.dumps(pending),encoding='utf-8')
                    result=subprocess.run([self.server.node,str(self.server.renderer),str(self.server.module),str(self.server.font),str(path)],
                        capture_output=True,text=True,timeout=180)
                    if result.returncode:raise ValueError('Source preview could not be rendered. The source notes and GP remain available.')
            payload=json.dumps(dict(ready=True)).encode();self.send_response(200)
        except (ValueError,KeyError,TypeError,subprocess.TimeoutExpired):
            payload=json.dumps(dict(error='Audio preparation failed for this part. The notes and source GP remain available.')).encode();self.send_response(422)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--port',type=int,default=5191)
    p.add_argument('--node',default='node');p.add_argument('--module',type=Path,required=True);p.add_argument('--font',type=Path,required=True);a=p.parse_args()
    root=a.directory.resolve()
    if 'local-artifacts' not in root.parts:p.error('Serve only private local artifacts')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),partial(DiffHandler,directory=str(root)))
    server.root=root;server.node=a.node;server.module=a.module.resolve();server.font=a.font.resolve()
    server.renderer=Path(__file__).with_name('render_source_passages.mjs').resolve();server.jobs=json.loads((root/'render-index.json').read_text())
    server.serve_forever()
