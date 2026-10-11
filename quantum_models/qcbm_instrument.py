"""Frozen motif QCBM with explicit classical adaptation for each instrument."""
from __future__ import annotations

import hashlib
import json
import math
from importlib.resources import files
from pathlib import Path

import numpy as np
from music21 import note as m21note
from pydantic import Field
from qiskit.quantum_info import Statevector

from orchestrator.generation import GeneratedSequence, GenerationRequest
from orchestrator.instruments import profile
from orchestrator.models import InputNote, Schema
from orchestrator.theory import parse_key
from .qcbm_circuit import bind_parameters, build_circuit


class DecoderOptions(Schema):
    key: str = "C major"
    stride_beats: float | None = Field(default=None, ge=0.25, le=4, allow_inf_nan=False)
    gate: float = Field(default=0.85, ge=0.1, le=1, allow_inf_nan=False)
    register_fraction: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    velocity: int | None = Field(default=None, ge=1, le=127)


class QCBMInstrumentGenerator:
    """Reuse one frozen checkpoint; instrument differences are classical decoding.

    Sampling is local exact Statevector inference, with zero provider submissions.
    This does not alter Quantum Duet's original mapping or its scientific evidence.
    """

    def __init__(self, instrument: str | None = None, checkpoint: str | None = None):
        if instrument is not None:
            profile(instrument)
        self.instrument = instrument
        raw = (Path(checkpoint).read_bytes() if checkpoint else
               files("quantum_models").joinpath("data/qcbm_melody.json").read_bytes())
        payload = json.loads(raw)
        angles = np.asarray(payload["parameters_radians"], dtype=float)
        if angles.shape != (84,) or not np.isfinite(angles).all():
            raise ValueError("The frozen motif checkpoint requires 84 finite angles")
        self.payload_sha256 = hashlib.sha256(raw).hexdigest()
        self.original_checkpoint_sha256 = payload["source_checkpoint_sha256"]
        probabilities = Statevector.from_instruction(
            bind_parameters(build_circuit(), angles)).probabilities()
        self.probabilities = probabilities / probabilities.sum()
        self.probabilities.flags.writeable = False

    def generate(self, request: GenerationRequest) -> GeneratedSequence:
        if self.instrument is not None and request.instrument != self.instrument:
            raise ValueError(f"Adapter is bound to {self.instrument}")
        pr = profile(request.instrument)
        options = DecoderOptions.model_validate(request.options)
        bass = request.instrument in {"cello", "double_bass", "bassoon", "tuba", "trombones"}
        stride = options.stride_beats or (2 if bass or pr.family == "brass" else 1)
        token_count = math.ceil(request.duration_beats / stride)
        rng = np.random.default_rng(request.seed)
        outcomes = rng.choice(4096, size=math.ceil(token_count / 4), p=self.probabilities)
        tokens = [int((int(outcome) >> (3 * i)) & 7)
                  for outcome in outcomes for i in range(4)][:token_count]
        if pr.family == "drums":
            pitches = [36, 38, 42, 46, 49, 51, 45]
        else:
            tonality = parse_key(options.key)
            available = [int(p.midi) for p in tonality.getScale().getPitches(
                m21note.Note(pr.low).pitch, m21note.Note(pr.high).pitch)]
            if len(available) < 7:
                raise ValueError("Instrument range must contain a full diatonic octave")
            centre = pr.low + (options.register_fraction if options.register_fraction is not None else
                              (0.25 if bass else 0.5)) * (pr.high - pr.low)
            starts = range(len(available) - 6)
            start = min(starts, key=lambda i: abs(available[i + 3] - centre))
            pitches = available[start:start + 7]
        velocity = options.velocity or (64 if pr.family == "brass" else 72 if bass else 84)
        notes, lineage = [], []
        for index, token in enumerate(tokens):
            if token == 0:
                continue
            onset = index * stride
            duration = min(stride * options.gate, request.duration_beats - onset)
            notes.append(InputNote(pitch=pitches[token - 1], onset_beats=onset,
                                   duration_beats=duration, velocity=velocity))
            lineage.append({"note_index": len(notes) - 1, "token_index": index,
                            "motif_index": index // 4, "token": token})
        return GeneratedSequence(notes=notes, tempo_bpm=request.tempo_bpm, source={
            "kind": "frozen_qcbm_inference",
            "checkpoint_payload_sha256": self.payload_sha256,
            "original_checkpoint_sha256": self.original_checkpoint_sha256,
            "quantum_backend": "Qiskit Statevector simulator",
            "backend_submissions": "0",
            "decoder": "instrument_register_and_phrasing_v1",
            "decoder_instrument": request.instrument,
            "decoder_options": options.model_dump_json(),
            "raw_token_sequence": json.dumps(tokens),
            "sampled_motif_bitstrings": json.dumps([format(int(n), "012b") for n in outcomes]),
            "decoded_token_map": json.dumps(lineage),
            "adaptation": "Classical note decoding; instruments reuse the same frozen checkpoint",
        })
