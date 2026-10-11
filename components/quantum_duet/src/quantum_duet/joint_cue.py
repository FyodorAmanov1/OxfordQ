"""One supplied-simulator circuit; joint cues, frozen angles, RECORDED melody.

Separate qm.joint-cue-result.v1, never qm.run-result.v1. No provider creation,
new QCBM draw, retry, cue redraw, postselection, or musical arrangement.
"""
import hashlib
import json
import math
import secrets
from datetime import datetime, timezone

import numpy as np
from qiskit import QuantumCircuit, transpile

from .duet_quantum import angles_array, exact_metrics
from .duet_referee import SETTINGS, wins
from .duet_classical import shared_choices, alice_output, bob_output
from .integration import backend_limits, load_assets, reconstructed, generate_take
from .music import events_from_outputs
from .probe import runtime_versions

CONTRACT = 'qm.joint-cue-result.v1'
CIRCUIT_VERSION = 'qm.joint-cue-circuit.v1'
QIS = ['h', 'cx', 'ry', 'rz', 'x']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def build_joint_circuit(angles, *, measure=True):
    a0, a1, b0, b1 = angles_array(angles)
    circuit = QuantumCircuit(4, 4 if measure else 0, name='duet_joint_cues_v1')
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.h(2)
    circuit.h(3)
    circuit.ry(-float(a0), 0)
    circuit.cry(float(a0-a1), 2, 0)  # Alice's own cue only
    circuit.ry(-float(b0), 1)
    circuit.cry(float(b0-b1), 3, 1)  # Bob's own cue only
    if measure:
        circuit.measure(range(4), range(4))
    circuit.metadata = {'circuit_version': CIRCUIT_VERSION, 'bit_order': 'yxba',
                        'qubits': {'a': 0, 'b': 1, 'x': 2, 'y': 3}}
    return circuit


def compile_joint(angles):
    # Explicit QIS decomposition: no unsupported controlled-RY reaches IonQ.
    # All-to-all gates, no layout permutation; qi is still measured into ci.
    return transpile(build_joint_circuit(angles), basis_gates=QIS, optimization_level=1)


def decode_joint(bits):
    if not isinstance(bits, str) or len(bits) != 4 or set(bits)-{'0', '1'}:
        raise ValueError('Require four measured bits in yxba order')
    return tuple(int(bits[i]) for i in (1, 0, 3, 2))  # x,y,a,b


def validate_counts(counts):
    if not isinstance(counts, dict) or not counts:
        raise ValueError('Require a nonempty integer yxba histogram')
    clean = {}
    for bits, n in counts.items():
        decode_joint(bits)
        if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 0:
            raise ValueError('Histogram must contain nonnegative integer shot counts')
        clean[bits] = int(n)
    if not sum(clean.values()):
        raise ValueError('No shots returned')
    return clean


def joint_statistics(counts):
    counts = validate_counts(counts)
    rows = []
    for x, y in SETTINGS:
        group = {bits[2:]: n for bits, n in counts.items() if decode_joint(bits)[:2] == (x, y)}
        n = sum(group.values())
        w = sum(v for ba, v in group.items() if wins(x, y, int(ba[1]), int(ba[0])))
        correlation = sum(v*(1 if ba[0] == ba[1] else -1) for ba, v in group.items())/n if n else None
        rows.append({'x': x, 'y': y, 'shots': n, 'wins': w, 'counts_ba': group,
                     'success': w/n if n else None, 'correlation': correlation})
    total = sum(r['shots'] for r in rows)
    p = sum(r['success'] for r in rows)/4 if all(r['shots'] for r in rows) else None
    radius = math.sqrt(math.log(40)/2 * sum(1/(16*r['shots']) for r in rows)) if p is not None else None
    return {'allocation': rows, 'total_independent_shots': total,
            'conditional_available': p is not None, 'expected_success': p,
            'chsh': 8*p-4 if p is not None else None,
            'pooled_success': sum(r['wins'] for r in rows)/total,
            'success_interval': [max(0, p-radius), min(1, p+radius)] if p is not None else None,
            'hoeffding_radius': radius, 'interval_method': '95% weighted conditional Hoeffding',
            'independence_assumption': 'Conditional on observed positive setting allocations; independent fresh preparations and fixed channel. Noise correlation/drift not certified.',
            'hardware_certified': False, 'postselection': False,
            'unavailable_reason': None if p is not None else 'At least one cue pair has zero shots; no additional job requested'}


