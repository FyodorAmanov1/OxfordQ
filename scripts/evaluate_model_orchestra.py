"""Evaluate local model variants using symbolic metrics, without API or QPU calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics

from quantum_models.orchestra import main as generate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("output-model-evaluation"))
    parser.add_argument("--bars", type=int, default=16)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--keys", nargs="+", default=["C major", "E- major", "A minor"])
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if out.exists():
        parser.error("Choose a fresh --out to preserve previous evaluations")
    out.mkdir(parents=True)
    runs = []
    for key_index, key in enumerate(args.keys):
        for seed in args.seeds:
            directory = out / f"key-{key_index}-seed-{seed}"
            harmony = "infer" if key.lower().endswith("minor") else "pop909"
            code = generate(["--bars", str(args.bars), "--seed", str(seed), "--key", key,
                             "--harmony", harmony, "--no-audio", "--out", str(directory)])
            if code:
                raise RuntimeError(f"Model generation failed for {key}, seed {seed}")
            report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
            runs.append({"key": key, "seed": seed, "harmony": harmony,
                         "directory": directory.relative_to(out).as_posix(),
                         "lead_preserved": report["lead_preserved"],
                         "hard_validation_errors": report["hard_validation_errors"],
                         "warnings": report["warnings"], "metrics": report["metrics"]})
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Seed/key robustness checks for frozen shared checkpoints and classical decoding; not a listening study or held-out model evaluation",
        "bars": args.bars, "runs": runs,
        "all_leads_preserved": all(r["lead_preserved"] for r in runs),
        "hard_validation_error_count": sum(len(r["hard_validation_errors"]) for r in runs),
        "warning_count": sum(len(r["warnings"]) for r in runs),
        "mean_heuristic_improvement": statistics.mean(
            r["metrics"]["arrangement"]["heuristic_score"] -
            r["metrics"]["original"]["heuristic_score"] for r in runs),
        "physical_execution": False, "api_calls": 0, "training_performed": False,
    }
    (out / "evaluation.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "runs"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
