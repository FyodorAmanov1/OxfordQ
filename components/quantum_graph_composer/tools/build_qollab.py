"""Build a self-contained Qollab upload from canonical sources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=('index.html','main.js','main.css','ui.mjs','audio.mjs','bridge.py',
       'quantum_engine.py','graph.py','composer.py','score_writer.py',
       'requirements.txt','LICENSE','SOURCE_NOTICES.md','data/piano.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/qollab')
    args=parser.parse_args();out=args.out.resolve();archive=out.with_suffix('.zip')
    if out.exists() or archive.exists():
        raise SystemExit('Choose a fresh --out; existing builds are preserved')
    out.mkdir(parents=True)
    for name in FILES:
        destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,destination)
    shutil.copyfile(ROOT/'PROJECT_PAGE.md',out/'README.md')
    manifest={'component':'Quantum Graph Composer','files':{
        name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in (*FILES,'README.md')}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    files=[p for p in out.rglob('*') if p.is_file()]
    if len(files)>100 or any(p.stat().st_size>2_000_000 for p in files):
        raise SystemExit('Qollab upload limit exceeded: 100 files, 2 MB per file')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(files):z.write(path,path.relative_to(out).as_posix())
    print('Qollab upload:',out)
    print('ZIP:',archive)
    print('Files:',len(files),'Bytes:',sum(p.stat().st_size for p in files))
    print('ZIP SHA-256:',hashlib.sha256(archive.read_bytes()).hexdigest())


if __name__=='__main__':main()
