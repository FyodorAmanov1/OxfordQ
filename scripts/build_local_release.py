"""Compile and package local deliverables. No fetch, upload or provider API calls."""
import argparse
import compileall
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=ROOT):
    subprocess.run([str(x) for x in args], cwd=cwd, check=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist/local-release")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if out.exists():
        parser.error("Choose a fresh --out; existing builds are preserved")
    out.mkdir(parents=True)
    for name in ("orchestrator", "quantum_models", "components/quantum_duet/src",
                 "components/quantum_duet/dev", "pop909_qollab_studio_v2/quantum_harmony", "scripts"):
        if not compileall.compile_dir(str(ROOT / name), quiet=1):
            raise RuntimeError("Python compilation failed: " + name)
    javascript = sorted((ROOT / "components/quantum_duet/web").glob("*.mjs"))
    javascript += list((ROOT / "components/quantum_duet/dev").glob("*.mjs"))
    javascript += [ROOT / "components/quantum_duet/web/main.js",
                   ROOT / "pop909_qollab_studio_v2/main.js"]
    for path in javascript:
        # Qollab's .js entry points are browser ES modules, not Node CommonJS.
        subprocess.run(["node", "--input-type=module", "--check"],
                       input=path.read_bytes(), cwd=ROOT, check=True)
    run([sys.executable, "-m", "pip", "check"])
    wheels = out / "wheels"
    for package in (ROOT, ROOT / "components/quantum_duet"):
        run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
             "--no-index", package, "--wheel-dir", wheels])
    run([sys.executable, ROOT / "components/quantum_duet/tools/build_qollab.py",
         "--out", out / "quantum-duet"])
    run([sys.executable, ROOT / "scripts/verify_duet_build.py", out / "quantum-duet"])
    run([sys.executable, ROOT / "pop909_qollab_studio_v2/tools/build_zip.py",
         "--out", out / "pop909-studio.zip"])
    with zipfile.ZipFile(out / "pop909-studio.zip") as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, digest in manifest["files"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    # Separate site-packages proves wheel assets are not supplied by editable source.
    env = out / "wheel-environment"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(env)
    executable = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    # venv --system-site-packages shares the base interpreter, not this active
    # development venv. Add its dependency directory without executing editable
    # finder .pth files. Wheel-installed project packages retain precedence.
    package_dir = subprocess.check_output(
        [str(executable), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        text=True).strip()
    dependencies = sorted({sysconfig.get_path("purelib"), sysconfig.get_path("platlib")})
    (Path(package_dir) / "verified-build-dependencies.pth").write_text(
        "import sys; sys.path.extend(" + ascii(dependencies) + ")\n", encoding="ascii")
    installed = sorted(wheels.glob("*.whl"))
    run([executable, "-m", "pip", "install", "--no-index", "--no-deps",
         "--force-reinstall", *installed], cwd=out)
    check = (
        "from pathlib import Path; import quantum_models, quantum_duet, orchestrator; "
        "import sys; modules=(quantum_models,quantum_duet,orchestrator); "
        "assert all(Path(m.__file__).resolve().is_relative_to(Path(sys.prefix)) for m in modules); "
        "from importlib.resources import files; "
        "assert files('quantum_models').joinpath('SOURCE_NOTICES.md').is_file(); "
        "print('Wheel imports and packaged notices:', [m.__file__ for m in modules])"
    )
    run([executable, "-c", check], cwd=out)
    run([executable, "-m", "quantum_models.orchestra", "--bars", "4",
         "--no-audio", "--out", out / "wheel-smoke/orchestra"], cwd=out)
    run([executable, "-m", "quantum_duet", "--shots", "32",
         "--out", out / "wheel-smoke/duet.json"], cwd=out)
    run([executable, "-m", "orchestrator.composition", "--style", "debussy", "--bars", "12",
         "--no-audio", "--out", out / "wheel-smoke/composition"], cwd=out)
    run([executable.parent / ("qml-compose.exe" if sys.platform == "win32" else "qml-compose"), "--help"], cwd=out)
    artifacts = sorted(wheels.glob("*.whl")) + sorted(out.glob("*.zip"))
    source_names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    source_paths = [ROOT / name.decode("utf-8") for name in source_names.split(b"\0") if name]
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Local CPython, Node and BasicSimulator verification; no platform or hardware execution",
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_has_uncommitted_changes": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "source_files_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(source_paths) if p.is_file()},
        "python": sys.version,
        "versions": {name: importlib.metadata.version(name) for name in
                     ("qiskit", "numpy", "music21", "mido", "pydantic", "google-genai")},
        "artifacts": {p.relative_to(out).as_posix(): {"bytes": p.stat().st_size,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in artifacts},
        "checks": {"python_compiled": True, "javascript_syntax": True, "dependencies": True,
                   "duet_generated_namespace": True, "studio_archive_hashes": True,
                   "isolated_wheel_imports_and_inference": True},
    }
    (out / "release-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Local release verified:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
