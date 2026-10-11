"""Build a separate runnable folder under 100 files / 2 MB each / 200 MB total.

Original module and component paths stay intact. Compact audio is read directly
from Ogg sample banks through SFZ boundaries; no sample extraction is required.
The native Windows sampler is a compressed dependency with a temporary DLL cache.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import urllib.request
import wave
import zlib

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ["Flute-KS.sfz", "Clarinet-KS.sfz", "ViolinEns-KS.sfz",
           "CelloEns-KS.sfz", "Contrabass-KS.sfz", "VSUpright1.sfz"]
INSTRUMENTS = ["flute", "clarinet", "violin_1", "cello", "double_bass", "piano"]
SOURCE_URL = "https://github.com/sfztools/sfizz/releases/download/1.2.3/sfizz-1.2.3.tar.gz"
SOURCE_SHA = "a9339eac7620d7f0f6b44bdfe860680fab73e66efad4b5f15b21198dd9436822"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sample_paths(base):
    paths = set()
    for name in PATCHES:
        default = ""
        text = (base / name).read_text(encoding="utf-8")
        if re.search(r"\b(?:loop_start|loop_end|offset|end)\s*=", text):
            raise ValueError("Explicit sample-frame SFZ opcodes need rescaling: " + name)
        for line in text.splitlines():
            line = line.split("//", 1)[0].strip()
            if line.startswith("#include"):
                raise ValueError("Unexpected SFZ include in pinned sample patches")
            if line.startswith("default_path="):
                default = line.split("=", 1)[1].strip().replace("\\", "/")
            if line.startswith("sample="):
                filename = line.split("=", 1)[1].strip().replace("\\", "/")
                path = (base / default / filename).resolve()
                if not path.is_relative_to(base) or not path.is_file():
                    raise ValueError("Missing or unsafe sample reference: " + filename)
                paths.add(path)
    return sorted(paths)


def sample_metadata(path, rate, frames):
    """Preserve embedded sustain loops and cue positions at the new sample rate."""
    with wave.open(str(path), "rb") as audio:
        ratio = rate / audio.getframerate()
    chunks = []
    with path.open("rb") as source:
        if source.read(4) != b"RIFF":
            raise ValueError("Expected ordinary RIFF PCM WAV")
        source.seek(12)
        while header := source.read(8):
            if len(header) != 8:
                raise ValueError("Truncated WAV chunk")
            kind, size = struct.unpack("<4sI", header)
            if kind in (b"smpl", b"cue ", b"LIST"):
                data = source.read(size)
                if kind == b"smpl":
                    values = list(struct.unpack("<" + "I" * (len(data) // 4), data))
                    if len(values) < 9 or len(values) < 9 + values[7] * 6:
                        raise ValueError("Invalid sample-loop metadata")
                    values[2] = round(1_000_000_000 / rate)
                    for index in range(values[7]):
                        position = 9 + index * 6
                        values[position+2] = min(frames-1, round(values[position+2] * ratio))
                        values[position+3] = min(frames-1, max(values[position+2],
                            round((values[position+3]+1) * ratio)-1))
                    data = struct.pack("<" + "I" * len(values), *values)
                elif kind == b"cue ":
                    values = list(struct.unpack("<" + "I" * (len(data) // 4), data))
                    if not values or len(values) != 1 + values[0] * 6:
                        raise ValueError("Invalid cue metadata")
                    for index in range(values[0]):
                        position = 1 + index * 6
                        for offset in (1, 5):
                            values[position+offset] = min(frames-1, round(values[position+offset] * ratio))
                    data = struct.pack("<" + "I" * len(values), *values)
                chunks.append((kind, data))
            else:
                source.seek(size, 1)
            if size % 2:
                source.seek(1, 1)
    return chunks


def convert(source, target, rate, ffmpeg):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
        "-i", str(source), "-map_metadata", "-1", "-ac", "1", "-ar", str(rate),
        "-af", "aresample=dither_method=triangular", "-c:a", "pcm_s16le", str(target)],
        capture_output=True, check=True)
    with wave.open(str(target), "rb") as audio:
        frames = audio.getnframes()
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, rate):
            raise ValueError("Unexpected compact WAV format")
    metadata = sample_metadata(source, rate, frames)
    if metadata:
        with target.open("r+b") as handle:
            handle.seek(0, 2)
            for kind, data in metadata:
                handle.write(struct.pack("<4sI", kind, len(data)))
                handle.write(data)
                if len(data) % 2:
                    handle.write(b"\0")
            size = handle.tell()
            handle.seek(4)
            handle.write(struct.pack("<I", size-8))
    return source.stat().st_size, target.stat().st_size


def notices(cache):
    archive = cache / "sfizz-1.2.3.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(SOURCE_URL, timeout=45) as source, archive.open("wb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
    if digest(archive) != SOURCE_SHA:
        raise ValueError("sfizz upstream source checksum mismatch")
    text = ["sfizz 1.2.3 and dependency notices", "Source: " + SOURCE_URL]
    with tarfile.open(archive) as bundle:
        for item in bundle.getmembers():
            if item.isfile() and any(word in Path(item.name).name.lower()
                    for word in ("license", "copying", "copyright", "notice", "authors")):
                text.extend(["\n===== " + item.name + " =====",
                    bundle.extractfile(item).read().decode("utf-8", errors="replace")])
    return "\n".join(text)


def runtime_files():
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others",
        "--exclude-standard", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    exact = {"README.md", "LICENSE", "pyproject.toml",
        "components/quantum_duet/LICENSE", "components/quantum_duet/SOURCE_NOTICES.md",
        "components/quantum_duet/pyproject.toml", "components/quantum_duet/requirements.txt",
        "components/quantum_duet/tests/fixtures/qollab-local-run.json",
        "docs/fixtures/run-result.v1.json"}
    selected = []
    for name in names:
        core = name.startswith(("orchestrator/", "quantum_models/")) and not name.endswith("IMPORT_MANIFEST.json")
        duet = name.startswith(("components/quantum_duet/src/", "components/quantum_duet/web/", "components/quantum_duet/dev/"))
        pop = name.startswith("pop909_qollab_studio_v2/") and "/tools/" not in name
        if name and (core or duet or pop or name in exact) and (ROOT/name).is_file():
            selected.append(name)
    return sorted(set(selected))


def pack_banks(converted, output, work, rate, ffmpeg, bitrate):
    # Each source gets a guard gap, with exact SFZ boundaries around its frames.
    # Ogg is decoded directly by sfizz's pinned stb_vorbis implementation.
    mapping, groups, group, frames = {}, [], [], 0
    # About 425 seconds per bank; exact encoded size is checked below.
    # This stays below the native 16M-frame preload limit at all allowed rates.
    budget = round(rate * 425)
    for source, path in converted:
        with wave.open(str(path), "rb") as audio:
            length = audio.getnframes()
        if group and frames + length + 4096 > budget:
            groups.append(group)
            group, frames = [], 0
        group.append((source, path, length))
        frames += length + 4096
    if group:
        groups.append(group)
    banks = output / "banks"
    banks.mkdir()
    serial = [0]
    def encode(items):
        serial[0] += 1
        name = f"bank{serial[0]:03d}.ogg"
        pcm = work / (name + ".wav")
        entries, cursor = [], 0
        with wave.open(str(pcm), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(rate)
            for source, path, length in items:
                target.writeframesraw(b"\0" * 4096)
                cursor += 2048
                with wave.open(str(path), "rb") as audio:
                    target.writeframesraw(audio.readframes(length))
                loops = []
                for kind, data in sample_metadata(path, rate, length):
                    if kind == b"smpl":
                        values = struct.unpack("<" + "I"*(len(data)//4), data)
                        if values[7]:
                            loops = [cursor+values[11], cursor+values[12]]
                entries.append((source, {"bank":"banks/"+name, "offset":cursor,
                    "end":cursor+length-1, "loop":loops, "frames":length}))
                cursor += length
                target.writeframesraw(b"\0" * 4096)
                cursor += 2048
        encoded = work / name
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-i", str(pcm), "-map_metadata", "-1", "-c:a", "libvorbis",
            "-b:a", str(bitrate), str(encoded)], capture_output=True, check=True)
        if encoded.stat().st_size > 1_950_000:
            if len(items) == 1:
                raise ValueError("A sample bank exceeds the per-file cap")
            middle = len(items)//2
            encode(items[:middle])
            encode(items[middle:])
            return
        shutil.copyfile(encoded, banks / name)
        for source, entry in entries:
            mapping[source] = entry
        print("Packed", name, encoded.stat().st_size, "bytes", flush=True)
    for items in groups:
        encode(items)
    return mapping


def write_patches(base, compact, mapping):
    for name in PATCHES:
        default, lines = "", []
        for line in (base/name).read_text(encoding="utf-8").splitlines():
            stripped = line.split("//", 1)[0].strip()
            if stripped.startswith("default_path="):
                default = stripped.split("=", 1)[1].strip().replace("\\", "/")
                lines.append("default_path=./")
            elif stripped.startswith("sample="):
                filename = stripped.split("=", 1)[1].strip().replace("\\", "/")
                source = (base/default/filename).resolve()
                entry = mapping[source]
                lines.extend(["sample="+entry["bank"], "offset="+str(entry["offset"]), "end="+str(entry["end"])])
                if entry["loop"]:
                    lines.extend(["loop_mode=loop_continuous", "loop_start="+str(entry["loop"][0]),
                        "loop_end="+str(entry["loop"][1])])
                else:
                    lines.append("loop_mode=no_loop")
            else:
                lines.append(line)
        (compact/name).write_text("\n".join(lines)+"\n", encoding="utf-8")


def build(output, *, rate=22050, bitrate=40000, workers=4):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a fresh submission folder")
    if output == ROOT or ROOT.is_relative_to(output):
        raise ValueError("Submission cannot replace or enclose the source project")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise OSError("ffmpeg is required to build; it is not needed to run the folder")
    work = ROOT / "build" / (output.name + "-staging")
    if work.exists():
        raise ValueError("Choose a fresh submission name; staging results are preserved")
    work.mkdir(parents=True)
    output.mkdir(parents=True)
    source_files = runtime_files()
    for name in source_files:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    receipt = json.loads((ROOT / "assets/acoustic/receipt.json").read_text(encoding="utf-8"))
    asset_root = ROOT / "assets/acoustic"
    base = Path(receipt["samples"])
    base = (base if base.is_absolute() else asset_root/base).resolve()
    library = Path(receipt["library"])
    library = (library if library.is_absolute() else asset_root/library).resolve()
    sample_relative = Path("assets/acoustic/vsco") / base.name
    compact = output / sample_relative
    compact.mkdir(parents=True)
    shutil.copyfile(base/"LICENSE", compact/"LICENSE")
    paths = sample_paths(base)
    converted = [(p, work/"samples"/p.relative_to(base)) for p in paths]
    before, after = 0, 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(convert, p, target, rate, ffmpeg) for p, target in converted]
        for index, future in enumerate(as_completed(futures), 1):
            original, converted_bytes = future.result()
            before += original
            after += converted_bytes
            if index % 50 == 0 or index == len(paths):
                print(f"Converted {index}/{len(paths)} acoustic samples", flush=True)
    mapping = pack_banks(converted, compact, work, rate, ffmpeg, bitrate)
    write_patches(base, compact, mapping)
    runtime = output / "assets/acoustic/sfizz/bin/Release/sfizz.dll.zlib"
    runtime.parent.mkdir(parents=True)
    binary = library.read_bytes()
    payload = zlib.compress(binary, level=9)
    runtime.write_bytes(payload)
    cache = ROOT / "build/submission-assets-20261011"
    cache.mkdir(exist_ok=True)
    (output / "assets/acoustic/SFIZZ-NOTICES.txt").write_text(notices(cache), encoding="utf-8")
    compact_info = {"rate":rate, "channels":1, "pcm_bits_before_encoding":16,
        "encoding":"Ogg Vorbis sample banks", "nominal_bitrate":bitrate,
        "instruments":INSTRUMENTS, "samples":len(paths), "source_sample_bytes":before,
        "compact_pcm_bytes":after, "banks":len(list((compact/"banks").glob("*.ogg"))),
        "sample_extraction_required":False, "embedded_loops_rescaled":True,
        "quality":"Reduced bandwidth, mono and lossy compression; original assets unchanged"}
    compact_receipt = dict(receipt, library="sfizz/bin/Release/sfizz.dll.zlib",
        samples=sample_relative.relative_to("assets/acoustic").as_posix(), compact=compact_info,
        packed_library={"bytes":len(binary), "sha256":hashlib.sha256(binary).hexdigest(),
            "compressed_sha256":hashlib.sha256(payload).hexdigest()})
    (output / "assets/acoustic/receipt.json").write_text(json.dumps(compact_receipt, indent=2), encoding="utf-8")
    instructions = f"""# OxfordQ compact submission

