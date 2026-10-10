"""Independent instrument generators feeding the existing arrangement pipeline.

Adapters own checkpoint loading, inference, quantum execution and token decoding.
The orchestrator sees only concert-pitch MIDI or beat-based note events.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path
from shutil import copy2
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, JsonValue, model_validator

from .instruments import profile
from .models import ArrangementResult, InputNote, Manifest, OrchestrationConfig, PartSpec, Role, Schema


class GenerationRequest(Schema):
    part_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    instrument: str
    bars: int = Field(ge=1)
    beats_per_bar: Literal[4] = 4
    tempo_bpm: float = Field(gt=0, le=400, allow_inf_nan=False)
    pitch_low: int = Field(ge=0, le=127)
    pitch_high: int = Field(ge=0, le=127)
    max_polyphony: int = Field(ge=1)
    seed: int | None = Field(default=None, ge=0)
    options: dict[str, JsonValue] = Field(default_factory=dict)

    @property
    def duration_beats(self) -> int:
        return self.bars * self.beats_per_bar


class GeneratedSequence(Schema):
    """Model output. MIDI paths are relative to the Python process, not the manifest."""

    notes: list[InputNote] | None = None
    path: Path | None = None
    midi_track: int | None = Field(default=None, ge=0)
    channel: int | None = Field(default=None, ge=0, le=15)
    tempo_bpm: float | None = Field(default=None, gt=0, le=400, allow_inf_nan=False)
    source: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def one_source(self):
        if (self.notes is None) == (self.path is None):
            raise ValueError("A generator must return exactly one of notes or path")
        if self.notes is not None and (self.midi_track is not None or self.channel is not None):
            raise ValueError("midi_track and channel apply only to MIDI output")
        return self


@runtime_checkable
class SequenceGenerator(Protocol):
    """Implement this method on any smaller classical or QML model adapter."""

    def generate(self, request: GenerationRequest) -> GeneratedSequence | Mapping: ...


class CallableGenerator:
    """Wrap an existing inference function after adding its note/MIDI decoder."""

    def __init__(self, generate: Callable[[GenerationRequest], GeneratedSequence | Mapping]):
        self._generate = generate

    def generate(self, request: GenerationRequest) -> GeneratedSequence | Mapping:
        return self._generate(request)


class GenerationJob(Schema):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    instrument: str
    model: str | None = Field(default=None, min_length=1)
    bars: int | None = Field(default=None, ge=1)
    tempo_bpm: float | None = Field(default=None, gt=0, le=400, allow_inf_nan=False)
    seed: int | None = Field(default=None, ge=0)
    role: Role | None = None
    options: dict[str, JsonValue] = Field(default_factory=dict)
    source: dict[str, str] = Field(default_factory=dict)


class GeneratorFactory(Schema):
    """An explicitly selected, trusted Python factory; instantiated once per run."""

    factory: str = Field(pattern=r"^[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*:[A-Za-z_][\w]*$")
    kwargs: dict[str, JsonValue] = Field(default_factory=dict)
    source: dict[str, str] = Field(default_factory=dict)


class GenerationManifest(Schema):
    lead_track: str
    models: dict[str, GeneratorFactory] = Field(default_factory=dict)
    routes: dict[str, str] = Field(default_factory=dict)
    jobs: list[GenerationJob] = Field(min_length=1)
    parts: list[PartSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_parts(self):
        _validate_parts(self.jobs, self.parts, self.lead_track)
        return self


@dataclass(frozen=True)
class _Registration:
    generator: SequenceGenerator
    source: dict[str, str]
    adapter: str


def _validate_parts(jobs, parts, lead_track):
    ids = [p.id for p in [*jobs, *parts]]
    if len(ids) != len(set(ids)):
        raise ValueError("Generated and supplied parts must have unique IDs")
    if lead_track not in ids:
        raise ValueError(f"Lead track {lead_track!r} is not among the parts")
    for part in [*jobs, *parts]:
        limits = profile(part.instrument)
        if part.id == lead_track and limits.family == "drums":
            raise ValueError("Unpitched percussion cannot be the lead")


def _retain_midi(path: Path, part_id: str, directory: Path | None) -> Path:
    path = path.resolve()
    if directory is None:
        return path
    directory.mkdir(parents=True, exist_ok=True)
    retained = (directory / f"{part_id}.mid").resolve()
    if retained != path:
        copy2(path, retained)
    return retained


class GenerationRegistry:
    """Named model instances plus default instrument routes; no automatic fallback.

    One instance can serve multiple section tracks. Generation is sequential so local
    device contexts and quantum clients need not support concurrent requests.
    """

    def __init__(self):
        self._models: dict[str, _Registration] = {}
        self._routes: dict[str, str] = {}

    def register(self, name: str, generator: SequenceGenerator, *,
                 instruments: Sequence[str] = (), source: dict[str, str] | None = None):
        if not name or name in self._models:
            raise ValueError(f"Model name must be nonempty and unique: {name!r}")
        if not callable(getattr(generator, "generate", None)):
            raise ValueError(f"Model {name!r} must implement generate(request)")
        metadata = dict(source or {})
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()):
            raise ValueError("Generator source metadata must contain string keys and values")
        for instrument in instruments:
            profile(instrument)
            if instrument in self._routes:
                raise ValueError(f"Instrument {instrument!r} already has a route; use route() to replace it")
        adapter_type = type(generator)
        self._models[name] = _Registration(
            generator, metadata, f"{adapter_type.__module__}:{adapter_type.__qualname__}")
        for instrument in instruments:
            self._routes[instrument] = name
        return self

    def route(self, instrument: str, model: str):
        profile(instrument)
        if model not in self._models:
            raise ValueError(f"Unknown generator model {model!r}")
        self._routes[instrument] = model
        return self

    def _select(self, job: GenerationJob) -> str:
        name = job.model if job.model is not None else self._routes.get(job.instrument)
        if name is None:
            raise ValueError(f"Part {job.id!r}: no model or route for {job.instrument!r}")
        if name not in self._models:
            raise ValueError(f"Part {job.id!r}: unknown generator model {name!r}")
        return name

    def generate_parts(self, jobs: Sequence[GenerationJob | dict], lead_track: str, *,
                       bars: int = 16, tempo_bpm: float = 96,
                       parts: Sequence[PartSpec | dict] = (),
                       retain_midi_dir: str | Path | None = None) -> Manifest:
        """Generate independent material, then return the arranger's normal input.

        All routes are checked before inference starts. There is no shared harmonic
        plan; adapter-specific conditioning may be passed explicitly in options.
        A seed is a request to the adapter, not a promise of hardware determinism.
        retain_midi_dir snapshots each MIDI immediately, allowing adapters to reuse
        temporary output filenames. Without it, returned files must remain stable.
        """
        jobs = [GenerationJob.model_validate(j) for j in jobs]
        existing = [PartSpec.model_validate(p).model_copy(deep=True) for p in parts]
        _validate_parts(jobs, existing, lead_track)
        for part in existing:
            if part.path is not None:
                part.path = part.path.resolve()
                if not part.path.is_file():
                    raise ValueError(f"Supplied part {part.id!r}: MIDI file does not exist")
        selected = [self._select(job) for job in jobs]
        requests = []
        for job in jobs:
            limits = profile(job.instrument)
            requests.append(GenerationRequest(
                part_id=job.id, instrument=job.instrument,
                bars=job.bars if job.bars is not None else bars,
                tempo_bpm=job.tempo_bpm if job.tempo_bpm is not None else tempo_bpm,
                pitch_low=limits.low, pitch_high=limits.high, max_polyphony=limits.polyphony,
                seed=job.seed, options=job.model_copy(deep=True).options))
        retained_directory = Path(retain_midi_dir).resolve() if retain_midi_dir is not None else None
        for part in existing:
            if part.path is not None:
                part.path = _retain_midi(part.path, part.id, retained_directory)
        generated = []
        for job, name, request in zip(jobs, selected, requests):
            entry = self._models[name]
            try:
                raw = entry.generator.generate(request.model_copy(deep=True))
                # Revalidate even returned model instances to catch unchecked model_construct outputs.
                output = GeneratedSequence.model_validate(
                    raw.model_dump() if isinstance(raw, GeneratedSequence) else raw)
                payload = output.model_dump()
                if output.path is not None:
                    path = output.path.resolve()
                    if not path.is_file():
                        raise ValueError("Generated MIDI path does not name an existing file")
                    payload["path"] = _retain_midi(path, job.id, retained_directory)
                else:
                    # For inline events, tempo is a playback hint. MIDI retains its own tempo.
                    payload["tempo_bpm"] = output.tempo_bpm or request.tempo_bpm
                metadata = {**output.source, **job.source, **entry.source,
                            "generator": name, "generator_adapter": entry.adapter,
                            "generation_bars": str(request.bars),
                            "generation_tempo_bpm": str(request.tempo_bpm)}
                if request.seed is not None:
                    metadata["generation_seed"] = str(request.seed)
                payload["source"] = metadata
                part = PartSpec(id=job.id, instrument=job.instrument, role=job.role, **payload)
            except Exception as exc:
                # Do not expose options, factory kwargs, credentials or raw SDK errors.
                raise ValueError(
                    f"Generation failed for part {job.id!r}, model {name!r} "
                    f"({type(exc).__name__}); inspect the adapter's local diagnostics") from exc
            generated.append(part)
        return Manifest(parts=[*generated, *existing], lead_track=lead_track)


def load_generation_manifest(path: str | Path) -> GenerationManifest:
    path = Path(path).resolve()
    manifest = GenerationManifest.model_validate_json(path.read_text(encoding="utf-8"))
    for part in manifest.parts:
        if part.path is not None:
            part.path = (path.parent / part.path).resolve()
    return manifest


def registry_from_manifest(manifest: GenerationManifest) -> GenerationRegistry:
    """Import trusted factories. kwargs paths stay exactly as provided (cwd-relative).

    Credentials should be obtained by adapters from their environment, not JSON.
    Factories return SequenceGenerator objects and own their resource lifecycle.
    """
    # Check every reference before loading checkpoints or initiating remote work.
    for job in manifest.jobs:
        name = job.model if job.model is not None else manifest.routes.get(job.instrument)
        if name is None or name not in manifest.models:
            raise ValueError(f"Part {job.id!r}: missing generator definition for {name!r}")
    for instrument, name in manifest.routes.items():
        profile(instrument)
        if name not in manifest.models:
            raise ValueError(f"Route {instrument!r}: unknown generator {name!r}")
    registry = GenerationRegistry()
    used = {job.model if job.model is not None else manifest.routes[job.instrument]
            for job in manifest.jobs}
    for name, spec in manifest.models.items():
        if name not in used:
            continue
        try:
            module, attribute = spec.factory.split(":")
            factory = getattr(import_module(module), attribute)
            registry.register(name, factory(**spec.kwargs), source=spec.source)
        except Exception as exc:
            raise ValueError(f"Could not load generator {name!r} from {spec.factory!r} "
                             f"({type(exc).__name__}); inspect the adapter's local diagnostics") from exc
    for instrument, name in manifest.routes.items():
        if name in used:
            registry.route(instrument, name)
    return registry


def orchestrate_generated(jobs: Sequence[GenerationJob | dict], lead_track: str,
                         registry: GenerationRegistry,
                         config: OrchestrationConfig | dict | None = None, *,
                         parts: Sequence[PartSpec | dict] = (), provider=None) -> ArrangementResult:
    """Generate with distinct models, then reconcile using Gemini or local rules.

    Generation covers the excerpt start plus its length unless a job overrides bars.
    The persisted input can be replayed with --manifest without rerunning generators.
    """
    from .pipeline import orchestrate

    config = config if isinstance(config, OrchestrationConfig) else OrchestrationConfig.model_validate(config or {})
    destination = config.output_dir.resolve() if config.output_dir is not None else None
    manifest = registry.generate_parts(
        jobs, lead_track, bars=config.start_bar + config.bars,
        tempo_bpm=config.tempo_bpm or 96, parts=parts,
        retain_midi_dir=destination / "input_midi" if destination is not None else None)
    manifest_path = None
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=True)
        manifest_path = destination / "generated_parts.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    result = orchestrate(manifest.parts, manifest.lead_track, config, provider=provider)
    if manifest_path is not None:
        result.artifacts["generated_parts_json"] = str(manifest_path)
        result.report["artifacts"] = result.artifacts
        Path(result.artifacts["report_json"]).write_text(
            json.dumps(result.report, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
