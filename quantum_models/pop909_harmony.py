"""POP909 hierarchical quantum harmony integration for OxfordQ."""
from __future__ import annotations

import csv
import hashlib
import json
from importlib.resources import files
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from music21 import key as m21key
from music21 import pitch as m21pitch
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


COARSE = ["I", "ii", "iii", "IV", "V", "vi", "vii°", "OTHER"]
RESOLVER = [
    "V:sus", "IV:min", "II:dom", "III:dom",
    "bVII:maj", "II:maj", "V:dom", "I:dom",
    "V:min", "III:maj", "bVI:maj", "VI:maj",
    "VI:dom", "#IV:hdim", "#IV:dim", "RARE_OTHER",
]

DEGREE_TO_SEMITONE = {
    "I": 0, "bII": 1, "II": 2, "bIII": 3,
    "III": 4, "IV": 5, "#IV": 6, "V": 7,
    "bVI": 8, "VI": 9, "bVII": 10, "VII": 11,
}
DIATONIC_ROOT = {"I": 0, "ii": 2, "iii": 4, "IV": 5, "V": 7, "vi": 9, "vii°": 11}
DIATONIC_SUFFIX = {"I": "", "ii": "m", "iii": "m", "IV": "", "V": "", "vi": "m", "vii°": "dim"}
QUALITY_SUFFIX = {
    "maj": "", "min": "m", "dom": "7", "dim": "dim",
    "hdim": "m7b5", "aug": "+", "sus": "sus4", "power": "5",
}


@dataclass
class HarmonyStep:
    step: int
    previous_coarse: str
    coarse_bits: str
    next_coarse: str
    resolver_bits: str | None = None
    resolved_label: str | None = None
    fallback: str | None = None


@dataclass
class QuantumHarmonyResult:
    key: str
    coarse_sequence: list[str]
    resolved_sequence: list[str]
    chord_symbols: list[str]
    steps: list[HarmonyStep]
    source: dict[str, str]

    def to_dict(self):
        return {
            "key": self.key,
            "coarse_sequence": self.coarse_sequence,
            "resolved_sequence": self.resolved_sequence,
            "chord_symbols": self.chord_symbols,
            "display_chord_symbols": [
                symbol.replace("-", "b")
                for symbol in self.chord_symbols
            ],
            "steps": [asdict(x) for x in self.steps],
            "source": self.source,
        }


def _load_models(path, qubits):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)

    models = {}
    with np.load(path, allow_pickle=False) as data:
        for i, context in enumerate(COARSE):
            key = f"theta_{i}"
            if key not in data.files:
                raise ValueError(f"{path} is missing {key}")
            models[context] = data[key]
    return _validate_family(models, qubits)


def _validate_family(models, qubits):
    if set(models) != set(COARSE):
        raise ValueError("Require all eight coarse contexts in each checkpoint family")
    validated = {}
    for context in COARSE:
        theta = np.asarray(models[context], dtype=float).copy()
        if theta.ndim != 1 or not theta.size or theta.size % qubits or not np.isfinite(theta).all():
            raise ValueError(f"Invalid finite {qubits}-qubit checkpoint for {context}")
        theta.flags.writeable = False
        validated[context] = theta
    if len({len(theta) for theta in validated.values()}) != 1:
        raise ValueError("Checkpoint depths must agree across contexts")
    return validated


def _ring_circuit(theta, qubits):
    depth = len(theta) // qubits
    qc = QuantumCircuit(qubits)
    k = 0

    for layer in range(depth):
        for q in range(qubits):
            qc.ry(float(theta[k]), q)
            k += 1

        if layer < depth - 1:
            for q in range(qubits - 1):
                qc.cx(q, q + 1)
            qc.cx(qubits - 1, 0)

    return qc


def _sample(theta, qubits, labels, rng):
    state = Statevector.from_instruction(_ring_circuit(theta, qubits))
    probs = np.asarray(state.probabilities(), dtype=float)
    probs /= probs.sum()
    index = int(rng.choice(len(labels), p=probs))
    return format(index, f"0{qubits}b"), labels[index]


