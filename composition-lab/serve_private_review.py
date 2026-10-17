"""Loopback-only review server with byte ranges for reliable audio seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re


def byte_range(value,size):
    m=re.fullmatch(r'bytes=(\d*)-(\d*)',value or '')
    if not m or not any(m.groups()) or not size:raise ValueError('Invalid byte range')
    a,b=m.groups()
    if not a:start=max(0,size-int(b));end=size-1
    else:start=int(a);end=min(size-1,int(b)) if b else size-1
    if start<0 or start>=size or end<start:raise ValueError('Unsatisfiable byte range')
    return start,end


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self._remaining=None
        path=Path(self.translate_path(self.path))
        if not path.is_file() or not self.headers.get('Range'):return super().send_head()
        size=path.stat().st_size
        try:start,end=byte_range(self.headers['Range'],size)
        except ValueError:
            self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
        stream=path.open('rb');stream.seek(start);self._remaining=end-start+1
        self.send_response(206);self.send_header('Content-Type',self.guess_type(str(path)));self.send_header('Content-Range',f'bytes {start}-{end}/{size}');self.send_header('Content-Length',str(self._remaining));self.send_header('Accept-Ranges','bytes');self.end_headers();return stream

    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        super().end_headers()

    def copyfile(self,source,outputfile):
        if self._remaining is None:return super().copyfile(source,outputfile)
        while self._remaining:
            chunk=source.read(min(65536,self._remaining))
            if not chunk:break
            outputfile.write(chunk);self._remaining-=len(chunk)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--port',type=int,default=5180);a=p.parse_args()
    if not a.directory.is_dir():p.error('Directory does not exist')
    ThreadingHTTPServer(('127.0.0.1',a.port),partial(Handler,directory=str(a.directory.resolve()))).serve_forever()
