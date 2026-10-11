"""Source-preserving composition, independent of the legacy arrangement policy."""
from .models import CompositionRequest, CompositionPlan, ComposedScore, MusicalTimeline
from .pipeline import compose, CompositionResult
from .sources import generate_source_bank

__all__ = ["CompositionRequest", "CompositionPlan", "ComposedScore", "MusicalTimeline",
           "CompositionResult", "compose", "generate_source_bank"]
