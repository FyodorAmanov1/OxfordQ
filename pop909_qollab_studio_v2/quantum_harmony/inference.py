"Interactive POP909 quantum harmony inference for Qollab."

from __future__ import annotations

import json
import secrets
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile

MODEL_PATH = Path("data/models.json")
_CACHE = {"coarse": {}, "resolver": {}}

MAJOR_COARSE = ["I", "ii", "iii", "IV", "V", "vi", "vii°", "OTHER"]
MINOR_COARSE = ["i", "III", "iv", "v", "V", "VI", "VII", "OTHER"]

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

MAJOR_DIATONIC_DEGREE = {"I":0, "ii":1, "iii":2, "IV":3, "V":4, "vi":5, "vii°":6}
MAJOR_DIATONIC_QUALITY = {"I":"maj", "ii":"min", "iii":"min", "IV":"maj", "V":"maj", "vi":"min", "vii°":"dim"}

MINOR_CORE_DEGREE = {"i":0, "III":2, "iv":3, "v":4, "V":4, "VI":5, "VII":6}
MINOR_CORE_QUALITY = {"i":"min", "III":"maj", "iv":"min", "v":"min", "V":"maj", "VI":"maj", "VII":"maj"}

ROMAN_DEGREE = {"I":0, "II":1, "III":2, "IV":3, "V":4, "VI":5, "VII":6}
MINOR_INTERVALS = [0, 2, 3, 5, 7, 8, 10]

QUALITY_SUFFIX = {
    "maj":"", "min":"m", "dom":"7", "dim":"dim",
    "hdim":"m7b5", "aug":"+", "sus":"sus4", "power":"5",
}
QUALITY_INTERVALS = {
    "maj":[0,4,7], "min":[0,3,7], "dom":[0,4,7,10], "dim":[0,3,6],
    "hdim":[0,3,6,10], "aug":[0,4,8], "sus":[0,5,7], "power":[0,7],
}


def _load_payload(mode):
    if not MODEL_PATH.is_file():
        raise FileNotFoundError("data/models.json is missing. Run tools/export_models.py first.")

    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    mode = str(mode).lower()

    if payload.get("schema_version") == 3 and "modes" in payload:
        if mode not in payload["modes"]:
            raise ValueError(f"Unsupported mode {mode!r}")
        model = payload["modes"][mode]
    elif payload.get("schema_version") == 2 and mode == "major":
        model = payload
    else:
        raise ValueError("models.json does not contain the requested trained mode")

    expected = MAJOR_COARSE if mode == "major" else MINOR_COARSE
    if model.get("coarse_contexts") != expected:
        raise ValueError(f"models.json {mode} coarse context order is invalid")

    resolver = model.get("resolver_labels", [])
    if len(resolver) != 16 or resolver[-1] != "RARE_OTHER":
        raise ValueError(f"models.json {mode} resolver labels are invalid")

    return model


def _theta(payload, family, context, qubits):
    values = np.asarray(payload[family][context], dtype=float)
    if values.ndim != 1 or len(values) == 0 or len(values) % qubits:
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
    cfg = backend.configuration() if callable(getattr(backend, "configuration", None)) else None
    if cfg is not None and getattr(cfg, "simulator", True) is False:
        raise RuntimeError("Physical hardware is disabled for this demo. Select a simulator.")


def _run_one(backend, theta, qubits, labels, shots, cache_family, context, mode):
    cache = _CACHE[cache_family]
    cache_key = (
        mode, context, shots, _backend_name(backend),
        type(backend).__module__, type(backend).__name__,
    )
    if cache_key in cache:
        return cache[cache_key], False

    safe_context = context.replace("°", "dim")
    circuit = _build(theta, qubits, f"pop909_{mode}_{cache_family}_{safe_context}")
    compiled = transpile(circuit, backend, optimization_level=0)
    job = backend.run(compiled, shots=shots)
    result = job.result()
    counts = result.get_counts()

    histogram = [0] * len(labels)
    for raw_key, raw_value in counts.items():
        bits = str(raw_key).replace(" ", "")
        if len(bits) != qubits or set(bits) - {"0", "1"}:
            raise RuntimeError(f"Unsupported count key {raw_key!r}; expected {qubits} bits")
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
        "mode": mode,
    }
    cache[cache_key] = record
    return record, True


def _filtered_probs(probs, colour, coarse_labels):
    p = np.asarray(probs, dtype=float).copy()
    other_index = coarse_labels.index("OTHER")
    if colour == "diatonic":
        p[other_index] = 0.0
    elif colour == "chromatic":
        p[other_index] *= 2.5
    elif colour != "original":
        raise ValueError("colour must be diatonic, original, or chromatic")
    total = p.sum()
    if total <= 0:
        raise RuntimeError("Post-filter produced an empty distribution")
    return p / total