def simulator_identity(backend, shots):
    limits = backend_limits(backend, shots, 1, 4)
    config = backend.configuration() if callable(getattr(backend, 'configuration', None)) else None
    ionq = any('ionq' in cls.__module__.lower() for cls in type(backend).__mro__)
    # Fail closed if the supplied backend cannot positively declare simulation.
    known_basic = any(cls.__module__ == 'qiskit.providers.basic_provider.basic_simulator' and cls.__name__ == 'BasicSimulator' for cls in type(backend).__mro__)
    known_ionq = any(cls.__module__ == 'qiskit_ionq.ionq_backend' and cls.__name__ == 'IonQSimulatorBackend' for cls in type(backend).__mro__)
    if not (known_basic or known_ionq or (config is not None and getattr(config, 'simulator', None) is True)):
        raise RuntimeError('Supplied backend is not confirmed as a simulator; no job submitted')
    if ionq and (not callable(getattr(backend, 'gateset', None)) or backend.gateset() != 'qis'):
        raise RuntimeError('Require IonQ QIS simulator; no native/unknown gateset submission')
    return limits, ionq


def prepare_presentation(seed):
    streams = np.random.SeedSequence(seed).spawn(2)
    shared_seed = int(streams[0].generate_state(1)[0])
    indices, strategies = shared_choices(shared_seed, 16)  # BEFORE backend run/cues/results
    commitment = digest({'indices': indices, 'strategies': strategies})
    return {'seed': seed, 'shared_seed': shared_seed, 'indices': indices,
            'strategies': strategies, 'commitment': commitment,
            'rng': np.random.default_rng(streams[1])}


def assemble_joint(counts, execution, angles, melody, recorded, prepared):
    counts = validate_counts(counts)
    if sum(counts.values()) < 16:
        raise ValueError('Need sixteen actual returned shots for playback; no resubmission')
    run_id = 'qm-joint-' + execution['job_id']
    ordering = reconstructed(counts, prepared['rng'])  # ONE permutation, no second cue draw
    selected = ordering[:16]
    rounds = {'quantum': [], 'classical': []}
    for i, bits in enumerate(selected):
        x, y, a, b = decode_joint(bits)
        common = {'round': i, 'round_id': f'{run_id}/r{i:02}', 'run_id': run_id,
                  'x': x, 'y': y, 'base_token': recorded['tokens'][i], 'required_parity': x*y,
                  'source_measurement': {'displayed_yxba': bits, 'reconstructed_index': i,
                                         'histogram_sha256': digest(counts)}}
        rounds['quantum'].append({**common, 'a': a, 'b': b, 'displayed_ba': bits[2:], 'win': bool(wins(x, y, a, b))})
        strategy = prepared['strategies'][i]
        a, b = alice_output(x, strategy[:2]), bob_output(y, strategy[2:])
        rounds['classical'].append({**common, 'a': a, 'b': b, 'win': bool(wins(x, y, a, b)),
                                   'shared_strategy': strategy, 'shared_strategy_index': prepared['indices'][i]})
    events = {}
    for policy, rs in rounds.items():
        events[policy] = events_from_outputs(recorded['tokens'], [r['a'] for r in rs], [r['b'] for r in rs])
        for e in events[policy]:
            e.update(run_id=run_id, round_id=rs[e['round']]['round_id'], velocity=80,
                     event_id=f"{rs[e['round']]['round_id']}/{policy}/{e['voice']}",
                     source_measurement=rs[e['round']]['source_measurement'])
    result = {'contract_version': CONTRACT, 'status': 'completed', 'run_id': run_id,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'execution': execution, 'joint_histogram_yxba': counts, 'histogram_sha256': digest(counts),
              'circuit': {'version': CIRCUIT_VERSION, 'angle_order': ['A0','A1','B0','B1'], 'bit_order': 'yxba'},
              'models': {'bell_angles_radians': angles['parameters_radians'], 'bell_checkpoint_sha256': angles['source_sha256'],
                         'qcbm_checkpoint_sha256': melody['source_checkpoint_sha256'], 'qcbm_parameters': 84, 'qcbm_qubits': 12},
              'base_melody': {**recorded, 'generated_now': False, 'data_status': 'RECORDED'},
              'cue_sequence': [[r['x'],r['y']] for r in rounds['quantum']],
              'rounds': rounds, 'events': events,
              'excerpt': {name: {'wins': sum(r['win'] for r in rs), 'rounds': 16} for name, rs in rounds.items()},
              'statistics': joint_statistics(counts), 'tempo_bpm': 120,
              'references': {'quantum_exact': exact_metrics(angles['parameters_radians'])['expected_success'],
                             'local_classical_maximum': .75, 'unrestricted_centralized': 1.},
              'randomness': {'presentation_master_seed': str(prepared['seed']), 'shared_strategy_seed': prepared['shared_seed'],
                             'classical_commitment_sha256': prepared['commitment'], 'committed_before_backend_submission': True,
                             'independent_streams': True, 'cue_redraws': 0},
              'playback_ordering': 'Uniform permutation of full measured multiset, first 16 without replacement; not chronological memory',
              'limitations': ['Cues generated centrally inside circuit, not external spacelike-separated choices',
                              'Ideal conditional equivalence does not establish noise-model equivalence',
                              'Classically simulatable; no hardware certification, speedup or musical-quality advantage',
                              'Recorded QCBM melody did not beat classical likelihood baseline'],
              'errors': [], 'fallback': {'requested': False, 'used': False, 'reason': None},
              'attribution': 'This effort is supported by Qollab & IonQ'}
    json.dumps(result, allow_nan=False)
    return result


