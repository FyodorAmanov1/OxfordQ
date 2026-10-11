from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

MAJOR_COARSE = ["I","ii","iii","IV","V","vi","vii°","OTHER"]
MAJOR_RESOLVER = [
    "V:sus","IV:min","II:dom","III:dom","bVII:maj","II:maj","V:dom","I:dom",
    "V:min","III:maj","bVI:maj","VI:maj","VI:dom","#IV:hdim","#IV:dim","RARE_OTHER"
]
MINOR_COARSE = ["i","III","iv","v","V","VI","VII","OTHER"]

p = argparse.ArgumentParser()
p.add_argument("--major-coarse", required=True, type=Path)
p.add_argument("--major-resolver", required=True, type=Path)
p.add_argument("--major-rare-csv", type=Path)
p.add_argument("--minor-coarse", required=True, type=Path)
p.add_argument("--minor-resolver", required=True, type=Path)
p.add_argument("--minor-rare-csv", required=True, type=Path)
p.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "models.json")
args = p.parse_args()

def load_npz(path, contexts, qubits):
    data = np.load(path)
    out = {}
    for i, context in enumerate(contexts):
        key = f"theta_{i}"
        if key not in data.files:
            raise SystemExit(f"{path} missing {key}")
        arr = np.asarray(data[key], dtype=float)
        if arr.ndim != 1 or len(arr) == 0 or len(arr) % qubits:
            raise SystemExit(f"Invalid {path}:{key} shape {arr.shape}")
        out[context] = arr.tolist()
    return out

def rare_table(path):
    if path is None or not path.is_file():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [], []
    label_column = "other_class" if "other_class" in rows[0] else "resolved_other"
    labels, weights = [], []
    for row in rows:
        if int(row["rank"]) <= 15:
            continue
        labels.append(row[label_column])
        weights.append(float(row["count"]))
    total = sum(weights)
    if total > 0:
        weights = [w / total for w in weights]
    return labels, weights

major_coarse = load_npz(args.major_coarse, MAJOR_COARSE, 3)
major_resolver = load_npz(args.major_resolver, MAJOR_COARSE, 4)
major_rare_labels, major_rare_weights = rare_table(args.major_rare_csv)

minor_coarse = load_npz(args.minor_coarse, MINOR_COARSE, 3)
minor_resolver = load_npz(args.minor_resolver, MINOR_COARSE, 4)
minor_npz = np.load(args.minor_resolver)
if "resolver_states" in minor_npz.files:
    minor_resolver_labels = [str(x) for x in minor_npz["resolver_states"].tolist()]
else:
    with args.minor_rare_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    minor_resolver_labels = [r["resolved_other"] for r in rows[:15]] + ["RARE_OTHER"]

minor_rare_labels, minor_rare_weights = rare_table(args.minor_rare_csv)

payload = {
    "schema_version": 3,
    "mode_order": ["major", "minor"],
    "modes": {
        "major": {
            "coarse_contexts": MAJOR_COARSE,
            "resolver_labels": MAJOR_RESOLVER,
            "coarse_theta": major_coarse,
            "resolver_theta": major_resolver,
            "rare_labels": major_rare_labels,
            "rare_weights": major_rare_weights,
            "source": {
                "coarse": args.major_coarse.name,
                "resolver": args.major_resolver.name,
                "rare_csv": args.major_rare_csv.name if args.major_rare_csv else None,
                "training_scope": "POP909 major-key sections",
            },
        },
        "minor": {
            "coarse_contexts": MINOR_COARSE,
            "resolver_labels": minor_resolver_labels,
            "coarse_theta": minor_coarse,
            "resolver_theta": minor_resolver,
            "rare_labels": minor_rare_labels,
            "rare_weights": minor_rare_weights,
            "source": {
                "coarse": args.minor_coarse.name,
                "resolver": args.minor_resolver.name,
                "rare_csv": args.minor_rare_csv.name,
                "training_scope": "POP909 minor-key sections",
            },
        },
    },
}

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("Wrote", args.output)
print("Major coarse depth:", len(major_coarse["I"]) // 3)
print("Major resolver depth:", len(major_resolver["I"]) // 4)
print("Minor coarse depth:", len(minor_coarse["i"]) // 3)
print("Minor resolver depth:", len(minor_resolver["i"]) // 4)
print("Major rare fallback labels:", len(major_rare_labels))
print("Minor rare fallback labels:", len(minor_rare_labels))
