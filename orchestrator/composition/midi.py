"""Expressive MIDI conductor export and a strict event reader for round trips."""
from collections import defaultdict, deque
import json
from pathlib import Path
import mido
from orchestrator.midi_io import export_midi


def export_composed_midi(score, path):
    export_midi(score, path)
    midi = mido.MidiFile(path)
    events = [(0, mido.MetaMessage("track_name", name=score.title))]
    previous = None
    for tick, bar in zip(score.timeline.bar_starts, score.timeline.bars):
        signature = (bar.numerator, bar.denominator)
        if signature != previous:
            events.append((tick, mido.MetaMessage("time_signature", numerator=bar.numerator,
                                                 denominator=bar.denominator)))
            previous = signature
        if bar.groups:
            events.append((tick, mido.MetaMessage("marker", text="grouping:" + "+".join(map(str, bar.groups)))))
    events.extend((event.tick, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(event.bpm)))
                  for event in score.timeline.tempos)
    events.append((score.end_tick, mido.MetaMessage("end_of_track")))
    conductor, cursor = mido.MidiTrack(), 0
    for tick, message in sorted(events, key=lambda item: item[0]):
        conductor.append(message.copy(time=tick - cursor))
        cursor = tick
    midi.tracks[0] = conductor
    for part, track in zip(score.parts, midi.tracks[1:]):
        spec = score.performance.get(part.id)
        if spec is not None:
            for message in track:
                if message.type == "control_change" and message.control == 7:
                    message.value = round(spec.volume * 127)
                    break
            track.insert(1, mido.MetaMessage("text", text="instrument-envelope:" + json.dumps(spec.model_dump(), separators=(",", ":"))))
    midi.save(Path(path))


def read_composed_midi(path):
    """Retain integer timing and expression; reject unpaired note events."""
    midi = mido.MidiFile(path)
    result = {"ppq": midi.ticks_per_beat, "tempos": [], "metres": [], "parts": {}, "end_tick": 0}
    for index, track in enumerate(midi.tracks):
        tick, name, notes, controls = 0, str(index), [], []
        active = defaultdict(deque)
        for message in track:
            tick += message.time
            if message.type == "track_name":
                name = message.name.split(" (")[0]
            elif message.type == "set_tempo":
                result["tempos"].append((tick, message.tempo))
            elif message.type == "time_signature":
                result["metres"].append((tick, message.numerator, message.denominator))
            elif message.type == "control_change" and message.control == 11:
                controls.append((tick, message.value))
            elif message.type == "note_on" and message.velocity > 0:
                active[(message.channel, message.note)].append((tick, message.velocity))
            elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                queue = active[(message.channel, message.note)]
                if not queue:
                    raise ValueError("Unpaired MIDI release")
                onset, velocity = queue.popleft()
                notes.append((message.note, onset, tick - onset, velocity))
        if any(active.values()):
            raise ValueError("Unreleased MIDI note")
        if index:
            result["parts"][name] = {"notes": sorted(notes), "expression": controls}
        result["end_tick"] = max(result["end_tick"], tick)
    return result
