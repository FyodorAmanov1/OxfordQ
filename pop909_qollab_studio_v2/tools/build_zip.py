from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
MODEL = ROOT / "data" / "models.json"
LICENSE = REPO_ROOT / "LICENSE"
OUT = REPO_ROOT / "quantum-harmony-studio-qollab.zip"

if not MODEL.is_file():
    raise SystemExit("Missing data/models.json. Run tools/export_models.py first.")
if not LICENSE.is_file():
    raise SystemExit("Missing repository LICENSE file.")

include = [
    ROOT / "index.html",
    ROOT / "main.js",
    ROOT / "main.css",
    ROOT / "README.md",
    ROOT / "requirements.txt",
    ROOT / "quantum_harmony" / "__init__.py",
    ROOT / "quantum_harmony" / "inference.py",
    MODEL,
]

if OUT.exists():
    OUT.unlink()

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for path in include:
        z.write(path, path.relative_to(ROOT).as_posix())
    z.write(LICENSE, "LICENSE")

print("Built", OUT)
print("Included README.md and LICENSE")
