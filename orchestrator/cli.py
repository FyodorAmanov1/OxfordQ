import argparse
import json
import sys
from pathlib import Path

from .generation import load_generation_manifest, orchestrate_generated, registry_from_manifest
from .midi_io import load_manifest
from .models import OrchestrationConfig
from .pipeline import orchestrate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate or import independent instrument parts, then orchestrate while protecting the main melody.")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--manifest", type=Path, help="Existing MIDI/note-event parts")
    inputs.add_argument("--generation-manifest", type=Path, help="Jobs and trusted Python factories for instrument-specific models")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--backend", choices=("gemini", "rules"))
    parser.add_argument("--model", help="Gemini arrangement model; sequence models are selected in the generation manifest")
    parser.add_argument("--lead-track")
    parser.add_argument("--bars", type=int)
    parser.add_argument("--start-bar", type=int)
    parser.add_argument("--key")
    parser.add_argument("--tempo", type=float)
    parser.add_argument("--soundfont", type=Path)
    parser.add_argument("--fluidsynth")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--require-gemini", action="store_true", help="Return nonzero if Gemini was unavailable or any window failed, while preserving fallback artifacts.")
    parser.add_argument("--require-audio", action="store_true", help="Return nonzero when audio rendering was requested but unavailable or failed.")
    args = parser.parse_args(argv)
    try:
        values = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
        if args.config and values.get("soundfont"):
            values["soundfont"] = args.config.resolve().parent / values["soundfont"]
        for arg_name, field in (("backend", "backend"), ("model", "model"), ("bars", "bars"),
                                ("start_bar", "start_bar"), ("key", "key"), ("tempo", "tempo_bpm"),
                                ("soundfont", "soundfont"), ("fluidsynth", "fluidsynth")):
            value = getattr(args, arg_name)
            if value is not None:
                values[field] = value
        values["output_dir"] = args.out
        if args.no_audio:
            values["render_audio"] = False
        config = OrchestrationConfig.model_validate(values)
        if args.generation_manifest:
            manifest = load_generation_manifest(args.generation_manifest)
            if args.lead_track:
                manifest.lead_track = args.lead_track
            registry = registry_from_manifest(manifest)
            result = orchestrate_generated(manifest.jobs, manifest.lead_track, registry,
                                           config, parts=manifest.parts)
        else:
            manifest = load_manifest(args.manifest)
            result = orchestrate(manifest.parts, args.lead_track or manifest.lead_track, config)
        print(f"Arrangement written to {args.out.resolve()}")
        print(f"Provider: {result.report['provider_status']}; audio: {result.report['audio']['status']}")
        for warning in result.report["warnings"]:
            print(f"Review: {warning}", file=sys.stderr)
        for name, path in result.artifacts.items():
            print(f"{name}: {path}")
        if args.require_gemini and result.report["provider_status"] != "active":
            return 2
        if args.require_audio and result.report["audio"]["status"] != "rendered":
            return 3
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Orchestration failed: {exc}", file=sys.stderr)
        return 1
