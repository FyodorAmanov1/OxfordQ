"""Source-preserving composition, independent of the legacy arrangement policy."""
from .models import CompositionRequest, CompositionPlan, ComposedScore, MusicalTimeline, PhraseMark
from .pipeline import compose, CompositionResult
from .sources import generate_source_bank
from .performer import PerformanceAdapter, PerformancePlan, PlayedNote, Control, RulePerformer

__all__ = ["CompositionRequest", "CompositionPlan", "ComposedScore", "MusicalTimeline",
           "CompositionResult", "compose", "generate_source_bank", "PhraseMark",
           "PerformanceAdapter", "PerformancePlan", "PlayedNote", "Control", "RulePerformer"]
