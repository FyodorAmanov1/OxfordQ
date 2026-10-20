"""Qiskit reference and verified batched differentiable exact statevector."""
import numpy as np
import torch
from torch import nn
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import Statevector
from .encoding import FEATURES, AGGREGATION

EPS = 1e-9
LAYERS = 3

def projection(layers=LAYERS):
    # Fixed public encoder, never fitted on validation or test material.
    rng = np.random.default_rng(20261011)
    return rng.normal(0, 1 / np.sqrt(FEATURES), (layers, 8, 2, FEATURES))

def encoded_angles(features, layers=LAYERS):
    return np.pi * np.einsum('...f,lqaf->...lqa', features, projection(layers))

def build_circuit(layers=LAYERS, measure=False):
    qc = QuantumCircuit(8, 7 if measure else 0)
    theta, data = ParameterVector('theta', layers*16), ParameterVector('context', layers*16)
    qc.h(range(8))
    for layer in range(layers):
        for q in range(8):
            i = layer*16 + q*2
            qc.ry(data[i], q); qc.rz(data[i+1], q)
            qc.ry(theta[i], q); qc.rz(theta[i+1], q)
        # Connected ring couples pitch, register, duration and latent q7.
        for q in range(8):
            qc.cx(q, (q+1) % 8)
    qc.h(range(8))  # expose final-layer phase rotations to measurement
    if measure:
        qc.measure(range(7), range(7))
    return qc, tuple(theta), tuple(data)

def bind_parameters(theta, features):
    theta = np.asarray(theta, dtype=float)
    layers = theta.size // 16
    if theta.shape != (layers*16,) or layers < 1 or np.shape(features) != (FEATURES,):
        raise ValueError('Unexpected parameter/context shape')
    qc, parameters, inputs = build_circuit(layers)
    return qc.assign_parameters(dict(zip(parameters + inputs,
        np.concatenate([theta, encoded_angles(features, layers).reshape(-1)]))))

def qiskit_probabilities(theta, features):
    state = Statevector.from_instruction(bind_parameters(theta, features))
    # State basis index q7...q0: sum q7, keeping little-endian low 7 bits.
    measured = state.probabilities().reshape(2, 128).sum(axis=0)
    return measured @ AGGREGATION

def normalize_legal(probabilities, remaining):
    """Add declared epsilon ONLY to legal tokens, then normalize. Same train/sample."""
    if torch.any((remaining < 1) | (remaining > 8)):
        raise ValueError('Invalid remaining bar duration')
    legal = (torch.arange(120, device=probabilities.device) % 8 + 1)[None, :] <= remaining[:, None]
    p = (probabilities + EPS) * legal
    return p / p.sum(dim=-1, keepdim=True)

class QuantumModel(nn.Module):
    def __init__(self, seed=0, layers=LAYERS):
        super().__init__()
        rng = np.random.default_rng(seed)
        self.layers = layers
        self.theta = nn.Parameter(torch.tensor(rng.normal(0, .25, layers*16), dtype=torch.float64))
        self.register_buffer('encoder', torch.tensor(projection(layers)))
        self.register_buffer('aggregation', torch.tensor(AGGREGATION))
        indices = torch.arange(256)
        self.register_buffer('indices', indices)
        for q in range(8):
            self.register_buffer(f'flip{q}', indices ^ (1 << q))
            self.register_buffer(f'sign{q}', (2*((indices >> q) & 1)-1).double())
            target = (q+1) % 8
            self.register_buffer(f'cx{q}', indices ^ (((indices >> q) & 1) << target))

    def statevector(self, x):
        state = torch.ones((len(x), 256), dtype=torch.complex128, device=x.device) / 16
        angles = torch.pi * torch.einsum('bf,lqaf->blqa', x, self.encoder)
        for layer in range(self.layers):
            for q in range(8):
                i = layer*16 + q*2
                for ry, rz in ((angles[:, layer, q, 0], angles[:, layer, q, 1]),
                               (self.theta[i].expand(len(x)), self.theta[i+1].expand(len(x)))):
                    c, s = torch.cos(ry[:, None]/2), torch.sin(ry[:, None]/2)
                    sign = getattr(self, f'sign{q}')
                    state = c*state + s*state[:, getattr(self, f'flip{q}')]*sign
                    state = state * torch.exp(.5j*rz[:, None]*sign)
            for q in range(8):
                state = state[:, getattr(self, f'cx{q}')]
        for q in range(8):
            state = (state[:, getattr(self, f'flip{q}')] - state*getattr(self, f'sign{q}')) / np.sqrt(2)
        return state

    def joint(self, x):
        p = self.statevector(x).abs().square().reshape(-1, 2, 128).sum(dim=1)
        return p @ self.aggregation

    def forward(self, x, remaining):
        return normalize_legal(self.joint(x), remaining)

    def parameter_count(self):
        return self.theta.numel()

def verify_equivalence():
    torch.set_num_threads(1)
    errors = []
    for seed in (0, 7, 31):
        model = QuantumModel(seed)
        x = np.random.default_rng(seed+300).uniform(-1, 1, (4, FEATURES))
        with torch.no_grad():
            actual = model.joint(torch.tensor(x)).numpy()
        for i, row in enumerate(x):
            expected = qiskit_probabilities(model.theta.detach().numpy(), row)
            errors.append(float(np.max(np.abs(actual[i]-expected))))
    maximum = max(errors)
    if maximum > 1e-10:
        raise AssertionError(f'Qiskit equivalence failed: {maximum}')
    return {'contexts': 12, 'parameter_seeds': 3, 'max_absolute_error': maximum,
            'tolerance': 1e-10, 'passed': True}
