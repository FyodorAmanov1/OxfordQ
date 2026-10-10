"""MIDI input and export, with independent tempi mapped to the anchor's pulse."""
from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path

import mido

from .instruments import profile
from .models import Manifest, NoteEvent, OrchestrationConfig, Part, PartSpec, Score


def load_manifest(path: str | Path) -> Manifest:
    path = Path(path).resolve()
    manifest = Manifest.model_validate_json(path.read_text(encoding="utf-8"))
    for part in manifest.parts:
        if part.path is not None:
            part.path = (path.parent / part.path).resolve()
    return manifest


def _read_midi(spec: PartSpec, ppq: int) -> tuple[list[tuple], float | None, list[str]]:
    midi = mido.MidiFile(spec.path)
    if midi.type == 2:
        raise ValueError(f"{spec.id}: asynchronous type-2 MIDI is unsupported")
    warnings = []
    tempi = set()
    signatures = set()
    for track in midi.tracks:
        for message in track:
            if message.type == "set_tempo":
                tempi.add(message.tempo)
            elif message.type == "time_signature":
                signatures.add((message.numerator, message.denominator))
    if len(tempi) > 1:
        raise ValueError(f"{spec.id}: tempo changes within a part are unsupported in v1")
    if signatures and signatures != {(4, 4)}:
        raise ValueError(f"{spec.id}: v1 accepts 4/4 only; found {sorted(signatures)}")
    if not signatures:
        warnings.append(f"{spec.id}: no metre metadata; assumed 4/4")
    tempo = mido.tempo2bpm(next(iter(tempi))) if tempi else None
    if spec.midi_track is None:
        candidates = [i for i, tr in enumerate(midi.tracks) if any(
            msg.type == "note_on" and msg.velocity > 0 and
            (spec.channel is None or msg.channel == spec.channel) for msg in tr)]
        if len(candidates) != 1:
            raise ValueError(f"{spec.id}: select midi_track explicitly; note-bearing tracks: {candidates}")
        index = candidates[0]
    else:
        index = spec.midi_track
    if index >= len(midi.tracks):
        raise ValueError(f"{spec.id}: MIDI track {index} does not exist")

    active = defaultdict(deque)
    sustained = defaultdict(list)
    pedal = defaultdict(bool)
    notes = []
    tick = 0
    sequence = 0
    ignored = set()

    def finish(item, end):
        note_id, pitch, start, velocity = item
        onset = round(start * ppq / midi.ticks_per_beat)
        stop = round(end * ppq / midi.ticks_per_beat)
        notes.append((note_id, pitch, onset, max(1, stop - onset), velocity))

    for msg in midi.tracks[index]:
        tick += msg.time
        if getattr(msg, "is_meta", False):
            continue
        channel = getattr(msg, "channel", None)
        if spec.channel is not None and channel != spec.channel:
            continue
        if msg.type == "note_on" and msg.velocity > 0:
            active[(channel, msg.note)].append((sequence, msg.note, tick, msg.velocity))
            sequence += 1
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            if active[(channel, msg.note)]:
                item = active[(channel, msg.note)].popleft()
                if pedal[channel]:
                    sustained[channel].append(item)
                else:
                    finish(item, tick)
            else:
                warnings.append(f"{spec.id}: unmatched note-off at source tick {tick}")
        elif msg.type == "control_change" and msg.control == 64:
            pedal[channel] = msg.value >= 64
            if not pedal[channel]:
                for item in sustained[channel]:
                    finish(item, tick)
                sustained[channel].clear()
        elif msg.type in {"pitchwheel", "aftertouch", "polytouch", "control_change"}:
            ignored.add(msg.type)
    for queue in active.values():
        for item in queue:
            finish(item, max(tick, item[2] + 1))
            warnings.append(f"{spec.id}: missing note-off closed at end of source track")
    for held in sustained.values():
        for item in held:
            finish(item, max(tick, item[2] + 1))
    if ignored:
        warnings.append(f"{spec.id}: {', '.join(sorted(ignored))} performance data omitted; sustain converted to note lengths")
    return sorted(notes, key=lambda n: (n[2], n[0])), spec.tempo_bpm or tempo, warnings


