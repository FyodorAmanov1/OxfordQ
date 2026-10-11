"""Build the experimental studio locally; preserve existing archives."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO / "build/pop909-studio.zip")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if out.exists():
        parser.error("Choose a fresh --out; existing archives are preserved")
    names = ["index.html", "main.js", "main.css", "requirements.txt",
             "quantum_harmony/__init__.py", "quantum_harmony/inference.py",
             "data/models.json", "README.md"]
    data = {name: (ROOT / name).read_bytes() for name in names}
    data["LICENSE"] = (REPO / "LICENSE").read_bytes()
    data["SOURCE_NOTICES.md"] = (REPO / "quantum_models/SOURCE_NOTICES.md").read_bytes()
    manifest = {"scope": "Local build only; platform execution unverified",
                "files": {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}}
    data["manifest.json"] = json.dumps(manifest, indent=2).encode("utf-8")
    if len(data) > 100 or any(len(content) > 2_000_000 for content in data.values()):
        parser.error("Upload budget exceeded")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(data.items()):
            archive.writestr(name, content)
    print(json.dumps({"archive": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                      "files": len(data), "scope": manifest["scope"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
