"""Download official preview assets into this project; no system install changes.

FluidSynth is pinned to a release. GeneralUser GS resolves to a concrete commit.
Archive hashes are recorded and upstream licenses remain in the asset folders.
"""
import argparse
import hashlib
import json
import os
import shutil
import ssl
import stat
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "QML-Orchestrator/0.1", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=45) as response:
        return json.load(response)


def download(url, path, expected_digest=None):
    if not url.startswith("https://"):
        raise ValueError("Asset downloads must use HTTPS")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        request = urllib.request.Request(url, headers={"User-Agent": "QML-Orchestrator/0.1"})
        partial = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=45) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target)
        partial.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_digest and expected_digest.removeprefix("sha256:") != digest:
        raise ValueError(f"Upstream checksum mismatch for {path.name}")
    return digest


def extract(archive, destination):
    root = destination.resolve()
    if not root.is_relative_to(ROOT.resolve()):
        raise ValueError("Audio assets must stay inside the project")
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        if sum(item.file_size for item in bundle.infolist()) > 512 * 1024 * 1024:
            raise ValueError("Asset archive exceeds the extraction size limit")
        for item in bundle.infolist():
            target = (root / item.filename).resolve()
            if not target.is_relative_to(root) or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Asset archive contains an unsafe path or symbolic link")
        bundle.extractall(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fluid-version", default="v2.6.1")
    parser.add_argument("--soundfont-commit", help="Reuse a specific GeneralUser GS commit")
    parser.add_argument("--skip-fluidsynth", action="store_true", help="Use a separately installed renderer")
    args = parser.parse_args()
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    receipt = {}
    if not args.skip_fluidsynth:
        if os.name != "nt":
            raise SystemExit("On Linux/macOS install FluidSynth separately, then rerun with --skip-fluidsynth.")
        release = fetch_json(f"https://api.github.com/repos/FluidSynth/fluidsynth/releases/tags/{args.fluid_version}")
        candidates = [asset for asset in release["assets"] if asset["name"].endswith(".zip")
                      and "win" in asset["name"].lower()
                      and any(token in asset["name"].lower() for token in ("x64", "amd64", "win64"))]
        if not candidates:
            raise ValueError("The selected FluidSynth release has no Windows x64 ZIP")
        asset = sorted(candidates, key=lambda a: ("win10" not in a["name"].lower(), a["name"]))[0]
        path = assets / "downloads" / asset["name"]
        print(f"Downloading FluidSynth {release['tag_name']}: {asset['name']}", flush=True)
        digest = download(asset["browser_download_url"], path, asset.get("digest"))
        extract(path, assets / "fluidsynth")
        receipt["fluidsynth"] = {"version": release["tag_name"], "url": asset["browser_download_url"], "sha256": digest}
    sha = args.soundfont_commit or fetch_json("https://api.github.com/repos/mrbumpy409/GeneralUser-GS/commits/main")["sha"]
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha.lower()):
        raise ValueError("SoundFont commit must be a full 40-character Git SHA")
    url = f"https://codeload.github.com/mrbumpy409/GeneralUser-GS/zip/{sha}"
    archive = assets / "downloads" / f"GeneralUser-GS-{sha}.zip"
    print(f"Downloading GeneralUser GS at commit {sha}", flush=True)
    digest = download(url, archive)
    extract(archive, assets / "soundfonts")
    receipt["soundfont"] = {"commit": sha, "url": url, "sha256": digest}
    (assets / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    executables = sorted((assets / "fluidsynth").glob("**/fluidsynth.exe"))
    fonts = sorted((assets / "soundfonts").glob("**/*.sf2"))
    print("FluidSynth:", executables[0] if executables else "use separately installed renderer")
    print("SoundFont:", fonts[0] if fonts else "not found")
    if not fonts:
        raise ValueError("Downloaded repository contains no SoundFont")


if __name__ == "__main__":
    main()
