from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'data'/'models.json'
OUT=ROOT.parent/'quantum-harmony-studio-qollab.zip'
if not MODEL.is_file(): raise SystemExit('Missing data/models.json. Run tools/export_models.py first.')
include=[ROOT/'index.html',ROOT/'main.js',ROOT/'main.css',ROOT/'requirements.txt',ROOT/'quantum_harmony'/'__init__.py',ROOT/'quantum_harmony'/'inference.py',MODEL]
if OUT.exists(): OUT.unlink()
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
    for path in include: z.write(path,path.relative_to(ROOT).as_posix())
print('Built',OUT)
