"""Local inference and serialization checks, never remote IonQ evidence."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.providers.basic_provider import BasicSimulator
from qiskit.quantum_info import Statevector

from quantum_duet import fresh_qcbm as f
from quantum_duet.circuit import bind_parameters, build_circuit

ASSETS = Path(__file__).parents[1] / 'src/quantum_duet/data'


class SpySimulator(BasicSimulator):
    calls = 0
    def run(self, circuit, **kwargs):
        self.calls += 1
        assert isinstance(circuit, QuantumCircuit)
        assert circuit.num_qubits == circuit.num_clbits == 12
        assert not circuit.parameters
        return super().run(circuit, seed_simulator=32003, **kwargs)


@pytest.fixture
def source():
    backend = SpySimulator()
    result = json.loads(f.generate_fresh(backend, asset_dir=ASSETS))
    assert backend.calls == 1
    return result


def test_frozen_identity_and_compile_equivalence():
    melody, sha = f.load_frozen(ASSETS)
    assert sha == hashlib.sha256((ASSETS / 'melody_angles.json').read_bytes()).hexdigest()
    compiled = f.compile_frozen(melody)
    assert set(compiled.count_ops()) <= {'h', 'cx', 'ry', 'rz', 'x', 'measure'}
    assert compiled.count_ops()['measure'] == 12
    measure = [instruction for instruction in compiled.data if instruction.operation.name == 'measure']
    assert [(compiled.find_bit(i.qubits[0]).index, compiled.find_bit(i.clbits[0]).index) for i in measure] == [(i, i) for i in range(12)]
    original = Statevector.from_instruction(bind_parameters(build_circuit(), melody['parameters_radians']))
    transformed = Statevector.from_instruction(compiled.remove_final_measurements(inplace=False))
    assert original.equiv(transformed)


def test_sdk_one_circuit_serialization(monkeypatch):
    from types import SimpleNamespace
    from qiskit.providers import Options
    from qiskit_ionq.helpers import qiskit_to_ionq
    def denied(*args, **kwargs):
        raise AssertionError('Network forbidden during offline serialization')
    monkeypatch.setattr('requests.sessions.Session.request', denied)
    melody, _ = f.load_frozen(ASSETS)
    backend = SimpleNamespace(name='ionq_simulator', gateset=lambda:'qis', options=Options(noise_model='aria-1', sampler_seed=None))
    payload = json.loads(qiskit_to_ionq(f.compile_frozen(melody), backend, {'shots': 32}))
    assert payload['type'] == 'ionq.circuit.v1'
    assert payload['shots'] == 32
    assert payload['input']['qubits'] == 12
    assert 'circuits' not in payload['input']


@pytest.mark.parametrize('bits,tokens', [('000000000000',[0,0,0,0]), ('111110101100',[4,5,6,7]), ('000000001000',[0,1,0,0])])
def test_token_order(bits, tokens):
    assert f.decode_tokens(bits) == tokens


def test_occurrences_counts_rest_and_unique_assignment(source):
    assert f.validate_source(source) is source
    assert len(source['source_occurrences']) == 32
    assert len(source['unused_occurrence_ids']) == 12
    ids = [i for p in source['instrument_sources'] for i in p['motif_occurrence_ids']]
    assert len(set(ids)) == len(ids) == 20
    assert set(ids).isdisjoint(source['unused_occurrence_ids'])
    observed = {}
    for row in source['source_occurrences']:
        observed[row['bitstring']] = observed.get(row['bitstring'], 0) + 1
    assert observed == source['histogram_y12bit']
    assert source['models']['same_checkpoint_all_instruments'] is True
    assert 'statistics' not in source and 'rounds' not in source


def test_reproducibility_without_job(source):
    melody, sha = f.load_frozen(ASSETS)
    rebuilt = f.assemble_fresh(source['histogram_y12bit'], source['execution'], melody, sha, 20261011)
    for key in ('source_occurrences', 'instrument_sources', 'unused_occurrence_ids', 'randomness', 'histogram_sha256'):
        assert rebuilt[key] == source[key]


def test_duplicate_occurrences_and_rests():
    melody, sha = f.load_frozen(ASSETS)
    execution = {'job_id': 'test-only', 'backend_run_calls': 1, 'circuit_count': 1,
                 'requested_shots': 32, 'returned_shots': 32}
    result = f.assemble_fresh({'000000000000':32}, execution, melody, sha, 20261011)
    assert len({r['occurrence_id'] for r in result['source_occurrences']}) == 32
    assert all(r['tokens'] == [0,0,0,0] for r in result['source_occurrences'])


@pytest.mark.parametrize('counts', [{'0':32}, {'000000000000': True}, {'000000000000': 32.0}, {'000000000000': -1}, {'000000000000':19}])
def test_invalid_counts(counts):
    with pytest.raises(ValueError):
        f.validate_counts(counts)


def test_corrupt_source_rejected(source):
    bad = copy.deepcopy(source)
    bad['source_occurrences'][0]['tokens'][0] ^= 1
    with pytest.raises(ValueError):
        f.validate_source(bad)


def test_checkpoint_changes_fail_before_job(tmp_path):
    melody, _ = f.load_frozen(ASSETS)
    melody['parameters_radians'][0] += .001
    (tmp_path / 'melody_angles.json').write_text(json.dumps(melody), encoding='utf8')
    backend = SpySimulator()
    with pytest.raises(RuntimeError, match='preflight'):
        f.generate_fresh(backend, asset_dir=tmp_path)
    assert backend.calls == 0


def test_failure_never_retries():
    class FailingSimulator(BasicSimulator):
        calls = 0
        def run(self, circuit, **kwargs):
            self.calls += 1
            raise RuntimeError('offline test failure')
    backend = FailingSimulator()
    with pytest.raises(RuntimeError, match='submit'):
        f.generate_fresh(backend, asset_dir=ASSETS)
    assert backend.calls == 1


def test_unknown_provider_rejected_before_submission():
    class Unknown:
        from qiskit.providers import Options
        options = Options(shots=32)
        name = 'unknown_simulator'
        calls = 0
        def run(self, *args, **kwargs):
            self.calls += 1
    backend = Unknown()
    with pytest.raises(RuntimeError, match='preflight'):
        f.generate_fresh(backend, asset_dir=ASSETS)
    assert backend.calls == 0