def generate_joint(backend, shots=32, presentation_seed=None, *, asset_dir=None):
    trace = {'stage': 'preflight', 'backend_run_calls': 0, 'job_id': None,
             'versions': runtime_versions(), 'requested_shots': shots, 'circuit_count': 1}
    try:
        limits, ionq = simulator_identity(backend, shots)
        angles, melody, recorded = load_assets(asset_dir)
        seed = secrets.randbits(64) if presentation_seed is None else int(presentation_seed)
        prepared = prepare_presentation(seed)
        trace.update(backend_name=limits['name'], backend_class=limits['class'], advertised_limits=limits,
                     is_ionq_simulator=ionq, simulator_verified=True, hardware_executed=False,
                     noise_model=getattr(backend.options, 'noise_model', None),
                     gateset=backend.gateset() if callable(getattr(backend, 'gateset', None)) else 'local simulator target',
                     data_status='live', mode='joint-cue-recorded', bit_order='yxba',
                     submitted_representation='single QuantumCircuit object', expected_job_type='ionq.circuit.v1',
                     classical_commitment_sha256=prepared['commitment'])
        trace['stage'] = 'transpile'
        compiled = compile_joint(angles['parameters_radians'])
        trace['compiled_operations'] = dict(compiled.count_ops())
        trace['stage'] = 'submit'
        trace['backend_run_calls'] = 1
        job = backend.run(compiled, shots=shots)  # ONE OBJECT, ONE CALL, no retry
        trace['job_id'] = str(job.job_id()) if job.job_id() is not None else None
        trace['stage'] = 'result'
        result = job.result()
        trace['stage'] = 'validate_result'
        if not result.success or len(result.results) != 1 or not result.results[0].success or not trace['job_id']:
            raise RuntimeError('Incomplete/failed one-circuit result or missing actual job identity')
        counts = validate_counts(result.get_counts(0))
        actual = sum(counts.values())
        if actual != shots or int(result.results[0].shots) != actual:
            raise RuntimeError('Returned shot count differs from requested/experiment allocation')
        trace.update(returned_shots=actual, result_status=str(getattr(result, 'status', None)),
                     result_success=bool(result.success), experiment_success=bool(result.results[0].success),
                     job_status=str(job.status()),
                     result_backend_name=str(result.backend_name), backend_version=str(result.backend_version), stage='completed')
        return json.dumps(assemble_joint(counts, trace, angles, melody, recorded, prepared), allow_nan=False)
    except Exception as error:
        trace.update(status='failed', error_code=type(error).__name__, fallback_used=False)
        print(json.dumps({'event': 'joint-cue-failure', **trace}, allow_nan=False))
        raise RuntimeError(f"Joint-cue execution failed at {trace['stage']} ({type(error).__name__}); no retry/fallback") from error


def run_selected(backend, shots=32, mode='joint-cue-recorded', execution_mode='selected-simulator-unverified'):
    if mode == 'joint-cue-recorded':
        return generate_joint(backend, shots)
    _, ionq = simulator_identity(backend, shots)
    if ionq:
        raise RuntimeError('Legacy multi-circuit batches are disabled on IonQ; select single-circuit joint cues')
    return generate_take(backend, shots, mode, execution_mode)
