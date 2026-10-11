"""Qiskit evolution and a single-job, six-qubit musical entrance circuit.

The selected backend supplies the contour prior. Persistent 13-qubit evolution
is explicitly an ideal statevector calculation, including hypothetical readout.
"""
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator, Statevector
from graph import MusicalGraph


class QiskitDynamics:
    def __init__(self):
        self.operators = {}

    def step(self, graph, state, duration, interaction, feedback, steps):
        key = (graph.shape, float(duration), int(steps))
        if key not in self.operators:
            self.operators[key] = [Operator(u) for u in graph.gates(duration, steps)]
        axes, low = [], 0
        for size in reversed(graph.shape):
            width = int(np.log2(size))
            axes.insert(0, list(range(low, low + width)))
            low += width
        phase = np.exp(-0.5j * duration / steps *
                       (interaction * graph.interaction + np.asarray(feedback).reshape(graph.shape))).ravel()
        psi = Statevector(np.asarray(state).ravel().copy())
        for _ in range(steps):
            # Exact diagonal unitary, applied elementwise to avoid a dense
            # 8192-by-8192 matrix. This is the same DiagonalGate action.
            psi.data[:] *= phase
            for operator, qubits in zip(self.operators[key], axes):
                psi = psi.evolve(operator, qargs=qubits)
            psi.data[:] *= phase
        return psi.data.reshape(graph.shape)


def entrance_circuit(seed=1201, phase_bias=0.65, measure=True):
    """Three interval registers walk on four-node paths, coupled by ZZ phases.

    Q5,Q4 encode the first interval, Q3,Q2 the second, Q1,Q0 the third.
    High bits encode interval direction. Interaction changes joint gesture
    probabilities through interference with subsequent path-walk unitaries.
    """
    graph = MusicalGraph()
    random = np.random.default_rng(np.random.SeedSequence([seed, 503]))
    circuit = QuantumCircuit(6, name='musical_contour_walk')
    for q, phase in enumerate(random.uniform(-np.pi, np.pi, 6)):
        circuit.h(q)
        circuit.rz(float(phase), q)
    dt = 0.74 / 4
    for _ in range(4):
        circuit.rzz(float(phase_bias * dt), 5, 3)
        circuit.rzz(float(0.8 * phase_bias * dt), 3, 1)
        for axis, qubits in enumerate(([4, 5], [2, 3], [0, 1])):
            circuit.unitary(graph.gates(0.74, 4)[axis], qubits)
        circuit.rzz(float(phase_bias * dt), 5, 3)
        circuit.rzz(float(0.8 * phase_bias * dt), 3, 1)
    if measure:
        circuit.measure_all()
    return circuit


def run_entrance(backend, seed=1201, shots=512, phase_bias=0.65):
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Seed must be an integer in 0..4294967295')
    if type(shots) is not int or not 64 <= shots <= 4096:
        raise ValueError('Shots must be 64..4096')
    if not np.isfinite(phase_bias) or not 0 <= phase_bias <= 2:
        raise ValueError('Phase interaction must be 0..2')
    name = getattr(backend, 'name', 'unknown')
    name = str(name() if callable(name) else name)
    configuration = backend.configuration() if callable(getattr(backend, 'configuration', None)) else None
    if configuration is not None and getattr(configuration, 'simulator', True) is False:
        raise ValueError('Choose a FREE simulator; physical hardware is disabled')
    if 'ionq' in type(backend).__module__.lower() and 'simulator' not in name.lower():
        raise ValueError('Choose an IonQ simulator, not a quantum computer')
    qubits = getattr(backend, 'num_qubits', None) or getattr(configuration, 'n_qubits', None)
    maximum = getattr(configuration, 'max_shots', None)
    if qubits is not None and qubits < 6:
        raise ValueError('The selected simulator needs six qubits')
    if maximum is not None and shots > maximum:
        raise ValueError('Shots exceed the advertised simulator limit')
    circuit = entrance_circuit(seed, phase_bias)
    # A portable one/two-qubit gate circuit, rather than opaque unitaries.
    circuit = transpile(circuit, basis_gates=['rx','ry','rz','cx'], optimization_level=1)
    circuit = transpile(circuit, backend, optimization_level=1)
    job = backend.run(circuit, shots=shots)  # Exactly one call on every backend.
    result = job.result()
    counts = result.get_counts()
    if not isinstance(counts, dict) or not counts:
        raise RuntimeError('Simulator returned no measurement counts')
    frequencies = np.zeros(64)
    for bits, n in counts.items():
        key = str(bits).replace(' ', '')
        if len(key) != 6 or set(key) - {'0', '1'} or type(n) is not int or n < 0:
            raise RuntimeError('Invalid six-bit simulator measurement')
        frequencies[int(key, 2)] += n
    if int(frequencies.sum()) != shots:
        raise RuntimeError('Simulator returned an unexpected number of shots')
    # Disclosed classical half-count smoothing, not invented backend counts.
    prior = (frequencies + 0.5) / (shots + 32)
    return prior, {'backend_name': name,
        'backend_class': type(backend).__module__ + '.' + type(backend).__name__,
        'job_id': str(job.job_id()), 'backend_run_calls': 1, 'circuits': 1,
        'qubits': 6, 'shots': shots, 'counts': counts, 'phase_bias': phase_bias,
        'compiled_depth': circuit.depth(), 'compiled_gates': len(circuit.data),
        'ideal_continuation_qubits': 13, 'smoothing_pseudocount_per_node': 0.5,
        'continuation': 'Explicit ideal Qiskit Statevector simulation; not the selected QPU',
        'readout': 'Ideal non-disturbing access to the continuation state probabilities'}
