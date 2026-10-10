"""Synthetic adapter examples. These are fixtures, not trained or quantum models."""
from __future__ import annotations

import random

from .generation import GeneratedSequence, GenerationRequest
from .models import InputNote


class DemoMelodyGenerator:
    """Replace this class with an instrument-specific sequence-model adapter."""

    def __init__(self, instrument: str = "flute"):
        self.instrument = instrument

    def generate(self, request: GenerationRequest) -> GeneratedSequence:
        if request.instrument != self.instrument:
            raise ValueError(f"This adapter supports only {self.instrument}")
        rng = random.Random(request.seed)
        motif = rng.choice(([0, 2, 4, 7], [4, 2, 0, 7]))
        # Concert C near the middle of the requested profile.
        root = 12 * round((request.pitch_low + request.pitch_high) / 24)
        while root + 7 > request.pitch_high:
            root -= 12
        while root < request.pitch_low:
            root += 12
        notes = [InputNote(pitch=root + motif[beat % len(motif)], onset_beats=beat,
                           duration_beats=0.9, velocity=88)
                 for beat in range(request.duration_beats)]
        return GeneratedSequence(notes=notes, tempo_bpm=request.tempo_bpm,
                                 source={"kind": "synthetic_fixture", "version": "1"})


class DemoBassGenerator:
    """A second, independent adapter to demonstrate routing a distinct model."""

    def __init__(self, instrument: str = "cello"):
        self.instrument = instrument

    def generate(self, request: GenerationRequest) -> GeneratedSequence:
        if request.instrument != self.instrument:
            raise ValueError(f"This adapter supports only {self.instrument}")
        pitch = request.pitch_low + (12 - request.pitch_low % 12) % 12
        notes = [InputNote(pitch=pitch, onset_beats=bar * request.beats_per_bar,
                           duration_beats=3.75, velocity=64)
                 for bar in range(request.bars)]
        return GeneratedSequence(notes=notes, tempo_bpm=request.tempo_bpm,
                                 source={"kind": "synthetic_fixture", "version": "1"})
