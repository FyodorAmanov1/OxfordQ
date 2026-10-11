"""Qollab asynchronous JS-to-Python entry. No native audio or external service."""
import json
from pathlib import Path
import qiskit
import numpy as np
from quantum_engine import QiskitDynamics, run_entrance
from composer import compose
from score_writer import midi_bytes


def load_piano():
    # Literal path required by Qollab's static data-file loader.
    path = Path('data/piano.json')
    if not path.exists():
        path = Path(__file__).resolve().parent / 'data/piano.json'
    return path.read_text(encoding='utf-8')


def generate(backend, seed=1201, bars=64, bpm=104, shots=512, phase_bias=0.65):
    if type(bars) is not int or not 8 <= bars <= 64:
        raise ValueError('Bars must be 8..64')
    if not np.isfinite(bpm) or not 50 <= bpm <= 180:
        raise ValueError('Tempo must be 50..180 BPM')
    prior, execution = run_entrance(backend, int(seed), int(shots), float(phase_bias))
    score = compose(seed=int(seed), bars=bars, bpm=float(bpm), steps=64,
                    interaction=float(phase_bias), contour_prior=prior, engine=QiskitDynamics())
    score['metadata']['execution'] = execution
    score['metadata']['qiskit_version'] = qiskit.__version__
    score['metadata']['numpy_version'] = np.__version__
    score['metadata']['attribution'] = 'This effort is supported by Qollab & IonQ'
    score['midi_base64'] = __import__('base64').b64encode(midi_bytes(score)).decode()
    return json.dumps(score, allow_nan=False)
