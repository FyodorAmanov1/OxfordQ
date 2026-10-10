"""One-circuit structured bridge smoke test; run separately from the duet."""
from qiskit import QuantumCircuit, transpile

def probe(backend, shots=32):
    circuit = QuantumCircuit(2, 2, name='bridge_probe')
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    job = backend.run(transpile(circuit, backend), shots=shots)
    result = job.result()
    if not result.success:
        raise RuntimeError('Bridge probe backend failed')
    return {'schema_version': 1, 'circuit': circuit.name, 'counts': result.get_counts(),
            'shots': shots, 'job_id': str(job.job_id()), 'backend': str(result.backend_name),
            'backend_run_calls': 1}