def _load_rare(path):
    if path is None or not Path(path).is_file():
        return [], np.array([], dtype=float)

    labels, weights = [], []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if int(row["rank"]) <= 15:
                continue
            labels.append(row["other_class"])
            weights.append(float(row["count"]))

    weights = np.asarray(weights, dtype=float)
    if not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Rare-class frequencies must be finite and nonnegative")
    if weights.size and weights.sum() > 0:
        weights /= weights.sum()

    return labels, weights


def _quality(q):
    if q in QUALITY_SUFFIX:
        return q
    for prefix, replacement in [
        ("maj", "maj"), ("min", "min"), ("hdim", "hdim"),
        ("dim", "dim"), ("aug", "aug"), ("sus", "sus"),
    ]:
        if q.startswith(prefix):
            return replacement
    return "maj"


ROMAN_DEGREE_NUMBER = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
}

DIATONIC_DEGREE = {
    "I": "I",
    "ii": "II",
    "iii": "III",
    "IV": "IV",
    "V": "V",
    "vi": "VI",
    "vii°": "VII",
}


def _degree_root_name(tonality, degree_token):
    """
    Spell a scale degree correctly rather than choosing an arbitrary
    enharmonic equivalent.

    Examples in C major:
        bVI  -> Ab, not G#
        bVII -> Bb, not A#
        #IV  -> F#, not Gb
    """
    token = degree_token
    chromatic_shift = 0

    while token.startswith("b"):
        chromatic_shift -= 1
        token = token[1:]

    while token.startswith("#"):
        chromatic_shift += 1
        token = token[1:]

    numeral = token.upper()

    if numeral not in ROMAN_DEGREE_NUMBER:
        raise ValueError(f"Unsupported Roman degree: {degree_token!r}")

    degree_number = ROMAN_DEGREE_NUMBER[numeral]

    # Start from the correctly spelled diatonic scale degree.
    root = tonality.getScale().pitchFromDegree(degree_number)

    # Preserve the scale-degree LETTER NAME and modify only its accidental.
    # For example in C major:
    #   A + flat  -> Ab
    # rather than allowing chromatic transpose to respell it as G#.
    current_alter = (
        float(root.accidental.alter)
        if root.accidental is not None
        else 0.0
    )

    new_alter = current_alter + chromatic_shift

    if new_alter == 0:
        root.accidental = None
    else:
        root.accidental = m21pitch.Accidental(new_alter)

    # Keep music21's internal flat notation ("A-" rather than "Ab").
    # Human-readable conversion is done only when displaying the result.
    return root.name


def label_to_chord_symbol(label, key_name="C major"):
    words = key_name.strip().split()

    if len(words) == 1:
        tonality = m21key.Key(words[0])
    elif len(words) == 2 and words[1].lower() in {"major", "minor"}:
        tonality = m21key.Key(words[0], words[1].lower())
    else:
        raise ValueError(
            "Key must be a tonic and optional mode, e.g. 'C major' or 'A minor'"
        )

    if tonality.mode != "major":
        raise ValueError(
            "The POP909 model was trained on major-key sections only."
        )

    # Ordinary diatonic chord.
    if label in DIATONIC_DEGREE:
        root = _degree_root_name(
            tonality,
            DIATONIC_DEGREE[label],
        )
        return root + DIATONIC_SUFFIX[label]

    # Chromatic / altered OTHER-resolver chord.
    if ":" not in label:
        raise ValueError(
            f"Unsupported POP909 chord label: {label}"
        )

    degree, q = label.split(":", 1)

    root = _degree_root_name(
        tonality,
        degree,
    )

    return root + QUALITY_SUFFIX[_quality(q)]



