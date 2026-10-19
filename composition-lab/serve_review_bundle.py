"""Loopback-only review bundle server with byte ranges for seekable audio.

Only index.html and immediate assets/*.wav or *.gp are exposed. No listing,
other artifact folders, source/model JSON, symlinks or traversal are served.
"""
import argparse,re
from pathlib import Path
from urllib.parse import unquote,urlsplit
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer


def handler(root):
    root=Path(root).resolve()
    class ReviewHandler(SimpleHTTPRequestHandler):
        def send_head(self):
            self.remaining=0
            route=unquote(urlsplit(self.path).path)
            if route=='/':route='/index.html'
            candidate=root/route.lstrip('/')
            allowed=route=='/index.html' or (len(Path(route).parts)==3 and Path(route).parts[1]=='assets' and Path(route).suffix in ('.wav','.gp'))
            resolved=candidate.resolve()
            if not allowed or not resolved.is_relative_to(root) or resolved!=candidate or not resolved.is_file():
                self.send_error(404);return None
            stream=resolved.open('rb');size=resolved.stat().st_size;start,end=0,size-1;partial=False
            value=self.headers.get('Range')
            if value:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',value)
                if not match or not any(match.groups()):stream.close();self.send_error(416);return None
                first,last=match.groups()
                if first:start=int(first);end=min(int(last),size-1) if last else size-1
                else:start=max(0,size-int(last))
                if start>end or start>=size:stream.close();self.send_error(416);return None
                partial=True
            self.send_response(206 if partial else 200)
            self.send_header('Content-Type',self.guess_type(str(resolved)))
            self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
            self.send_header('Cache-Control','no-store')
            if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers();stream.seek(start);self.remaining=end-start+1;return stream

        def copyfile(self,source,outputfile):
            try:
                while self.remaining:
                    block=source.read(min(65536,self.remaining))
                    if not block:break
                    outputfile.write(block);self.remaining-=len(block)
            except (BrokenPipeError,ConnectionResetError):pass
    return ReviewHandler


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--port',type=int,default=5200);a=p.parse_args()
    root=a.root.resolve()
    if 'local-artifacts' not in root.parts or not (root/'index.html').is_file():p.error('Explicit private review bundle required')
    ThreadingHTTPServer(('127.0.0.1',a.port),handler(root)).serve_forever()
