"""Interactive POP909 quantum harmony inference for Qollab.

Quantum boundary:
- Coarse 3-qubit and resolver 4-qubit PQCs are executed on the Qollab-supplied backend.
- Each backend submission contains exactly ONE circuit.
- Measured histograms are cached per context during the page session.
- Harmonic-colour controls are classical post-filters applied after quantum measurement.
- Rare OTHER fallback is classical, using the exported POP909 frequency table.
"""
from __future__ import annotations

import json
import hashlib
from copy import deepcopy
import secrets
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile

COARSE = ["I", "ii", "iii", "IV", "V", "vi", "vii°", "OTHER"]
RESOLVER = [
    "V:sus", "IV:min", "II:dom", "III:dom",
    "bVII:maj", "II:maj", "V:dom", "I:dom",
    "V:min", "III:maj", "bVI:maj", "VI:maj",
    "VI:dom", "#IV:hdim", "#IV:dim", "RARE_OTHER",
]
MODEL_PATH = Path("data/models.json")
_CACHE = {"coarse": {}, "resolver": {}}
_BACKENDS = {}  # Retain instances so object IDs cannot be reused during a session.

MAJOR_SCALES = {
    "C":  ["C", "D", "E", "F", "G", "A", "B"],
    "Db": ["Db", "Eb", "F", "Gb", "Ab", "Bb", "C"],
    "D":  ["D", "E", "F#", "G", "A", "B", "C#"],
    "Eb": ["Eb", "F", "G", "Ab", "Bb", "C", "D"],
    "E":  ["E", "F#", "G#", "A", "B", "C#", "D#"],
    "F":  ["F", "G", "A", "Bb", "C", "D", "E"],
    "F#": ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
    "G":  ["G", "A", "B", "C", "D", "E", "F#"],
    "Ab": ["Ab", "Bb", "C", "Db", "Eb", "F", "G"],
    "A":  ["A", "B", "C#", "D", "E", "F#", "G#"],
    "Bb": ["Bb", "C", "D", "Eb", "F", "G", "A"],
    "B":  ["B", "C#", "D#", "E", "F#", "G#", "A#"],
}
NOTE_PC = {
    "C":0, "B#":0, "C#":1, "Db":1, "D":2, "D#":3, "Eb":3,
    "E":4, "Fb":4, "E#":5, "F":5, "F#":6, "Gb":6, "G":7,
    "G#":8, "Ab":8, "A":9, "A#":10, "Bb":10, "B":11, "Cb":11,
}
FLAT_NAMES = ["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"]
SHARP_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
FLAT_KEYS = {"C", "Db", "Eb", "F", "Ab", "Bb"}
DIATONIC_DEGREE = {"I":0, "ii":1, "iii":2, "IV":3, "V":4, "vi":5, "vii°":6}
DIATONIC_QUALITY = {"I":"maj", "ii":"min", "iii":"min", "IV":"maj", "V":"maj", "vi":"min", "vii°":"dim"}
ROMAN_DEGREE = {"I":0, "II":1, "III":2, "IV":3, "V":4, "VI":5, "VII":6}
QUALITY_SUFFIX = {"maj":"", "min":"m", "dom":"7", "dim":"dim", "hdim":"m7b5", "aug":"+", "sus":"sus4", "power":"5"}
QUALITY_INTERVALS = {
    "maj":[0,4,7], "min":[0,3,7], "dom":[0,4,7,10], "dim":[0,3,6],
    "hdim":[0,3,6,10], "aug":[0,4,8], "sus":[0,5,7], "power":[0,7],
}


def _load_payload():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError("data/models.json is missing. Run tools/export_models.py first.")
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2 or payload.get("coarse_contexts") != COARSE:
        raise ValueError("models.json coarse context order is invalid")
    if payload.get("resolver_labels") != RESOLVER:
        raise ValueError("models.json resolver label order is invalid")
    return payload


def _theta(payload, family, context, qubits):
    values = np.asarray(payload[family][context], dtype=float)
    if values.ndim != 1 or len(values) == 0 or len(values) % qubits or not np.isfinite(values).all():
        raise ValueError(f"Invalid {family} theta for {context}: {values.shape}")
    return values


def _build(theta, qubits, name):
    depth = len(theta) // qubits
    qc = QuantumCircuit(qubits, qubits, name=name)
    k = 0
    for layer in range(depth):
        for q in range(qubits):
            qc.ry(float(theta[k]), q)
            k += 1
        if layer < depth - 1:
            for q in range(qubits - 1):
                qc.cx(q, q + 1)
            qc.cx(qubits - 1, 0)
    qc.measure(range(qubits), range(qubits))
    return qc


def _backend_name(backend):
    name = getattr(backend, "name", "")
    try:
        return str(name() if callable(name) else name)
    except Exception:
        return ""


