"""Generate an upload directory/ZIP from canonical source. Never edit output."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=ROOT/'build/qollab')
args=parser.parse_args()
out=args.out.resolve()
if out.exists():
    raise SystemExit('Output already exists; choose a fresh --out (no destructive cleanup)')
out.mkdir(parents=True)
for source in sorted((ROOT/'web').glob('*')):
    if source.is_file(): shutil.copyfile(source,out/source.name)
for source in sorted((ROOT/'src/quantum_duet').glob('*.py')):
    if source.name in ('cli.py','__main__.py'): continue
    dest=out/'quantum_duet'/source.name;dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(source,dest)
for source in sorted((ROOT/'src/quantum_duet/data').glob('*.json')):
    dest=out/'data'/source.name;dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(source,dest)
for name in ('requirements.txt','LICENSE','SOURCE_NOTICES.md','DEPLOYMENT_NOTES.md'):
    shutil.copyfile(ROOT/name,out/name)
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(out.rglob('*')) if p.is_file()}
(out/'manifest.json').write_text(json.dumps({'generated_from':'canonical components/quantum_duet sources',
 'files':files,'manifest_self_hash':'excluded to avoid circular digest'},indent=2),encoding='utf-8')
archive=out.with_suffix('.zip')
if archive.exists(): raise SystemExit('Archive already exists; choose a fresh --out')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(out).as_posix())
print('Generated',archive,'sha256',hashlib.sha256(archive.read_bytes()).hexdigest())
