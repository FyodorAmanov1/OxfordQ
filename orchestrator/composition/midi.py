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


def export_performed_midi(score, performance, path):
    """Portable performance MIDI; SFZ-specific control notes are never exported."""
    from orchestrator.instruments import profile
    from .performer import validate_performance
    validate_performance(score,performance)
    midi = mido.MidiFile(ticks_per_beat=score.ppq)
    conductor = mido.MidiTrack()
    midi.tracks.append(conductor)
    events = [(0,0,mido.MetaMessage("track_name",name=score.title+" performed"))]
    previous = None
    for tick,bar in zip(performance.timeline.bar_starts,performance.timeline.bars):
        signature = (bar.numerator,bar.denominator)
        if signature != previous:
            events.append((tick,1,mido.MetaMessage("time_signature",numerator=bar.numerator,denominator=bar.denominator)))
            previous = signature
    events.extend((t.tick,2,mido.MetaMessage("set_tempo",tempo=mido.bpm2tempo(t.bpm))) for t in performance.timeline.tempos)
    def fill(track, events):
        cursor = 0
        for tick,_,message in sorted(events,key=lambda e:(e[0],e[1])):
            track.append(message.copy(time=tick-cursor))
            cursor = tick
        track.append(mido.MetaMessage("end_of_track",time=score.end_tick-cursor))
    fill(conductor,events)
    for index,part in enumerate(score.parts):
        channel = index if index < 9 else index+1
        if channel > 15:
            raise ValueError("Too many performed MIDI parts")
        pr = profile(part.instrument)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        spec = score.performance.get(part.id)
        events = [(0,0,mido.MetaMessage("track_name",name=part.id+" ("+part.instrument+")")),
                  (0,1,mido.Message("program_change",channel=channel,program={"violin_1":40,"violin_2":40,"viola":41,"cello":42}.get(part.instrument,pr.program))),
                  (0,1,mido.Message("control_change",channel=channel,control=7,value=round((spec.volume if spec else .8)*127))),
                  (0,1,mido.Message("control_change",channel=channel,control=10,value=part.pan))]
        for control in performance.controls[part.id]:
            events.append((control.tick,2,mido.Message("control_change",channel=channel,control=control.controller,value=control.value)))
        for note in performance.notes:
            if note.part_id != part.id:
                continue
            meta = json.dumps({"note_id":note.note_id,"source_id":note.source_id,"phrase_id":note.phrase_id,"articulation":note.articulation},separators=(",",":"))
            events.extend([(note.onset_tick,3,mido.MetaMessage("text",text=meta)),
                           (note.onset_tick,4,mido.Message("note_on",channel=channel,note=note.pitch,velocity=note.velocity)),
                           (note.onset_tick+note.duration_ticks,2,mido.Message("note_off",channel=channel,note=note.pitch,velocity=0))])
        fill(track,events)
    midi.save(Path(path))
