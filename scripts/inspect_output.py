"""Read a generated comparison and verify actual MIDI lead timing and WAV data."""
import argparse
import json
import wave
from collections import Counter, defaultdict, deque
from pathlib import Path

import mido
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    score = json.loads((directory / "arrangement.json").read_text(encoding="utf-8"))
    lead_id = score["lead_track"]
    lead = next(p for p in score["parts"] if p["id"] == lead_id)
    midi = mido.MidiFile(directory / "arrangement.mid")
    track = next(t for t in midi.tracks if any(
        msg.type == "track_name" and msg.name.startswith(lead_id + " (") for msg in t))
    active = defaultdict(deque)
    heard = []
    tick = 0
    for msg in track:
        tick += msg.time
        if msg.type == "note_on" and msg.velocity:
            active[msg.note].append(tick)
        elif msg.type == "note_off" or (msg.type == "note_on" and not msg.velocity):
            onset = active[msg.note].popleft()
            heard.append((msg.note, onset, tick-onset))
    expected = [(n["pitch"], n["onset_tick"], n["duration_ticks"]) for n in lead["notes"]]
    if Counter(heard) != Counter(expected):
        raise ValueError("Exported MIDI does not preserve every lead note's pitch and timing")
    if any(active.values()):
        raise ValueError("Exported lead contains unreleased notes")
    print(f"Lead MIDI roundtrip: {len(heard)} notes preserved")
    print("Provider:", report["provider_status"], "Audio:", report["audio"]["status"])
    print("Heuristic scores:", {k: v["heuristic_score"] for k,v in report["metrics"].items()})
    if report["audio"]["status"] == "rendered":
        for name in ("original", "baseline", "arrangement"):
            with wave.open(str(directory / f"{name}.wav"), "rb") as file:
                rate, channels, frames = file.getframerate(), file.getnchannels(), file.getnframes()
                samples = np.frombuffer(file.readframes(frames), dtype="<i2") / 32768.0
            peak = float(np.max(np.abs(samples)))
            if peak <= 0 or peak > 10 ** (-1/20) + 1/32768:
                raise ValueError(f"{name}: silent audio or peak headroom violation")
            if frames / rate < score["bars"] * 4 * 60 / score["tempo_bpm"]:
                raise ValueError(f"{name}: audio shorter than the musical excerpt")
            print(f"{name}.wav: {frames/rate:.2f}s, {rate} Hz, {channels} channels, peak {peak:.4f}")


if __name__ == "__main__":
    main()
