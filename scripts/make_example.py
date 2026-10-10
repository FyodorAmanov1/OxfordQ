"""Create a deterministic full-orchestra fixture. These notes are not QML output."""
import json
from pathlib import Path

import mido


ROOT = Path(__file__).resolve().parent.parent


def main():
    destination = ROOT / "examples" / "midi"
    destination.mkdir(parents=True, exist_ok=True)
    instruments = {
        "piccolo": (84, 72), "flute": (72, 73), "oboe": (72, 68), "clarinet": (60, 71),
        "bassoon": (48, 70), "horns": (60, 60), "trumpets": (60, 56), "trombones": (48, 57),
        "tuba": (36, 58), "violin_1": (72, 48), "violin_2": (60, 48), "viola": (60, 48),
        "cello": (48, 48), "double_bass": (36, 43), "timpani": (48, 47), "percussion": (36, 0),
    }
    progression = [(0, 4, 7), (9, 0, 4), (5, 9, 0), (7, 11, 2)]
    parts = []
    for index, (instrument, (register, program)) in enumerate(instruments.items()):
        midi = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        bpm = 96 if instrument == "flute" else (88 if index % 2 else 104)
        track.extend([mido.MetaMessage("track_name", name=instrument),
                      mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)),
                      mido.MetaMessage("time_signature", numerator=4, denominator=4),
                      mido.Message("program_change", program=program, channel=9 if instrument == "percussion" else 0)])
        events = []
        for bar in range(16):
            pcs = progression[bar % 4]
            if instrument == "flute":
                patterns = [(76, 79, 81, 79), (76, 72, 71, 69), (69, 72, 74, 72), (71, 74, 72, 71)]
                pitches = patterns[bar % 4]
                durations = [1, 1, 1, 1]
            elif instrument == "percussion":
                pitches = [36, 49] if bar % 4 == 0 else [36]
                durations = [0.15] * len(pitches)
            elif instrument == "timpani":
                pitches = [48 if bar % 4 in {0, 1} else 43]
                durations = [1]
            elif instrument in {"cello", "double_bass", "tuba", "bassoon"}:
                pitches = [register + pcs[0]]
                durations = [4]
            else:
                # Independent parts deliberately include a shared key offset and different tempi.
                offset = 2 if index % 3 == 0 else 0
                pitches = [register + pcs[index % 3] + offset]
                durations = [4]
            onset = bar * 4
            for i, (pitch, duration) in enumerate(zip(pitches, durations)):
                at = onset + (i if instrument == "flute" else i * 2)
                channel = 9 if instrument == "percussion" else 0
                events.append((round(at * 480), 1, mido.Message("note_on", note=pitch, velocity=86, channel=channel)))
                events.append((round((at + duration) * 480), 0, mido.Message("note_off", note=pitch, velocity=0, channel=channel)))
        previous = 0
        for tick, _, message in sorted(events, key=lambda e: (e[0], e[1])):
            message.time = tick - previous
            track.append(message)
            previous = tick
        track.append(mido.MetaMessage("end_of_track", time=max(0, 16 * 4 * 480 - previous)))
        midi.save(destination / f"{instrument}.mid")
        parts.append({"id": instrument, "instrument": instrument, "path": f"midi/{instrument}.mid",
                      "source": {"generator": "deterministic synthetic example", "backend": "classical fixture; not quantum hardware"}})
    manifest = {"lead_track": "flute", "parts": parts}
    (ROOT / "examples" / "parts.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Created 16 independent MIDI parts and {ROOT / 'examples' / 'parts.json'}")


if __name__ == "__main__":
    main()
