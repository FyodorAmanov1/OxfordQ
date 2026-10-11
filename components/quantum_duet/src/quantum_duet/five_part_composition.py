"""Compact, source-preserving rules orchestration; stdlib only, zero executions.

Thematic return/rhythm: orchestrator.composition.planner.local_plan/_steps.
Octave placement: orchestrator.composition.compiler._place.
Phrase dynamics: orchestrator.composition.performer._arc/RulePerformer.
This explicit extraction uses fixed C-major harmony rather than POP909/music21.
It is creative classical arrangement, not raw measurement evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
from collections import Counter

SCHEMA = "qm.five-part-composition.v1"
SOURCE_SCHEMA = "qm.fresh-qcbm-source.v1"
SCALE = (0, 2, 4, 5, 7, 9, 11)
# Concert pitch and zero-based GM programs. Conservative limits are extracted
# from orchestrator/instruments.py; single monophonic lines except the piano.
INSTRUMENTS = (
    ("Flute", "flute", 60, 96, 77, 73),
    ("Clarinet", "clarinet", 50, 94, 68, 71),
    ("Violin", "violin", 55, 100, 72, 48),
    ("Cello", "cello", 36, 81, 48, 42),
    ("Piano", "piano", 21, 108, 60, 0),
)
MOTIF_ORDER = ((0, 1, 0, 2), (0, 1, 0, 3), (2, 3, 2, 1), (0, 1, 2, 0))
RHYTHMS = ((1, 1, 1, 1), (.5, .5, 1, 2), (1, .5, .5, 2), (.5, 1.5, 1, 1))
CHORDS = ((0, 4, 7), (5, 9, 0), (7, 11, 2), (0, 4, 7),
          (0, 4, 7), (5, 9, 0), (7, 11, 2), (0, 4, 7),
          (9, 0, 4), (2, 5, 9), (7, 11, 2), (7, 11, 2),
          (0, 4, 7), (5, 9, 0), (7, 11, 2), (0, 4, 7))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_source(source):
    if source.get("contract_version") != SOURCE_SCHEMA or not source.get("run_id"):
        raise ValueError("Require a completed fresh QCBM source envelope")
    histogram = source["histogram_y12bit"]
    if not histogram or any(len(b) != 12 or set(b) - {"0", "1"} or
                            type(n) is not int or n <= 0 for b, n in histogram.items()):
        raise ValueError("Invalid complete 12-bit histogram")
    if digest(canonical(histogram)) != source["histogram_sha256"]:
        raise ValueError("Histogram identity mismatch")
    occurrences = source["source_occurrences"]
    if len(occurrences) != sum(histogram.values()) or len(occurrences) < 20:
        raise ValueError("Need all returned shots and at least twenty occurrences")
    ids = [o["occurrence_id"] for o in occurrences]
    if len(set(ids)) != len(ids) or Counter(o["bitstring"] for o in occurrences) != histogram:
        raise ValueError("Occurrences must preserve every measured draw, including duplicates")
    for occurrence in occurrences:
        expected = [(int(occurrence["bitstring"], 2) >> (3 * i)) & 7 for i in range(4)]
        if occurrence["tokens"] != expected or occurrence.get("chronological") is not False:
            raise ValueError("Invalid token decoding or false chronological label")
    parts = source["instrument_sources"]
    if [p["instrument"] for p in parts] != [p[0] for p in INSTRUMENTS]:
        raise ValueError("Require the five agreed instrument assignments")
    assigned = [o for p in parts for o in p["motif_occurrence_ids"]]
    if any(len(p["motif_occurrence_ids"]) != 4 for p in parts) or len(set(assigned)) != 20:
        raise ValueError("Require twenty distinct assigned measured occurrences")
    if (set(assigned) - set(ids) or set(source["unused_occurrence_ids"]) != set(ids) - set(assigned)
            or len(source["unused_occurrence_ids"]) != len(ids)-20):
        raise ValueError("Unknown assignment or missing unused occurrences")
    model = source["models"]
    if model.get("qcbm_parameters") != 84 or model.get("qcbm_qubits") != 12 or not model.get("same_checkpoint_all_instruments"):
        raise ValueError("Require the unchanged shared 12-qubit/84-parameter checkpoint")


def _place(pc, low, high, target, previous=None):
    choices = [pitch for pitch in range(low, high + 1) if pitch % 12 == pc % 12]
    return min(choices, key=lambda p: abs(p-target) + (.25*abs(p-previous) if previous is not None else 0))


def compose(source):
    """Arrange one existing source; preserve exact text when passed JSON text.

    No imports of Qiskit, NumPy, music21, samplers, providers or desktop audio.
    All four source tokens, including rests, are retained in each motif reuse.
    """
    source_text = source if isinstance(source, str) else canonical(source)
    source = json.loads(source_text)
    _validate_source(source)
    occurrences = {o["occurrence_id"]: o for o in source["source_occurrences"]}
    tracks = []
    for channel, (name, instrument, low, high, center, program) in enumerate(INSTRUMENTS):
        assignment = source["instrument_sources"][channel]["motif_occurrence_ids"]
        events, previous = [], None
        for bar in range(16):
            section, phase = divmod(bar, 4)
            motif_id = assignment[MOTIF_ORDER[section][phase]]
            motif = occurrences[motif_id]
            rhythm = RHYTHMS[(section+phase) % 4]
            if name == "Cello":
                rhythm = (1, 1, 1, 1) if section != 2 else (1.5, .5, 1, 1)
            cursor = bar * 4
            for slot, (token, step) in enumerate(zip(motif["tokens"], rhythm)):
                rest = token == 0
                pc = None if rest else SCALE[token-1]
                transforms = ["classical_token_to_C_major", "classical_theme_repetition",
                              "classical_rhythm_variation", "classical_octave_placement",
                              "classical_note_length", "classical_phrase_dynamics"]
                if not rest and name in ("Piano", "Cello"):
                    pc = CHORDS[bar][slot % 3] if name == "Cello" else min(
                        CHORDS[bar], key=lambda c: min((c-pc) % 12, (pc-c) % 12))
                    transforms.append("classical_harmonic_projection")
                if bar == 15 and slot == 3 and not rest:
                    pc = 0
                    transforms.append("classical_final_tonic_cadence")
                phrase_position = (phase*4 + cursor-bar*4)/16
                arc = math.sin(math.pi * phrase_position)
                velocity = round((76 if name == "Flute" else 59) + 10*arc + (6 if section == 2 else 0))
                gate = .94 if name in ("Violin", "Cello") else .84
                duration = step * gate
                if phase == 3 and slot == 3 and bar != 15:
                    duration = min(duration, step*.65)
                    transforms.append("classical_phrase_breath")
                target = center + (12 if section == 2 and name == "Flute" else 0)
                pitch = None if rest else _place(pc, low, high, target, previous)
                if pitch is not None:
                    previous = pitch
                # Piano triads are explicitly classical accompaniment derived
                # from the measured source slot; source rests never become notes.
                pitches = [pitch]
                if name == "Piano" and not rest:
                    pitches = sorted({_place(c, low, high, center) for c in CHORDS[bar]})
                    transforms.append("classical_chord_voicing")
                for voice, value in enumerate(pitches):
                    events.append({
                        "event_id": f"{source['run_id']}/composition/{instrument}/b{bar:02}/s{slot}/v{voice}",
                        "run_id": source["run_id"], "bar_index": bar, "section": ("A", "A-prime", "B", "A-double-prime")[section],
                        "pitch_midi": value, "onset_beats": cursor,
                        "duration_beats": round(duration, 6), "velocity": velocity,
                        "rest": rest, "muted": False, "source_token": token,
                        "source_occurrence_id": motif_id, "source_token_index": slot,
                        "source_event_ids": [f"{motif_id}/token/{slot}"],
                        "measured_occurrence_reused": True,
                        "data_status": "CLASSICAL ARRANGEMENT OF MEASURED SOURCE",
                        "transformation_lineage": transforms.copy(),
                    })
                cursor += step
        tracks.append({"instrument": name, "instrument_id": instrument,
                       "channel": channel, "program": program, "register_midi": [low, high], "events": events})
    result = {"schema_version": SCHEMA, "run_id": source["run_id"], "mode": "creative-composition",
              "execution": copy.deepcopy(source["execution"]), "models": copy.deepcopy(source["models"]),
              "source": source, "source_json_text": source_text,
              "source_json_sha256": digest(source_text), "source_canonical_sha256": digest(canonical(source)),
              "tempo_bpm": 120, "metre": [4, 4], "bars": 16, "duration_beats": 64,
              "duration_seconds": 32, "ppq": 480, "tracks": tracks,
              "arrangement": {"backend": "classical rules", "additional_backend_submissions": 0,
                  "harmony": "C F G C / C F G C / Am Dm G G / C F G C",
                  "form": "A-A-prime-B-A-double-prime", "motif_order": [list(x) for x in MOTIF_ORDER],
                  "scope": "Explicit compact extraction; not the full desktop orchestrator"},
              "export": {"midi_format": 1, "midi_tracks": 6, "midi_filename": "fresh-five-part-composition.mid"},
              "warnings": ["All five instruments use one frozen QCBM checkpoint, not five trained models.",
                           "Theme reuse, harmony, cadence, register, rhythm and dynamics are classical.",
                           "Histogram occurrences are reconstructed, not chronological shot memory.",
                           "No CHSH statistics apply to these composition notes.",
                           "Musical quality and instrument realism require human listening; no quality verdict is claimed."],
              "errors": []}
    for track in tracks:
        if all(event["rest"] for event in track["events"]):
            result["warnings"].append(f"{track['instrument']}: all assigned tokens are rests; this part remains silent without resampling.")
    validate_composition(result)
    return result


def validate_composition(result):
    if result.get("schema_version") != SCHEMA or result["duration_beats"] != 64 or result["tempo_bpm"] != 120:
        raise ValueError("Composition identity/duration mismatch")
    if digest(result["source_json_text"]) != result["source_json_sha256"] or json.loads(result["source_json_text"]) != result["source"]:
        raise ValueError("Immutable source identity mismatch")
    if (digest(canonical(result["source"])) != result["source_canonical_sha256"] or
            result["execution"] != result["source"]["execution"] or
            result["models"] != result["source"]["models"] or result["run_id"] != result["source"]["run_id"]):
        raise ValueError("Source execution/model provenance changed")
    _validate_source(result["source"])
    source_map = {o["occurrence_id"]: o for o in result["source"]["source_occurrences"]}
    ids = set()
    if len(result["tracks"]) != 5:
        raise ValueError("Require five parts")
    for channel, (track, spec) in enumerate(zip(result["tracks"], INSTRUMENTS)):
        if (track["instrument"] != spec[0] or track["instrument_id"] != spec[1]
                or track["channel"] != channel or track["program"] != spec[5]):
            raise ValueError("Instrument identity mismatch")
        assigned = set(result["source"]["instrument_sources"][channel]["motif_occurrence_ids"])
        for event in track["events"]:
            if event["event_id"] in ids:
                raise ValueError("Duplicate event identity")
            ids.add(event["event_id"])
            original = source_map[event["source_occurrence_id"]]
            if original["occurrence_id"] not in assigned or event["run_id"] != result["run_id"]:
                raise ValueError("Cross-instrument/run source identity mismatch")
            slot = event["source_token_index"]
            if event["source_token"] != original["tokens"][slot] or event["rest"] != (original["tokens"][slot] == 0):
                raise ValueError("Source token/rest changed")
            if event["source_event_ids"] != [f"{original['occurrence_id']}/token/{slot}"]:
                raise ValueError("Source event lineage changed")
            onset, duration = event["onset_beats"], event["duration_beats"]
            if not math.isfinite(onset+duration) or onset < 0 or duration <= 0 or onset+duration > 64:
                raise ValueError("Invalid event timing")
            pitch = event["pitch_midi"]
            if (pitch is None) != event["rest"] or (pitch is not None and (type(pitch) is not int or not spec[2] <= pitch <= spec[3])):
                raise ValueError("Invalid note/register/rest")
            if type(event["velocity"]) is not int or not 1 <= event["velocity"] <= 127:
                raise ValueError("Invalid velocity")
            if not event["transformation_lineage"] or any(not s.startswith("classical_") for s in event["transformation_lineage"]):
                raise ValueError("Arrangement must be explicitly classical")


def _vlq(value):
    output = [value & 127]
    while value := value >> 7:
        output.insert(0, 128 | (value & 127))
    return bytes(output)


def midi_bytes(result):
    """Standard MIDI type 1: conductor + five instrument tracks, exact 32 s EOT."""
    validate_composition(result)
    end = 64 * 480
    conductor = b"\x00\xff\x51\x03\x07\xa1\x20\x00\xff\x58\x04\x04\x02\x18\x08" + _vlq(end) + b"\xff\x2f\x00"
    chunks = [b"MTrk" + struct.pack(">I", len(conductor)) + conductor]
    for track in result["tracks"]:
        channel = track["channel"]
        name = track["instrument"].encode("ascii")
        body = b"\x00\xff\x03" + _vlq(len(name)) + name + bytes([0, 192+channel, track["program"]])
        edges = []
        for event in track["events"]:
            if event["rest"] or event["muted"]:
                continue
            start = round(event["onset_beats"]*480)
            stop = start + max(1, round(event["duration_beats"]*480))
            edges.extend([(start, 1, event["pitch_midi"], event["velocity"]), (stop, 0, event["pitch_midi"], 0)])
        tick = 0
        for at, kind, pitch, velocity in sorted(edges):
            body += _vlq(at-tick) + bytes([(144 if kind else 128)+channel, pitch, velocity])
            tick = at
        body += _vlq(end-tick) + b"\xff\x2f\x00"
        chunks.append(b"MTrk" + struct.pack(">I", len(body)) + body)
    return b"MThd" + struct.pack(">IHHH", 6, 1, 6, 480) + b"".join(chunks)
