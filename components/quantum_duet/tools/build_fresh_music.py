"""Build a separate private fresh-music candidate; never alters canonical release."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out.resolve();archive=out.with_suffix('.zip')
if out.exists() or archive.exists():raise SystemExit('Choose a fresh output; nothing is overwritten')
out.mkdir(parents=True)
for f in (ROOT/'fresh_web').iterdir():shutil.copyfile(f,out/f.name)
modules=('__init__.py','circuit.py','duet_quantum.py','duet_referee.py','duet_classical.py','integration.py','music.py','probe.py','joint_cue.py','fresh_qcbm.py','five_part_composition.py','fresh_music_bridge.py')
(out/'quantum_duet').mkdir()
for name in modules:shutil.copyfile(ROOT/'src/quantum_duet'/name,out/'quantum_duet'/name)
(out/'data').mkdir()
for name in ('melody_angles.json','selected_angles.json','recorded_melody.json'):
 shutil.copyfile(ROOT/'src/quantum_duet/data'/name,out/'data'/name)
for name in ('LICENSE','SOURCE_NOTICES.md','requirements.txt'):shutil.copyfile(ROOT/name,out/name)
hashes={f.relative_to(out).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.rglob('*')) if f.is_file()}
(out/'manifest.json').write_text(json.dumps({'generated_from':'separate canonical fresh-music sources','files':hashes},indent=2),encoding='utf8')
files=[f for f in out.rglob('*') if f.is_file()]
if len(files)>100 or any(f.stat().st_size>2_000_000 for f in files):raise SystemExit('Qollab upload limits exceeded')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,f.relative_to(out).as_posix())
print(json.dumps({'files':len(files),'bytes':sum(f.stat().st_size for f in files),'largest':max(f.stat().st_size for f in files),'zip':str(archive),'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