This is a runnable local Windows x64 snapshot of the project. Original Python
module paths and the Quantum Duet / POP909 component directories are preserved.
Development tests, historical reports and duplicate import manifests are omitted.
The required recorded fixture remains at its original path. No source file was
moved or original sample altered in the development repository.

## Run

Python 3.11+ on Windows x64, with pip dependencies installed separately:

```powershell
python -m venv ../OxfordQ-submission-env
../OxfordQ-submission-env/Scripts/python -B -c "import subprocess, sys, tomllib; p = tomllib.load(open('pyproject.toml', 'rb'))['project']; subprocess.check_call([sys.executable, '-m', 'pip', 'install', *p['dependencies'], *p['optional-dependencies']['quantum']])"
../OxfordQ-submission-env/Scripts/python -B -m orchestrator.composition --style all --require-audio --out ../output-submission-pieces
```

Use external environment and output directories to keep this submitted folder
unchanged. `-B` prevents Python bytecode files appearing in the snapshot.
The default ensemble includes flute, clarinet, violin, cello, bass and piano.
Piano has two-hand accompaniment, strike dynamics and harmonic pedal changes.
Quantum-model inference is local Qiskit Statevector, not physical hardware.
Generators remain replaceable using GenerationRegistry. No paid API is required.
Text preferences and exact seconds are not implemented in this snapshot.

