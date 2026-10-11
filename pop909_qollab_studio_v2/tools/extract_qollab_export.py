
from __future__ import annotations
import argparse
import base64
import json
from pathlib import Path

def objects_from_console(text: str):
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        pos = 0
        while True:
            start = line.find("{", pos)
            if start < 0:
                break
            try:
                obj, consumed = decoder.raw_decode(line[start:])
            except json.JSONDecodeError:
                pos = start + 1
                continue
            yield obj
            pos = start + consumed

def main():
    parser = argparse.ArgumentParser(
        description="Recover Quantum Harmony MIDI/MP3 from downloaded Qollab console output."
    )
    parser.add_argument("console_file", type=Path)
    parser.add_argument("--kind", choices=["midi", "mp3"], required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    text = args.console_file.read_text(encoding="utf-8", errors="replace")
    candidates = []

    for obj in objects_from_console(text):
        if not isinstance(obj, dict):
            continue
        if obj.get("event") != "quantum-harmony-export":
            continue
        if obj.get("encoding") != "base64":
            continue

        filename = str(obj.get("filename") or "")
        payload = obj.get("payload")
        if not isinstance(payload, str):
            continue

        lower = filename.lower()
        if args.kind == "midi" and not lower.endswith((".mid", ".midi")):
            continue
        if args.kind == "mp3" and not lower.endswith(".mp3"):
            continue

        candidates.append((filename, payload))

    if not candidates:
        raise SystemExit(f"No {args.kind.upper()} quantum-harmony-export payload found.")

    filename, payload = candidates[-1]
    data = base64.b64decode(payload, validate=True)
    output = args.out or Path(filename)
    output.write_bytes(data)
    print(f"Wrote {output} ({len(data):,} bytes)")

if __name__ == "__main__":
    main()
