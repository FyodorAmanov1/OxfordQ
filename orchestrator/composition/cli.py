"""Generate expressive source-preserving studies without training new models."""
import argparse
import json
from pathlib import Path
from orchestrator.gemini import safe_error
from orchestrator.models import OrchestrationConfig
from .models import CompositionRequest, SourceBank
from .pipeline import compose
from .listening import write_collection_page


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=["bach", "mozart", "debussy", "rachmaninoff", "all"], default="mozart")
    parser.add_argument("--planner", choices=["local", "gemini"], default="local")
    parser.add_argument("--compare", action="store_true", help="Attempt Gemini as well; unavailability is explicit")
    parser.add_argument("--live-gemini", action="store_true", help="Explicitly enable external Gemini calls (sends source material; may incur charges)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bars", type=int, help="Override style defaults (roughly one minute)")
    parser.add_argument("--key")
    parser.add_argument("--model", default="gemini-3.8-flash")
    parser.add_argument("--instruments", nargs="+", default=["flute", "clarinet", "violin_1", "cello", "double_bass"])
    parser.add_argument("--lead", default="flute")
    parser.add_argument("--part-volume", action="append", default=[], metavar="INSTRUMENT=LEVEL",
                        help="Per-instrument volume from 0 to 1; repeat for multiple instruments")
    parser.add_argument("--out", type=Path, default=Path("output-composition"))
    parser.add_argument("--source-bank", type=Path, help="Reuse a source bank from earlier inference or a custom registry")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--fluidsynth")
    parser.add_argument("--soundfont", type=Path)
    parser.add_argument("--renderer", choices=["sfizz", "soundfont"], default="sfizz")
    parser.add_argument("--sample-library", type=Path, help="VSCO SFZ patch directory")
    parser.add_argument("--sfizz-library", type=Path, help="sfizz shared library (.dll/.so/.dylib)")
    parser.add_argument("--expression-strength", type=float, default=.6, help="Phrase performance strength, 0 to 1")
    parser.add_argument("--reverb-wet", type=float, default=.14, help="Shared acoustic room amount, 0 to .5")
    args = parser.parse_args(argv)
    if args.no_audio and args.require_audio:
        parser.error("--no-audio conflicts with --require-audio")
    if args.style == "all" and (args.key or args.source_bank):
        parser.error("Use a single style with a custom key/source bank")
    if args.out.exists():
        parser.error("Choose a fresh --out; existing pieces are preserved")
    styles = ["bach", "mozart", "debussy", "rachmaninoff"] if args.style == "all" else [args.style]
    try:
        volumes = {}
        for item in args.part_volume:
            name, value = item.split("=", 1)
            if name in volumes:
                raise ValueError("Duplicate part volume " + name)
            volumes[name] = float(value)
        bank = SourceBank.model_validate_json(args.source_bank.read_text(encoding="utf-8")) if args.source_bank else None
        audio = OrchestrationConfig(fluidsynth=args.fluidsynth, soundfont=args.soundfont,
            audio_renderer=args.renderer, sample_library=args.sample_library, sfizz_library=args.sfizz_library,
            expression_strength=args.expression_strength, reverb_wet=args.reverb_wet)
        studies, status = [], 0
        for index, style in enumerate(styles):
            name = f"piece{index + 1}"
            out = args.out / name if args.style == "all" else args.out
            bars = args.bars if args.bars is not None else {"bach": 24, "mozart": 36, "debussy": 18, "rachmaninoff": 18}[style]
            request = CompositionRequest(style=style, seed=args.seed + index * 101, bars=bars,
                instruments=args.instruments, lead_track=args.lead, key=args.key,
                planner=args.planner, compare=args.compare, model=args.model)
            request.part_volumes = volumes
            result = compose(request, bank=bank, output_dir=out, render_audio=not args.no_audio,
                             audio_config=audio, allow_live_api=args.live_gemini)
            print(json.dumps({"piece": name, "style": style, "output": str(out.resolve()),
                "status": result.report["status"], "gemini": result.report["gemini"]["status"],
                "audio": result.report["audio"]["status"]}))
            if result.report["status"] != "completed":
                status = max(status, 2)
            if args.require_audio and result.report["audio"]["status"] != "rendered":
                status = max(status, 3)
            studies.append((name, style))
        if args.style == "all":
            write_collection_page(args.out, studies)
        return status
    except Exception as exc:
        print(safe_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
