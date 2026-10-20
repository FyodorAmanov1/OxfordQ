"""Generate an upload directory/ZIP from canonical source. Never edit output."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--out',type=Path,default=ROOT/'build/qollab')
parser.add_argument('--with-composition',action='store_true',help='Include the frozen optional PRE-GENERATED showcase; default release is unchanged')
args=parser.parse_args()
out=args.out.resolve()
if out.exists():
    raise SystemExit('Output already exists; choose a fresh --out (no destructive cleanup)')
out.mkdir(parents=True)
for source in sorted((ROOT/'web').glob('*')):
    if source.name.startswith('composition-'): continue
    if source.is_file(): shutil.copyfile(source,out/source.name)
for source in sorted((ROOT/'src/quantum_duet').glob('*.py')):
    # Optional CPython creative modules require orchestrator/music21/pydantic.
    if source.name in ('cli.py','__main__.py','orchestration_adapter.py','browser_projection.py','composition_showcase.py','fresh_qcbm.py','five_part_composition.py','fresh_music_bridge.py'): continue
    dest=out/'quantum_duet'/source.name;dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(source,dest)
for source in sorted((ROOT/'src/quantum_duet/data').glob('*.json')):
    dest=out/'data'/source.name;dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(source,dest)
# Preserve the authoritative shared envelope and historical source bytes exactly.
for source, name in ((ROOT.parents[1]/'docs/fixtures/run-result.v1.json','run-result.v1.json'),
                     (ROOT/'tests/fixtures/qollab-local-run.json','qollab-local-run.json')):
    shutil.copyfile(source,out/'data'/name)
for name in ('requirements.txt','LICENSE','SOURCE_NOTICES.md','DEPLOYMENT_NOTES.md'):
    shutil.copyfile(ROOT/name,out/name)
if args.with_composition:
    freeze=json.loads((ROOT/'composition/freeze.json').read_bytes())
    for name, meta in freeze['files'].items():
        source=ROOT/'composition'/name
        if source.name!=name or hashlib.sha256(source.read_bytes()).hexdigest()!=meta['sha256']:
            raise SystemExit('Frozen composition asset mismatch: '+name)
        dest=out/'data/composition'/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,dest)
    shutil.copyfile(ROOT/'composition/freeze.json',out/'data/composition/freeze.json')
    shutil.copyfile(ROOT/'src/quantum_duet/composition_showcase.py',out/'quantum_duet/composition_showcase.py')
    shutil.copyfile(ROOT/'web/composition-mode.mjs',out/'composition-mode.mjs')
    shutil.copyfile(ROOT/'web/composition-main.js',out/'main.js')
    # Preserve the original Experiment body byte-for-byte inside the optional app.
    (out/'index.html').write_bytes((ROOT/'web/composition-mode.html').read_bytes()+(ROOT/'web/index.html').read_bytes())
files={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(out.rglob('*')) if p.is_file()}
(out/'manifest.json').write_text(json.dumps({'generated_from':'canonical components/quantum_duet sources',
 'files':files,'manifest_self_hash':'excluded to avoid circular digest'},indent=2),encoding='utf-8')
# Qollab runtime docs checked 2026-10-10: 100 files, 2 MB per file.
# https://qollab.xyz/learn/docs/runtime-environment#limits
all_files=[p for p in out.rglob('*') if p.is_file()]
if len(all_files)>100 or any(p.stat().st_size>2_000_000 for p in all_files):
    raise SystemExit('Upload exceeds Qollab limits (100 files / 2 MB each)')
print('Upload budget:',len(all_files),'files,',sum(p.stat().st_size for p in all_files),'bytes')
archive=out.with_suffix('.zip')
if archive.exists(): raise SystemExit('Archive already exists; choose a fresh --out')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(out.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(out).as_posix())
print('Generated',archive,'sha256',hashlib.sha256(archive.read_bytes()).hexdigest())
