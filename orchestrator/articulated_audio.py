"""Render isolated SoundFont notes and mix independent amplitude envelopes."""
import ctypes as ct
from ctypes.util import find_library
import os
import shutil
from pathlib import Path
import numpy as np
from .instruments import profile
from .performance import envelope, performance_for


class NoteSynth:
    """Single-thread offline FluidSynth: no device, sequencer, network or shared voices."""
    def __init__(self, executable, soundfont, rate):
        self.settings = self.synth = None
        self.directory_handle = None
        directory = Path(shutil.which(executable) or executable).resolve().parent
        candidates = sorted(directory.glob("*fluidsynth*.dll")) if os.name == "nt" else []
        library = str(candidates[0]) if candidates else find_library("fluidsynth")
        if not library:
            raise OSError("Instrument envelopes require the FluidSynth shared library next to its executable or on the library path")
        if os.name == "nt":
            self.directory_handle = os.add_dll_directory(str(directory))
        try:
            self.lib = ct.CDLL(library)
            p, i, f = ct.c_void_p, ct.c_int, ct.c_float
            signatures = {
                "new_fluid_settings": (p, []), "delete_fluid_settings": (None, [p]),
                "fluid_settings_setnum": (i, [p, ct.c_char_p, ct.c_double]),
                "fluid_settings_setint": (i, [p, ct.c_char_p, i]),
                "new_fluid_synth": (p, [p]), "delete_fluid_synth": (None, [p]),
                "fluid_synth_sfload": (i, [p, ct.c_char_p, i]),
                "fluid_synth_program_select": (i, [p, i, i, i, i]),
                "fluid_synth_cc": (i, [p, i, i, i]),
                "fluid_synth_noteon": (i, [p, i, i, i]),
                "fluid_synth_all_sounds_off": (i, [p, i]),
                "fluid_synth_get_voicelist": (None, [p, ct.POINTER(p), i, i]),
                "fluid_voice_gen_set": (None, [p, i, f]),
                "fluid_voice_update_param": (None, [p, i]),
                "fluid_synth_write_float": (i, [p, i, p, i, i, p, i, i]),
            }
            for name, (result, arguments) in signatures.items():
                method = getattr(self.lib, name)
                method.restype, method.argtypes = result, arguments
            self.settings = self.lib.new_fluid_settings()
            if not self.settings:
                raise RuntimeError("FluidSynth settings allocation failed")
            self.lib.fluid_settings_setnum(self.settings, b"synth.sample-rate", rate)
            self.lib.fluid_settings_setnum(self.settings, b"synth.gain", .25)
            self.lib.fluid_settings_setint(self.settings, b"synth.reverb.active", 0)
            self.lib.fluid_settings_setint(self.settings, b"synth.chorus.active", 0)
            self.synth = self.lib.new_fluid_synth(self.settings)
            if not self.synth:
                raise RuntimeError("FluidSynth allocation failed")
            self.font = self.lib.fluid_synth_sfload(self.synth, os.fsencode(soundfont), 1)
            if self.font < 0:
                raise RuntimeError("FluidSynth could not load the SoundFont")
        except Exception:
            self.close()
            raise

    def close(self):
        if self.synth:
            self.lib.delete_fluid_synth(self.synth)
            self.synth = None
        if self.settings:
            self.lib.delete_fluid_settings(self.settings)
            self.settings = None
        if self.directory_handle:
            self.directory_handle.close()
            self.directory_handle = None

    def note(self, instrument, pitch, velocity, count):
        pr = profile(instrument)
        channel, bank = (9, 128) if pr.family == "drums" else (0, 0)
        self.lib.fluid_synth_all_sounds_off(self.synth, channel)
        # Flush the internal synthesis block so the next onset cannot inherit samples.
        self._frames(64)
        if self.lib.fluid_synth_program_select(self.synth, channel, self.font, bank, pr.program) < 0:
            raise RuntimeError("Missing SoundFont instrument " + instrument)
        self.lib.fluid_synth_cc(self.synth, channel, 7, 100)
        self.lib.fluid_synth_cc(self.synth, channel, 10, 64)
        self.lib.fluid_synth_cc(self.synth, channel, 11, 127)
        if self.lib.fluid_synth_noteon(self.synth, channel, pitch, velocity) < 0:
            raise RuntimeError("FluidSynth note allocation failed")
        voices = (ct.c_void_p * 256)()
        self.lib.fluid_synth_get_voicelist(self.synth, voices, len(voices), -1)
        for voice in voices:
            if not voice:
                continue
            # The explicit DSP envelope replaces the sample's volume envelope.
            # SoundFont 2 generator IDs, per installed fluidsynth/gen.h.
            for generator, value in [(33, -12000), (34, -12000), (35, -12000),
                                     (36, -12000), (37, 0), (38, -12000), (39, 0), (40, 0)]:
                self.lib.fluid_voice_gen_set(voice, generator, value)
                self.lib.fluid_voice_update_param(voice, generator)
        result = self._frames(count)
        self.lib.fluid_synth_all_sounds_off(self.synth, channel)
        return result

    def _frames(self, count):
        result = np.zeros((count, 2), dtype=np.float32)
        pointer = result.ctypes.data_as(ct.c_void_p)
        if self.lib.fluid_synth_write_float(self.synth, count, pointer, 0, 2, pointer, 1, 2) < 0:
            raise RuntimeError("FluidSynth audio rendering failed")
        return result


def render_score(score, executable, soundfont, rate):
    """Overlapping notes keep independent envelopes; expression affects existing notes."""
    performance = {part.id: getattr(score, "performance", {}).get(part.id, performance_for(part.instrument)) for part in score.parts}
    timeline = getattr(score, "timeline", None)
    if timeline is None:
        from types import SimpleNamespace
        timeline = SimpleNamespace(seconds_at=lambda tick: tick * 60 / (score.ppq * score.tempo_bpm))
    seconds = timeline.seconds_at(score.end_tick)
    tail = max(spec.release_seconds for spec in performance.values()) + .05
    mix = np.zeros((round((seconds + tail) * rate), 2), dtype=np.float32)
    synth = NoteSynth(executable, soundfont, rate)
    try:
        for part in score.parts:
            spec = performance[part.id]
            # Linear interpolation avoids staircase volume changes between phrase points.
            points = sorted(part.expression)
            xp = [timeline.seconds_at(tick) for tick, _ in points] or [0]
            fp = [value / 127 for _, value in points] or [100 / 127]
            pan = part.pan / 127
            stereo = np.array([np.cos(pan * np.pi / 2), np.sin(pan * np.pi / 2)], dtype=np.float32)
            for note in part.notes:
                if note.muted:
                    continue
                at = timeline.seconds_at(note.onset_tick)
                duration = timeline.seconds_at(note.end_tick) - at
                shape = envelope(spec, duration, rate, note.pitch)
                sound = synth.note(part.instrument, note.pitch, note.velocity, len(shape))
                time = at + np.arange(len(shape)) / rate
                shape *= np.interp(time, xp, fp).astype(np.float32) * spec.volume
                start = round(at * rate)
                stop = min(len(mix), start + len(shape))
                mix[start:stop] += sound[:stop-start] * shape[:stop-start, None] * stereo
    finally:
        synth.close()
    return mix, {"renderer": "FluidSynth isolated SoundFont notes with independent DSP envelopes",
                 "effects": "dry; no artificial reverb/chorus", "volume": "SoundFont velocity response, per-part gain and interpolated CC11",
                 "instrument_envelopes": {name: spec.model_dump() for name, spec in performance.items()}}
