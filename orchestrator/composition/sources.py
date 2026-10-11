"""Frozen inference bank; optional caller-owned registries remain replaceable."""
import json
from music21 import harmony
from orchestrator import GenerationJob, GenerationRegistry, OrchestrationConfig
from orchestrator.midi_io import import_parts
from orchestrator.theory import parse_key
from .models import SourceBank, SourceEvent, SourceMotif, SourceChord

STYLE_KEYS = {"bach": "D minor", "mozart": "C major",
              "debussy": "E- major", "rachmaninoff": "C minor"}


def generate_source_bank(request, *, registry=None):
    from quantum_models import QCBMInstrumentGenerator, Pop909QuantumHarmony
    key = request.key or STYLE_KEYS[request.style]
    default_registry = registry is None
    if default_registry:
        registry = GenerationRegistry()
        registry.register("frozen-qcbm", QCBMInstrumentGenerator(), instruments=request.instruments)
    jobs = [GenerationJob(id=instrument, instrument=instrument,
            seed=request.seed + index * 101,
            options={"key": key, **({"stride_beats": 1} if default_registry else {})})
            for index, instrument in enumerate(request.instruments)]
    manifest = registry.generate_parts(jobs, request.lead_track, bars=16, tempo_bpm=120)
    normalised, _ = import_parts(manifest.parts, request.lead_track,
        OrchestrationConfig(bars=16, tempo_bpm=120, backend="rules", render_audio=False))
    events, motifs = [], []
    for part, spec in zip(normalised.parts, manifest.parts):
        if "raw_token_sequence" in spec.source and "decoded_token_map" in spec.source:
            tokens = json.loads(spec.source["raw_token_sequence"])
            decoded = {item["token_index"]: part.notes[item["note_index"]].pitch
                       for item in json.loads(spec.source["decoded_token_map"])}
            source = [SourceEvent(id=f"{part.id}/token/{i}", pitch=decoded.get(i),
                      source_part=part.id, model="qcbm" if spec.source.get("kind") == "frozen_qcbm_inference" else "external", token_index=i)
                      for i, _ in enumerate(tokens)]
        else:
            source = [SourceEvent(id=n.source_id, pitch=n.pitch,
                      source_part=part.id, model="external") for n in part.notes]
        if not source or not any(e.pitch is not None for e in source):
            raise ValueError(f"{part.id}: source bank requires sounding notes")
        events.extend(source)
        for index in range(0, len(source), 4):
            motifs.append(SourceMotif(id=f"{part.id}/motif/{index // 4}",
                source_part=part.id, events=[e.id for e in source[index:index + 4]]))
        # Cadential sustained tones are selections of actual source events.
        tonic = parse_key(key).tonic.pitchClass
        candidate = next((e for e in source if e.pitch is not None and e.pitch % 12 == tonic),
                         next(e for e in source if e.pitch is not None))
        motifs.append(SourceMotif(id=f"{part.id}/arrival", source_part=part.id, events=[candidate.id]))
    tonality = parse_key(key)
    major = tonality if tonality.mode == "major" else tonality.relative
    harmony_key = major.tonic.name + " major"
    progression = Pop909QuantumHarmony.from_json().generate(
        64, key=harmony_key, seed=request.seed + 10007)
    chords = []
    for index, symbol in enumerate(progression.chord_symbols):
        chord = harmony.ChordSymbol(symbol)
        root = chord.root().pitchClass
        notes = [SourceEvent(id=f"pop909/chord/{index}/{j}",
                 pitch=48 + root + (pitch.pitchClass - root) % 12,
                 source_part="pop909", model="pop909")
                 for j, pitch in enumerate(chord.pitches)]
        events.extend(notes)
        chords.append(SourceChord(id=f"pop909/chord/{index}", symbol=symbol,
                                  events=[note.id for note in notes]))
    return SourceBank(key=key, events=events, motifs=motifs, chords=chords,
        provenance={"instrument_sources": {spec.id: spec.source for spec in manifest.parts},
                    "harmony": progression.to_dict(), "harmony_training_key": harmony_key,
                    "minor_key_policy": "Relative-major POP909 material; classical selection establishes the minor centre",
                    "execution": "Local frozen inference; no physical hardware or provider submissions" if default_registry else
                        "Caller-owned instrument registry; see instrument metadata. POP909 harmony uses local Statevector inference",
                    "training_performed_by_source_bank_builder": False})
