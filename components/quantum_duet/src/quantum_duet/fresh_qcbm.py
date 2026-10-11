"""Fresh frozen QCBM inference: one supplied simulator, one object, one call.

No Bell experiment, retraining, provider creation, retry, musical correction or
fallback. Histogram occurrences are reconstructed, never chronological memory.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import transpile

from .circuit import build_circuit, bind_parameters
from .integration import backend_limits
from .joint_cue import digest, simulator_identity, QIS
from .probe import runtime_versions

CONTRACT = 'qm.fresh-qcbm-source.v1'
CHECKPOINT_SHA256 = 'ecd7faaa232a15c261a5e3daf8047e0b4d71be9f4eb4bb597e70acb671c5b8a4'
PARAMETERS_SHA256 = '9c0e4f62413257d90d575300a1ce856143e728c637e1fc1c9e4ffdc9ce4c843a'
INSTRUMENTS = ('Flute', 'Clarinet', 'Violin', 'Cello', 'Piano')


def load_frozen(asset_dir=None):
    if asset_dir is None:
        # Literal visible to Qollab's static file loader.
        with open('data/melody_angles.json', 'rb') as stream:
            raw = stream.read()
    else:
        raw = (Path(asset_dir) / 'melody_angles.json').read_bytes()
    melody = json.loads(raw)
    if (melody.get('source_checkpoint_sha256') != CHECKPOINT_SHA256
            or digest(melody.get('parameters_radians')) != PARAMETERS_SHA256):
        raise ValueError('Frozen 84-parameter checkpoint identity mismatch')
    return melody, hashlib.sha256(raw).hexdigest()


def compile_frozen(melody):
    circuit = bind_parameters(build_circuit(measure=True), melody['parameters_radians'])
    circuit.name = 'fresh_frozen_qcbm_12q_v1'
    # IonQ QIS has all-to-all connectivity. CZ decomposes into H/CX/H.
    # No layout change: qubit i is measured into classical bit i.
    return transpile(circuit, basis_gates=QIS, optimization_level=1)


def decode_tokens(bits):
    if not isinstance(bits, str) or len(bits) != 12 or set(bits) - {'0', '1'}:
        raise ValueError('Require exactly twelve binary bits in q11..q0 order')
    value = int(bits, 2)
    return [(value >> (3 * i)) & 7 for i in range(4)]


def validate_counts(counts):
    if not isinstance(counts, dict) or not counts:
        raise ValueError('Require a complete nonempty 12-bit histogram')
    result = {}
    for bits, count in counts.items():
        decode_tokens(bits)
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
            raise ValueError('Require nonnegative integer counts')
        result[bits] = int(count)
    if sum(result.values()) < 20:
        raise ValueError('Need twenty actual returned motif draws; no resubmission')
    return result


def assemble_fresh(counts, execution, melody, asset_sha, seed):
    counts = validate_counts(counts)
    if not execution.get('job_id'):
        raise ValueError('Require actual accepted job identity')
    run_id = 'qm-fresh-' + execution['job_id']
    reconstructed = []
    for bits, count in sorted(counts.items()):
        for _ in range(count):
            index = len(reconstructed)
            reconstructed.append({'occurrence_id': f'{run_id}/m{index:04}',
                                  'reconstructed_index': index, 'bitstring': bits,
                                  'tokens': decode_tokens(bits), 'measured_draw': True,
                                  'chronological': False})
    rng = np.random.Generator(np.random.PCG64(seed))
    order = rng.permutation(len(reconstructed)).tolist()
    occurrences = [reconstructed[i] for i in order]
    source = {'contract_version': CONTRACT, 'status': 'completed', 'run_id': run_id,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'execution': execution,
              'models': {'melody_checkpoint_sha256': melody['source_checkpoint_sha256'],
                         'angle_asset_sha256': asset_sha,
                         'angle_parameters_sha256': digest(melody['parameters_radians']),
                         'qcbm_parameters': 84, 'qcbm_qubits': 12,
                         'same_checkpoint_all_instruments': True},
              'histogram_y12bit': counts, 'histogram_sha256': digest(counts),
              'source_occurrences': occurrences,
              'instrument_sources': [
                  {'instrument': name, 'instrument_id': name.lower(),
                   'motif_occurrence_ids': [r['occurrence_id'] for r in occurrences[4*i:4*i+4]]}
                  for i, name in enumerate(INSTRUMENTS)],
              'unused_occurrence_ids': [r['occurrence_id'] for r in occurrences[20:]],
              'randomness': {'assignment_seed': str(seed),
                             'seed_specified_before_submission': True,
                             'method': 'NumPy PCG64 permutation of complete lexicographically reconstructed multiset; first20 without replacement',
                             'permutation': order, 'postselection': False},
              'token_order': ['q2q1q0', 'q5q4q3', 'q8q7q6', 'q11q10q9'],
              'token_zero': 'rest', 'generated_now': True,
              'warnings': ['Histogram reconstruction is not chronological measurement memory',
                           'All five instruments share one frozen trained checkpoint',
                           'Instrument decoding, repetition and arrangement are classical',
                           'No CHSH or musical-quality advantage is claimed'],
              'errors': [], 'fallback': {'requested': False, 'used': False, 'reason': None},
              'attribution': 'This effort is supported by Qollab & IonQ'}
    validate_source(source)
    return source


def validate_source(source):
    if source.get('contract_version') != CONTRACT or source.get('status') != 'completed':
        raise ValueError('Unsupported/incomplete fresh source contract')
    counts = validate_counts(source['histogram_y12bit'])
    if digest(counts) != source['histogram_sha256']:
        raise ValueError('Histogram hash differs')
    models = source['models']
    if (models['melody_checkpoint_sha256'] != CHECKPOINT_SHA256
            or models['angle_parameters_sha256'] != PARAMETERS_SHA256
            or models['qcbm_parameters'] != 84 or models['qcbm_qubits'] != 12
            or models['same_checkpoint_all_instruments'] is not True):
        raise ValueError('Frozen model identity differs')
    execution = source['execution']
    if (execution['backend_run_calls'] != 1 or execution['circuit_count'] != 1
            or execution['returned_shots'] != sum(counts.values())
            or execution['requested_shots'] != sum(counts.values())
            or source['run_id'] != 'qm-fresh-' + execution['job_id']):
        raise ValueError('Execution identity/shot allocation differs')
    rows = source['source_occurrences']
    if len(rows) != sum(counts.values()):
        raise ValueError('Measurement occurrences missing')
    indices = [r['reconstructed_index'] for r in rows]
    if sorted(indices) != list(range(len(rows))):
        raise ValueError('Occurrence indices must be unique and complete')
    expected_bits = [bits for bits, count in sorted(counts.items()) for _ in range(count)]
    expected_order = np.random.Generator(np.random.PCG64(int(source['randomness']['assignment_seed']))).permutation(len(rows)).tolist()
    if indices != expected_order or source['randomness']['permutation'] != expected_order:
        raise ValueError('Assignment differs from documented unbiased permutation')
    for row in rows:
        index = row['reconstructed_index']
        if (row['bitstring'] != expected_bits[index]
                or row['tokens'] != decode_tokens(row['bitstring'])
                or row['occurrence_id'] != f"{source['run_id']}/m{index:04}"
                or row['measured_draw'] is not True or row['chronological'] is not False):
            raise ValueError('Measured source identity/token mapping differs')
    for i, name in enumerate(INSTRUMENTS):
        part = source['instrument_sources'][i]
        if part != {'instrument': name, 'instrument_id': name.lower(),
                    'motif_occurrence_ids': [r['occurrence_id'] for r in rows[4*i:4*i+4]]}:
            raise ValueError('Instrument draw assignment differs')
    if len(source['instrument_sources']) != 5 or source['unused_occurrence_ids'] != [r['occurrence_id'] for r in rows[20:]]:
        raise ValueError('Unused measurement draws must be preserved')
    json.dumps(source, allow_nan=False)
    return source


def generate_fresh(backend, shots=32, assignment_seed=20261011, *, asset_dir=None):
    trace = {'stage': 'preflight', 'backend_run_calls': 0, 'circuit_count': 1,
             'job_id': None, 'requested_shots': shots, 'versions': runtime_versions()}
    try:
        if type(shots) is not int or not 20 <= shots <= 4096:
            raise ValueError('Select 20..4096 integer shots; default32')
        if type(assignment_seed) is not int or assignment_seed < 0:
            raise ValueError('Specify a nonnegative deterministic assignment seed before submission')
        _, ionq = simulator_identity(backend, shots)
        limits = backend_limits(backend, shots, 1, 12)
        melody, asset_sha = load_frozen(asset_dir)
        trace.update(backend_name=limits['name'], backend_class=limits['class'],
                     advertised_limits=limits, is_ionq_simulator=ionq,
                     simulator_verified=True, hardware_executed=False,
                     data_status='live', mode='fresh-qcbm', bit_order='q11..q0',
                     noise_model=getattr(backend.options, 'noise_model', None),
                     gateset=backend.gateset() if callable(getattr(backend, 'gateset', None)) else 'local simulator target',
                     assignment_seed=str(assignment_seed),
                     expected_job_type='ionq.circuit.v1',
                     submitted_representation='single QuantumCircuit object')
        trace['stage'] = 'transpile'
        compiled = compile_frozen(melody)
        trace['compiled_operations'] = dict(compiled.count_ops())
        trace['stage'] = 'submit'
        trace['backend_run_calls'] = 1
        job = backend.run(compiled, shots=shots)  # ONE OBJECT / ONE CALL
        accepted_id = job.job_id()
        trace['job_id'] = None if accepted_id is None else str(accepted_id)
        trace['stage'] = 'result'
        result = job.result()
        trace['stage'] = 'validate_result'
        if not result.success or len(result.results) != 1 or not result.results[0].success or not trace['job_id']:
            raise RuntimeError('Incomplete or failed one-circuit result')
        trace.update(result_success=bool(result.success), experiment_success=bool(result.results[0].success),
                     result_status=str(getattr(result, 'status', None)), job_status=str(job.status()),
                     result_backend_name=str(result.backend_name), backend_version=str(result.backend_version),
                     experiment_reported_shots=int(result.results[0].shots))
        returned = result.get_counts(0)
        # Preserve histogram-only diagnostics on failure, including SDK rounding
        # to zero at low shot counts. Never fabricate replacement measurements.
        trace['returned_histogram_y12bit'] = {bits: int(n) if isinstance(n, np.integer) else n
                                             for bits, n in returned.items()}
        counts = validate_counts(returned)
        if sum(counts.values()) != shots or int(result.results[0].shots) != shots:
            raise RuntimeError('Returned shot allocation differs; no retry')
        trace.pop('returned_histogram_y12bit')
        trace.update(returned_shots=sum(counts.values()), result_success=bool(result.success),
                     experiment_success=bool(result.results[0].success),
                     result_status=str(getattr(result, 'status', None)),
                     job_status=str(job.status()), result_backend_name=str(result.backend_name),
                     backend_version=str(result.backend_version), stage='completed')
        return json.dumps(assemble_fresh(counts, trace, melody, asset_sha, assignment_seed), allow_nan=False)
    except Exception as error:
        trace.update(status='failed', error_code=type(error).__name__, fallback_used=False)
        print(json.dumps({'event': 'fresh-qcbm-failure', **trace}, allow_nan=False))
        raise RuntimeError(f"Fresh QCBM failed at {trace['stage']} ({type(error).__name__}); no retry/fallback") from error
