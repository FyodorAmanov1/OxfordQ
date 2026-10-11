"""Install pinned sfizz and CC0 VSCO samples locally, never into Git."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import urllib.request
import zipfile

ASSETS = {
    "sfizz": ("1.2.3", "https://github.com/sfztools/sfizz/releases/download/1.2.3/sfizz-1.2.3-win64.zip"),
    "vsco": ("1.1.0", "https://codeload.github.com/sgossner/VSCO-2-CE/zip/refs/tags/1.1.0"),
}
CHECKSUMS = {
    "sfizz": "7431cbe9b7f2e71a9ff4b12fbbe82c766dbf75b1eedecca627e7506cb06a9fcc",
    "vsco": "4a4446628df0e1a12aaee58e9f65f8fa7cde51971e961abb1b43083a6d3a8ab7",
}


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def install(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_path = root / "receipt.json"
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    receipt = {}
    for name, (version, url) in ASSETS.items():
        archive = root / (name + "-" + version + ".zip")
        if not archive.exists():
            partial = archive.with_suffix(".partial")
            request = urllib.request.Request(url, headers={"User-Agent": "OxfordQ-acoustic-setup"})
            print("Downloading", name, version, flush=True)
            count, announced = 0, 0
            with urllib.request.urlopen(request, timeout=90) as source, partial.open("wb") as target:
                while block := source.read(4 * 1024 * 1024):
                    target.write(block)
                    count += len(block)
                    if count - announced >= 64 * 1024 * 1024:
                        print(name, count // (1024 * 1024), "MiB", flush=True)
                        announced = count
            partial.replace(archive)
        sha = digest(archive)
        if sha != CHECKSUMS[name]:
            raise ValueError("Pinned asset checksum mismatch: " + name)
        if name in previous and previous[name]["sha256"] != sha:
            raise ValueError("Cached asset checksum changed: " + name)
        destination = root / name
        if not (destination / ".complete").exists():
            destination.mkdir(exist_ok=True)
            with zipfile.ZipFile(archive) as bundle:
                if sum(i.file_size for i in bundle.infolist()) > 6 * 1024 ** 3:
                    raise ValueError("Archive exceeds 6 GiB extraction limit")
                for item in bundle.infolist():
                    target = (destination / item.filename).resolve()
                    if not target.is_relative_to(destination) or stat.S_ISLNK(item.external_attr >> 16):
                        raise ValueError("Unsafe archive member")
                bundle.extractall(destination)
            (destination / ".complete").write_text(sha, encoding="ascii")
        if (destination / ".complete").read_text() != sha:
            raise ValueError("Extracted asset receipt differs: " + name)
        receipt[name] = {"version": version, "url": url, "sha256": sha}
    dlls = sorted((root / "sfizz").glob("**/sfizz.dll"))
    fonts = sorted((root / "vsco").glob("**/Flute-KS.sfz"))
    if not dlls or not fonts:
        raise ValueError("Missing sfizz DLL or VSCO SFZ patches")
    receipt.update(library=str(dlls[0]), samples=str(fonts[0].parent),
                   sample_license="CC0-1.0", engine_license="BSD-2-Clause")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("Installed:", receipt_path, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "acoustic")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This installer supplies Windows x64 sfizz; on other platforms provide --sfizz-library separately")
    install(args.assets_dir)


if __name__ == "__main__":
    main()