def _validate_simulator(backend):
    from qiskit.providers.basic_provider import BasicSimulator
    cfg = backend.configuration() if callable(getattr(backend, "configuration", None)) else None
    verified = isinstance(backend, BasicSimulator) or (cfg is not None and getattr(cfg, "simulator", None) is True)
    if not verified:
        raise RuntimeError("Physical hardware is disabled for this demo. Select a simulator.")


def _run_one(backend, theta, qubits, labels, shots, cache_family, context):
    cache = _CACHE[cache_family]
    parameter_hash = hashlib.sha256(np.asarray(theta, dtype="<f8").tobytes()).hexdigest()
    _BACKENDS[id(backend)] = backend
    # A new backend instance may have different noise/options.
    cache_key = (context, shots, parameter_hash, id(backend))
    if cache_key in cache:
        return deepcopy(cache[cache_key]), False

    circuit = _build(theta, qubits, f"pop909_{cache_family}_{context.replace('°','dim')}")
    compiled = transpile(circuit, backend, optimization_level=0)
    job = backend.run(compiled, shots=shots)  # one circuit per submission
    result = job.result()
    if getattr(result, "success", False) is not True:
        raise RuntimeError("Backend job did not succeed")
    counts = result.get_counts()
    if not isinstance(counts, dict) or not counts:
        raise RuntimeError("Backend must return a nonempty count dictionary")

    histogram = [0] * len(labels)
    for raw_key, raw_value in counts.items():
        if not isinstance(raw_key, str):
            raise RuntimeError("Count keys must be bit strings")
        bits = raw_key.replace(" ", "")
        if len(bits) != qubits or set(bits) - {"0", "1"}:
            raise RuntimeError(f"Unsupported count key {raw_key!r}; expected {qubits} bits")
        if isinstance(raw_value, (bool, np.bool_)) or not isinstance(raw_value, (int, np.integer)):
            raise RuntimeError("Counts must be integers, not probabilities")
        value = int(raw_value)
        if value < 0:
            raise RuntimeError("Backend returned a negative count")
        histogram[int(bits, 2)] += value
    if sum(histogram) != shots:
        raise RuntimeError(f"Expected {shots} shots, received {sum(histogram)}")

    record = {
        "context": context, "labels": labels, "counts": histogram,
        "probabilities": [count / shots for count in histogram],
        "shots": shots, "backend_name": _backend_name(backend),
        "backend_class": f"{type(backend).__module__}.{type(backend).__name__}",
        "job_id": str(job.job_id()) if callable(getattr(job, "job_id", None)) else None,
        "qubits": qubits, "depth": len(theta) // qubits, "parameters": len(theta),
        "parameter_sha256": parameter_hash,
    }
    cache[cache_key] = record
    return deepcopy(record), True


def _filtered_probs(probs, colour):
    p = np.asarray(probs, dtype=float).copy()
    if colour == "diatonic":
        p[COARSE.index("OTHER")] = 0.0
    elif colour == "chromatic":
        p[COARSE.index("OTHER")] *= 2.5
    elif colour != "original":
        raise ValueError("colour must be diatonic, original, or chromatic")
    total = p.sum()
    if total <= 0:
        raise RuntimeError("Post-filter produced an empty distribution")
    return p / total


def _rare_choice(payload, rng):
    labels = payload.get("rare_labels", [])
    weights = np.asarray(payload.get("rare_weights", []), dtype=float)
    if weights.ndim != 1 or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Rare-class weights must be finite and nonnegative")
    if labels and len(labels) == len(weights) and weights.sum() > 0:
        weights /= weights.sum()
        return str(rng.choice(labels, p=weights)), "classical POP909 rare-class frequency"
    return "I", "tonic fallback; rare table unavailable"


def _quality_name(q):
    for name in ("hdim", "maj", "min", "dim", "aug", "sus", "power", "dom"):
        if q == name or q.startswith(name):
            return name
    return "maj"


def _parse_degree_token(token):
    shift = 0
    while token.startswith("b"):
        shift -= 1
        token = token[1:]
    while token.startswith("#"):
        shift += 1
        token = token[1:]
    numeral = token.upper()
    if numeral not in ROMAN_DEGREE:
        raise ValueError(f"Unsupported degree token {token!r}")
    return ROMAN_DEGREE[numeral], shift


def _root_name(key, degree_index, shift=0):
    scale = MAJOR_SCALES[key]
    base = scale[degree_index]
    if shift == 0:
        return base
    pc = (NOTE_PC[base] + shift) % 12
    names = FLAT_NAMES if key in FLAT_KEYS or shift < 0 else SHARP_NAMES
    return names[pc]


