"""Explicit local adapter; loopback only, never shipped to Qollab."""
import argparse, json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from quantum_duet.integration import generate_take
from quantum_duet.cli import __file__ as package_file
from qiskit.providers.basic_provider import BasicSimulator
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT.parents[1]/'docs/team/fixtures/run-result.v1.json'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if self.path=='/api/fixture':
            # Fixed local asset only, never an unsupported Qollab/private fetch.
            text=FIXTURE.read_bytes()
            self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(text);return
        if self.path=='/':
            html='<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/web/main.css"></head><body>'+(ROOT/'web/index.html').read_text(encoding='utf-8')+'<script type="module" src="/dev/main.mjs"></script></body></html>'
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(html.encode());return
        super().do_GET()
    def do_POST(self):
        try:
            if self.path!='/api/run': raise ValueError('Unknown endpoint')
            request=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))))
            backend=BasicSimulator();backend.set_options(seed_simulator=32001,use_clifford_optimization=False)
            text=generate_take(backend,request['shots'],request['mode'],'ideal-local-development',32002,
                               asset_dir=Path(package_file).parent/'data');status=200
        except Exception as exc:
            text=json.dumps({'error':str(exc)});status=500
        self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(text.encode())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    print(f'LOCAL development, not Qollab: http://127.0.0.1:{a.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
