"""Arrange independent quantum-generated instrument parts."""
from .midi_io import load_manifest
from .models import ArrangementResult, InputNote, Manifest, OrchestrationConfig, PartSpec
from .pipeline import orchestrate
from .generation import (
    CallableGenerator, GeneratedSequence, GenerationJob, GenerationManifest,
    GenerationRegistry, GenerationRequest, GeneratorFactory, SequenceGenerator,
    load_generation_manifest, orchestrate_generated, registry_from_manifest,
)

__all__ = [
    "orchestrate", "load_manifest", "OrchestrationConfig", "ArrangementResult",
    "PartSpec", "InputNote", "Manifest", "CallableGenerator", "GeneratedSequence",
    "GenerationJob", "GenerationManifest", "GenerationRegistry", "GenerationRequest",
    "GeneratorFactory", "SequenceGenerator", "load_generation_manifest",
    "orchestrate_generated", "registry_from_manifest",
]