def import_parts(parts: list[PartSpec], lead_track: str, config: OrchestrationConfig) -> tuple[Score, list[str]]:
    ids = [part.id for part in parts]
    if len(ids) != len(set(ids)):
        raise ValueError("Part identifiers must be unique")
    if lead_track not in ids:
        raise ValueError("lead_track must name a supplied part")
    warnings = []
    normalised = []
    start = config.start_bar * config.bar_ticks
    end = start + config.end_tick
    for spec in parts:
        instrument = profile(spec.instrument)
        if spec.notes is not None:
            raw = [(i, n.pitch, round(n.onset_beats * config.ppq),
                    max(1, round(n.duration_beats * config.ppq)), n.velocity)
                   for i, n in enumerate(spec.notes)]
            tempo = spec.tempo_bpm
        else:
            raw, tempo, messages = _read_midi(spec, config.ppq)
            warnings.extend(messages)
        events = []
        for sequence, pitch, onset, duration, velocity in raw:
            if onset >= end or onset + duration <= start:
                continue
            left = max(onset, start) - start
            right = min(onset + duration, end) - start
            if onset < start or onset + duration > end:
                warnings.append(f"{spec.id}: source note {sequence} clipped at the selected excerpt boundary")
            source_id = f"{spec.id}:n{sequence}"
            phrase = left // (config.window_bars * config.bar_ticks)
            events.append(NoteEvent(id=source_id, source_id=source_id,
                                    phrase_id=f"{spec.id}:p{phrase}", pitch=pitch,
                                    onset_tick=left, duration_ticks=max(1, right-left), velocity=velocity))
        if not events:
            warnings.append(f"{spec.id}: no notes in the selected excerpt; part remains silent")
        default_role = "bass" if spec.instrument in {"cello", "double_bass", "tuba", "bassoon"} else (
            "rhythm" if instrument.family in {"drums", "percussion"} else "harmony")
        normalised.append(Part(id=spec.id, instrument=spec.instrument, notes=events,
                               role="melody" if spec.id == lead_track else spec.role or default_role,
                               source=spec.source, source_tempo_bpm=tempo, pan=instrument.pan))
    lead = next(p for p in normalised if p.id == lead_track)
    if not lead.notes:
        raise ValueError("The designated lead has no notes in the selected excerpt")
    if profile(lead.instrument).family == "drums":
        raise ValueError("Unpitched percussion cannot be the melodic anchor")
    tempo = config.tempo_bpm or lead.source_tempo_bpm or 96.0
    for part in normalised:
        if part.source_tempo_bpm and abs(part.source_tempo_bpm-tempo) > 0.1:
            warnings.append(f"{part.id}: mapped source tempo {part.source_tempo_bpm:.2f} BPM to anchor {tempo:.2f} BPM, preserving beat positions")
    return Score(parts=normalised, lead_track=lead_track, tempo_bpm=tempo, ppq=config.ppq,
                 bars=config.bars, window_bars=config.window_bars), warnings


def export_midi(score: Score, path: str | Path) -> None:
    """One channel per pitched part; percussion uses channel 10 (zero-based 9)."""
    melodic = [p for p in score.parts if profile(p.instrument).family != "drums"]
    if len(melodic) > 15:
        raise ValueError("MIDI export supports 15 pitched parts; combine section parts before export")
    if sum(profile(p.instrument).family == "drums" for p in score.parts) > 1:
        raise ValueError("Supply one combined unpitched percussion part")
    channels = {p.id: ch for p, ch in zip(melodic, [n for n in range(16) if n != 9])}
    midi = mido.MidiFile(type=1, ticks_per_beat=score.ppq)
    meta = mido.MidiTrack()
    midi.tracks.append(meta)
    meta.extend([mido.MetaMessage("track_name", name="Conductor"),
                 mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(score.tempo_bpm)),
                 mido.MetaMessage("time_signature", numerator=4, denominator=4),
                 mido.MetaMessage("end_of_track", time=score.end_tick)])
    for part in score.parts:
        pr = profile(part.instrument)
        channel = 9 if pr.family == "drums" else channels[part.id]
        track = mido.MidiTrack()
        midi.tracks.append(track)
        track.append(mido.MetaMessage("track_name", name=f"{part.id} ({part.instrument})"))
        track.append(mido.Message("program_change", channel=channel, program=pr.program))
        track.append(mido.Message("control_change", channel=channel, control=10, value=part.pan))
        track.append(mido.Message("control_change", channel=channel, control=7, value=100))
        track.append(mido.Message("control_change", channel=channel, control=11, value=100))
        events = []
        for note in part.notes:
            if note.muted:
                continue
            events.extend([(note.onset_tick, 2, note.pitch, note.velocity),
                           (note.end_tick, 1, note.pitch, 0)])
        events.extend((tick, 0, -1, value) for tick, value in part.expression)
        active = defaultdict(int)
        previous = 0
        for tick, kind, pitch, velocity in sorted(events):
            if kind == 0:
                message = mido.Message("control_change", channel=channel, control=11, value=velocity)
            elif kind == 2:
                active[pitch] += 1
                if active[pitch] != 1:
                    continue  # overlapping unisons sustain until the final release
                message = mido.Message("note_on", channel=channel, note=pitch, velocity=velocity)
            else:
                active[pitch] -= 1
                if active[pitch] != 0:
                    continue
                message = mido.Message("note_off", channel=channel, note=pitch, velocity=0)
            message.time = tick-previous
            track.append(message)
            previous = tick
        track.append(mido.MetaMessage("end_of_track", time=max(0, score.end_tick-previous)))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)
