"""Feed POP909 quantum harmony into the existing OxfordQ orchestrator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchestrator import OrchestrationConfig, load_manifest, orchestrate
from quantum_models import Pop909QuantumHarmony


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default="examples/parts.json")
    p.add_argument("--coarse-model", required=True)
    p.add_argument("--resolver-model", required=True)
    p.add_argument("--rare-csv", default=None)
    p.add_argument("--bars", type=int, default=16)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--key", default="C major")
    p.add_argument("--backend", choices=["rules", "gemini"], default="rules")
    p.add_argument("--out", default="output-quantum-harmony")
    p.add_argument("--no-audio", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    model = Pop909QuantumHarmony(
        args.coarse_model,
        args.resolver_model,
        args.rare_csv,
    )

    harmony = model.generate(
        args.bars,
        key=args.key,
        seed=args.seed,
    )

    print("=" * 72)
    print("POP909 QUANTUM HARMONY -> OXFORDQ")
    print("=" * 72)
    print("Resolved labels:")
    print(" -> ".join(harmony.resolved_sequence))
    print("\nChord symbols:")
    print(
        " -> ".join(
            symbol.replace("-", "b")
            for symbol in harmony.chord_symbols
        )
    )

    harmony_json = out / "quantum_harmony.json"
    harmony_json.write_text(
        json.dumps(harmony.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = load_manifest(args.manifest)

    config = OrchestrationConfig(
        bars=args.bars,
        key=args.key,
        chords=harmony.chord_symbols,
        backend=args.backend,
        render_audio=not args.no_audio,
        output_dir=out,
    )

    result = orchestrate(
        manifest.parts,
        manifest.lead_track,
        config,
    )

    result.report["quantum_harmony"] = harmony.to_dict()
    result.artifacts["quantum_harmony_json"] = str(harmony_json)
    result.report["artifacts"] = result.artifacts

    report_path = result.artifacts.get("report_json")
    if report_path:
        Path(report_path).write_text(
            json.dumps(result.report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print("\nSaved:", harmony_json)
    print("Status:", result.report["status"])


if __name__ == "__main__":
    main()
