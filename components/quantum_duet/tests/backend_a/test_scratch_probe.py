"""Exercise the standalone platform reproduction without network access."""
import importlib.util
import json
from pathlib import Path

from qiskit.providers.basic_provider import BasicSimulator


def module():
    spec = importlib.util.spec_from_file_location('scratch_probe', Path(__file__).parent / 'fixtures/probe.py')
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    return probe


def test_scratch_supplied_backend_one_32_shot_job(monkeypatch):
    backend = BasicSimulator()
    original = backend.run
    calls = []
    def run(circuit, **kwargs):
        calls.append((circuit, kwargs))
        return original(circuit, **kwargs)
    monkeypatch.setattr(backend, 'run', run)
    report = json.loads(module().probe_json(backend))
    assert report['status'] == 'completed' and report['job_id']
    assert len(calls) == report['backend_run_calls'] == 1
    assert calls[0][0].name == 'bridge_probe' and calls[0][1] == {'shots': 32}
    assert sum(report['counts'].values()) == 32


def test_scratch_rejection_has_no_counts_or_retry(monkeypatch):
    backend = BasicSimulator()
    calls = []
    def reject(*args, **kwargs):
        calls.append(1)
        raise RuntimeError('secret-token-must-not-escape')
    monkeypatch.setattr(backend, 'run', reject)
    raw = module().probe_json(backend)
    report = json.loads(raw)
    assert report['status'] == 'failed' and report['stage'] == 'submit'
    assert len(calls) == 1 and report['counts'] is report['job_id'] is None
    assert 'secret-token' not in raw
