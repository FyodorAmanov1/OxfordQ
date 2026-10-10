"""Real SDK serialization with all HTTP intercepted; no provider/account creation."""
import json
from types import SimpleNamespace

import pytest
from qiskit import QuantumCircuit
from qiskit.providers import Options

pytest.importorskip('qiskit_ionq', reason='Offline IonQ SDK checks require optional qiskit-ionq; no app dependency added')

from qiskit_ionq.helpers import qiskit_to_ionq, decompress_metadata_string
from qiskit_ionq.ionq_client import IonQClient
from qiskit_ionq.exceptions import IonQAPIError

from quantum_duet.circuit import build_circuit, bind_parameters
from quantum_duet.duet_quantum import REFERENCE_ANGLES, setting_batch


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Unexpected network call in offline SDK check')
    monkeypatch.setattr('requests.sessions.Session.request', denied)


def backend():
    return SimpleNamespace(name='ionq_simulator', gateset=lambda: 'qis',
                           options=Options(noise_model='ideal', sampler_seed=None))


def circuits(count):
    if count == 1:
        circuit = QuantumCircuit(2, 2, name='bridge_probe')
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        return circuit
    melody = bind_parameters(build_circuit(), [0.0] * 84) if count == 5 else None
    return setting_batch(REFERENCE_ANGLES, melody_circuit=melody)[0]


@pytest.mark.parametrize('count', [1, 4, 5])
def test_actual_sdk_type_names_measurement_map_and_allocations(count):
    source = circuits(count)
    payload = json.loads(qiskit_to_ionq(source, backend(), {'shots': 32, 'type': 'ionq.circuit.v1'}))
    assert payload['shots'] == 32 and payload['backend'] == 'simulator'
    assert payload['type'] == ('ionq.circuit.v1' if count == 1 else 'ionq.multi-circuit.v1')
    header = decompress_metadata_string(payload['metadata']['qiskit_header'])
    headers = [header] if count == 1 else header
    submitted = [source] if count == 1 else source
    assert [h['name'] for h in headers] == [c.name for c in submitted]
    assert [h['meas_mapped'] for h in headers] == [list(range(c.num_clbits)) for c in submitted]
    assert ('circuit' in payload['input']) == (count == 1)
    assert payload['input']['qubits'] == (12 if count == 5 else 2)


def test_one_element_list_is_still_multi_circuit():
    payload = json.loads(qiskit_to_ionq([circuits(1)], backend(), {'shots': 32}))
    assert payload['type'] == 'ionq.multi-circuit.v1'


@pytest.mark.parametrize('count', [1, 4, 5])
def test_intercepted_sdk_http_boundary_no_retry_on_400(monkeypatch, count):
    calls = []
    def reject(url, **kwargs):
        # Retain only schema/body, never headers or authentication values.
        calls.append((url, json.loads(kwargs['data'])))
        body = {'error': {'type': 'invalid_request', 'message': 'Only job type ionq.circuit.v1 is supported'}}
        return SimpleNamespace(status_code=400, headers={}, text=json.dumps(body),
                               request=SimpleNamespace(method='POST'), json=lambda: body)
    monkeypatch.setattr('requests.post', reject)
    job = SimpleNamespace(circuit=circuits(count), backend=backend, _passed_args={'shots': 32},
                          extra_query_params={}, extra_metadata={})
    client = IonQClient(token='offline-dummy', url='https://offline.invalid/v0.4')
    with pytest.raises(IonQAPIError):
        client.submit_job(job)
    assert len(calls) == 1 and calls[0][0] == 'https://offline.invalid/v0.4/jobs'
    assert calls[0][1]['type'] == ('ionq.circuit.v1' if count == 1 else 'ionq.multi-circuit.v1')
