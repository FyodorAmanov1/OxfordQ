"""Inference only. Passed backend; one frozen-model batch; JSON string bridge.

JSON text avoids PyProxy dict-to-Map differences across browser bridge versions.
All literal data paths are visible to Qollab's static project-file loader.
"""
import json
import secrets
from copy import copy
from datetime import datetime, timezone
import numpy as np
from qiskit.providers import Options

from .circuit import build_circuit, bind_parameters
from .duet_quantum import run_batch, decode_outcome, exact_metrics
from .duet_referee import SETTINGS, cues, sampled_metrics, wins
from .duet_classical import shared_choices, alice_output, bob_output
from .music import events_from_outputs

def load_assets(asset_dir=None):
    if asset_dir is not None:
        from pathlib import Path
        directory = Path(asset_dir)
        assets = [json.loads((directory / name).read_text(encoding="utf-8")) for name in
                  ("selected_angles.json", "melody_angles.json", "recorded_melody.json")]
        if len(assets[0]["parameters_radians"]) != 4 or len(assets[1]["parameters_radians"]) != 84:
            raise ValueError("Frozen checkpoint dimensions invalid")
        return tuple(assets)
    with open('data/selected_angles.json') as f:
        angles = json.load(f)
    with open('data/melody_angles.json') as f:
        melody = json.load(f)
    with open('data/recorded_melody.json') as f:
        recorded = json.load(f)
    if len(angles['parameters_radians']) != 4 or len(melody['parameters_radians']) != 84:
        raise ValueError('Frozen checkpoint dimensions invalid')
    return angles, melody, recorded

def backend_limits(backend, shots, circuit_count, qubits):
    if type(shots) is not int or not 16 <= shots <= 4096:
        raise ValueError('Select 16..4096 integer shots per circuit; default 1024')
    options = getattr(backend, 'options', None)
    if options is None or not hasattr(options, 'shots'):
        raise RuntimeError('Backend does not advertise the shots option; unsupported, no fallback')
    if isinstance(options, Options):
        copy(options).update_options(shots=shots)  # public validators; leave the supplied backend unchanged
    configuration = backend.configuration() if callable(getattr(backend, 'configuration', None)) else None
    if configuration is not None and getattr(configuration, 'simulator', True) is False:
        raise RuntimeError('Physical hardware is disabled for this milestone; select a free simulator')
    name = getattr(backend, 'name', '')
    name = name() if callable(name) else name
    ionq_backend = any('ionq' in cls.__module__.lower() for cls in type(backend).__mro__)
    if ionq_backend and 'simulator' not in str(name).lower():
        raise RuntimeError('IonQ physical/unknown device disabled; select a free IonQ simulator')
    maximum = getattr(configuration, 'max_shots', None)
    max_circuits = getattr(backend, 'max_circuits', None)
    if max_circuits is None:
        max_circuits = getattr(configuration, 'max_experiments', None)
    max_qubits = getattr(backend, 'num_qubits', None) or getattr(configuration, 'n_qubits', None)
    for selected, limit, label in ((shots, maximum, 'shots'), (circuit_count, max_circuits, 'circuits'), (qubits, max_qubits, 'qubits')):
        if limit is not None and selected > limit:
            raise ValueError(f'Selected {label} {selected} exceeds advertised backend limit {limit}')
    return {'name': str(name), 'class': f'{type(backend).__module__}.{type(backend).__name__}',
            'shots_option': True, 'max_shots': maximum, 'max_circuits': max_circuits,
            'shots_validator_checked': isinstance(options, Options),
            'max_qubits': max_qubits, 'unknown_limits': 'Unadvertised limits remain unknown; provider errors propagate, no retries'}

def reconstructed(counts, rng):
    """Uniform permutation of the full measured multiset, without replacement."""
    values = [key for key, n in sorted(counts.items()) for _ in range(n)]
    rng.shuffle(values)
    return values

