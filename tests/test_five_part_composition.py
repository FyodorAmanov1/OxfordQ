"""Focused compact-orchestrator checks; no provider submissions or audio stack."""
import copy
import io
import json
from collections import Counter

import mido
import pytest

from quantum_duet.five_part_composition import (
    INSTRUMENTS, MOTIF_ORDER, canonical, compose, digest, midi_bytes, validate_composition,
)


def source_fixture():
    # Deliberately include duplicate bitstrings and rests; each occurrence stays distinct.
    numbers = [int("001010011100", 2), int("000101110111", 2), int("111000010101", 2),
               int("100011000001", 2)] * 8
    ids = [f"test-run/m{i:04}" for i in range(32)]
    histogram = dict(Counter(format(n, "012b") for n in numbers))
    return {"contract_version": "qm.fresh-qcbm-source.v1", "run_id": "test-run",
            "models": {"qcbm_parameters": 84, "qcbm_qubits": 12,
                       "same_checkpoint_all_instruments": True, "melody_checkpoint_sha256": "f"*64},
            "execution": {"backend_name": "test-only", "data_status": "mock", "backend_run_calls": 1},
            "histogram_y12bit": histogram, "histogram_sha256": digest(canonical(histogram)),
            "source_occurrences": [{"occurrence_id": ids[i], "reconstructed_index": i,
                "bitstring": format(n, "012b"), "tokens": [(n >> (3*j)) & 7 for j in range(4)],
                "measured_draw": True, "chronological": False} for i, n in enumerate(numbers)],
            "instrument_sources": [{"instrument": spec[0], "instrument_id": spec[1],
                "motif_occurrence_ids": ids[i*4:i*4+4]} for i, spec in enumerate(INSTRUMENTS)],
            "unused_occurrence_ids": ids[20:]}


def test_reproducible_exact_source_text_and_input_immutable():
    source = source_fixture()
    before = copy.deepcopy(source)
    text = json.dumps(source, indent=2) + "\n"
    first = compose(text)
    assert first == compose(text)
    assert source == before
    assert first["source_json_text"] == text
    assert first["source_json_sha256"] == digest(text)
    assert first["source"] == before
    assert first["arrangement"]["additional_backend_submissions"] == 0
    assert "statistics" not in first and "statistics" not in first["source"]


def test_duration_registers_and_all_five_parts():
    result = compose(source_fixture())
    assert (result["bars"], result["duration_beats"], result["duration_seconds"], result["tempo_bpm"]) == (16, 64, 32, 120)
    assert [t["instrument"] for t in result["tracks"]] == [s[0] for s in INSTRUMENTS]
    assert {t["channel"] for t in result["tracks"]} == set(range(5))
    assert [t["program"] for t in result["tracks"]] == [73, 71, 40, 42, 0]
    assert all(e["onset_beats"]+e["duration_beats"] <= 64 for t in result["tracks"] for e in t["events"])
    assert all(s[2] <= e["pitch_midi"] <= s[3] for t, s in zip(result["tracks"], INSTRUMENTS)
               for e in t["events"] if not e["rest"])


def test_every_assigned_source_used_and_original_32_shots_preserved():
    result = compose(source_fixture())
    assigned = {o for p in result["source"]["instrument_sources"] for o in p["motif_occurrence_ids"]}
    assert {e["source_occurrence_id"] for t in result["tracks"] for e in t["events"]} == assigned
    assert len(result["source"]["source_occurrences"]) == 32
    assert len(result["source"]["unused_occurrence_ids"]) == 12
    assert len({o["occurrence_id"] for o in result["source"]["source_occurrences"]}) == 32


def test_reused_motifs_retain_all_four_tokens_and_rests():
    result = compose(source_fixture())
    originals = {o["occurrence_id"]: o for o in result["source"]["source_occurrences"]}
    for track in result["tracks"]:
        for bar in range(16):
            events = [e for e in track["events"] if e["bar_index"] == bar]
            assert {e["source_token_index"] for e in events} == set(range(4))
            occurrence = originals[events[0]["source_occurrence_id"]]
            for event in events:
                assert event["source_token"] == occurrence["tokens"][event["source_token_index"]]
                assert event["rest"] == (event["source_token"] == 0)
                assert (event["pitch_midi"] is None) == event["rest"]
                assert all(t.startswith("classical_") for t in event["transformation_lineage"])


def test_theme_return_and_distinct_classical_harmony():
    result = compose(source_fixture())
    flute = result["tracks"][0]["events"]
    assert flute[0]["source_occurrence_id"] == next(e for e in flute if e["bar_index"] == 12)["source_occurrence_id"]
    assert len(MOTIF_ORDER) == 4
    assert any("classical_harmonic_projection" in e["transformation_lineage"] for e in result["tracks"][3]["events"])
    assert any("classical_chord_voicing" in e["transformation_lineage"] for e in result["tracks"][4]["events"])


def test_midi_tracks_programs_duration_and_notes_match_score():
    result = compose(source_fixture())
    midi = mido.MidiFile(file=io.BytesIO(midi_bytes(result)))
    assert midi.type == 1 and len(midi.tracks) == 6 and midi.ticks_per_beat == 480
    assert midi.length == pytest.approx(32)
    for midi_track, part in zip(midi.tracks[1:], result["tracks"]):
        assert sum(m.time for m in midi_track) == 64*480
        assert [m.program for m in midi_track if m.type == "program_change"] == [part["program"]]
        events = sorted((round(e["onset_beats"]*480), e["pitch_midi"], e["velocity"])
                        for e in part["events"] if not e["rest"])
        tick, actual, sounding = 0, [], Counter()
        for message in midi_track:
            tick += message.time
            if message.type == "note_on" and message.velocity:
                actual.append((tick, message.note, message.velocity))
                sounding[message.note] += 1
                assert sounding[message.note] == 1
            elif message.type == "note_off":
                sounding[message.note] -= 1
                assert sounding[message.note] == 0
        assert sorted(actual) == events
        assert not any(sounding.values())


@pytest.mark.parametrize("mutation", ["tokens", "histogram", "duplicate", "unused"])
def test_corrupt_sources_rejected(mutation):
    source = source_fixture()
    if mutation == "tokens":
        source["source_occurrences"][0]["tokens"][0] ^= 1
    elif mutation == "histogram":
        source["histogram_sha256"] = "0"*64
    elif mutation == "duplicate":
        source["instrument_sources"][1]["motif_occurrence_ids"][0] = source["instrument_sources"][0]["motif_occurrence_ids"][0]
    else:
        source["unused_occurrence_ids"] = []
    with pytest.raises(ValueError):
        compose(source)


def test_changed_source_or_lineage_rejected():
    result = compose(source_fixture())
    result["tracks"][0]["events"][0]["source_event_ids"] = ["unknown"]
    with pytest.raises(ValueError, match="lineage"):
        validate_composition(result)
    result = compose(source_fixture())
    result["source"]["execution"]["backend_name"] = "invented"
    with pytest.raises(ValueError, match="identity"):
        validate_composition(result)


def test_all_rest_source_not_replaced_or_resampled():
    source = source_fixture()
    source["histogram_y12bit"] = {"000000000000": 32}
    source["histogram_sha256"] = digest(canonical(source["histogram_y12bit"]))
    for occurrence in source["source_occurrences"]:
        occurrence.update(bitstring="000000000000", tokens=[0, 0, 0, 0])
    result = compose(source)
    assert all(e["rest"] for t in result["tracks"] for e in t["events"])
    assert mido.MidiFile(file=io.BytesIO(midi_bytes(result))).length == pytest.approx(32)