class Pop909QuantumHarmony:
    """Load the existing theta_0 ... theta_7 archives and generate harmony."""

    def __init__(self, coarse_model_path, resolver_model_path, rare_ranking_csv=None):
        self.coarse_models = _load_models(coarse_model_path, 3)
        self.resolver_models = _load_models(resolver_model_path, 4)
        self.rare_labels, self.rare_weights = _load_rare(rare_ranking_csv)
        self.checkpoint_source = {
            "coarse_checkpoint_sha256": hashlib.sha256(Path(coarse_model_path).read_bytes()).hexdigest(),
            "resolver_checkpoint_sha256": hashlib.sha256(Path(resolver_model_path).read_bytes()).hexdigest(),
        }
        if rare_ranking_csv is not None and Path(rare_ranking_csv).is_file():
            self.checkpoint_source["rare_table_sha256"] = hashlib.sha256(Path(rare_ranking_csv).read_bytes()).hexdigest()

    @classmethod
    def from_json(cls, path=None):
        """Load the unchanged exported checkpoint shipped with this package."""
        raw = Path(path).read_bytes() if path is not None else files("quantum_models").joinpath("data/pop909_models.json").read_bytes()
        payload = json.loads(raw)
        if payload.get("schema_version") != 2 or payload.get("coarse_contexts") != COARSE or payload.get("resolver_labels") != RESOLVER:
            raise ValueError("Unknown POP909 checkpoint schema or label order")
        instance = cls.__new__(cls)
        instance.coarse_models = _validate_family(payload["coarse_theta"], 3)
        instance.resolver_models = _validate_family(payload["resolver_theta"], 4)
        instance.rare_labels = payload.get("rare_labels", [])
        weights = np.asarray(payload.get("rare_weights", []), dtype=float)
        if len(instance.rare_labels) != len(weights) or not np.isfinite(weights).all() or (weights < 0).any():
            raise ValueError("Invalid rare-class labels/weights")
        instance.rare_weights = weights / weights.sum() if weights.size and weights.sum() > 0 else np.array([])
        if instance.rare_labels and not instance.rare_weights.size:
            raise ValueError("Rare-class weights must have positive total mass")
        for label in instance.rare_labels:
            label_to_chord_symbol(label)
        instance.checkpoint_source = {"checkpoint_payload_sha256": hashlib.sha256(raw).hexdigest(),
                                      "source_revision": "747871ce68ebbd7b9febe42c08c020aa688cb432"}
        return instance

    @property
    def coarse_depth(self):
        return len(self.coarse_models["I"]) // 3

    @property
    def resolver_depth(self):
        return len(self.resolver_models["I"]) // 4

    def generate(self, bars, *, start="I", key="C major", seed=None):
        if type(bars) is not int or not 1 <= bars <= 128:
            raise ValueError("bars must be >= 1")
        if start not in COARSE or start == "OTHER":
            raise ValueError("start must be a concrete coarse chord")

        # Validate key immediately.
        label_to_chord_symbol(start, key)

        rng = np.random.default_rng(seed)
        current = start
        coarse = [start]
        resolved = [start]
        steps = []

        for n in range(1, bars):
            coarse_bits, nxt = _sample(self.coarse_models[current], 3, COARSE, rng)

            if nxt != "OTHER":
                concrete = nxt
                step = HarmonyStep(n, current, coarse_bits, nxt, resolved_label=concrete)
            else:
                resolver_bits, concrete = _sample(
                    self.resolver_models[current], 4, RESOLVER, rng
                )
                fallback = None

                if concrete == "RARE_OTHER":
                    if self.rare_labels and self.rare_weights.size:
                        concrete = str(rng.choice(self.rare_labels, p=self.rare_weights))
                        fallback = "classical POP909 rare-class frequency"
                    else:
                        concrete = "I"
                        fallback = "tonic fallback; rare table unavailable"

                step = HarmonyStep(
                    n, current, coarse_bits, nxt,
                    resolver_bits=resolver_bits,
                    resolved_label=concrete,
                    fallback=fallback,
                )

            coarse.append(nxt)
            resolved.append(concrete)
            steps.append(step)

            # Keep the coarse Markov state as OTHER after an OTHER event.
            current = nxt

        chords = [label_to_chord_symbol(x, key) for x in resolved]

        return QuantumHarmonyResult(
            key=key,
            coarse_sequence=coarse,
            resolved_sequence=resolved,
            chord_symbols=chords,
            steps=steps,
            source={
                **self.checkpoint_source,
                "model": "POP909 hierarchical PQC",
                "quantum_backend": "Qiskit Statevector simulator",
                "coarse_qubits": "3",
                "coarse_depth": str(self.coarse_depth),
                "resolver_qubits": "4",
                "resolver_depth": str(self.resolver_depth),
                "training_scope": "POP909 major-key sections",
                "rare_other_fallback": "classical" if self.rare_labels else "tonic",
            },
        )
