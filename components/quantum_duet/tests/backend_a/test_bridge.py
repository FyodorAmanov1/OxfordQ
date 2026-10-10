import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator

from quantum_duet.duet_quantum import REFERENCE_ANGLES, decode_outcome, run_batch
from quantum_duet.integration import generate_take
from quantum_duet.probe import probe, probe_json

ASSETS = Path(__file__).resolve().parents[2] / 'src/quantum_duet/data'


class Backend(BasicSimulator):
    def __init__(self, transform=None, failure=None):
        super().__init__()
        self.calls = []
        self.transform, self.failure = transform, failure
        self.set_options(seed_simulator=32001)

    def run(self, circuits, **options):
        self.calls.append((circuits, options))
        if self.failure:
            raise self.failure
        job = super().run(circuits, **options)
        if self.transform:
            result = self.transform(job.result())
            return SimpleNamespace(job_id=job.job_id, result=lambda: result)
        return job


def test_single_probe_preserves_object_input_and_ba_counts():
    backend = Backend()
    result = probe(backend)
    assert len(backend.calls) == 1
    circuit, options = backend.calls[0]
    assert isinstance(circuit, QuantumCircuit)
    assert circuit.name == 'bridge_probe'
    assert circuit.num_qubits == circuit.num_clbits == 2
    assert options == {'shots': 32}
    assert sum(result['counts'].values()) == 32
    assert set(result['counts']) <= {'00', '11'}
    assert result['job_id'] and result['backend_run_calls'] == 1
    assert decode_outcome('01') == (1, 0)
    assert decode_outcome('10') == (0, 1)


@pytest.mark.parametrize('shots', [True, 0, 15, 4097, 32.0])
def test_probe_invalid_allocation_never_submits(shots):
    backend = Backend()
    with pytest.raises(ValueError):
        probe(backend, shots)
    assert backend.calls == []


def test_probe_hardware_and_advertised_limits_never_submit():
    backend = Backend()
    backend.configuration = lambda: SimpleNamespace(simulator=False)
    with pytest.raises(RuntimeError, match='Physical hardware'):
        probe(backend)
    assert not backend.calls
    backend.configuration = lambda: SimpleNamespace(simulator=True, max_shots=16)
    with pytest.raises(ValueError, match='shots'):
        probe(backend)
    assert not backend.calls


def test_options_validator_leaves_backend_unchanged():
    backend = Backend()
    before = copy.copy(backend.options)
    backend.options.set_validator('shots', (16, 32))
    with pytest.raises(ValueError):
        probe(backend, 64)
    assert backend.options.shots == before.shots
    assert not backend.calls


def test_ionq_hardware_subclass_outside_provider_module_is_blocked():
    class IonQMarker:
        pass
    IonQMarker.__module__ = 'qiskit_ionq.ionq_backend'
    class PlatformBackend(Backend, IonQMarker):
        pass
    backend = PlatformBackend()
    backend.name = 'ionq_qpu.aria-1'
    with pytest.raises(RuntimeError, match='IonQ physical/unknown'):
        probe(backend)
    assert not backend.calls


def test_submit_error_propagates_once_and_report_redacts():
    failure = RuntimeError('private-url?token=SECRET')
    failure.status_code = 400
    backend = Backend(failure=failure)
    with pytest.raises(RuntimeError) as caught:
        probe(backend)
    assert caught.value is failure and len(backend.calls) == 1
    backend = Backend(failure=failure)
    raw = probe_json(backend)
    report = json.loads(raw)
    assert len(backend.calls) == report['backend_run_calls'] == 1
    assert report['status'] == 'failed' and report['result'] is None
    assert report['job_id'] is None
    assert report['errors'][0]['stage'] == 'submit'
    assert report['errors'][0]['http_status'] == 400
    assert 'SECRET' not in raw and 'private-url' not in raw
    assert report['fallback']['used'] is False


