"""Standalone private Qollab reproduction; one supplied free-backend job only."""
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from numbers import Integral

from qiskit import QuantumCircuit, transpile


def probe_json(backend, shots=32):
    report = {'observed_utc': datetime.now(timezone.utc).isoformat(),
              'versions': {'python': platform.python_version()},
              'backend_class': f'{type(backend).__module__}.{type(backend).__name__}',
              'api_path': 'unknown (platform transport not inspected)',
              'platform_proxy': 'unknown', 'backend_run_calls': 0,
              'job_id': None, 'counts': None, 'shots': shots, 'stage': 'preflight'}
    for package in ('qiskit', 'qiskit-ionq', 'numpy', 'pyodide', 'qollab'):
        try:
            report['versions'][package] = version(package)
        except PackageNotFoundError:
            report['versions'][package] = 'unknown (distribution metadata unavailable)'
    try:
        if type(shots) is not int or shots != 32:
            raise ValueError('This reproduction requires exactly 32 shots')
        config = backend.configuration() if callable(getattr(backend, 'configuration', None)) else None
        name = getattr(backend, 'name', '')
        name = name() if callable(name) else name
        report['backend_name'] = str(name)
        ionq = any('ionq' in cls.__module__.lower() for cls in type(backend).__mro__)
        if getattr(config, 'simulator', None) is False or (ionq and 'simulator' not in str(name).lower()):
            raise ValueError('Simulator identity required')
        circuit = QuantumCircuit(2, 2, name='bridge_probe')
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        report['stage'] = 'transpile'
        compiled = transpile(circuit, backend, optimization_level=0)
        if ionq:
            from qiskit_ionq.helpers import qiskit_to_ionq
            payload = json.loads(qiskit_to_ionq(compiled, backend, {'shots': shots}))
            report['serialized_schema'] = {'type': payload.get('type'),
                'shots': payload.get('shots'), 'input_keys': sorted(payload['input']),
                'qubits': payload['input'].get('qubits')}
        report['stage'] = 'submit'
        report['backend_run_calls'] = 1
        job = backend.run(compiled, shots=shots)
        report['stage'] = 'job_id'
        report['job_id'] = str(job.job_id())
        report['stage'] = 'result'
        result = job.result()
        report['stage'] = 'validate_result'
        rows = result.results
        header = rows[0].header if len(rows) == 1 else None
        label = header.get('name') if isinstance(header, dict) else getattr(header, 'name', None)
        if not result.success or len(rows) != 1 or not rows[0].success or label != 'bridge_probe':
            raise ValueError('Invalid named result')
        counts = result.get_counts(0)
        if not isinstance(counts, dict) or any(
            not isinstance(k, str) or len(k) != 2 or set(k) - {'0', '1'}
            or isinstance(v, bool) or not isinstance(v, Integral) or v < 0
            for k, v in counts.items()
        ) or sum(counts.values()) != shots:
            raise ValueError('Invalid measured integer counts')
        report.update(status='completed', counts={k: int(v) for k, v in counts.items()}, errors=[])
    except Exception as error:
        status = getattr(error, 'status_code', getattr(getattr(error, 'response', None), 'status_code', None))
        report.update(status='failed', errors=[{'code': type(error).__name__,
            'http_status': status if type(status) is int else None,
            'message': 'Probe failed; inspect platform console privately'}])
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    return json.dumps(report, allow_nan=False)
