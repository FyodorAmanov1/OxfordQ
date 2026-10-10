"""Reusable two-qubit runtime: Qiskit/NumPy only, no training/data/audio imports.

This is centrally orchestrated simulation of logically local setting choices.
Qubit 0 is Alice; qubit 1 is Bob; displayed strings are ba, not ab.
"""

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from .duet_referee import SETTINGS, bit, metrics

ANGLE_ORDER = ("A0", "A1", "B0", "B1")
REFERENCE_ANGLES = (0, np.pi / 2, np.pi / 4, -np.pi / 4)
OPTIMAL_SUCCESS = float(np.cos(np.pi / 8) ** 2)


def angles_array(angles):
    values = np.asarray(angles, dtype=float)
    if values.shape != (4,) or not np.isfinite(values).all():
        raise ValueError("Require four finite radians in A0,A1,B0,B1 order")
    return values


def alice_setting(x, local_angles):
    if len(local_angles) != 2:
        raise ValueError("Alice receives only A0,A1")
    angle = float(local_angles[bit(x)])
    if not np.isfinite(angle):
        raise ValueError("Nonfinite angle")
    return angle


def bob_setting(y, local_angles):
    if len(local_angles) != 2:
        raise ValueError("Bob receives only B0,B1")
    angle = float(local_angles[bit(y)])
    if not np.isfinite(angle):
        raise ValueError("Nonfinite angle")
    return angle


def bell_pair():
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    return circuit


def build_round_circuit(alice_angle, bob_angle, *, measure=False, name="duet_round"):
    # Fresh state preparation precedes all cue-dependent operations.
    circuit = QuantumCircuit(2, 2 if measure else 0, name=name)
    circuit.h(0)
    circuit.cx(0, 1)
    if not np.isfinite([alice_angle, bob_angle]).all():
        raise ValueError("Nonfinite local setting")
    circuit.ry(-float(alice_angle), 0)
    circuit.ry(-float(bob_angle), 1)
    if measure:
        circuit.measure([0, 1], [0, 1])
    circuit.metadata = {"bit_order": "ba: classical bit 0 Alice, bit 1 Bob", "model": "four-parameter variational quantum coordination model"}
    return circuit


def build_setting_circuit(angles, x, y, *, measure=False):
    """Referee-side orchestration; each setting selector sees only its own cue."""
    values = angles_array(angles)
    circuit = build_round_circuit(alice_setting(x, values[:2]), bob_setting(y, values[2:]),
                                  measure=measure, name=f"duet_xy_{bit(x)}{bit(y)}")
    circuit.metadata.update(setting=[bit(x), bit(y)])
    return circuit


def exact_outcomes(angles, x, y):
    p = Statevector.from_instruction(build_setting_circuit(angles, x, y)).probabilities()
    if not np.isfinite(p).all() or p.min() < 0 or abs(p.sum() - 1) > 1e-12:
        raise RuntimeError("Invalid two-qubit probabilities")
    return p


def exact_metrics(angles):
    return metrics([exact_outcomes(angles, x, y) for x, y in SETTINGS])


def decode_outcome(displayed):
    if not isinstance(displayed, str) or len(displayed) != 2 or set(displayed) - {"0", "1"}:
        raise ValueError("Expected a two-bit Qiskit ba string")
    return int(displayed[1]), int(displayed[0])


def sample_round(angles, x, y, rng):
    """Independent Born draw from a newly prepared circuit; no feedback input."""
    outcome = int(rng.choice(4, p=exact_outcomes(angles, x, y)))
    displayed = format(outcome, "02b")
    return displayed, decode_outcome(displayed)


def setting_batch(angles, *, melody_circuit=None):
    circuits = [build_setting_circuit(angles, x, y, measure=True) for x, y in SETTINGS]
    labels = [{"index": i, "name": c.name, "role": "coordination", "setting": list(SETTINGS[i])}
              for i, c in enumerate(circuits)]
    if melody_circuit is not None:
        if melody_circuit.num_qubits != 12 or melody_circuit.num_parameters or melody_circuit.num_clbits:
            raise ValueError("Live melody needs the supplied bound unmeasured 12-qubit circuit")
        melody = melody_circuit.copy(name="duet_live_melody")
        melody.add_register(ClassicalRegister(12))
        melody.measure(range(12), range(12))
        circuits.append(melody)
        labels.append({"index": 4, "name": melody.name, "role": "live_base_melody", "bit_order": "q11...q0"})
    return circuits, labels


def run_batch(backend, angles, shots, *, melody_circuit=None, seed_simulator=None, memory=False):
    """Exactly ONE supplied-backend submission, including optional live melody.

    Errors propagate; never substitute a simulator for the requested backend.
    Providers can choose their own compilation while preserving named labels.
    """
    if type(shots) is not int or shots < 1:
        raise ValueError("shots must be positive integer")
    circuits, labels = setting_batch(angles, melody_circuit=melody_circuit)
    compiled = transpile(circuits, backend, optimization_level=0)
    options = {"shots": shots}
    if hasattr(getattr(backend, 'options', None), 'use_clifford_optimization'):
        # Preserve M3A's sequential simulator RNG behavior when this option exists.
        options['use_clifford_optimization'] = False
    if seed_simulator is not None:
        options["seed_simulator"] = seed_simulator
    if memory:
        options["memory"] = True
    job = backend.run(compiled, **options)  # One job per future Qollab/IonQ code run.
    result = job.result()
    if not hasattr(result, 'results') or not callable(getattr(result, 'get_counts', None)):
        raise RuntimeError('Unsupported provider result representation: require labelled Qiskit Result experiments; no positional fallback')
    if not result.success or len(result.results) != len(circuits):
        raise RuntimeError("Requested backend returned failed/incomplete batch")
    matched = {}
    for result_index, experiment in enumerate(result.results):
        header = experiment.header
        name = header.get('name') if isinstance(header, dict) else getattr(header, 'name', None)
        if not isinstance(name, str) or name in matched:
            raise RuntimeError('Missing/duplicate provider circuit label; no positional fallback')
        matched[name] = result_index
    if set(matched) != {label['name'] for label in labels}:
        raise RuntimeError('Provider result labels differ from submitted circuits')
    experiments = []
    for label in labels:
        index = matched[label['name']]
        experiment = result.results[index]
        if not experiment.success:
            raise RuntimeError('Provider returned an unsuccessful circuit')
        counts = {}
        width = 12 if label['role'] == 'live_base_melody' else 2
        for key, value in result.get_counts(index).items():
            bits = str(key).replace(' ', '')
            if len(bits) != width or set(bits) - {'0', '1'} or isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
                raise RuntimeError('Unsupported count key/value; require measured Qiskit bit strings and integer counts')
            counts[bits] = counts.get(bits, 0) + int(value)
        if sum(counts.values()) != shots:
            raise RuntimeError("Requested backend returned an unexpected shot count")
        row = {**label, 'result_index': index, 'shots': shots, 'counts': counts}
        if memory:
            row["memory"] = [str(v) for v in result.get_memory(index)]
        experiments.append(row)
    return {"backend_name": str(result.backend_name), "backend_version": str(result.backend_version),
            "backend_class": f"{type(backend).__module__}.{type(backend).__name__}",
            "job_id": str(job.job_id()), "backend_run_calls": 1, "shots_per_circuit": shots,
            "circuit_count": len(circuits), "seed_simulator": seed_simulator,
            "submitted_options": options, "experiments": experiments}