def test_failed_preflight_report_has_zero_calls():
    backend = Backend()
    report = json.loads(probe_json(backend, 0))
    assert report['status'] == 'failed'
    assert report['stage'] == 'preflight'
    assert report['backend_run_calls'] == 0 and not backend.calls
    assert report['result'] is None and report['job_id'] is None


def test_result_failure_retains_accepted_job_without_counts():
    def fail(result):
        result.success = False
        return result
    backend = Backend(transform=fail)
    report = json.loads(probe_json(backend))
    assert report['status'] == 'failed' and report['result'] is None
    assert report['job_id'] and len(backend.calls) == 1
    assert report['stage'] == 'validate_result'


def test_success_report_does_not_claim_platform_verification():
    report = json.loads(probe_json(Backend()))
    assert report['status'] == 'completed' and report['errors'] == []
    assert report['free_selection_verified'] is False
    assert 'unknown' in report['api_path']
    assert report['versions']['qiskit'] == '2.5.2'
    assert report['observed_utc'] <= report['finished_utc']


@pytest.mark.parametrize('histogram', [
    {'00': 32.0}, {'00': True}, {'00': -1, '11': 33},
    {'0x0': 32}, {0: 32}, {'0': 32}, {'000': 32}, {'00': 31}, [],
])
@pytest.mark.parametrize('single', [True, False])
def test_invalid_provider_counts_fail_without_retry(histogram, single):
    def corrupt(result):
        result.get_counts = lambda index: histogram
        return result
    backend = Backend(transform=corrupt)
    with pytest.raises(RuntimeError):
        probe(backend) if single else run_batch(backend, REFERENCE_ANGLES, 32)
    assert len(backend.calls) == 1


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'unknown', 'incomplete', 'unsuccessful'])
def test_provider_labels_and_status_are_required(problem):
    def corrupt(result):
        if problem == 'missing':
            result.results[0].header = {}
        elif problem == 'duplicate':
            result.results[0].header['name'] = result.results[1].header['name']
        elif problem == 'unknown':
            result.results[0].header['name'] = 'unknown'
        elif problem == 'incomplete':
            result.results.pop()
        else:
            result.results[0].success = False
        return result
    backend = Backend(transform=corrupt)
    with pytest.raises(RuntimeError):
        run_batch(backend, REFERENCE_ANGLES, 32)
    assert len(backend.calls) == 1


def test_permuted_results_match_names_and_numpy_integer_allocations():
    def reverse(result):
        result.results.reverse()
        get_counts = result.get_counts
        result.get_counts = lambda index: {k: np.int64(v) for k, v in get_counts(index).items()}
        return result
    backend = Backend(transform=reverse)
    batch = run_batch(backend, REFERENCE_ANGLES, 32)
    assert len(backend.calls) == 1
    assert [row['result_index'] for row in batch['experiments']] == [3, 2, 1, 0]
    assert [row['name'] for row in batch['experiments']] == ['duet_xy_00', 'duet_xy_01', 'duet_xy_10', 'duet_xy_11']
    assert all(type(v) is int for row in batch['experiments'] for v in row['counts'].values())


@pytest.mark.parametrize('mode', ['four-recorded', 'five-live'])
def test_generate_take_preserves_one_batch_and_provenance(mode):
    backend = Backend()
    take = json.loads(generate_take(backend, 32, mode, 'ideal-local-development', 32002, asset_dir=ASSETS))
    assert len(backend.calls) == take['execution']['backend_run_calls'] == 1
    assert take['execution']['circuit_count'] == (5 if mode == 'five-live' else 4)
    assert take['statistics']['total_independent_shots'] == 128
    assert take['base_melody']['generated_now'] == (mode == 'five-live')
    assert all(len(take['rounds'][name]) == 16 and len(take['events'][name]) == 32 for name in ('quantum', 'classical'))
    bell = json.loads((ASSETS / 'selected_angles.json').read_text())
    melody = json.loads((ASSETS / 'melody_angles.json').read_text())
    assert take['models']['bell_checkpoint_sha256'] == bell['source_sha256']
    assert take['models']['qcbm_checkpoint_sha256'] == melody['source_checkpoint_sha256']
