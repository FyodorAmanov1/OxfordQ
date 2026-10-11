"""Private loopback-only preview, with HTTP byte ranges for native WAV seeking."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re

class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        path=Path(self.translate_path(self.path))
        if not path.is_file():
            self.remaining=None
            return super().send_head()
        size=path.stat().st_size
        start,end=0,size-1
        request=self.headers.get('Range')
        if request:
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',request)
            if not match or int(match[1])>=size:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return None
            start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
            if end<start:
                self.send_error(416);return None
        self.send_response(206 if request else 200)
        self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
        if request:
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers();self.remaining=end-start+1
        stream=path.open('rb');stream.seek(start);return stream

    def copyfile(self,source,output):
        if self.remaining is None:
            return super().copyfile(source,output)
        while self.remaining:
            data=source.read(min(65536,self.remaining))
            if not data:break
            output.write(data);self.remaining-=len(data)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8781)
    args=parser.parse_args()
    if not (args.directory/'listen.html').is_file():parser.error('Directory must contain generated listen.html')
    ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(args.directory.resolve()))).serve_forever()
