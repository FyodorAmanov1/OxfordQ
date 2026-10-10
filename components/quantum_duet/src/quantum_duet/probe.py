"""One-circuit bridge diagnosis; run separately from the duet, on a free simulator."""
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

from qiskit import QuantumCircuit, transpile

from .duet_quantum import validated_experiments
from .integration import backend_limits


def runtime_versions():
    """Distribution versions only: never inspect credentials, client or environment."""
    versions = {"python": platform.python_version()}
    for package in ("qiskit", "qiskit-ionq", "numpy", "pyodide", "qollab"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "unknown (distribution metadata unavailable)"
    return versions


def _execute_probe(backend, shots, trace):
    trace['stage'] = 'preflight'
    trace['advertised_limits'] = backend_limits(backend, shots, 1, 2)
    circuit = QuantumCircuit(2, 2, name='bridge_probe')
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    trace['stage'] = 'transpile'
    compiled = transpile(circuit, backend, optimization_level=0)
    trace['stage'] = 'submit'
    trace['backend_run_calls'] = 1
    # A circuit object, not a one-element list: SDK serialization distinguishes them.
    job = backend.run(compiled, shots=shots)
    trace['stage'] = 'job_id'
    accepted_id = job.job_id()
    trace['job_id'] = None if accepted_id is None else str(accepted_id)
    trace['stage'] = 'result'
    result = job.result()
    trace['stage'] = 'validate_result'
    labels = [{'index': 0, 'name': circuit.name, 'role': 'bridge_probe'}]
    row = validated_experiments(result, labels, shots)[0]
    return {'schema_version': 1, 'circuit': circuit.name, 'counts': row['counts'],
            'shots': shots, 'job_id': trace['job_id'], 'backend': str(result.backend_name),
            'backend_run_calls': 1}


def probe(backend, shots=32):
    """Preserve the dict/raising API, with no retry or replacement backend."""
    return _execute_probe(backend, shots, {})


def probe_json(backend, shots=32):
    """JSON bridge report including redacted failure stage and runtime versions.

    The platform selection must visibly say Free simulator before calling this.
    An SDK endpoint is not proof of the platform proxy route; both stay unknown here.
    """
    trace = {'backend_run_calls': 0, 'job_id': None}
    report = {'schema_version': 1, 'observed_utc': datetime.now(timezone.utc).isoformat(),
              'versions': runtime_versions(),
              'backend_class': f'{type(backend).__module__}.{type(backend).__name__}',
              'api_path': 'unknown (platform transport not inspected)',
              'platform_proxy': 'unknown', 'free_selection_verified': False,
              'simulator_verification': 'runner must verify free simulator selection',
              'fallback': {'requested': False, 'used': False, 'reason': None}}
    try:
        report.update(status='completed', result=_execute_probe(backend, shots, trace), errors=[])
    except Exception as error:
        response = getattr(error, 'response', None)
        status = getattr(error, 'status_code', getattr(response, 'status_code', None))
        if type(status) is not int:
            status = None
        # Never export arbitrary exception text: it may contain URLs or credentials.
        report.update(status='failed', result=None, errors=[{
            'stage': trace['stage'], 'code': type(error).__name__, 'http_status': status,
            'message': 'Bridge probe failed; inspect the platform console privately'}])
    report.update(trace)
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    return json.dumps(report, allow_nan=False)
