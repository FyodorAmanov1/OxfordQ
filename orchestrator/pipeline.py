"""Public orchestration interface and artifact/report lifecycle."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .audio import render_comparisons
from .baseline import arrange_baseline
from .gemini import GeminiProvider, safe_error
from .instruments import profile
from .midi_io import export_midi, import_parts
from .models import ArrangementPlan, ArrangementResult, EditProposal, OrchestrationConfig, PartSpec
from .theory import baseline_plan, musical_metrics, musical_warnings
from .validation import apply_proposal, validate_plan, validate_score


def _track_summaries(score):
    return [{"id": p.id, "instrument": p.instrument, "role": p.role, "note_count": len(p.notes),
             "pitch_range": [min(n.pitch for n in p.notes), max(n.pitch for n in p.notes)] if p.notes else None,
             "pitch_classes": sorted({n.pitch % 12 for n in p.notes}),
             "instrument_profile": vars(profile(p.instrument))} for p in score.parts]


def _request_validated(provider, schema, payload, check, config, log):
    feedback = []
    for attempt in range(config.max_corrections + 1):
        try:
            response = provider.request(schema, payload, feedback)
            if not isinstance(response, schema):
                response = schema.model_validate(response)
            check(response)
            log.append({"schema": schema.__name__, "attempt": attempt + 1, "status": "accepted"})
            return response
        except Exception as exc:
            message = safe_error(exc)
            log.append({"schema": schema.__name__, "attempt": attempt + 1, "status": "rejected", "error": message})
            feedback = [message]
    return None


def _note_changes(original, score):
    changes = []
    for part in score.parts:
        source = {n.id: n for n in original.part(part.id).notes}
        for n in part.notes:
            old = source[n.id]
            fields = {name: {"before": getattr(old, name), "after": getattr(n, name)}
                      for name in ("pitch", "onset_tick", "duration_ticks", "velocity", "muted", "transpose", "phrase_shift")
                      if getattr(old, name) != getattr(n, name)}
            if fields:
                changes.append({"source_id": n.source_id, "track_id": part.id, "phrase_id": n.phrase_id, "changes": fields})
    return changes


def orchestrate(parts: list[PartSpec] | list[dict], lead_track: str,
                config: OrchestrationConfig | dict | None = None, *, provider=None) -> ArrangementResult:
    """Arrange supplied parts. Provider injection supports offline integration tests.

    File-based inputs use paths supplied by the caller; load_manifest resolves paths
    relative to a manifest. output_dir=None returns in-memory results only.
    """
    config = config if isinstance(config, OrchestrationConfig) else OrchestrationConfig.model_validate(config or {})
    parts = [p if isinstance(p, PartSpec) else PartSpec.model_validate(p) for p in parts]
    original, warnings = import_parts(parts, lead_track, config)
    local_plan = baseline_plan(original, config)
    plan_errors = validate_plan(local_plan, original, config)
    if plan_errors:
        raise ValueError("; ".join(plan_errors))
    baseline = arrange_baseline(original, local_plan, config)
    plan, score = local_plan, baseline.model_copy(deep=True)
    request_log, window_log = [], []
    provider_state = "disabled" if config.backend == "rules" else "active"
    owned_provider = False
    if config.backend == "gemini" and provider is None:
        try:
            provider = GeminiProvider(config)
            owned_provider = True
        except Exception as exc:
            provider_state = "unavailable"
            warnings.append("Gemini unavailable; using local baseline. " + safe_error(exc))
    try:
        if config.backend == "gemini" and provider is not None:
            payload = {
                "task": "Produce a complete arrangement plan. Chords and directives must cover the entire excerpt exactly once. Keep configured overrides.",
                "ppq": original.ppq, "bars": original.bars, "metre": "4/4", "tempo_bpm": original.tempo_bpm,
                "lead_track": lead_track, "tracks": _track_summaries(original),
                "lead_notes": [n.model_dump() for n in original.part(lead_track).notes],
                "baseline_plan": local_plan.model_dump(), "key_override": config.key, "chord_override": config.chords,
            }
            def check_plan(candidate):
                errors = validate_plan(candidate, original, config)
                if errors:
                    raise ValueError("; ".join(errors[:12]))
                arrange_baseline(original, candidate, config)
            proposed = _request_validated(provider, ArrangementPlan, payload, check_plan, config, request_log)
            if proposed is None:
                provider_state = "degraded"
                warnings.append("Gemini global plan failed validation; retained the local baseline")
            else:
                plan = proposed
                score = arrange_baseline(original, plan, config)

            source_notes = {n.id: n for p in original.parts for n in p.notes}
            for start_bar in range(0, config.bars, config.window_bars):
                end_bar = min(config.bars, start_bar + config.window_bars)
                left, right = start_bar * config.bar_ticks, end_bar * config.bar_ticks
                context_left = max(0, left - config.bar_ticks)
                budgets = defaultdict(lambda: {"note_count": 0, "individual_changes": 0})
                window_parts = []
                for part in score.parts:
                    notes = []
                    for n in part.notes:
                        ref = source_notes[n.id]
                        if (n.onset_tick < right and n.end_tick > context_left) or left <= ref.onset_tick < right:
                            item = n.model_dump()
                            item.update({"editable": left <= ref.onset_tick < right and part.id != lead_track,
                                         "source_pitch": ref.pitch, "source_duration_ticks": ref.duration_ticks,
                                         "source_onset_tick": ref.onset_tick})
                            notes.append(item)
                        if left <= ref.onset_tick < right:
                            budgets[n.phrase_id]["note_count"] += 1
                            budgets[n.phrase_id]["individual_changes"] += int(
                                n.pitch != ref.pitch + n.transpose or n.duration_ticks != ref.duration_ticks)
                    window_parts.append({"track_id": part.id, "instrument": part.instrument, "notes": notes})
                payload = {
                    "task": "Improve this window using source-referenced edits only. The preceding bar is read-only. Keep the lead's notes intact.",
                    "plan": plan.model_dump(), "ppq": config.ppq, "window_start_tick": left, "window_end_tick": right,
                    "tracks": window_parts, "lead_track": lead_track, "phrase_budgets": dict(budgets),
                    "edit_budget_fraction": config.edit_budget,
                    "constraints": {
                        "individual_pitch_repair_semitones": 2, "duration_factor": [0.5, 2.0],
                        "whole_phrase_shift_max_ticks": config.bar_ticks, "whole_phrase_transpose_semitones": [-48, 48],
                        "set_velocity_target": "track identifier; affects source-onsets in this window",
                        "set_pan_target": "track identifier", "other_edit_targets": "supplied note or phrase identifiers",
                        "muting": "explicit; cannot mute the lead", "new_notes": "forbidden"},
                }
                def check_edits(proposal):
                    apply_proposal(score, proposal, original, config, left, right)
                proposal = _request_validated(provider, EditProposal, payload, check_edits, config, request_log)
                if proposal is None:
                    provider_state = "degraded"
                    warnings.append(f"Bars {start_bar+1}–{end_bar}: Gemini edits failed; retained the validated arrangement")
                    window_log.append({"start_bar": start_bar, "end_bar": end_bar, "status": "unrepaired"})
                    continue
                candidate = apply_proposal(score, proposal, original, config, left, right)
                before = musical_metrics(score, plan, original)["heuristic_score"]
                after = musical_metrics(candidate, plan, original)["heuristic_score"]
                accepted = after >= before - 0.005
                if accepted:
                    score = candidate
                window_log.append({"start_bar": start_bar, "end_bar": end_bar,
                                   "status": "accepted" if accepted else "retained_previous",
                                   "heuristic_before": before, "heuristic_candidate": after,
                                   "proposal": proposal.model_dump()})
    finally:
        if owned_provider:
            provider.close()

    errors = validate_score(score, original, config)
    if errors:
        raise ValueError("Final validation failed: " + "; ".join(errors))
    warnings.extend(musical_warnings(score, original))
    report = {
        "version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "backend_requested": config.backend, "model": config.model if config.backend == "gemini" else None,
        "provider_status": provider_state, "status": "needs_review" if warnings else "structurally_valid",
        "lead_track": lead_track, "lead_preserved": True, "hard_validation_errors": [],
        "excerpt": {"start_bar": config.start_bar, "bars": config.bars, "metre": "4/4",
                    "ppq": config.ppq, "tempo_bpm": score.tempo_bpm},
        "warnings": warnings, "config": config.model_dump(mode="json"),
        "sources": {p.id: {"instrument": p.instrument, "metadata": p.source,
                           "source_tempo_bpm": p.source_tempo_bpm,
                           "path": str(parts[i].path) if parts[i].path else None} for i, p in enumerate(original.parts)},
        "metrics": {"original": musical_metrics(original, local_plan, original),
                    "baseline": musical_metrics(baseline, local_plan, original),
                    "arrangement": musical_metrics(score, plan, original)},
        "plans": {"baseline": local_plan.model_dump(), "arrangement": plan.model_dump()},
        "note_changes": _note_changes(original, score), "requests": request_log, "windows": window_log,
        "note_lineage": [{"output_id": n.id, "source_id": n.source_id, "track_id": p.id,
                          "muted": n.muted} for p in score.parts for n in p.notes],
        "audio": {"status": "not_requested"},
        "quality_assessment": "Hard checks ensure structural consistency. Musical quality and source recognisability require listening; metrics are heuristic.",
    }
    result = ArrangementResult(score=score, plan=plan, report=report)
    if config.output_dir is not None:
        destination = config.output_dir.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        midis = {}
        for name, music in (("original", original), ("baseline", baseline), ("arrangement", score)):
            path = destination / f"{name}.mid"
            export_midi(music, path)
            midis[name] = path
            result.artifacts[f"{name}_midi"] = str(path)
        for name, music in (("normalized_input", original), ("arrangement", score)):
            path = destination / f"{name}.json"
            path.write_text(music.model_dump_json(indent=2), encoding="utf-8")
            result.artifacts[name + "_json"] = str(path)
        if config.render_audio:
            audio_artifacts, audio_report = render_comparisons(midis, config,
                scores={"original": original, "baseline": baseline, "arrangement": score})
            result.artifacts.update(audio_artifacts)
            result.report["audio"] = audio_report
            if audio_report["status"] != "rendered":
                result.report["warnings"].append(audio_report["message"])
                result.report["status"] = "needs_review"
        report_path = destination / "report.json"
        result.artifacts["report_json"] = str(report_path)
        result.report["artifacts"] = result.artifacts
        report_path.write_text(json.dumps(result.report, indent=2, ensure_ascii=False), encoding="utf-8")
    return result
