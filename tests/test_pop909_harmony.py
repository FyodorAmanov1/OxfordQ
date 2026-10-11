import json
from pathlib import Path

import numpy as np
import pytest
from music21 import harmony

from quantum_models import Pop909QuantumHarmony, label_to_chord_symbol


def test_packaged_checkpoint_reproducible_and_labelled():
    model = Pop909QuantumHarmony.from_json()
    first = model.generate(16, seed=42).to_dict()
    assert first == model.generate(16, seed=42).to_dict()
    assert len(first["chord_symbols"]) == 16
    assert first["source"]["quantum_backend"] == "Qiskit Statevector simulator"
    assert len(first["source"]["checkpoint_payload_sha256"]) == 64
    assert model.coarse_depth > 0 and model.resolver_depth > 0
    for symbol in first["chord_symbols"]:
        assert harmony.ChordSymbol(symbol).pitches


@pytest.mark.parametrize("key", ["C", "D", "E", "F", "G", "A", "B", "D-", "E-", "G-", "A-", "B-"])
def test_major_keys_and_chromatic_spelling(key):
    for label in ["I", "ii", "iii", "IV", "V", "vi", "vii°", "bVI:maj", "bVII:maj", "#IV:hdim"]:
        assert harmony.ChordSymbol(label_to_chord_symbol(label, key + " major")).pitches


def test_npz_compatibility_preserves_weights(tmp_path):
    model = Pop909QuantumHarmony.from_json()
    coarse, resolver = tmp_path / "coarse.npz", tmp_path / "resolver.npz"
    np.savez(coarse, **{f"theta_{i}": theta for i, theta in enumerate(model.coarse_models.values())})
    np.savez(resolver, **{f"theta_{i}": theta for i, theta in enumerate(model.resolver_models.values())})
    loaded = Pop909QuantumHarmony(coarse, resolver)
    assert loaded.generate(12, seed=9).coarse_sequence == model.generate(12, seed=9).coarse_sequence


def test_checkpoint_validation(tmp_path):
    from importlib.resources import files
    payload = json.loads(files("quantum_models").joinpath("data/pop909_models.json").read_text(encoding="utf-8"))
    payload["coarse_theta"]["I"][0] = float("nan")
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        Pop909QuantumHarmony.from_json(path)
    with pytest.raises(ValueError, match="major"):
        label_to_chord_symbol("I", "A minor")
