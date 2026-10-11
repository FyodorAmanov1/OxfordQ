"""Generate adapted QCBM instrument parts and reconcile with POP909 harmony."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from orchestrator import GenerationJob, GenerationRegistry, OrchestrationConfig, orchestrate_generated
from orchestrator.instruments import profile
from .pop909_harmony import Pop909QuantumHarmony
from .qcbm_instrument import QCBMInstrumentGenerator


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instruments", nargs="+", default=["flute", "cello", "violin_1", "viola", "clarinet"])
    parser.add_argument("--lead", default="flute")
    parser.add_argument("--bars", type=int, default=16)
    parser.add_argument("--tempo", type=float, default=96)
    parser.add_argument("--key", default="C major")
    parser.add_argument("--harmony", choices=["pop909", "infer"], default="pop909")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--backend", choices=["rules", "gemini"], default="rules")
    parser.add_argument("--model")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--soundfont", type=Path)
    parser.add_argument("--fluidsynth")
    parser.add_argument("--out", type=Path, default=Path("output-model-orchestra"))
    parser.add_argument("--require-gemini", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = OrchestrationConfig(bars=args.bars, tempo_bpm=args.tempo, key=args.key,
            backend=args.backend, render_audio=not args.no_audio, output_dir=args.out,
            soundfont=args.soundfont, fluidsynth=args.fluidsynth,
            **({"model": args.model} if args.model else {}))
        if args.seed < 0 or len(set(args.instruments)) != len(args.instruments) or args.lead not in args.instruments:
            raise ValueError("Require a nonnegative seed, unique instruments and a selected lead")
        registry, jobs = GenerationRegistry(), []
        for index, instrument in enumerate(args.instruments):
            pr = profile(instrument)
            registry.register(f"qcbm-{instrument}", QCBMInstrumentGenerator(instrument),
                              instruments=[instrument])
            role = "melody" if instrument == args.lead else "bass" if instrument in {"cello", "double_bass", "tuba"} else "rhythm" if pr.family == "drums" else "harmony"
            jobs.append(GenerationJob(id=instrument, instrument=instrument, role=role,
                                      seed=args.seed + index * 101, options={"key": args.key}))
        harmony = None
        if args.harmony == "pop909":
            harmony = Pop909QuantumHarmony.from_json().generate(args.bars, key=args.key, seed=args.seed)
            config.chords = harmony.chord_symbols
        result = orchestrate_generated(jobs, args.lead, registry, config)
        if harmony is not None:
            path = args.out.resolve() / "quantum_harmony.json"
            path.write_text(json.dumps(harmony.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            result.artifacts["quantum_harmony_json"] = str(path)
            result.report["quantum_harmony"] = harmony.to_dict()
        result.report["generation_scope"] = {
            "motif_model": "Frozen 12-qubit QCBM; same checkpoint reused for all instruments",
            "instrument_adaptation": "Classical register, scale and phrasing decoder",
            "harmony_model": args.harmony, "physical_hardware_executed": False,
        }
        result.report["artifacts"] = result.artifacts
        Path(result.artifacts["report_json"]).write_text(
            json.dumps(result.report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"output": str(args.out.resolve()), "provider": result.report["provider_status"],
                          "warnings": result.report["warnings"]}, ensure_ascii=False))
        return 2 if args.require_gemini and result.report["provider_status"] != "active" else 0
    except (ValueError, OSError) as exc:
        print(f"Model orchestra failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