def assemble_take(batch, angles, melody, recorded, mode, execution_mode, seed):
    # Four independent SeedSequence children: no cue-generator seed reaches a policy.
    streams = np.random.SeedSequence(seed).spawn(4)
    shared_seed = int(streams[0].generate_state(1)[0])
    cue_seed = int(streams[1].generate_state(1)[0])
    playback_rng = np.random.default_rng(streams[2])
    melody_rng = np.random.default_rng(streams[3])
    indices, strategies = shared_choices(shared_seed, 16)  # committed BEFORE cues
    sequence = cues(cue_seed)
    experiments = batch['experiments']
    groups = [row['counts'] for row in experiments if row['role'] == 'coordination']
    stats = sampled_metrics(groups)  # ALL shots including musical rests, equal allocation
    if 'ideal' not in execution_mode:
        stats['independence_assumption'] = 'Conditional independent fresh preparations, fixed equal allocation. Noise correlations/drift are not certified by this interval.'
    stats['hardware_certified'] = False
    stats['allocation'] = [{'x': x, 'y': y, 'shots': sum(count.values())} for (x, y), count in zip(SETTINGS, groups)]
    ordering = [reconstructed(count, playback_rng) for count in groups]
    used = [0] * 4
    if mode == 'five-live':
        memories = reconstructed(experiments[4]['counts'], melody_rng)[:4]
        motifs = [[(int(bits, 2) >> (3 * i)) & 7 for i in range(4)] for bits in memories]
        base = {'motifs': motifs, 'tokens': [t for m in motifs for t in m],
                'sampled_bitstrings': memories, 'origin': 'current-run QCBM histogram',
                'generated_now': True, 'ordering': 'Unbiased reconstructed order, not chronological memory'}
    else:
        base = {**recorded, 'generated_now': False, 'ordering': 'Recorded M3A four-motif draw'}
    rounds = {'quantum': [], 'classical': []}
    for i, (x, y) in enumerate(sequence):
        group = SETTINGS.index((x, y))
        bits = ordering[group][used[group]]
        used[group] += 1
        a, b = decode_outcome(bits)
        common = {'round': i, 'x': x, 'y': y, 'base_token': base['tokens'][i], 'required_parity': x & y}
        rounds['quantum'].append({**common, 'a': a, 'b': b, 'displayed_ba': bits,
                                  'win': bool(wins(x, y, a, b))})
        strategy = strategies[i]
        a, b = alice_output(x, strategy[:2]), bob_output(y, strategy[2:])
        rounds['classical'].append({**common, 'a': a, 'b': b, 'win': bool(wins(x, y, a, b)),
            'shared_strategy_index': indices[i], 'shared_strategy': strategy})
    events = {name: events_from_outputs(base['tokens'], [r['a'] for r in rs], [r['b'] for r in rs])
              for name, rs in rounds.items()}
    result = {'schema_version': 1, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'execution': {**batch, 'mode': mode, 'execution_mode': execution_mode,
                      'execution_mode_source': 'verified local development adapter' if execution_mode == 'ideal-local-development' else 'runner declaration; not independently verified',
                      'execution_mode_verified': execution_mode == 'ideal-local-development',
                      'measurement_origin': 'current-run supplied backend', 'hardware_executed': False},
        'models': {'bell_angles_radians': angles['parameters_radians'],
                   'bell_checkpoint_sha256': angles['source_sha256'],
                   'qcbm_checkpoint_sha256': melody['source_checkpoint_sha256'],
                   'qcbm_parameters': 84, 'qcbm_qubits': 12},
        'base_melody': base, 'cue_sequence': sequence, 'rounds': rounds, 'events': events,
        'excerpt': {name: {'wins': sum(r['win'] for r in rs), 'rounds': 16,
                          'interpretation': 'Audible excerpt only; not the full-count estimate'} for name, rs in rounds.items()},
        'statistics': stats,
        'references': {'quantum_exact': exact_metrics(angles['parameters_radians'])['expected_success'],
                       'local_classical_maximum': 0.75, 'unrestricted_centralized': 1.0},
        'playback_ordering': 'Unbiased reconstructed ordering from counts, not original chronological measurements',
        'randomness': {'presentation_master_seed': seed, 'shared_strategy_seed': shared_seed,
                       'referee_cue_seed': cue_seed, 'independent_streams': True,
                       'policy_access': 'Only local two-entry function and own cue; seeds/schedules are referee/export metadata only'},
        'limitations': ['Centralized simulation of noncommunicating policies; classically simulatable',
                       'No established speedup or musical-quality advantage',
                       'Earlier QCBM did not beat classical melody likelihood baselines'],
        'attribution': 'This effort is supported by Qollab & IonQ'}
    validate_take(result)
    return result

def validate_take(take):
    execution = take['execution']
    if execution['backend_run_calls'] != 1 or execution['circuit_count'] != (5 if execution['mode'] == 'five-live' else 4):
        raise ValueError('Invalid job/circuit allocation')
    if take['base_melody']['generated_now'] != (execution['mode'] == 'five-live'):
        raise ValueError('Recorded/current melody mismatch')
    if len(take['base_melody']['tokens']) != 16:
        raise ValueError('Require exactly sixteen base tokens')
    for name in ('quantum', 'classical'):
        rs = take['rounds'][name]
        if len(rs) != 16 or len(take['events'][name]) != 32:
            raise ValueError('All rounds, including rests, must be retained')
        expected = events_from_outputs(take['base_melody']['tokens'], [r['a'] for r in rs], [r['b'] for r in rs])
        if expected != take['events'][name]:
            raise ValueError('Events differ from committed local outputs')
    json.dumps(take, allow_nan=False)

def generate_take(backend, shots=1024, mode='five-live', execution_mode='selected-simulator-unverified', presentation_seed=None, *, asset_dir=None):
    if mode not in ('five-live', 'four-recorded'):
        raise ValueError('Explicitly select five-live or four-recorded mode')
    if execution_mode not in ('selected-simulator-unverified', 'ideal-local-development', 'ideal-simulator', 'noisy-simulator'):
        raise ValueError('Hardware execution mode is unsupported')
    limits = backend_limits(backend, shots, 5 if mode == 'five-live' else 4, 12 if mode == 'five-live' else 2)
    angles, melody, recorded = load_assets(asset_dir)
    circuit = bind_parameters(build_circuit(), melody['parameters_radians']) if mode == 'five-live' else None
    batch = run_batch(backend, angles['parameters_radians'], shots, melody_circuit=circuit)
    batch['advertised_limits'] = limits
    seed = secrets.randbits(64) if presentation_seed is None else int(presentation_seed)
    return json.dumps(assemble_take(batch, angles, melody, recorded, mode, execution_mode, seed), allow_nan=False)