def _label_info(label, key):
    if label in DIATONIC_DEGREE:
        degree = DIATONIC_DEGREE[label]
        quality = DIATONIC_QUALITY[label]
        root = _root_name(key, degree)
    else:
        if ":" not in label:
            raise ValueError(f"Unsupported chord label {label!r}")
        token, q = label.split(":", 1)
        degree, shift = _parse_degree_token(token)
        quality = _quality_name(q)
        root = _root_name(key, degree, shift)

    symbol = root + QUALITY_SUFFIX[quality]
    root_pc = NOTE_PC[root]
    root_midi = 60 + root_pc
    if root_midi > 71:
        root_midi -= 12
    midi = [root_midi + interval for interval in QUALITY_INTERVALS[quality]]
    return {
        "label": label, "symbol": symbol, "root": root, "root_pc": root_pc,
        "quality": quality, "midi": midi, "bass_midi": 36 + root_pc,
    }


def generate_progression(backend, key="C", bars=16, colour="original", shots=1024, seed=None):
    if key not in MAJOR_SCALES:
        raise ValueError("Select one of the supported major keys")
    if bars not in (8, 16, 32):
        raise ValueError("bars must be 8, 16, or 32")
    if type(shots) is not int or not 16 <= shots <= 4096:
        raise ValueError("shots must be an integer from 16 to 4096")
    if colour not in ("diatonic", "original", "chromatic"):
        raise ValueError("Unsupported harmonic colour")
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("seed must be a nonnegative integer")

    _validate_simulator(backend)
    payload = _load_payload()
    seed = secrets.randbits(63) if seed is None else int(seed)
    rng = np.random.default_rng(seed)
    current = "I"
    coarse_sequence = ["I"]
    resolved_sequence = ["I"]
    steps = []
    new_jobs = 0
    cache_hits = 0

    for step_index in range(1, bars):
        coarse_theta = _theta(payload, "coarse_theta", current, 3)
        coarse_record, was_new = _run_one(backend, coarse_theta, 3, COARSE, shots, "coarse", current)
        new_jobs += int(was_new); cache_hits += int(not was_new)
        effective = _filtered_probs(coarse_record["probabilities"], colour)
        coarse_idx = int(rng.choice(len(COARSE), p=effective))
        nxt = COARSE[coarse_idx]
        resolver_record = None
        resolver_idx = None
        fallback = None

        if nxt == "OTHER":
            resolver_theta = _theta(payload, "resolver_theta", current, 4)
            resolver_record, was_new = _run_one(backend, resolver_theta, 4, RESOLVER, shots, "resolver", current)
            new_jobs += int(was_new); cache_hits += int(not was_new)
            resolver_idx = int(rng.choice(len(RESOLVER), p=resolver_record["probabilities"]))
            concrete = RESOLVER[resolver_idx]
            if concrete == "RARE_OTHER":
                concrete, fallback = _rare_choice(payload, rng)
        else:
            concrete = nxt

        steps.append({
            "step": step_index,
            "previous_coarse": current,
            "coarse": coarse_record,
            "effective_coarse_probabilities": effective.tolist(),
            "harmonic_colour": colour,
            "sampled_coarse_index": coarse_idx,
            "sampled_coarse": nxt,
            "resolver": resolver_record,
            "sampled_resolver_index": resolver_idx,
            "resolved_label": concrete,
            "fallback": fallback,
        })
        coarse_sequence.append(nxt)
        resolved_sequence.append(concrete)
        current = nxt

    chord_info = [_label_info(label, key) for label in resolved_sequence]
    return json.dumps({
        "schema_version": 2,
        "key": f"{key} major",
        "bars": bars,
        "seed": seed,
        "shots": shots,
        "harmonic_colour": colour,
        "coarse_sequence": coarse_sequence,
        "resolved_sequence": resolved_sequence,
        "chords": chord_info,
        "steps": steps,
        "execution": {
            "backend_name": _backend_name(backend),
            "backend_class": f"{type(backend).__module__}.{type(backend).__name__}",
            "new_quantum_jobs": new_jobs,
            "cache_hits": cache_hits,
            "submission_policy": "one circuit per backend.run call",
        },
        "model": {
            "checkpoint_payload_sha256": hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
            "coarse": "3-qubit POP909 PQC",
            "resolver": "4-qubit POP909 OTHER resolver",
            "training_scope": "POP909 major-key sections",
        },
        "controls": {
            "harmonic_colour_note": "Diatonic/Chromatic are classical post-filters applied after quantum measurement; Original uses the measured coarse distribution unchanged.",
            "playback_note": "Browser audio rendering is classical and does not request quantum shots.",
        },
    }, ensure_ascii=False, allow_nan=False)


def clear_cache():
    _CACHE["coarse"].clear(); _CACHE["resolver"].clear()
    _BACKENDS.clear()
    return json.dumps({"status": "cleared"})
