"""Circuit only: no audio, corpus, credentials or backend dependency.

Stable order theta[24*l + 2*q] = layer l RY(q), next index = RZ(q).
theta[72 + q] = final RY(q). Angles are radians. Both ablations use all 84.
Build with measure=True for backend submission, then transpile for the
supplied backend. No hardware topology or provider is assumed here.
"""

from collections.abc import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

N_QUBITS = 12
N_PARAMETERS = 84
CROSS_REGISTER_EDGES = {(2, 3), (5, 6), (8, 9), (11, 0)}


def build_circuit(*, measure: bool = False, ablate: bool = False) -> QuantumCircuit:
    theta = ParameterVector("theta", N_PARAMETERS)
    circuit = QuantumCircuit(N_QUBITS, N_QUBITS if measure else 0)
    circuit.h(range(N_QUBITS))
    for layer in range(3):
        for q in range(N_QUBITS):
            circuit.ry(theta[24 * layer + 2 * q], q)
            circuit.rz(theta[24 * layer + 2 * q + 1], q)
        for q in range(N_QUBITS):
            edge = (q, (q + 1) % N_QUBITS)
            if not (ablate and edge in CROSS_REGISTER_EDGES):
                circuit.cz(*edge)
    for q in range(N_QUBITS):
        circuit.ry(theta[72 + q], q)
    if measure:
        circuit.measure(range(N_QUBITS), range(N_QUBITS))
    circuit.metadata = {"parameter_order": "layer-major, qubit-major RY then RZ; final RY",
                        "ablation": ablate}
    return circuit


def ordered_parameters(circuit: QuantumCircuit) -> tuple:
    """Order by ParameterVectorElement.index, never lexicographic name sorting."""
    parameters = tuple(sorted(circuit.parameters, key=lambda p: p.index))
    if len(parameters) != N_PARAMETERS or [p.index for p in parameters] != list(range(84)):
        raise ValueError("Expected an unbound Quantum Motif circuit with 84 parameters")
    return parameters


def bind_parameters(circuit: QuantumCircuit, angles: Sequence[float]) -> QuantumCircuit:
    values = np.asarray(angles, dtype=float)
    if values.shape != (N_PARAMETERS,) or not np.isfinite(values).all():
        raise ValueError("Expected 84 finite angles")
    return circuit.assign_parameters(dict(zip(ordered_parameters(circuit), values)))


def random_parameters(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(-np.pi, np.pi, N_PARAMETERS)