## Compact audio and limits

All 709 referenced samples, articulation mappings, velocity layers and round
robins are retained. Samples are mono {rate} Hz, encoded into Ogg Vorbis banks
at nominal {bitrate} bits/second. SFZ offsets/endpoints restrict each region to
its own sample. Embedded loops are rescaled and recorded in the patch.
The native sampler reads the banks directly: no sample archive is extracted.
This reduces fidelity and stereo width relative to the full development edition.
Original high-quality assets and earlier pieces remain untouched.

The compressed native dependency is verified and restored to an operating-system
temporary cache on first use; the sample library stays in these shipped banks.
Python, installed pip packages and generated outputs are not part of this upload.
The manifest counts all shipped files recursively using decimal byte limits:
100 files, 2,000,000 bytes each, 200,000,000 bytes total.

This is not a Qollab/Pyodide browser deployment. Its native Windows sampler needs
an appropriate local runtime. Existing component source files are retained; their
separate browser deployment builders and platform verification are outside this
snapshot. Install the duet component separately with pip if using its local API.

## Licenses

Repository code is MIT (LICENSE). VSCO samples are CC0-1.0, recorded by Sam Gossner
and Simon Dalzell, edited by Elan Hickler. sfizz 1.2.3 is BSD-2-Clause; upstream
and dependency notices are in assets/acoustic/SFIZZ-NOTICES.txt.
"""
    (output/"README.md").write_text(instructions, encoding="utf-8")
    files = sorted(p for p in output.rglob("*") if p.is_file())
    identities = {p.relative_to(output).as_posix():{"bytes":p.stat().st_size,"sha256":digest(p)} for p in files}
    manifest = {"schema":"oxfordq.submission-folder.v1", "created_utc":datetime.now(timezone.utc).isoformat(),
        "source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "source_has_uncommitted_changes":bool(subprocess.check_output(["git","status","--porcelain"],cwd=ROOT)),
        "scope":"Directly runnable local Windows x64 snapshot; not Qollab/Pyodide",
        "dependencies_included":False, "directory_paths_preserved":True,
        "compact_audio":compact_info, "source_files":source_files,
        "source_files_sha256":{name:digest(ROOT/name) for name in source_files},
        "sample_map":{p.relative_to(base).as_posix():entry for p,entry in mapping.items()},
        "files":identities, "manifest_excluded_from_self_hash":True,
        "limits":{"files":100,"per_file_bytes":2_000_000,"total_bytes":200_000_000}}
    (output/"submission-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    submitted = [p for p in output.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in submitted)
    largest = max(p.stat().st_size for p in submitted)
    if len(submitted)>100 or total>200_000_000 or largest>2_000_000:
        raise ValueError(f"Submission does not fit: {len(submitted)} files, {total} bytes, largest {largest}; lower bank bitrate")
    print(json.dumps({"submission":str(output),"files":len(submitted),"bytes":total,
        "largest_file_bytes":largest,"audio":compact_info},indent=2),flush=True)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rate", type=int, choices=[16000,22050,32000], default=22050)
    parser.add_argument("--bitrate", type=int, choices=[24000,32000,40000,48000,64000], default=40000)
    parser.add_argument("--workers", type=int, choices=range(1,9), default=4)
    args = parser.parse_args()
    build(args.out, rate=args.rate, bitrate=args.bitrate, workers=args.workers)


if __name__ == "__main__":
    main()
