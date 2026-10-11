"""Preview a locally generated score with the same Qollab UI and Web Audio.

Serves GET only on localhost. The browser replays a newly generated local score;
it does not submit quantum jobs. Run run.py first.
"""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/','/index.html'):
            html='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="main.css"><title>Quantum Graph Composer</title></head><body>'
            html+=(ROOT/'index.html').read_text(encoding='utf-8')
            html+='<script type="module" src="main.js"></script></body></html>'
            self.send_bytes(html.encode(),'text/html; charset=utf-8');return
        if self.path=='/main.js':
            javascript="""import {mountComposer} from './ui.mjs';
const score=await (await fetch('output/browser-score.json')).text();
const bank=await (await fetch('data/piano.json')).text();
void mountComposer(async()=>score,async()=>bank);
document.getElementById('status').textContent='LOCAL PREVIEW: renders the score from run.py; this browser does not submit quantum jobs.';
document.getElementById('generate').textContent='Render local composition';
const metadata=JSON.parse(score).metadata;
for(const id of ['seed','bars','bpm','shots','interaction'])document.getElementById(id).disabled=true;
document.getElementById('seed').value=metadata.seed;
document.getElementById('bars').value=metadata.bars;
document.getElementById('bpm').value=metadata.bpm;
document.getElementById('interaction').value=metadata.interaction;
document.querySelector('.footnote').textContent='Local playback preview of the run.py output. Generate another score with run.py and reload. Qollab uses its supplied backend and one fresh job instead.';
"""
            self.send_bytes(javascript.encode(),'text/javascript');return
        return super().do_GET()

    def send_bytes(self,data,content_type):
        self.send_response(200);self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8772);args=parser.parse_args()
    handler=functools.partial(Handler,directory=str(ROOT))
    print(f'Local preview: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),handler).serve_forever()
