"""Loopback preview of the generated optional package; no backend calls."""
import argparse
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
from quantum_duet.composition_showcase import load_showcase
from quantum_duet.recorded_fixture import load_fixture
from experiments.qcbm_refinement.preview import Handler as RangeHandler

HERE = Path(__file__).resolve().parent


class Handler(RangeHandler):
    def do_GET(self):
        if self.path in ('/api/composition', '/api/fixture'):
            try:
                text = load_showcase() if self.path == '/api/composition' else load_fixture()
                status = 200
            except Exception as exc:
                text = json.dumps(dict(error=str(exc)))
                status = 500
            body = text.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
            return
        if self.path == '/':
            body = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/main.css"></head><body>'+Path('index.html').read_text(encoding='utf-8')+'<script type="module" src="/preview-main.mjs"></script></body></html>').encode('utf-8')
        elif self.path == '/preview-main.mjs':
            body = (HERE/'composition-main.mjs').read_bytes()
        else:
            return super().do_GET()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8' if self.path == '/' else 'text/javascript')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--port', type=int, default=8782)
    a=p.parse_args(); os.chdir(a.directory.resolve())
    print(f'PRIVATE LOCAL PACKAGE PREVIEW: http://127.0.0.1:{a.port} · zero backend calls',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