def _rare_choice(payload, rng, tonic_label):
    labels = payload.get("rare_labels", [])
    weights = np.asarray(payload.get("rare_weights", []), dtype=float)
    if labels and len(labels) == len(weights) and weights.sum() > 0:
        weights /= weights.sum()
        return str(rng.choice(labels, p=weights)), "classical POP909 rare-class frequency"
    return tonic_label, "tonic fallback; rare table unavailable"


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


def _root_name(key, degree_index, shift=0, mode="major"):
    if mode == "major":
        scale = MAJOR_SCALES[key]
        base = scale[degree_index]
        if shift == 0:
            return base
        pc = (NOTE_PC[base] + shift) % 12
    else:
        pc = (NOTE_PC[key] + MINOR_INTERVALS[degree_index] + shift) % 12

    names = FLAT_NAMES if key in FLAT_KEYS or shift < 0 else SHARP_NAMES
    return names[pc]


def _label_info(label, key, mode):
    if mode == "major" and label in MAJOR_DIATONIC_DEGREE:
        degree = MAJOR_DIATONIC_DEGREE[label]
        quality = MAJOR_DIATONIC_QUALITY[label]
        root = _root_name(key, degree, mode=mode)
    elif mode == "minor" and label in MINOR_CORE_DEGREE:
        degree = MINOR_CORE_DEGREE[label]
        quality = MINOR_CORE_QUALITY[label]
        root = _root_name(key, degree, mode=mode)
    else:
        if ":" not in label:
            raise ValueError(f"Unsupported chord label {label!r}")
        token, q = label.split(":", 1)
        degree, shift = _parse_degree_token(token)
        quality = _quality_name(q)
        root = _root_name(key, degree, shift, mode)

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


def generate_progression(backend, key="C", bars=16, colour="original", shots=1024, seed=None, mode="major"):
    mode = str(mode).lower()
    if mode not in ("major", "minor"):
        raise ValueError("mode must be major or minor")
    if key not in MAJOR_SCALES:
        raise ValueError("Select one of the supported keys")
    if bars not in (8, 16, 32):
        raise ValueError("bars must be 8, 16, or 32")
    if type(shots) is not int or not 16 <= shots <= 4096:
        raise ValueError("shots must be an integer from 16 to 4096")

    _validate_simulator(backend)
    payload = _load_payload(mode)
    coarse_labels = payload["coarse_contexts"]
    resolver_labels = payload["resolver_labels"]
    tonic = "I" if mode == "major" else "i"

    seed = secrets.randbits(63) if seed is None else int(seed)
    rng = np.random.default_rng(seed)
    current = tonic
    coarse_sequence = [tonic]
    resolved_sequence = [tonic]
    steps = []
    new_jobs = 0
    cache_hits = 0

    for step_index in range(1, bars):
        coarse_theta = _theta(payload, "coarse_theta", current, 3)
        coarse_record, was_new = _run_one(
            backend, coarse_theta, 3, coarse_labels, shots,
            "coarse", current, mode,
        )
        new_jobs += int(was_new)
        cache_hits += int(not was_new)

        effective = _filtered_probs(coarse_record["probabilities"], colour, coarse_labels)
        coarse_idx = int(rng.choice(len(coarse_labels), p=effective))
        nxt = coarse_labels[coarse_idx]

        resolver_record = None
        resolver_idx = None
        fallback = None

        if nxt == "OTHER":
            resolver_theta = _theta(payload, "resolver_theta", current, 4)
            resolver_record, was_new = _run_one(
                backend, resolver_theta, 4, resolver_labels, shots,
                "resolver", current, mode,
            )
            new_jobs += int(was_new)
            cache_hits += int(not was_new)
            resolver_idx = int(rng.choice(len(resolver_labels), p=resolver_record["probabilities"]))
            concrete = resolver_labels[resolver_idx]
            if concrete == "RARE_OTHER":
                concrete, fallback = _rare_choice(payload, rng, tonic)
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

    chord_info = [_label_info(label, key, mode) for label in resolved_sequence]

    return json.dumps({
        "schema_version": 3,
        "mode": mode,
        "key": f"{key} {mode}",
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
            "coarse": f"3-qubit POP909 {mode} PQC",
            "resolver": f"4-qubit POP909 {mode} OTHER resolver",
            "training_scope": f"POP909 {mode}-key sections",
        },
        "controls": {
            "harmonic_colour_note": (
                "In-key removes OTHER after quantum measurement; "
                "Adventurous boosts OTHER classically; "
                "Authentic uses the measured coarse distribution unchanged."
            ),
            "playback_note": "Browser audio rendering is classical and does not request quantum shots.",
        },
    }, ensure_ascii=False, allow_nan=False)


def clear_cache():
    _CACHE["coarse"].clear()
    _CACHE["resolver"].clear()
    return json.dumps({"status": "cleared"})
