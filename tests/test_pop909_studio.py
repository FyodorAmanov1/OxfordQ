import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from qiskit.providers.basic_provider import BasicSimulator

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pop909_studio_inference", ROOT / "pop909_qollab_studio_v2/quantum_harmony/inference.py")
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    studio.clear_cache()
    monkeypatch.setattr(studio, "MODEL_PATH", ROOT / "pop909_qollab_studio_v2/data/models.json")
    yield
    studio.clear_cache()


def test_local_progression_and_cache_preserve_counts():
    backend = BasicSimulator()
    backend.set_options(seed_simulator=123)
    first = json.loads(studio.generate_progression(backend, bars=8, shots=32, seed=1))
    second = json.loads(studio.generate_progression(backend, bars=8, shots=32, seed=1))
    assert first["resolved_sequence"] == second["resolved_sequence"]
    assert first["execution"]["new_quantum_jobs"] > 0
    assert second["execution"]["new_quantum_jobs"] == 0
    assert second["execution"]["cache_hits"] >= 7
    assert len(first["model"]["checkpoint_payload_sha256"]) == 64
    for step in first["steps"]:
        assert sum(step["coarse"]["counts"]) == 32
        assert len(step["coarse"]["parameter_sha256"]) == 64


@pytest.mark.parametrize("counts,success", [
    ({"000": 32.0}, True), ({"000": True}, True),
    ({"000": -1, "001": 33}, True), ({"000": 31}, True),
    ({"0x0": 32}, True), ({0: 32}, True), ({"000": 32}, False),
])
def test_invalid_backend_counts_fail_before_cache(monkeypatch, counts, success):
    monkeypatch.setattr(studio, "transpile", lambda circuit, backend, **kwargs: circuit)
    backend = Mock()
    backend.run.return_value.result.return_value = SimpleNamespace(
        success=success, get_counts=lambda: counts)
    with pytest.raises(RuntimeError):
        studio._run_one(backend, np.zeros(3), 3, studio.COARSE, 32, "coarse", "I")
    assert not studio._CACHE["coarse"]


def test_cache_includes_weights_and_is_immutable():
    backend = BasicSimulator()
    theta = np.zeros(3)
    a, new = studio._run_one(backend, theta, 3, studio.COARSE, 32, "coarse", "I")
    assert new
    a["counts"][0] = -999
    b, new = studio._run_one(backend, theta, 3, studio.COARSE, 32, "coarse", "I")
    assert not new and b["counts"][0] == 32
    _, new = studio._run_one(backend, theta + 0.1, 3, studio.COARSE, 32, "coarse", "I")
    assert new


def test_unknown_physical_backend_rejected():
    with pytest.raises(RuntimeError):
        studio._validate_simulator(SimpleNamespace())
    with pytest.raises(RuntimeError):
        studio._validate_simulator(SimpleNamespace(
            configuration=lambda: SimpleNamespace(simulator=False)))
